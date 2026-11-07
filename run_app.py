"""Entry point for the packaged app (PyInstaller) - same as `python -m echo.app`."""
from echo import single

single.guard()  # --quit, and "already running", before the heavy imports

from echo.app import main  # noqa: E402

if __name__ == "__main__":
    main()
