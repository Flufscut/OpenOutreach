"""
Shared utilities for LinkedIn cookie handling.

Used by ensure_cookie_from_env management command and the LinkedIn Login web view.
"""


def derive_handle(email: str) -> str:
    """Same logic as onboarding: email slug → handle."""
    return email.split("@")[0].lower().replace(".", "_").replace("+", "_")


def convert_cookies_to_playwright(cookies: list) -> dict:
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
