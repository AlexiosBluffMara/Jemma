"""
Jemma SafeBrain — Safety Watchdog & GPU Monitor

Monitors GPU temperature, VRAM usage, system health during overnight runs.
Provides automatic throttling, cooldown, and crash recovery.
Designed to protect the RTX 5090 during multi-hour autonomous training.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

log = logging.getLogger("watchdog")

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
GPU_TEMP_WARNING = 80       # °C — start logging warnings
GPU_TEMP_THROTTLE = 85      # °C — pause training, reduce batch size
GPU_TEMP_EMERGENCY = 90     # °C — full stop, cooldown period
VRAM_USAGE_WARNING = 0.90   # 90% — log warning
VRAM_USAGE_CRITICAL = 0.95  # 95% — trigger GC + cache clear
COOLDOWN_SECONDS = 60       # seconds to wait after emergency
MONITOR_INTERVAL = 10       # seconds between health checks
DISK_MIN_GB = 5             # minimum free disk space


@dataclass
class GPUStatus:
    timestamp: str
    gpu_name: str = ""
    temperature_c: int = 0
    fan_speed_pct: int = 0
    power_draw_w: float = 0
    power_limit_w: float = 0
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    vram_utilization: float = 0
    gpu_utilization: int = 0
    status: str = "unknown"  # ok, warning, throttle, emergency


class HealthAlert:
    """Thread-safe alert state management."""
    def __init__(self):
        self._lock = threading.Lock()
        self._paused = False
        self._stop = False
        self._throttle_factor = 1.0  # 1.0 = full speed, 0.5 = half batch
        self._alerts = []

    @property
    def paused(self):
        with self._lock:
            return self._paused

    @paused.setter
    def paused(self, v):
        with self._lock:
            self._paused = v

    @property
    def should_stop(self):
        with self._lock:
            return self._stop

    @should_stop.setter
    def should_stop(self, v):
        with self._lock:
            self._stop = v

    @property
    def throttle_factor(self):
        with self._lock:
            return self._throttle_factor

    @throttle_factor.setter
    def throttle_factor(self, v):
        with self._lock:
            self._throttle_factor = max(0.25, min(1.0, v))

    def add_alert(self, msg: str):
        with self._lock:
            self._alerts.append((datetime.utcnow().isoformat(), msg))
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-500:]

    def get_alerts(self, n: int = 20):
        with self._lock:
            return list(self._alerts[-n:])


# Global health state
health = HealthAlert()


# ---------------------------------------------------------------------------
# GPU queries via nvidia-smi
# ---------------------------------------------------------------------------
def query_gpu() -> GPUStatus:
    """Query GPU status via nvidia-smi."""
    status = GPUStatus(timestamp=datetime.utcnow().isoformat())
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,fan.speed,power.draw,power.limit,"
                "memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            status.status = "nvidia-smi-error"
            return status

        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) >= 8:
            status.gpu_name = parts[0]
            status.temperature_c = int(parts[1])
            try:
                status.fan_speed_pct = int(parts[2])
            except ValueError:
                status.fan_speed_pct = 0
            status.power_draw_w = float(parts[3])
            status.power_limit_w = float(parts[4])
            status.vram_used_mb = int(parts[5])
            status.vram_total_mb = int(parts[6])
            status.gpu_utilization = int(parts[7])

            if status.vram_total_mb > 0:
                status.vram_utilization = status.vram_used_mb / status.vram_total_mb

            # Determine status
            if status.temperature_c >= GPU_TEMP_EMERGENCY:
                status.status = "emergency"
            elif status.temperature_c >= GPU_TEMP_THROTTLE:
                status.status = "throttle"
            elif (status.temperature_c >= GPU_TEMP_WARNING or
                  status.vram_utilization >= VRAM_USAGE_WARNING):
                status.status = "warning"
            else:
                status.status = "ok"
    except FileNotFoundError:
        status.status = "no-nvidia-smi"
    except Exception as e:
        status.status = f"error: {e}"

    return status


def check_disk_space(path: str = ".") -> float:
    """Return free disk space in GB."""
    import shutil
    total, used, free = shutil.disk_usage(path)
    return free / (1024 ** 3)


def clear_gpu_cache():
    """Attempt to clear PyTorch GPU cache."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            log.info("GPU cache cleared")
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Monitor loop
# ---------------------------------------------------------------------------
def monitor_loop(interval: int = MONITOR_INTERVAL, log_file: Path = None):
    """Background monitoring — runs in a separate thread."""
    if log_file is None:
        log_file = LOGS_DIR / "gpu_health.jsonl"

    log.info(f"Watchdog started (interval={interval}s, thresholds={GPU_TEMP_WARNING}/"
             f"{GPU_TEMP_THROTTLE}/{GPU_TEMP_EMERGENCY}°C)")

    while not health.should_stop:
        try:
            status = query_gpu()

            # Log to JSONL
            with open(log_file, "a") as f:
                f.write(json.dumps(asdict(status)) + "\n")

            # React to status
            if status.status == "emergency":
                health.paused = True
                health.throttle_factor = 0.25
                msg = (f"EMERGENCY: GPU at {status.temperature_c}°C! "
                       f"Pausing for {COOLDOWN_SECONDS}s cooldown")
                log.critical(msg)
                health.add_alert(msg)
                clear_gpu_cache()
                # Wait for cooldown
                for _ in range(COOLDOWN_SECONDS):
                    if health.should_stop:
                        return
                    time.sleep(1)
                health.paused = False
                health.throttle_factor = 0.5  # resume at half speed

            elif status.status == "throttle":
                health.throttle_factor = 0.5
                msg = f"THROTTLE: GPU at {status.temperature_c}°C, reducing batch size"
                log.warning(msg)
                health.add_alert(msg)

            elif status.status == "warning":
                health.throttle_factor = 0.75
                if status.vram_utilization >= VRAM_USAGE_CRITICAL:
                    msg = f"VRAM critical: {status.vram_used_mb}/{status.vram_total_mb} MB"
                    log.warning(msg)
                    health.add_alert(msg)
                    clear_gpu_cache()

            else:
                # Gradually restore throttle
                if health.throttle_factor < 1.0:
                    health.throttle_factor = min(1.0, health.throttle_factor + 0.1)

            # Disk space check
            free_gb = check_disk_space()
            if free_gb < DISK_MIN_GB:
                msg = f"LOW DISK: Only {free_gb:.1f} GB free"
                log.critical(msg)
                health.add_alert(msg)
                health.paused = True

            # Periodic status log (every 5 minutes)
            if int(time.time()) % 300 < interval:
                log.info(
                    f"GPU: {status.temperature_c}°C | "
                    f"VRAM: {status.vram_used_mb}/{status.vram_total_mb}MB "
                    f"({status.vram_utilization:.0%}) | "
                    f"Power: {status.power_draw_w:.0f}/{status.power_limit_w:.0f}W | "
                    f"Throttle: {health.throttle_factor:.0%} | "
                    f"Status: {status.status}"
                )

        except Exception as e:
            log.error(f"Watchdog error: {e}")
            health.add_alert(f"Watchdog error: {e}")

        for _ in range(interval):
            if health.should_stop:
                return
            time.sleep(1)

    log.info("Watchdog stopped")


