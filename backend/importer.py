"""
Importer module for Meridian API.
Handles transcript fetching from URLs and file uploads.
Pure utility functions with no project-specific imports.
"""

import re
from urllib.request import urlopen, Request
from urllib.error import URLError


# ============================================================
# TRANSCRIPT IMPORT — URL fetch & file upload
# ============================================================
def fetch_transcript_from_url(url):
    """Fetches a URL and extracts readable text (strips HTML tags)."""
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # Strip HTML tags and extract text
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&#\d+;', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Try to extract the meaty part (between common markers)
        for start_marker in ['Prepared Remarks', 'Conference Call', 'Earnings Call', 'Good afternoon', 'Good morning', 'Thank you for standing by']:
            idx = text.find(start_marker)
            if idx > 0:
                text = text[idx:]
                break

        if len(text) < 200:
            raise ValueError("Le contenu extrait est trop court. Le site bloque peut-être l'accès.")

        return text[:100000]
    except URLError as e:
        raise ValueError(f"Impossible d'accéder à l'URL: {e}")
    except Exception as e:
        raise ValueError(f"Erreur lors de l'extraction: {e}")


def extract_text_from_upload(content_type, body):
    """Extracts text from an uploaded file (txt or pdf)."""
    if 'text/plain' in content_type or content_type.endswith('.txt'):
        return body.decode('utf-8', errors='ignore')

    # Try to detect plain text even without proper mime type
    try:
        text = body.decode('utf-8')
        if text.isprintable() or '\n' in text:
            return text
    except (UnicodeDecodeError, ValueError):
        pass

    raise ValueError("Format non supporté. Envoyez un fichier .txt avec le transcript.")


# ============================================================
# MULTIPART FORM DATA PARSER (replaces cgi.FieldStorage)
# ============================================================
def parse_multipart_form(content_type, body):
    """
    Simple multipart/form-data parser for file uploads.
    Returns a dict with form fields and file info.
    """
    # Extract boundary from Content-Type header
    boundary_match = re.search(r'boundary=([^\s;]+)', content_type)
    if not boundary_match:
        raise ValueError("No boundary found in Content-Type")

    boundary = boundary_match.group(1).strip('"')
    boundary_bytes = f'--{boundary}'.encode()
    end_boundary_bytes = f'--{boundary}--'.encode()

    parts = body.split(boundary_bytes)
    result = {}

    for part in parts:
        if not part or part == b'--\r\n' or part.startswith(end_boundary_bytes):
            continue

        # Split headers from content
        try:
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                header_end = part.find(b'\n\n')
                if header_end == -1:
                    continue
                header_section = part[:header_end].decode('utf-8', errors='ignore')
                content = part[header_end + 2:]
            else:
                header_section = part[:header_end].decode('utf-8', errors='ignore')
                content = part[header_end + 4:]

            # Remove trailing CRLLF or LF
            if content.endswith(b'\r\n'):
                content = content[:-2]
            elif content.endswith(b'\n'):
                content = content[:-1]

            # Parse Content-Disposition header
            name_match = re.search(r'name="([^"]+)"', header_section)
            if not name_match:
                continue

            field_name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]+)"', header_section)
            content_type_match = re.search(r'Content-Type:\s*([^\r\n]+)', header_section)

            if filename_match:
                result[field_name] = {
                    'filename': filename_match.group(1),
                    'content': content,
                    'content_type': content_type_match.group(1) if content_type_match else 'application/octet-stream'
                }
            else:
                result[field_name] = content.decode('utf-8', errors='ignore')
        except Exception:
            continue

    return result
