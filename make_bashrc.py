#!/usr/bin/env python
import os
import sys

contents = f"""# Bashrc for iceval

# Run Directory
export PROJECT_RUNDIR=/vol/iceval

# Project settings
export PROJECT_PORT=8000

# Database settings
export DB_NAME=iceval
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=iceval

# Redis and Celery settings
export REDIS_DB=1
export CELERY_NCPU=4
export CELERY_TASK_DEFAULT_QUEUE=iceval
export CELERY_RESULT_BACKEND=redis://localhost/$REDIS_DB
export CELERY_BROKER_URL=redis://localhost/$REDIS_DB

# GUnicorn
export PROJECT_GUNICORN_WORKER_NUM=5
export PROJECT_GUNICORN_MAX_REQUESTS=0
export PROJECT_GUNICORN_TIMEOUT=30
export PROJECT_GUNICORN_WORKER_CLASS=gevent
"""

if os.path.exists('./bashrc'):
    print("./bashrc exists, please do backup first!")
    sys.exit()

with open('./bashrc', 'w') as f:
    f.write(contents)
