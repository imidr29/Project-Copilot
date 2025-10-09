#!/usr/bin/env python3
"""
Simple HTTP server to serve the minimal OEE Co-Pilot frontend
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def serve_frontend(port=3000):
    """Serve the simple frontend HTML file"""
    
    # Change to the directory containing the HTML file
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if the HTML file exists
    html_file = script_dir / "simple_frontend.html"
    if not html_file.exists():
        print(f"❌ Error: {html_file} not found!")
        return
    
    # Create a custom handler that serves the HTML file
    class SimpleHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html':
                self.path = '/simple_frontend.html'
            return super().do_GET()
    
    try:
        with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
            print(f"🚀 Simple OEE Co-Pilot Frontend Server")
            print(f"📁 Serving from: {script_dir}")
            print(f"🌐 Frontend URL: http://localhost:{port}")
            print(f"🔗 Backend API: http://localhost:8000")
            print(f"")
            print(f"📝 Features:")
            print(f"   • Simple search interface")
            print(f"   • Fast backend response display")
            print(f"   • Raw JSON output")
            print(f"   • Copy to clipboard functionality")
            print(f"")
            print(f"Press Ctrl+C to stop the server")
            print(f"")
            
            # Try to open the browser automatically
            try:
                webbrowser.open(f'http://localhost:{port}')
                print(f"🌐 Opened browser automatically")
            except:
                print(f"🌐 Please open http://localhost:{port} in your browser")
            
            print(f"")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n👋 Server stopped")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Port {port} is already in use. Trying port {port + 1}")
            serve_frontend(port + 1)
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 3000")
    
    serve_frontend(port)
