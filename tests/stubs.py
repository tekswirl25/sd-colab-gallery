"""Заглушки тяжёлых зависимостей, чтобы тесты логики шли без GPU, torch и сети."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def install():
    """Подставляет torch и scripts.logger, если настоящих нет. Идемпотентна."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    if "torch" not in sys.modules:
        try:
            import torch  # noqa: F401
        except ImportError:
            torch = types.ModuleType("torch")
            torch.float16 = "float16"
            torch.float32 = "float32"
            torch.seed = lambda: 123456789

            class Generator:
                def __init__(self, device="cpu"):
                    self.device, self.seed = device, None

                def manual_seed(self, s):
                    self.seed = s
                    return self

            torch.Generator = Generator
            torch.manual_seed = lambda s: Generator().manual_seed(s)
            torch.cuda = types.SimpleNamespace(is_available=lambda: False)
            sys.modules["torch"] = torch

    # настоящий logger пишет в /content/logs (есть только в Colab)
    logger = types.ModuleType("scripts.logger")
    logger.LOG_FILE = "/dev/null"
    logger.log_info = lambda *a, **k: None
    logger.log_error = lambda *a, **k: None
    sys.modules["scripts.logger"] = logger
