import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Root endpoint."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "message": "Slack Conference Deadlines Bot",
            "status": "running",
            "endpoints": ["/slack/command", "/health"],
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Method not allowed."""
        self.send_response(405)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())
