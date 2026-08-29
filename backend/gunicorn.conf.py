import multiprocessing

# Bind address
bind = "0.0.0.0:8000"

# Workers — standard formula: (2 x CPU cores) + 1
# UvicornWorker wraps the ASGI app so FastAPI + socket.io both work
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Recycle workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 120        # kill worker if silent for 120s
keepalive = 5        # keep idle connections open for 5s
graceful_timeout = 30

# Logging — write to stdout so Docker captures it
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Worker connections (for async workers)
worker_connections = 1000
