"""
Routes module for Meridian API.
HTTP request handlers and all API endpoints.
"""

import json
import os
import re
import time
import uuid
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse

from config import FRONTEND_DIR
from auth import create_token, verify_token, hash_password, check_password
from db import get_db
from importer import parse_multipart_form, fetch_transcript_from_url, extract_text_from_upload
from ai import analyze_transcript
from export import generate_memo_html


# ============================================================
# REQUEST HANDLER
# ============================================================
class MeridianHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):
        if '/api/' in str(args[0]) if args else False:
            print(f"  API: {args[0]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _get_user_id(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return verify_token(auth[7:])
        return None

    def do_GET(self):
        path = urlparse(self.path).path

        # API routes
        if path == '/api/health':
            return self._json_response({"status": "ok", "service": "meridian-api"})

        if path == '/api/auth/me':
            uid = self._get_user_id()
            if not uid:
                return self._json_response({"success": False, "error": "Non autorisé"}, 401)
            conn = get_db()
            user = conn.execute("SELECT id, email, name FROM users WHERE id = ?", (uid,)).fetchone()
            conn.close()
            if not user:
                return self._json_response({"success": False, "error": "Utilisateur non trouvé"}, 404)
            return self._json_response({"success": True, "data": dict(user)})

        if path == '/api/memos':
            uid = self._get_user_id()
            if not uid:
                return self._json_response({"success": False, "error": "Non autorisé"}, 401)
            conn = get_db()
            rows = conn.execute("SELECT * FROM memos WHERE user_id = ? ORDER BY created_at DESC", (uid,)).fetchall()
            conn.close()
            memos = []
            for r in rows:
                memos.append({
                    "id": r["id"], "userId": r["user_id"], "ticker": r["ticker"],
                    "companyName": r["company_name"], "quarter": r["quarter"],
                    "title": r["title"], "transcriptExcerpt": r["transcript_excerpt"],
                    "analysis": json.loads(r["analysis"]), "createdAt": r["created_at"]
                })
            return self._json_response({"success": True, "data": memos})

        # GET /api/memos/:id
        memo_match = re.match(r'^/api/memos/([a-f0-9-]+)$', path)
        if memo_match:
            uid = self._get_user_id()
            if not uid:
                return self._json_response({"success": False, "error": "Non autorisé"}, 401)
            memo_id = memo_match.group(1)
            conn = get_db()
            r = conn.execute("SELECT * FROM memos WHERE id = ? AND user_id = ?", (memo_id, uid)).fetchone()
            conn.close()
            if not r:
                return self._json_response({"success": False, "error": "Mémo non trouvé"}, 404)
            memo = {
                "id": r["id"], "userId": r["user_id"], "ticker": r["ticker"],
                "companyName": r["company_name"], "quarter": r["quarter"],
                "title": r["title"], "transcriptExcerpt": r["transcript_excerpt"],
                "analysis": json.loads(r["analysis"]), "createdAt": r["created_at"]
            }
            return self._json_response({"success": True, "data": memo})

        # GET /api/memos/:id/pdf
        pdf_match = re.match(r'^/api/memos/([a-f0-9-]+)/pdf$', path)
        if pdf_match:
            uid = self._get_user_id()
            if not uid:
                return self._json_response({"success": False, "error": "Non autorisé"}, 401)
            memo_id = pdf_match.group(1)
            conn = get_db()
            r = conn.execute("SELECT * FROM memos WHERE id = ? AND user_id = ?", (memo_id, uid)).fetchone()
            conn.close()
            if not r:
                return self._json_response({"success": False, "error": "Mémo non trouvé"}, 404)
            analysis = json.loads(r["analysis"])
            pdf_html = generate_memo_html(r["company_name"], r["ticker"], r["quarter"], r["created_at"], analysis)
            self.send_response(200)
            self._cors_headers()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="Meridian_{r["ticker"]}_{r["quarter"]}.html"')
            self.end_headers()
            self.wfile.write(pdf_html.encode())
            self.wfile.flush()
            return

        # Serve frontend (SPA fallback)
        if path.startswith('/api/'):
            return self._json_response({"success": False, "error": "Route non trouvée"}, 404)

        # For SPA routing: serve index.html for non-file paths
        file_path = os.path.join(FRONTEND_DIR, path.lstrip('/'))
        if not os.path.isfile(file_path):
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        print(f"  [POST] {path}", flush=True)

        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length) if length > 0 else b'{}'
            print(f"  [POST] body length={len(raw)}", flush=True)
            content_type = self.headers.get('Content-Type', '')

            # File upload is multipart — don't parse as JSON
            if path == '/api/import/file':
                if 'multipart/form-data' in content_type:
                    try:
                        form_data = parse_multipart_form(content_type, raw)
                        if 'file' not in form_data:
                            return self._json_response({"success": False, "error": "Aucun fichier trouvé"}, 400)
                        file_info = form_data['file']
                        file_bytes = file_info['content']
                        file_type = file_info.get('content_type', 'text/plain')
                    except Exception as e:
                        return self._json_response({"success": False, "error": f"Erreur parsing: {e}"}, 400)
                else:
                    file_bytes = raw
                    file_type = content_type

                uid = self._get_user_id()
                if not uid:
                    return self._json_response({"success": False, "error": "Non autorisé"}, 401)
                if len(file_bytes) == 0:
                    return self._json_response({"success": False, "error": "Fichier vide"}, 400)
                if len(file_bytes) > 10 * 1024 * 1024:
                    return self._json_response({"success": False, "error": "Fichier trop volumineux (max 10 Mo)"}, 400)

                try:
                    text = extract_text_from_upload(file_type, file_bytes)
                    return self._json_response({"success": True, "data": {"transcript": text, "length": len(text)}})
                except ValueError as e:
                    return self._json_response({"success": False, "error": str(e)}, 400)

            # All other routes expect JSON
            try:
                body = json.loads(raw.decode('utf-8', errors='ignore'))
            except json.JSONDecodeError:
                body = {}

            # Router for all POST endpoints
            if path == '/api/auth/register':
                email = body.get('email', '').strip()
                password = body.get('password', '')
                name = body.get('name', '').strip()
                if not email or not password or not name:
                    return self._json_response({"success": False, "error": "Champs requis: email, password, name"}, 400)
                conn = get_db()
                existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if existing:
                    conn.close()
                    return self._json_response({"success": False, "error": "Cet email est déjà utilisé"}, 409)
                uid = str(uuid.uuid4())
                pw_hash = hash_password(password)
                conn.execute("INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)", (uid, email, pw_hash, name))
                conn.commit()
                conn.close()
                token = create_token(uid)
                return self._json_response({"success": True, "data": {"user": {"id": uid, "email": email, "name": name}, "token": token}}, 201)

            if path == '/api/auth/login':
                email = body.get('email', '').strip()
                password = body.get('password', '')
                if not email or not password:
                    return self._json_response({"success": False, "error": "Champs requis: email, password"}, 400)
                conn = get_db()
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                conn.close()
                if not user or not check_password(password, user["password_hash"]):
                    return self._json_response({"success": False, "error": "Identifiants invalides"}, 401)
                token = create_token(user["id"])
                return self._json_response({"success": True, "data": {"user": {"id": user["id"], "email": user["email"], "name": user["name"]}, "token": token}})

            # POST /api/import/url
            if path == '/api/import/url':
                uid = self._get_user_id()
                if not uid:
                    return self._json_response({"success": False, "error": "Non autorisé"}, 401)
                url = body.get('url', '').strip()
                if not url:
                    return self._json_response({"success": False, "error": "URL requise"}, 400)
                try:
                    text = fetch_transcript_from_url(url)
                    return self._json_response({"success": True, "data": {"transcript": text, "source": url, "length": len(text)}})
                except ValueError as e:
                    return self._json_response({"success": False, "error": str(e)}, 400)

            # POST /api/memos/analyze
            if path == '/api/memos/analyze':
                uid = self._get_user_id()
                if not uid:
                    return self._json_response({"success": False, "error": "Non autorisé"}, 401)
                transcript = body.get('transcript', '')
                ticker = body.get('ticker', '').strip().upper()
                company_name = body.get('companyName', '').strip()
                quarter = body.get('quarter', '').strip()
                if not transcript or not ticker or not company_name:
                    return self._json_response({"success": False, "error": "Champs requis: transcript, ticker, companyName"}, 400)

                analysis = analyze_transcript(transcript, company_name, ticker)

                memo_id = str(uuid.uuid4())
                title = f"{company_name} ({ticker}) — {quarter or 'N/A'}"
                excerpt = transcript[:500]

                conn = get_db()
                conn.execute(
                    "INSERT INTO memos (id, user_id, ticker, company_name, quarter, title, transcript_excerpt, analysis) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (memo_id, uid, ticker, company_name, quarter, title, excerpt, json.dumps(analysis, ensure_ascii=False))
                )
                conn.commit()
                conn.close()

                memo = {
                    "id": memo_id, "userId": uid, "ticker": ticker, "companyName": company_name,
                    "quarter": quarter, "title": title, "transcriptExcerpt": excerpt,
                    "analysis": analysis, "createdAt": time.strftime('%Y-%m-%dT%H:%M:%S')
                }
                return self._json_response({"success": True, "data": memo}, 201)

            return self._json_response({"success": False, "error": "Route non trouvée"}, 404)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._json_response({"success": False, "error": str(e)}, 500)

    def do_DELETE(self):
        path = urlparse(self.path).path
        memo_match = re.match(r'^/api/memos/([a-f0-9-]+)$', path)
        if memo_match:
            uid = self._get_user_id()
            if not uid:
                return self._json_response({"success": False, "error": "Non autorisé"}, 401)
            memo_id = memo_match.group(1)
            conn = get_db()
            cursor = conn.execute("DELETE FROM memos WHERE id = ? AND user_id = ?", (memo_id, uid))
            conn.commit()
            conn.close()
            if cursor.rowcount == 0:
                return self._json_response({"success": False, "error": "Mémo non trouvé"}, 404)
            return self._json_response({"success": True})
        return self._json_response({"success": False, "error": "Route non trouvée"}, 404)
