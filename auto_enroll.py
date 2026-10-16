"""BearTracks Sniper: watches a course in Schedule Builder and enrolls you when a seat opens.

Start it with run.bat (Windows) or run.sh (macOS/Linux). Every setting lives in .env next to
this file; the first run creates it from .env.example and asks for anything required.
"""
import getpass
import os
import re
import shutil
import time
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_TEMPLATE_PATH = BASE_DIR / ".env.example"
# Kept between runs so the browser stays signed in and MFA isn't needed every time
PROFILE_DIR = BASE_DIR / "browser-profile"

# User settings belong in .env. These describe the BearTracks site itself and only
# need changing if the university changes its pages.
PORTAL_URL = "https://www.beartracks.ualberta.ca/"
SSO_BUTTON = "img[alt='Click for single sign-on']"
SCHEDULE_BUILDER_LINK = "text=My Schedule Builder"
TERM_LINKS = "a[href^='javascript:UU.caseTermContinue(']"

QUESTIONS = [
    ("UOFA_USERNAME", "Your CCID (the part before @ualberta.ca)", {}),
    ("UOFA_PASSWORD", "Your CCID password (hidden as you type)", {"secret": True}),
    ("COURSE_IDENTIFIER", "Course to watch, as shown in Schedule Builder (e.g. INT D 249)", {}),
    ("DISCORD_WEBHOOK_URL", "Discord webhook URL for alerts (optional, press Enter to skip)", {"required": False}),
    ("DISCORD_USER_ID", "Your Discord user ID so alerts ping you (optional, press Enter to skip)", {"required": False}),
]


