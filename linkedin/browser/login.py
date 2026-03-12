# linkedin/browser/login.py
import logging
import time
from urllib.parse import unquote
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from termcolor import colored

from linkedin.browser.nav import goto_page, human_type

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

# When LinkedIn detects automation, it redirects to a challenge/verification page.
# We wait up to this many seconds for the user to complete it via VNC.
CHECKPOINT_WAIT_SECONDS = 300

SELECTORS = {
    "email": 'input#username',
    "password": 'input#password',
    "submit": 'button[type="submit"]',
}


def _wait_for_feed_after_submit(session: "AccountSession", submit_action) -> None:
    """
    Click submit and wait for redirect to /feed. If LinkedIn shows a checkpoint
    (verification) page, extend wait to CHECKPOINT_WAIT_SECONDS for the user to
    complete it via VNC.
    """
    page = session.page
    submit_action()

    # Initial wait for normal redirect (40s). Extended if checkpoint detected.
    deadline = time.monotonic() + 40
    poll_interval = 2
    last_checkpoint_log = 0

    while time.monotonic() < deadline:
        session.wait()
        current = unquote(page.url)

        if "/feed" in current:
            logger.debug("Navigated to %s", page.url)
            return

        if "/checkpoint/" in current:
            # Extend deadline to allow manual completion via VNC
            now = time.monotonic()
            if deadline - now < CHECKPOINT_WAIT_SECONDS - 10:
                deadline = now + CHECKPOINT_WAIT_SECONDS
            remaining = int(deadline - now)
            # Log at most every 60s to avoid spam
            if now - last_checkpoint_log >= 60:
                last_checkpoint_log = now
                logger.warning(
                    colored(
                        "LinkedIn checkpoint detected. Complete verification via VNC "
                        "(port 5900). Waiting %ds…",
                        "yellow",
                        attrs=["bold"],
                    )
                    % remaining
                )
            time.sleep(poll_interval)
            continue

        # Other URL (e.g. login error) – keep waiting briefly
        time.sleep(poll_interval)

    current = unquote(page.url)
    if "/checkpoint/" in current:
        raise RuntimeError(
            "LinkedIn requires verification. Connect via VNC (port 5900) to complete "
            "the challenge, or pre-authenticate locally and copy cookies to the volume."
        )
    raise RuntimeError(
        f"Login failed – no redirect to feed → expected '/feed' | got '{current}'"
    )


def playwright_login(session: "AccountSession"):
    page = session.page
    config = session.account_cfg
    logger.info(colored("Fresh login sequence starting", "cyan") + f" for @{session.handle}")

    goto_page(
        session,
        action=lambda: page.goto(LINKEDIN_LOGIN_URL),
        expected_url_pattern="/login",
        error_message="Failed to load login page",
    )

    human_type(page.locator(SELECTORS["email"]), config["username"])
    session.wait()
    human_type(page.locator(SELECTORS["password"]), config["password"])
    session.wait()

    _wait_for_feed_after_submit(
        session,
        lambda: page.locator(SELECTORS["submit"]).click(),
    )


def launch_browser(storage_state=None):
    logger.debug("Launching Playwright")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(storage_state=storage_state)
    Stealth().apply_stealth_sync(context)
    page = context.new_page()
    return page, context, browser, playwright


def start_browser_session(session: "AccountSession", handle: str):
    logger.debug("Configuring browser for @%s", handle)
    config = session.account_cfg
    state_file = Path(config["cookie_file"])

    storage_state = str(state_file) if state_file.exists() else None
    if storage_state:
        logger.info("Loading saved session for @%s", handle)

    session.page, session.context, session.browser, session.playwright = launch_browser(storage_state=storage_state)

    if not storage_state:
        playwright_login(session)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        session.context.storage_state(path=str(state_file))
        logger.info(colored("Login successful – session saved", "green", attrs=["bold"]) + f" → {state_file}")
    else:
        goto_page(
            session,
            action=lambda: session.page.goto(LINKEDIN_FEED_URL),
            expected_url_pattern="/feed",
            timeout=30_000,
            error_message="Saved session invalid",
        )

    session.page.wait_for_load_state("load")
    logger.info(colored("Browser ready", "green", attrs=["bold"]))


if __name__ == "__main__":
    import sys

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s │ %(message)s',
    )

    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.browser.login <handle>")
        sys.exit(1)

    handle = sys.argv[1]

    from linkedin.browser.registry import get_or_create_session
    session = get_or_create_session(handle=handle)

    session.ensure_browser()

    start_browser_session(session=session, handle=handle)
    print("Logged in! Close browser manually.")
    session.page.pause()
