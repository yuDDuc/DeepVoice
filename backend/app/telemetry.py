import os
import sys
from pathlib import Path
from collections import deque
from datetime import datetime, timezone
import psutil


class Telemetry:
    def __init__(self, settings):
        self.settings = settings
        try:
            self.process = psutil.Process()
            # Some managed runtimes expose a different PID namespace through /proc.
            # Never label another executable as our own process.
            if Path(self.process.exe()).resolve() != Path(sys.executable).resolve():
                self.process = None
        except psutil.Error:
            self.process = None
        self.samples = deque(
            maxlen=max(
                1, settings.telemetry_window_s * 1000 // settings.telemetry_sample_ms
            )
        )
        self.latest = None
        self.nvml = None
        psutil.cpu_percent(None)
        if self.process:
            self.process.cpu_percent(None)
        if settings.nvml_enabled:
            try:
                import pynvml

                pynvml.nvmlInit()
                self.nvml = pynvml
            except Exception:
                pass

    def sample(self):
        gpu = []
        if self.nvml:
            try:
                for i in range(self.nvml.nvmlDeviceGetCount()):
                    h = self.nvml.nvmlDeviceGetHandleByIndex(i)
                    m = self.nvml.nvmlDeviceGetMemoryInfo(h)
                    gpu.append(
                        {
                            "index": i,
                            "name": self.nvml.nvmlDeviceGetName(h),
                            "util_percent": self.nvml.nvmlDeviceGetUtilizationRates(
                                h
                            ).gpu,
                            "vram_used_mb": round(m.used / 2**20, 1),
                            "vram_total_mb": round(m.total / 2**20, 1),
                            "scope": "whole_device",
                        }
                    )
            except Exception:
                gpu = []
        ram = psutil.virtual_memory()
        process_cpu = None
        process_rss = None
        if self.process:
            try:
                process_cpu = self.process.cpu_percent(None)
                process_rss = round(self.process.memory_info().rss / 2**20, 1)
            except psutil.Error:
                self.process = None
        result = {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source": "local_psutil_nvml",
            "sample_window_ms": self.settings.telemetry_sample_ms,
            "cpu_percent": psutil.cpu_percent(None),
            "process_cpu_percent": process_cpu,
            "process_rss_mb": process_rss,
            "ram_used_mb": round(ram.used / 2**20, 1),
            "ram_total_mb": round(ram.total / 2**20, 1),
            "gpu": gpu,
            "remote_gpu": None,
            "gpu_unavailable_reason": None if gpu else "NVML/GPU không khả dụng",
            "pid": os.getpid(),
        }
        self.samples.append(result)
        self.latest = result
        return result