def ask(prompt, secret=False, required=True):
    read = getpass.getpass if secret else input
    while True:
        value = read(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("  This one is required.")


def should_ask(key, required, first_run):
    value = os.getenv(key)
    if value:
        return False
    if required:
        return True
    # Optional settings are offered on the first run, or if the key is missing from an older .env.
    # After that an empty value means "off", so we don't nag every time.
    if key == "DISCORD_USER_ID" and not os.getenv("DISCORD_WEBHOOK_URL"):
        return False
    return first_run or value is None


def int_setting(key, default):
    value = os.getenv(key) or str(default)
    if not value.isdigit():
        raise SystemExit(f"{key} in .env must be a whole number, but it's '{value}'.")
    return int(value)


def load_config():
    """Create .env from the template if needed, ask for anything missing, then return all settings."""
    first_run = not ENV_PATH.exists()
    if first_run:
        shutil.copy(ENV_TEMPLATE_PATH, ENV_PATH)
        print("First-time setup. Answers are saved to .env in this folder, along with every other setting.\n")
    load_dotenv(ENV_PATH)

    for key, prompt, options in QUESTIONS:
        if should_ask(key, options.get("required", True), first_run):
            value = ask(prompt, **options)
            set_key(ENV_PATH, key, value)
            os.environ[key] = value

    return {
        "username": os.environ["UOFA_USERNAME"],
        "password": os.environ["UOFA_PASSWORD"],
        "course": os.environ["COURSE_IDENTIFIER"],
        "webhook": os.getenv("DISCORD_WEBHOOK_URL", ""),
        "discord_user_id": os.getenv("DISCORD_USER_ID", ""),
        "check_interval": int_setting("CHECK_INTERVAL_SECONDS", 30),
        "login_failure_threshold": int_setting("LOGIN_FAILURE_NOTIFY_THRESHOLD", 3),
    }


def notify(config, message):
    print(message)
    if not config["webhook"]:
        return
    if config["discord_user_id"]:
        message = f"<@{config['discord_user_id']}> {message}"
    try:
        requests.post(config["webhook"], json={"content": message}, timeout=10)
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")


def select_term(page):
    """Click the saved term, or list the available terms and let the user pick one the first time."""
    links = page.locator(TERM_LINKS)
    links.first.wait_for()

    term_id = os.getenv("TERM_ID")
    if not term_id:
        terms = []
        for i in range(links.count()):
            link = links.nth(i)
            match = re.search(r"caseTermContinue\((\d+)\)", link.get_attribute("href") or "")
            if match:
                terms.append((match.group(1), link.inner_text().strip() or f"Term {match.group(1)}"))

        print("\nWhich term is the course in?")
        for number, (_, name) in enumerate(terms, start=1):
            print(f"  {number}. {name}")
        term_id = None
        while term_id is None:
            choice = input("Type the number or the term name: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(terms):
                term_id = terms[int(choice) - 1][0]
                continue
            # Accept "Fall 2026" or just "fall", as long as it matches exactly one term
            matches = [tid for tid, name in terms if choice and choice.lower() in name.lower()]
            if len(matches) == 1:
                term_id = matches[0]
            else:
                print(f"  Didn't match one term. Type a number from 1 to {len(terms)}.")
        set_key(ENV_PATH, "TERM_ID", term_id)
        os.environ["TERM_ID"] = term_id

    term_link = page.locator(f"a[href='javascript:UU.caseTermContinue({term_id});']")
    if term_link.count() == 0:
        raise RuntimeError(f"Term {term_id} isn't listed anymore. Delete the TERM_ID line in .env to pick again.")
    term_link.first.click()
    page.wait_for_load_state("networkidle")


def open_schedule_builder(page, config):
    """Log in through the portal, open My Schedule Builder and select the term.
    Schedule Builder opens as a popup, so this returns that new tab — the caller must use it from then on."""
    page.goto(PORTAL_URL)
    sso_button = page.locator(SSO_BUTTON)
    schedule_builder_link = page.locator(SCHEDULE_BUILDER_LINK)

    # The saved browser profile may still be signed in, in which case the login steps are skipped
    sso_button.or_(schedule_builder_link).first.wait_for()
    if sso_button.count() > 0:
        sso_button.click()
        username_field = page.locator("#username")
        username_field.or_(schedule_builder_link).first.wait_for()
        if username_field.count() > 0:
            username_field.fill(config["username"])
            page.locator("#user_pass").fill(config["password"])
            page.keyboard.press("Enter")
            print("Logging in... if you're asked for MFA, approve it in the browser window.")

    schedule_builder_link.wait_for()
    with page.expect_popup() as popup_info:
        schedule_builder_link.click()
    schedule_builder_page = popup_info.value
    schedule_builder_page.wait_for_load_state("domcontentloaded")

    select_term(schedule_builder_page)
    return schedule_builder_page


def find_seat_span(page, course):
    seat_span = page.locator(
        f"xpath=//h4[@class='course_title'][contains(@aria-label, '{course}')]"
        f"/following::span[@class='seatText'][1]"
    )
    try:
        seat_span.wait_for(timeout=60_000)
    except PlaywrightTimeout:
        print(
            f"Still can't find {course} on the page. Make sure it's added to your courses in "
            f"Schedule Builder and the name matches exactly. Waiting..."
        )
        seat_span.wait_for()
    return seat_span


def enroll(page):
    page.locator("text=Get this Schedule").click()

    do_actions_button = page.locator("input[value='Do Actions']")
    do_actions_button.wait_for()
    do_actions_button.scroll_into_view_if_needed()
    do_actions_button.click()

    confirm_button = page.locator("input.big_button.pbut1")
    confirm_button.wait_for()
    confirm_button.click()


def launch_browser(p):
    options = {"user_data_dir": str(PROFILE_DIR), "headless": False}
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **options)
    except PlaywrightError:
        print("Google Chrome not found, using Playwright's built-in Chromium instead.")
        return p.chromium.launch_persistent_context(**options)


def watch_and_enroll(config):
    course = config["course"]
    with sync_playwright() as p:
        context = launch_browser(p)
        # BearTracks can be very slow, so never give up waiting on a page
        context.set_default_timeout(0)

        start_page = context.pages[0] if context.pages else context.new_page()
        schedule_builder_page = open_schedule_builder(start_page, config)
        start_page.close()
        seat_span = find_seat_span(schedule_builder_page, course)

        previous_value = None
        consecutive_login_failures = 0

        notify(config, f"BearTracks Sniper started — watching {course} for an opening.")
        while True:
            try:
                schedule_builder_page.reload(wait_until="networkidle")

                # Check if we got bounced to a login page instead of Schedule Builder
                if schedule_builder_page.locator("#username").count() > 0:
                    notify(config, f"Session expired while watching {course} — logging back in automatically.")
                    try:
                        stale_page = schedule_builder_page
                        schedule_builder_page = open_schedule_builder(stale_page, config)
                        stale_page.close()
                        seat_span = find_seat_span(schedule_builder_page, course)
                        consecutive_login_failures = 0
                        notify(config, "Logged back in — resuming the watch.")
                    except Exception as relogin_error:
                        consecutive_login_failures += 1
                        print(f"Relogin failed (attempt {consecutive_login_failures}): {relogin_error}")
                        if consecutive_login_failures == config["login_failure_threshold"]:
                            notify(
                                config,
                                f"Login has failed {consecutive_login_failures} times in a row while watching "
                                f"{course} — something may be wrong (site changed, bad credentials, etc). "
                                f"Still retrying automatically, but you may want to check.",
                            )
                        time.sleep(config["check_interval"])
                        continue

                seat_span.wait_for()
                seat_span.scroll_into_view_if_needed()

                seat_text = seat_span.inner_text().strip()
                print(f"{time.strftime('%H:%M:%S')}  {course}: {seat_text}")

                first_number = int(seat_text.split("/")[0].strip())

                if previous_value is not None and first_number < previous_value:
                    notify(config, f"Seat opened in {course} ({seat_text}) — enrolling now.")
                    enroll(schedule_builder_page)
                    notify(config, f"Submitted enrollment for {course}. Check BearTracks to confirm it went through.")
                    input("\nPress Enter to close the browser...")
                    return

                previous_value = first_number

            except Exception as e:
                print(f"Error during check, will retry: {e}")

            time.sleep(config["check_interval"])


def main():
    config = load_config()
    print(f"\nOpening a browser to watch {config['course']}. Leave this window open; press Ctrl+C to stop.\n")
    try:
        watch_and_enroll(config)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
