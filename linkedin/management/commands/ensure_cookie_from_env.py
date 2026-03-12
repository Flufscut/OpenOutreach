"""
Write Playwright storage state from env var to the cookie file.

Accepts:
- LINKEDIN_STORAGE_STATE_B64 / LINKEDIN_STORAGE_STATE: Playwright storage state JSON
- LINKEDIN_COOKIES_JSON / LINKEDIN_COOKIES_B64: Array of cookies (browser extension format)
  with domain, name, value, path, expirationDate, httpOnly, secure, sameSite, etc.
  Converts to Playwright format automatically.
"""

import base64
import json
import os

from django.core.management.base import BaseCommand

from linkedin.conf import COOKIES_DIR


def _derive_handle(email: str) -> str:
    """Same logic as onboarding: email slug → handle."""
    return email.split("@")[0].lower().replace(".", "_").replace("+", "_")


def _convert_cookies_to_playwright(cookies: list) -> dict:
    """
    Convert browser-extension cookie format to Playwright storage state.
    Input: [{domain, name, value, path, expirationDate, httpOnly, secure, sameSite, session}, ...]
    Output: {cookies: [...], origins: []}
    """
    _SAMESITE = {"no_restriction": "None", "lax": "Lax", "strict": "Strict", None: "Lax"}

    out = []
    for c in cookies:
        expires = c.get("expirationDate")
        if c.get("session") or expires is None:
            expires = -1
        else:
            expires = int(expires)  # Playwright wants integer seconds
        same = c.get("sameSite")
        same = _SAMESITE.get(same, "Lax") if same else "Lax"
        out.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": expires,
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", True)),
            "sameSite": same,
        })
    return {"cookies": out, "origins": []}


class Command(BaseCommand):
    help = (
        "If LINKEDIN_STORAGE_STATE(_B64) or LINKEDIN_COOKIES(_B64) is set, "
        "write Playwright storage state to assets/cookies/<handle>.json."
    )

    def handle(self, *args, **options):
        b64 = os.environ.get("LINKEDIN_STORAGE_STATE_B64", "").strip()
        raw = os.environ.get("LINKEDIN_STORAGE_STATE", "").strip()
        cookies_b64 = os.environ.get("LINKEDIN_COOKIES_B64", "").strip()
        cookies_raw = os.environ.get("LINKEDIN_COOKIES_JSON", "").strip()
        email = os.environ.get("LINKEDIN_EMAIL", "").strip()

        if not any([b64, raw, cookies_b64, cookies_raw]):
            return

        if not email or "@" not in email:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping ensure_cookie_from_env: LINKEDIN_EMAIL required."
                )
            )
            return

        data = None

        if b64:
            try:
                data = json.loads(base64.b64decode(b64).decode("utf-8"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Invalid LINKEDIN_STORAGE_STATE_B64: {e}"))
                return
        elif raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"Invalid LINKEDIN_STORAGE_STATE JSON: {e}"))
                return

        if cookies_b64:
            try:
                arr = json.loads(base64.b64decode(cookies_b64).decode("utf-8"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Invalid LINKEDIN_COOKIES_B64: {e}"))
                return
            if not isinstance(arr, list):
                self.stdout.write(self.style.ERROR("LINKEDIN_COOKIES_B64 must be a JSON array."))
                return
            data = _convert_cookies_to_playwright(arr)
        elif cookies_raw:
            try:
                arr = json.loads(cookies_raw)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"Invalid LINKEDIN_COOKIES_JSON: {e}"))
                return
            if not isinstance(arr, list):
                self.stdout.write(self.style.ERROR("LINKEDIN_COOKIES_JSON must be a JSON array."))
                return
            data = _convert_cookies_to_playwright(arr)

        if data is None or "cookies" not in data:
            self.stdout.write(
                self.style.ERROR("Storage state must include 'cookies' (Playwright format).")
            )
            return

        handle = _derive_handle(email)
        path = COOKIES_DIR / f"{handle}.json"
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote cookie file for {handle} → {path}"))
