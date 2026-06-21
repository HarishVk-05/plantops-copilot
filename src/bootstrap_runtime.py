import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "plantops.db"
CHROMA_SQLITE_PATH = PROCESSED_DIR / "chroma_db" / "chroma.sqlite3"

def runtime_artifacts_exist() -> bool:
    return DB_PATH.exists() and CHROMA_SQLITE_PATH.exists()

def _run_script(relative_script_path: str) -> None:
    script_path = PROJECT_ROOT / relative_script_path

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Runtime bootstrap failed while running {relative_script_path}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

def ensure_runtime_artifacts(force: bool = False) -> dict:
    """
    Ensure generated runtime artifacts exist.

    Used for Streamlit Cloud deployment where data/processed is not committed.
    """

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if runtime_artifacts_exist() and not force:
        return {
            "rebuilt": False,
            "database": str(DB_PATH),
            "vector_store": str(CHROMA_SQLITE_PATH)
        }

    _run_script("src/data_generation/generate_factory_data.py")
    _run_script("src/rag/build_vector_index.py")

    if not runtime_artifacts_exist():
        raise RuntimeError(
            "Runtime bootstrap completed, but required artifacts are missing:\n"
            f"- {DB_PATH}\n"
            f"- {CHROMA_SQLITE_PATH}"
        )

    return {
        "rebuilt": True,
        "database": str(DB_PATH),
        "vector_store": str(CHROMA_SQLITE_PATH)
    }


if __name__ == "__main__":
    force = "--force" in sys.argv
    print(ensure_runtime_artifacts(force=force))