import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import platform_support
import setup_check


class FakeCuda:
    def __init__(self, available=False):
        self.available = available

    def is_available(self):
        return self.available

    def get_device_name(self, _index):
        return "Test NVIDIA GPU"

    def get_device_properties(self, _index):
        return SimpleNamespace(total_memory=12 * 1024**3)


class FakeMps:
    def __init__(self, available=False):
        self.available = available

    def is_available(self):
        return self.available


def fake_torch(cuda=False, mps=False):
    return SimpleNamespace(
        cuda=FakeCuda(cuda),
        backends=SimpleNamespace(mps=FakeMps(mps)),
    )


class AcceleratorInfoTests(unittest.TestCase):
    def test_detects_cuda_and_memory(self):
        info = platform_support.accelerator_info(fake_torch(cuda=True))
        self.assertEqual(info["type"], "cuda")
        self.assertEqual(info["memory"], "12.0 GiB")

    @mock.patch("platform_support.platform.processor", return_value="arm")
    def test_detects_apple_mps(self, _processor):
        info = platform_support.accelerator_info(fake_torch(mps=True))
        self.assertEqual(info["type"], "mps")
        self.assertIn("Apple Metal", info["name"])

    def test_rejects_cpu_only_training(self):
        error = platform_support.training_hardware_error(fake_torch())
        self.assertIsNotNone(error)
        self.assertIn("supported GPU", error)

    def test_supported_gpu_has_no_error(self):
        self.assertIsNone(platform_support.training_hardware_error(fake_torch(cuda=True)))


class SetupSelectionTests(unittest.TestCase):
    @mock.patch.object(setup_check, "verify_pytorch", return_value=True)
    @mock.patch.object(setup_check, "install_pytorch", return_value=True)
    @mock.patch.object(setup_check, "get_pytorch_info", return_value="MPS_NEEDS_UPGRADE")
    def test_macos_upgrades_torch_for_bf16(self, _status, install, _verify):
        with mock.patch.object(setup_check, "SYSTEM", "Darwin"):
            self.assertTrue(setup_check.check_pytorch())
        install.assert_called_once_with()

    @mock.patch.object(setup_check, "verify_pytorch", return_value=True)
    @mock.patch.object(setup_check, "install_pytorch", return_value=True)
    @mock.patch.object(setup_check, "get_pytorch_info", return_value="MISSING")
    @mock.patch.object(setup_check, "get_nvidia_gpu_info", return_value="NVIDIA GeForce RTX 5090")
    def test_rtx_50_selects_blackwell_build(self, _gpu, _status, install, _verify):
        with mock.patch.object(setup_check, "SYSTEM", "Linux"):
            self.assertTrue(setup_check.check_pytorch())
        install.assert_called_once_with(True)

    @mock.patch.object(setup_check, "verify_pytorch", return_value=True)
    @mock.patch.object(setup_check, "install_pytorch", return_value=True)
    @mock.patch.object(setup_check, "get_pytorch_info", return_value="NEEDS_UPGRADE")
    @mock.patch.object(setup_check, "get_nvidia_gpu_info", return_value="NVIDIA Blackwell GPU")
    def test_compute_capability_can_select_blackwell_build(self, _gpu, _status, install, _verify):
        with mock.patch.object(setup_check, "SYSTEM", "Linux"):
            self.assertTrue(setup_check.check_pytorch())
        install.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
