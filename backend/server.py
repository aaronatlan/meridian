#!/usr/bin/env python3
"""
Meridian API Server — Point d'entrée.
Lance le serveur HTTP sur le port configuré.
"""

from http.server import HTTPServer
from config import PORT, USE_CLAUDE
from db import init_db
from routes import MeridianHandler


def main():
    init_db()
    print(f"\n  🧭 Meridian API running on http://localhost:{PORT}")
    print(f"  📊 AI: {'Claude API' if USE_CLAUDE else 'Mock (set ANTHROPIC_API_KEY for real AI)'}")
    print(f"  💡 Open http://localhost:{PORT} in your browser\n")
    HTTPServer(('', PORT), MeridianHandler).serve_forever()


if __name__ == '__main__':
    main()
