#!/usr/bin/env python3
"""
Main entry point for MAGA AI on Railway
"""
import os
import sys
import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram_bot import MAGATelegramBot

# Устанавливаем headless режим для Railway
os.environ['HEADLESS'] = os.getenv('HEADLESS', '1')
os.environ['DISPLAY'] = os.getenv('DISPLAY', '')

# Получаем порт из Railway или используем 8000 по умолчанию
PORT = int(os.getenv('PORT', 8000))

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health_data = {
                "status": "healthy",
                "service": "maga-ai",
                "timestamp": asyncio.get_event_loop().time()
            }
            self.wfile.write(json.dumps(health_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        return

def run_health_server():
    """Run simple health check server in background"""
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"🏥 Health check server started on port {PORT}")

    # Run server in background thread
    import threading
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    return server

async def main():
    """Main application startup"""
    print("🚀 Starting MAGA AI on Railway...")

    # Start health check server
    health_server = run_health_server()

    try:
        # Create and start the bot
        bot = MAGATelegramBot()
        print("✅ MAGA AI initialized successfully")
        print("🤖 Telegram bot ready")
        print(f"🔗 Health check available at http://0.0.0.0:{PORT}/health")

        # Run the bot
        await bot.run()

    except Exception as e:
        print(f"❌ Error starting MAGA AI: {e}")
        import traceback
        traceback.print_exc()
        health_server.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    # Health check via command line
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        health_data = {
            "status": "healthy",
            "service": "maga-ai",
            "timestamp": asyncio.get_event_loop().time()
        }
        print(json.dumps(health_data))
        sys.exit(0)

    # Start the application
    asyncio.run(main())
