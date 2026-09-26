"""Small, dependency-light helpers for cross-platform hardware integration."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any


def accelerator_info(torch_module: Any | None = None) -> dict[str, str]:
    """Return the accelerator that training can actually use."""
    try:
        torch = torch_module
        if torch is None:
            import torch  # type: ignore

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            total = torch.cuda.get_device_properties(0).total_memory
            return {
                "type": "cuda",
                "name": name,
                "memory": f"{total / (1024 ** 3):.1f} GiB",
            }

        mps = getattr(getattr(torch, "backends", None), "mps", None)
        if mps is not None and mps.is_available():
            chip = platform.processor() or platform.machine() or "Apple Silicon"
            return {"type": "mps", "name": f"Apple Metal ({chip})", "memory": "Shared"}
    except Exception:
        pass

    return {"type": "none", "name": "No supported GPU found", "memory": "N/A"}


def training_hardware_error(torch_module: Any | None = None) -> str | None:
    info = accelerator_info(torch_module)
    if info["type"] != "none":
        return None

    launcher = "start.bat" if os.name == "nt" else "./start.sh"
    return (
        "対応GPUをPyTorchから使用できません。CPUだけでの非常に遅い学習を防ぐため開始しませんでした。"
        f"venvを削除して{launcher}を再実行し、GPUドライバーも確認してください。 / "
        "PyTorch cannot use a supported GPU (NVIDIA CUDA or Apple Metal/MPS). "
        f"Delete venv, run {launcher} again, and check the GPU driver."
    )


def schedule_shutdown() -> tuple[bool, str]:
    """Ask the host OS to shut down in roughly one minute."""
    system = platform.system()
    if system == "Windows":
        command = ["shutdown", "/s", "/t", "60"]
        cancel = "shutdown /a"
    elif system == "Linux":
        command = ["shutdown", "-h", "+1"]
        cancel = "shutdown -c"
    elif system == "Darwin":
        # macOS shutdown normally requires administrator authorization. Using
        # osascript gives desktop users the normal System Events authorization flow.
        if not shutil.which("osascript"):
            return False, "osascript is not available"
        command = [
            "osascript",
            "-e",
            'delay 60',
            "-e",
            'tell application "System Events" to shut down',
        ]
        cancel = "stop the osascript process"
    else:
        return False, f"automatic shutdown is not supported on {system}"

    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, cancel
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
