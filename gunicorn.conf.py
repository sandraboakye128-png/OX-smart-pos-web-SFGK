# gunicorn.conf.py
import multiprocessing

# Increase timeout for long-running operations
timeout = 120  # 2 minutes instead of default 30 seconds
graceful_timeout = 30
keepalive = 5

# Worker settings
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'  # or 'gevent' for async
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'