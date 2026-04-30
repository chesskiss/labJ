from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path


REQUIRED_MODULES = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "numpy",
    "soundfile",
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "av",
]

REQUIRED_MODEL_FILES = [
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.txt",
]


def main() -> int:
    runtime_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    model_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None

    imports: dict[str, str] = {}
    for name in REQUIRED_MODULES:
        module = importlib.import_module(name)
        imports[name] = getattr(module, "__file__", "<builtin>")

    if runtime_root is not None:
        python_exe = Path(sys.executable).resolve()
        if runtime_root not in python_exe.parents:
            raise RuntimeError(
                f"Bundled runtime check failed: interpreter {python_exe} is outside runtime root {runtime_root}"
            )
        prefix = Path(sys.prefix).resolve()
        if runtime_root not in prefix.parents and prefix != runtime_root:
            raise RuntimeError(
                f"Bundled runtime check failed: prefix {prefix} is outside runtime root {runtime_root}"
            )

    if model_dir is not None:
        missing = [
            name for name in REQUIRED_MODEL_FILES if not (model_dir / name).exists()
        ]
        if missing:
            raise RuntimeError(
                f"Bundled model check failed: missing files in {model_dir}: {', '.join(missing)}"
            )

    payload = {
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version.split()[0],
        "python_prefix": str(Path(sys.prefix).resolve()),
        "runtime_root": str(runtime_root) if runtime_root is not None else None,
        "model_dir": str(model_dir) if model_dir is not None else None,
        "imports": imports,
        "pid": os.getpid(),
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
