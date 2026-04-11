from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jemma.benchmarks.system_probe import collect_system_probe
from jemma.core.types import AppConfig


def collect_runtime_telemetry(config: AppConfig) -> dict[str, Any]:
    telemetry: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(),
        "system_probe": collect_system_probe(config.repo_root),
    }

    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        telemetry["process"] = {"available": False}
    else:
        memory = psutil.virtual_memory()
        telemetry["process"] = {
            "available": True,
            "cpu_percent": psutil.cpu_percent(interval=0.0),
            "memory_percent": memory.percent,
            "memory_used_mb": round(memory.used / 1024 / 1024, 1),
            "memory_total_mb": round(memory.total / 1024 / 1024, 1),
        }

    try:
        import pynvml  # type: ignore[import-not-found]
    except ImportError:
        telemetry["gpu_runtime"] = {"available": False}
    else:
        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            telemetry["gpu_runtime"] = {
                "available": True,
                "name": pynvml.nvmlDeviceGetName(handle).decode("utf-8"),
                "utilization_percent": pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
                "memory_used_mb": round(memory_info.used / 1024 / 1024, 1),
                "memory_total_mb": round(memory_info.total / 1024 / 1024, 1),
                "temperature_c": pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
            }
        finally:
            pynvml.nvmlShutdown()

    return telemetry

