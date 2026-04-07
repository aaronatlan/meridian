"""
Configuration module for Meridian API.
Handles environment detection and fallback values for database, JWT, and API keys.
"""

import os
import sqlite3

# ============================================================
# PORT CONFIGURATION
# ============================================================
PORT = int(os.environ.get('PORT', 4000))

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meridian.db')
# Si la DB par défaut est corrompue ou inaccessible, utilise /tmp
try:
    _tc = sqlite3.connect(_default_db)
    _tc.execute("PRAGMA integrity_check")
    _tc.close()
    DB_PATH = os.environ.get('MERIDIAN_DB', _default_db)
except Exception:
    print(f"  [WARN] DB {_default_db} inaccessible, utilisation de /tmp/meridian.db")
    try:
        os.remove(_default_db)
    except OSError:
        pass
    DB_PATH = os.environ.get('MERIDIAN_DB', '/tmp/meridian.db')

# ============================================================
# JWT & SECURITY
# ============================================================
JWT_SECRET = 'meridian-dev-secret-change-in-production'

# ============================================================
# FRONTEND & API
# ============================================================
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

# ============================================================
# AI SERVICE CONFIGURATION
# ============================================================
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

USE_CLAUDE = ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY != ''
