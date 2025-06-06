#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'locallibrary.settings')
    try:
        from django.core.management import execute_from_command_line

        # Lista de variables de entorno necesarias
        required_env_vars = [
            'OS_USERNAME',
            'OS_PROJECT_NAME',
            'OS_PASSWORD',
            'OS_AUTH_URL',
            'OS_REGION_NAME',
            'OS_USER_DOMAIN_NAME',
            'OS_PROJECT_DOMAIN_NAME',
            'OS_IDENTITY_API_VERSION',
            'ENCRYPTION_KEY'
        ]

        # Verificar variables de entorno críticas
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

        if missing_vars:
            print("\n" + "=" * 73)
            print("🚫  ERROR: NO TIENES CONFIGURADAS LAS VARIABLES DE ENTORNO NECESARIAS  🚫")
            print("=" * 73)
            print("Las siguientes variables faltan o están vacías:")
            for var in missing_vars:
                print(f" - {var}")
            print("=" * 73 + "\n")
            sys.exit(1)  # Sale con un código de error


    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
