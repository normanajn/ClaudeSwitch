#!/usr/bin/env python3
"""Build dist/claudeswitch.pyz — a self-contained single-file executable."""
import shutil
import tempfile
import zipapp
from pathlib import Path

HERE = Path(__file__).parent
DIST = HERE / "dist"


def build() -> None:
    DIST.mkdir(exist_ok=True)
    target = DIST / "claudeswitch.pyz"

    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(
            HERE / "claudeswitch",
            Path(tmp) / "claudeswitch",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        zipapp.create_archive(
            tmp,
            target=str(target),
            interpreter="/usr/bin/env python3",
            main="claudeswitch.cli:run",
        )

    target.chmod(0o755)
    print(f"Built {target}  ({target.stat().st_size:,} bytes)")
    print(f"Run with:  python3 {target.name}  or  ./{target.name}")


if __name__ == "__main__":
    build()
