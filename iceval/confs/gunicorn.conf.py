import multiprocessing
import os


PORT = os.getenv('PROJECT_PORT', '8000')
bind = "0.0.0.0:%s" % PORT
workers = int(os.getenv('PROJECT_GUNICORN_WORKER_NUM', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('PROJECT_GUNICORN_WORKER_CLASS', 'gevent')
max_requests = int(os.getenv('PROJECT_GUNICORN_MAX_REQUESTS', 0))
timeout = int(os.getenv('PROJECT_GUNICORN_TIMEOUT', 30))
