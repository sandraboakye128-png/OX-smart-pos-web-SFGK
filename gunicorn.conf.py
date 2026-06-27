# gunicorn.conf.py
import multiprocessing
import os

# --- Timeouts (critical for large imports) ---
timeout = 600              # 10 minutes – enough for 5000+ rows
graceful_timeout = 60
keepalive = 5

# --- Workers ---
# Use sync workers (gevent requires installation; sync works fine with timeout)
worker_class = 'sync'      # <-- changed from 'gevent'
workers = multiprocessing.cpu_count() * 2 + 1
worker_connections = 1000  # only used for gevent, but harmless

# --- Request limits ---
max_requests = 5000
max_requests_jitter = 100

# --- Logging ---
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# --- Bind ---
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"