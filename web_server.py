from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os
import logging

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is running')
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_health_server():
    try:
        port = int(os.getenv('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"✅ Сервер здоровья запущен на порту {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка сервера здоровья: {e}")

def start_health_server():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logger.info("✅ Сервер здоровья запущен в фоновом режиме")
