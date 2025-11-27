#!/bin/bash

# Activate virtual environment
source /home/administrator/Geo_node_08SEP_25/geonode/venv/bin/activate

# Ensure the script is executed from the correct directory
cd /home/administrator/Geo_node_08SEP_25/geonode

# Start Django server in foreground
exec python manage.py runserver 209.182.234.193:8007
