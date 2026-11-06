"""Single resident worker owns model weights; run more only with measured RAM budget."""

import json
import threading
import time
from redis import Redis
from .config import get_settings
from .jobs import JobRunner, QUEUE
from .models import Registry, ModelError
from .telemetry import Telemetry


def main():
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    registry = Registry(settings)
    runner = JobRunner(settings, registry)
    telemetry = Telemetry(settings)

    def sample():
        while True:
            try:
                client.setex(
                    "avrt:worker:metrics",
                    max(5, settings.telemetry_sample_ms // 1000 * 3),
                    json.dumps(telemetry.sample()),
                )
                client.setex("avrt:worker:models", 60, json.dumps(registry.describe()))
            except Exception:
                pass
            time.sleep(settings.telemetry_sample_ms / 1000)

    threading.Thread(target=sample, daemon=True).start()
    while True:
        item = client.blpop(QUEUE, timeout=5)
        if not item:
            continue
        ident = item[1]
        payload = client.getdel("avrt:payload:" + ident)
        if not payload:
            continue
        request = json.loads(payload)
        if time.time() > request["deadline"] or client.exists("avrt:cancel:" + ident):
            continue
        try:
            result = runner.execute(request["job"])
        except ModelError as e:
            result = {"error": str(e)}
        except Exception as e:
            result = {
                "error": f"Inference thất bại ({type(e).__name__}); xem cấu hình adapter."
            }
        client.setex(
            "avrt:result:" + ident, settings.job_result_ttl_s, json.dumps(result)
        )


if __name__ == "__main__":
    main()
