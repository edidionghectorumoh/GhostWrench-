"""
Minimal HTTP server for the Ghostwrench mock inventory portal.

Usage:
    python mock_portal/server.py          # serves on port 8501
    python mock_portal/server.py 9000     # serves on port 9000
"""

import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8501
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        print(f"Mock inventory portal running at http://localhost:{PORT}")
        httpd.serve_forever()
