import subprocess
import sys


def main() -> None:
    subprocess.check_call(["alembic", "upgrade", "head"])
    subprocess.check_call([sys.executable, "-m", "app.seed"])
    subprocess.check_call(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    )


if __name__ == "__main__":
    main()
