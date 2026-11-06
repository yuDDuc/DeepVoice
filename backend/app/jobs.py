import asyncio
import json
import secrets
import time
from redis import Redis
from .models import ModelError, infer

QUEUE = "avrt:jobs"


class JobRunner:
    def __init__(self, settings, registry):
        self.settings = settings
        self.registry = registry
        self.redis = (
            Redis.from_url(settings.redis_url, decode_responses=True)
            if settings.inference_mode == "redis"
            else None
        )
        self.lock = asyncio.Lock()

    async def run(self, job):
        if not self.redis:
            async with self.lock:
                return await asyncio.to_thread(self.execute, job)
        ident = secrets.token_hex(16)
        # Atomic bounded enqueue; no unbounded audio jobs in Redis.
        script = "if redis.call('LLEN', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end; redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]); redis.call('RPUSH', KEYS[1], ARGV[4]); return 1"
        payload = json.dumps(
            {
                "id": ident,
                "deadline": time.time() + self.settings.job_timeout_s,
                "job": job,
            }
        )
        queued = await asyncio.to_thread(
            self.redis.eval,
            script,
            2,
            QUEUE,
            "avrt:payload:" + ident,
            self.settings.queue_max_jobs,
            payload,
            self.settings.job_timeout_s,
            ident,
        )
        if not queued:
            raise ModelError("Hàng đợi inference đầy, vui lòng thử lại.")
        start = time.monotonic()
        try:
            while time.monotonic() - start < self.settings.job_timeout_s:
                result = await asyncio.to_thread(self.redis.get, "avrt:result:" + ident)
                if result:
                    await asyncio.to_thread(self.redis.delete, "avrt:result:" + ident)
                    data = json.loads(result)
                    if "error" in data:
                        raise ModelError(data["error"])
                    return data
                await asyncio.sleep(0.1)
            raise ModelError(
                "Worker timeout; kiểm tra worker, HF download và JOB_TIMEOUT_S."
            )
        except asyncio.CancelledError:
            await asyncio.to_thread(
                self.redis.setex,
                "avrt:cancel:" + ident,
                self.settings.job_result_ttl_s,
                "1",
            )
            raise
        finally:
            # The list holds IDs only; private payloads expire even if no worker is running.
            await asyncio.to_thread(self.redis.delete, "avrt:payload:" + ident)
            await asyncio.to_thread(self.redis.lrem, QUEUE, 1, ident)

    def execute(self, job):
        if job.get("action") == "registry":
            return {"models": self.registry.describe()}
        if job.get("action") == "warmup":
            self.registry.load(job["role"])
            return {"models": self.registry.describe()}
        return infer(self.settings, self.registry, job)
