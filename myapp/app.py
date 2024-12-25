from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from urllib.parse import urlparse as url_parse
import time
import psutil

app = Flask(__name__)

# In-memory storage for items
items = {}

# Custom metrics
REQUEST_COUNT = Counter('http_request_total', 'Total HTTP Requests', ['method', 'status', 'path'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Duration', ['method', 'status', 'path'])
REQUEST_IN_PROGRESS = Gauge('http_requests_in_progress', 'HTTP Requests in progress', ['method', 'path'])

# System metrics
CPU_USAGE = Gauge('process_cpu_usage', 'Current CPU usage in percent')
MEMORY_USAGE = Gauge('process_memory_usage_bytes', 'Current memory usage in bytes')

def update_system_metrics():
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.Process().memory_info().rss)

@app.before_request
def before_request():
    request.start_time = time.time()
    REQUEST_IN_PROGRESS.labels(method=request.method, path=request.path).inc()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_COUNT.labels(method=request.method, status=response.status_code, path=request.path).inc()
    REQUEST_LATENCY.labels(method=request.method, status=response.status_code, path=request.path).observe(request_latency)
    REQUEST_IN_PROGRESS.labels(method=request.method, path=request.path).dec()
    return response

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/healthcheck')
def health_check():
    # Perform any health checks you need here (database connection, etc.)
    # For now, we'll just simulate a successful check
    return jsonify({'status': 'healthy'}), 200

@app.route('/items', methods=['POST'])
def create_item():
    item = request.json
    item_id = len(items) + 1
    items[item_id] = item['name']
    return jsonify({"item_id": item_id, "name": item['name'], "status": "created"})

@app.route('/items/<int:item_id>', methods=['GET'])
def read_item(item_id):
    if item_id not in items:
        return jsonify({"detail": "Item not found"}), 404
    return jsonify({"item_id": item_id, "name": items[item_id]})

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    if item_id not in items:
        return jsonify({"detail": "Item not found"}), 404
    item = request.json
    items[item_id] = item['name']
    return jsonify({"item_id": item_id, "name": item['name'], "status": "updated"})

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    if item_id not in items:
        return jsonify({"detail": "Item not found"}), 404
    del items[item_id]
    return jsonify({"item_id": item_id, "status": "deleted"})

@app.route('/metrics')
def metrics():
    update_system_metrics()
    return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# Modify the middleware to return bytes
def metrics_app(environ, start_response):
    update_system_metrics()
    data = generate_latest(REGISTRY)
    status = '200 OK'
    headers = [('Content-Type', CONTENT_TYPE_LATEST), ('Content-Length', str(len(data)))]
    start_response(status, headers)
    return [data]

# Use the modified middleware
app_dispatch = DispatcherMiddleware(app, {
    '/metrics': metrics_app
})

#if __name__ == '__main__':
#    app.run(host='0.0.0.0')

if __name__ == '__main__':
    run_simple(hostname='0.0.0.0', port=5000, application=app_dispatch)