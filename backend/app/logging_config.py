import logging
import logging.handlers
import os
import sys


class _SafeTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """TimedRotatingFileHandler que tolera PermissionError en Windows.

    En Windows, uvicorn --reload corre dos procesos (reloader + server) que
    comparten el mismo archivo de log abierto. os.rename() falla si el otro
    proceso aún lo tiene abierto; capturamos el error y dejamos que el próximo
    ciclo lo intente de nuevo.
    """

    def rotate(self, source: str, dest: str) -> None:
        try:
            super().rotate(source, dest)
        except PermissionError:
            pass


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    # Evitar duplicar handlers si se llama más de una vez (ej. durante tests)
    if root.handlers:
        return

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)

    log_file = os.getenv("LOG_FILE_PATH")
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = _SafeTimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=30,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Silenciar loggers muy verbosos de librerías externas
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
