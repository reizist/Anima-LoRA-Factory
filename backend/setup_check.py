import os
import platform
import subprocess
import sys


SUPPORTED_PYTHON = {(3, 10), (3, 11), (3, 12)}
STABLE_TORCH = "torch==2.5.1+cu121"
STABLE_TORCHVISION = "torchvision==0.20.1+cu121"
STABLE_TORCH_INDEX = "https://download.pytorch.org/whl/cu121"
BLACKWELL_TORCH_INDEX = "https://download.pytorch.org/whl/nightly/cu130"
SYSTEM = platform.system()


def run_command(command, cwd=None):
    try:
        print(f"[COMMAND] {subprocess.list2cmdline(command)}")
        subprocess.check_call(command, cwd=cwd)
        return True
    except Exception as e:
        print(f"[ERROR] Command failed: {subprocess.list2cmdline(command)}")
        print(e)
        return False


def check_python_version():
    version = sys.version_info[:2]
    print(f"[INFO] Python {sys.version.split()[0]} ({sys.executable})")
    if version not in SUPPORTED_PYTHON:
        print("[ERROR] Python 3.10, 3.11, or 3.12 (64-bit) is required.")
        print("[ERROR] Python 3.10 is the recommended version.")
        return False
    if sys.maxsize <= 2**32:
        print("[ERROR] 32-bit Python is not supported. Please install 64-bit Python.")
        return False
    return True


def bootstrap_packaging_tools():
    print("[SETUP] Updating pip, setuptools, and wheel...")
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "setuptools",
        "wheel",
    ]
    if not run_command(command):
        print("[ERROR] Failed to update Python packaging tools.")
        return False
    return True


def check_sd_scripts():
    sd_scripts_path = os.path.join(os.getcwd(), "sd-scripts")
    key_file = os.path.join(sd_scripts_path, "anima_train_network.py")

    if not os.path.exists(sd_scripts_path):
        print("[ERROR] sd-scripts folder not found in backend directory.")
        print("[ERROR] This version requires sd-scripts to be bundled.")
        return False
    if not os.path.exists(key_file):
        print("[ERROR] sd-scripts folder exists but 'anima_train_network.py' is missing.")
        print("[ERROR] The folder might be corrupted or incorrect.")
        return False

    print("[INFO] Bundled sd-scripts found and verified.")
    return True


def get_nvidia_gpu_info():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True,
        )
        return output.strip()
    except Exception:
        return None


def get_pytorch_info():
    code = """
import torch
import torchvision

if torch.cuda.is_available():
    major, minor = torch.cuda.get_device_capability()
    arch_list = torch.cuda.get_arch_list()
    cc = major * 10 + minor
    if cc >= 120 and "sm_120" not in arch_list:
        print("NEEDS_UPGRADE")
    else:
        print("CUDA_OK")
elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
    version = tuple(int(part) for part in torch.__version__.split("+")[0].split(".")[:2])
    print("MPS_OK" if version >= (2, 6) else "MPS_NEEDS_UPGRADE")
else:
    print("NO_ACCELERATOR")
"""
    try:
        output = subprocess.check_output(
            [sys.executable, "-c", code],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        return output.splitlines()[-1]
    except Exception:
        return "MISSING"


def install_pytorch(is_blackwell=False):
    if SYSTEM == "Darwin":
        print("[SETUP] Installing PyTorch with Apple Metal (MPS) support...")
        return run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--force-reinstall",
                "torch>=2.6",
                "torchvision",
            ]
        )

    if is_blackwell:
        print("[SETUP] Installing PyTorch Nightly for RTX 50 series (CUDA 13.0)...")
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--pre",
            "--upgrade",
            "--force-reinstall",
            "torch",
            "torchvision",
            "--index-url",
            BLACKWELL_TORCH_INDEX,
        ]
    else:
        print("[SETUP] Installing verified PyTorch for NVIDIA GPU (CUDA 12.1)...")
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--force-reinstall",
            STABLE_TORCH,
            STABLE_TORCHVISION,
            "--index-url",
            STABLE_TORCH_INDEX,
        ]
    return run_command(command)


