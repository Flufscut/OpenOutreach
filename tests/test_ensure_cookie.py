"""Tests for ensure_cookie_from_env management command."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from linkedin.conf import COOKIES_DIR
from linkedin.cookie_utils import convert_cookies_to_playwright, derive_handle


class TestDeriveHandle:
    def test_email_to_handle(self):
        assert derive_handle("peter.mcgraw@mapledx.com") == "peter_mcgraw"
        assert derive_handle("user+tag@example.com") == "user_tag"
        assert derive_handle("UPPER@test.com") == "upper"


class TestConvertCookiesToPlaywright:
    def test_converts_browser_extension_format(self):
        """Browser extension format → Playwright storage state."""
        cookies = [
            {
                "domain": ".linkedin.com",
                "name": "li_at",
                "value": "AQEDAROf9EIF3liaAAAB",
                "path": "/",
                "expirationDate": 1804819924.0,
                "httpOnly": True,
                "secure": True,
                "sameSite": "no_restriction",
            },
        ]
        out = convert_cookies_to_playwright(cookies)
        assert "cookies" in out
        assert len(out["cookies"]) == 1
        c = out["cookies"][0]
        assert c["name"] == "li_at"
        assert c["value"] == "AQEDAROf9EIF3liaAAAB"
        assert c["domain"] == ".linkedin.com"
        assert c["path"] == "/"
        assert c["expires"] == 1804819924
        assert c["httpOnly"] is True
        assert c["secure"] is True
        assert c["sameSite"] == "None"

    def test_session_cookie_expires_minus_one(self):
        """Session cookies get expires=-1."""
        cookies = [
            {"domain": ".linkedin.com", "name": "lang", "value": "en", "session": True},
        ]
        out = convert_cookies_to_playwright(cookies)
        assert out["cookies"][0]["expires"] == -1

    def test_samesite_mapping(self):
        """sameSite values map correctly."""
        for raw, expected in [("no_restriction", "None"), ("lax", "Lax"), ("strict", "Strict")]:
            out = convert_cookies_to_playwright(
                [{"domain": ".x.com", "name": "x", "value": "1", "sameSite": raw}]
            )
            assert out["cookies"][0]["sameSite"] == expected


@pytest.mark.django_db
class TestEnsureCookieFromEnvCommand:
    def test_skips_when_no_env_vars(self):
        """No cookie env vars → command does nothing."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        with patch.dict(
            os.environ,
            {
                "LINKEDIN_COOKIES_B64": "",
                "LINKEDIN_COOKIES_JSON": "",
                "LINKEDIN_STORAGE_STATE_B64": "",
                "LINKEDIN_STORAGE_STATE": "",
            },
            clear=False,
        ):
            call_command("ensure_cookie_from_env", stdout=out)
        assert "Wrote" not in out.getvalue()

    def test_writes_cookie_file_from_b64(self, tmp_path):
        """LINKEDIN_COOKIES_B64 + LINKEDIN_EMAIL → writes cookie file."""
        from django.core.management import call_command
        from io import StringIO

        cookies = [
            {"domain": ".linkedin.com", "name": "li_at", "value": "test_token", "path": "/"},
        ]
        b64 = base64.b64encode(json.dumps(cookies).encode()).decode()

        with patch("linkedin.management.commands.ensure_cookie_from_env.COOKIES_DIR", tmp_path):
            with patch.dict(
                os.environ,
                {"LINKEDIN_COOKIES_B64": b64, "LINKEDIN_EMAIL": "test@example.com"},
                clear=False,
            ):
                out = StringIO()
                call_command("ensure_cookie_from_env", stdout=out)
                assert "Wrote" in out.getvalue()

        cookie_file = tmp_path / "test.json"
        assert cookie_file.exists()
        data = json.loads(cookie_file.read_text())
        assert "cookies" in data
        assert any(c["name"] == "li_at" for c in data["cookies"])
