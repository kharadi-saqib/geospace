#!/home/odoo/pratik/geospace/geo_space/env/bin/python3
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
