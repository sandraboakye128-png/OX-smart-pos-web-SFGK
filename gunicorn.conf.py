# gunicorn.conf.py
import multiprocessing
import os

# --- Timeouts (critical for large imports) ---
timeout = 600              # 10 minutes – enough for 5000+ rows
graceful_timeout = 60      # 30 seconds grace after worker timeout
keepalive = 5              # Keep connections alive

# --- Workers ---
# Use gevent for async I/O if you have many concurrent requests;
# otherwise sync workers with high timeout are fine.
worker_class = 'gevent'    # or 'sync' if you prefer
workers = multiprocessing.cpu_count() * 2 + 1  # typical formula
worker_connections = 1000  # only for gevent

# --- Request limits (prevents memory leaks) ---
max_requests = 2000
max_requests_jitter = 100

# --- Logging ---
accesslog = '-'            # stdout
errorlog = '-'             # stderr
loglevel = 'info'

# --- Performance ---
# Preload app to reduce memory overhead on fork (optional)
preload_app = False

# Bind to the port Render uses (or default)
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"