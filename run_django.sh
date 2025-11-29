#!/bin/bash

# Activate virtual environment
source /home/ubuntu/geospace/venv/bin/activate

# Ensure the script is executed from the correct directory
cd /home/ubuntu/geospace

# Start Django server in foreground
python3 manage.py runserver 0.0.0.0:8000
