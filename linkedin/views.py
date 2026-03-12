"""
Web views for the linkedin app.
"""

import json
import logging
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from linkedin.conf import COOKIES_DIR, RESTART_REQUESTED_PATH
from linkedin.cookie_utils import convert_cookies_to_playwright, derive_handle


logger = logging.getLogger(__name__)


def landing_page(request):
    """
    Root URL landing page. Lets users choose between CRM and Django Admin.
    """
    return render(request, "linkedin/landing.html")


@staff_member_required
@require_http_methods(["GET", "POST"])
def linkedin_login(request):
    """
    LinkedIn Login page: paste cookies or login with email/password.
    Staff-only. When cookies are saved, optionally restart daemon to apply.
    """
    from linkedin.conf import get_first_active_profile_handle
    from linkedin.models import LinkedInProfile

    # Get first active profile for pre-fill
    handle = get_first_active_profile_handle()
    profile = None
    if handle:
        profile = LinkedInProfile.objects.filter(active=True).select_related("user").first()
    default_email = (profile.linkedin_username if profile else "") or ""

    context = {
        "default_email": default_email,
        "handle": handle,
        "has_profile": bool(profile),
        "error": None,
        "success": None,
    }

    if request.method == "POST":
        action = request.POST.get("action")
        restart_requested = request.POST.get("restart_daemon") == "on"

        if action == "paste_cookies":
            cookies_json = request.POST.get("cookies_json", "").strip()
            email = request.POST.get("email", "").strip()

            if not email or "@" not in email:
                context["error"] = "Valid email is required."
                return render(request, "linkedin/linkedin_login.html", context)

            if not cookies_json:
                context["error"] = "Paste cookies (JSON array) from your browser extension."
                return render(request, "linkedin/linkedin_login.html", context)

            try:
                arr = json.loads(cookies_json)
            except json.JSONDecodeError as e:
                context["error"] = f"Invalid JSON: {e}"
                return render(request, "linkedin/linkedin_login.html", context)

            if not isinstance(arr, list):
                context["error"] = "Cookies must be a JSON array."
                return render(request, "linkedin/linkedin_login.html", context)

            data = convert_cookies_to_playwright(arr)
            handle = derive_handle(email)
            path = COOKIES_DIR / f"{handle}.json"
            COOKIES_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("LinkedIn Login UI: saved cookies for %s", handle)

            if restart_requested:
                RESTART_REQUESTED_PATH.touch()
                context["success"] = f"Cookies saved for {handle}. Daemon will restart shortly."
            else:
                context["success"] = f"Cookies saved for {handle}. Daemon will use them on next session."
            return render(request, "linkedin/linkedin_login.html", context)

        elif action == "email_password":
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "")

            if not email or "@" not in email:
                context["error"] = "Valid email is required."
                return render(request, "linkedin/linkedin_login.html", context)

            if not password:
                context["error"] = "Password is required."
                return render(request, "linkedin/linkedin_login.html", context)

            handle = derive_handle(email)
            cookie_file = COOKIES_DIR / f"{handle}.json"

            # Minimal session-like object for playwright_login
            class _LoginSession:
                def __init__(self):
                    self.handle = handle
                    self.account_cfg = {"username": email, "password": password}
                    self.page = None
                    self.context = None
                    self.browser = None
                    self.playwright = None

                def wait(self):
                    import random
                    import time
                    from linkedin.conf import MIN_DELAY, MAX_DELAY
                    delay = random.uniform(MIN_DELAY, MAX_DELAY)
                    time.sleep(delay)
                    if self.page:
                        self.page.wait_for_load_state("load")

            session = _LoginSession()

            try:
                from linkedin.browser.login import launch_browser, playwright_login

                session.page, session.context, session.browser, session.playwright = launch_browser(
                    storage_state=None
                )
                playwright_login(session)
                cookie_file.parent.mkdir(parents=True, exist_ok=True)
                session.context.storage_state(path=str(cookie_file))
                logger.info("LinkedIn Login UI: saved session for %s", handle)

                if restart_requested:
                    RESTART_REQUESTED_PATH.touch()
                    context["success"] = f"Login successful. Session saved for {handle}. Daemon will restart shortly."
                else:
                    context["success"] = f"Login successful. Session saved for {handle}."
            except Exception as e:
                logger.exception("LinkedIn Login UI: playwright login failed")
                context["error"] = str(e)
                if "checkpoint" in str(e).lower() or "verification" in str(e).lower():
                    context["error"] += " Connect via VNC (port 5900) to complete verification, then try again."
            finally:
                if session.context:
                    try:
                        session.context.close()
                    except Exception:
                        pass
                if session.browser:
                    try:
                        session.browser.close()
                    except Exception:
                        pass
                if session.playwright:
                    try:
                        session.playwright.stop()
                    except Exception:
                        pass

            return render(request, "linkedin/linkedin_login.html", context)

    return render(request, "linkedin/linkedin_login.html", context)
