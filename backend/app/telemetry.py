import time
try:
    import psutil
except ImportError:
    psutil = None

def snapshot():
    data = {"cpu_percent": psutil.cpu_percent(interval=None) if psutil else None, "ram_percent": psutil.virtual_memory().percent if psutil else None, "gpu": None}
    try:
        import torch
        if torch.cuda.is_available():
            data["gpu"] = {"name": torch.cuda.get_device_name(0), "allocated_mb": round(torch.cuda.memory_allocated(0) / 1048576, 2), "reserved_mb": round(torch.cuda.memory_reserved(0) / 1048576, 2)}
    except Exception:
        pass
    return data

class Timer:
    def __enter__(self):
        self.started = time.perf_counter(); self.before = snapshot(); return self
    def __exit__(self, *_):
        self.elapsed_ms = round((time.perf_counter() - self.started) * 1000, 2); self.after = snapshot()