def verify_pytorch(gpu_name=None):
    status = get_pytorch_info()
    expected = "MPS_OK" if SYSTEM == "Darwin" else "CUDA_OK"
    if status != expected:
        print(f"[ERROR] GPU verification failed (status: {status}, expected: {expected}).")
        if SYSTEM == "Darwin":
            print("[ERROR] Apple Silicon and a macOS version supported by PyTorch MPS are required.")
        else:
            print("[ERROR] PyTorch cannot use the NVIDIA GPU. Check the NVIDIA driver installation.")
        return False

    if status == "MPS_OK":
        details = """
import torch
print(f"PyTorch {torch.__version__}, device: Apple Metal (MPS)")
"""
    else:
        details = """
import torch
print(f"PyTorch {torch.__version__}, CUDA {torch.version.cuda}, GPU: {torch.cuda.get_device_name(0)}")
"""
    try:
        output = subprocess.check_output([sys.executable, "-c", details], text=True).strip()
        print(f"[INFO] Accelerator is ready: {output}")
    except Exception:
        print(f"[INFO] Accelerator is ready (GPU: {gpu_name or 'Apple Metal'}).")
    return True


def check_pytorch():
    if SYSTEM == "Darwin":
        status = get_pytorch_info()
        print(f"[INFO] Current PyTorch status: {status}")
        if status != "MPS_OK":
            print("[SETUP] PyTorch MPS is missing, unavailable, or too old for BF16. Installing the macOS build...")
            if not install_pytorch():
                return False
        return verify_pytorch()

    gpu_name = get_nvidia_gpu_info()
    if not gpu_name:
        print("[ERROR] NVIDIA GPU was not detected by nvidia-smi.")
        print("[ERROR] This application requires a supported NVIDIA GPU.")
        return False

    status = get_pytorch_info()
    is_blackwell = "RTX 50" in gpu_name or "RTX PRO" in gpu_name or status == "NEEDS_UPGRADE"
    print(f"[INFO] Detected GPU: {gpu_name}")
    print(f"[INFO] Current PyTorch status: {status}")

    if status != "CUDA_OK":
        if status == "NO_ACCELERATOR":
            print("[SETUP] CPU-only PyTorch detected. Replacing it with the CUDA build...")
        elif status == "NEEDS_UPGRADE":
            print("[SETUP] Current PyTorch does not support this RTX 50 series GPU.")
        else:
            print("[SETUP] PyTorch is missing or broken. Installing a verified CUDA build...")
        if not install_pytorch(is_blackwell):
            return False

    return verify_pytorch(gpu_name)


def check_requirements():
    print("[INFO] Installing verified application dependencies...")
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_path):
        if not run_command([sys.executable, "-m", "pip", "install", "-r", req_path]):
            print("[ERROR] Failed to install application requirements.")
            print("[ERROR] Check the pip error above, delete venv, and run the platform launcher again.")
            return False

    sd_scripts_path = os.path.join(os.getcwd(), "sd-scripts")
    sd_req_path = os.path.join(sd_scripts_path, "requirements.txt")
    if os.path.exists(sd_req_path):
        print("[INFO] Installing sd-scripts requirements...")
        if not run_command(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=sd_scripts_path,
        ):
            print("[ERROR] Failed to install sd-scripts requirements.")
            print("[ERROR] Check the pip error above, delete venv, and run the platform launcher again.")
            return False
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("  Anima LoRA Factory - Environment Setup Check")
    print(f"  Platform: {platform.platform()}")
    print("=" * 50)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = check_python_version()
    if success:
        success = bootstrap_packaging_tools()
    if success:
        success = check_sd_scripts()
    if success:
        success = check_pytorch()
    if success:
        success = check_requirements()
    if success:
        success = verify_pytorch()

    print("=" * 50)
    if success:
        print("  Setup Check Completed Successfully!")
    else:
        print("  Setup Check encountered some issues.")
    print("=" * 50)
    sys.exit(0 if success else 1)