def start_watchdog() -> threading.Thread:
    """Start the watchdog in a background daemon thread."""
    t = threading.Thread(target=monitor_loop, daemon=True, name="gpu-watchdog")
    t.start()
    return t


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------
def get_status_report() -> dict:
    """Get current system health summary."""
    gpu = query_gpu()
    free_gb = check_disk_space()
    return {
        "gpu": asdict(gpu),
        "disk_free_gb": round(free_gb, 2),
        "throttle_factor": health.throttle_factor,
        "paused": health.paused,
        "recent_alerts": health.get_alerts(10),
    }


def print_status():
    """Print formatted status to console."""
    report = get_status_report()
    gpu = report["gpu"]
    print(f"\n{'='*50}")
    print(f"  Jemma SafeBrain — System Health")
    print(f"{'='*50}")
    print(f"  GPU:          {gpu['gpu_name']}")
    print(f"  Temperature:  {gpu['temperature_c']}°C  (warn={GPU_TEMP_WARNING}, "
          f"throttle={GPU_TEMP_THROTTLE}, emergency={GPU_TEMP_EMERGENCY})")
    print(f"  VRAM:         {gpu['vram_used_mb']}/{gpu['vram_total_mb']} MB "
          f"({gpu['vram_utilization']:.0%})")
    print(f"  Power:        {gpu['power_draw_w']:.0f}/{gpu['power_limit_w']:.0f} W")
    print(f"  GPU Util:     {gpu['gpu_utilization']}%")
    print(f"  Fan:          {gpu['fan_speed_pct']}%")
    print(f"  Disk Free:    {report['disk_free_gb']:.1f} GB")
    print(f"  Throttle:     {report['throttle_factor']:.0%}")
    print(f"  Status:       {gpu['status'].upper()}")
    if report["recent_alerts"]:
        print(f"\n  Recent Alerts:")
        for ts, msg in report["recent_alerts"][-5:]:
            print(f"    [{ts}] {msg}")
    print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Run monitor in foreground
        try:
            monitor_loop(interval=5)
        except KeyboardInterrupt:
            health.should_stop = True
            print("\nWatchdog stopped")
    else:
        print_status()
