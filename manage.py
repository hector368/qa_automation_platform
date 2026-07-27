#!/usr/bin/env python
"""Utilidad de línea de comandos de Django."""

import os
import sys


def main() -> None:
    """Ejecuta tareas administrativas de Django."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings.local",
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que esté instalado, "
            "que el entorno virtual esté activo y que esté disponible "
            "en la variable PYTHONPATH."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()