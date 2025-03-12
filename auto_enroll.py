from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

UOFA_USERNAME = os.getenv("UOFA_USERNAME")
UOFA_PASSWORD = os.getenv("UOFA_PASSWORD")

def auto_enroll():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\Sheldon Tang\AppData\Local\Google\Chrome\User Data\Default",
            headless=False
        )

        page = browser.pages[0]

        page.goto("https://www.beartracks.ualberta.ca/")
        page.wait_for_selector("img[alt='Click for single sign-on']", timeout=10000)
        page.locator("img[alt='Click for single sign-on']").click()

        page.wait_for_selector("#username", timeout=10000)
        page.locator("#username").fill(UOFA_USERNAME)

        page.wait_for_selector("#user_pass", timeout=10000)
        page.locator("#user_pass").fill(UOFA_PASSWORD)

        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")

        with page.expect_popup() as new_page_info:
            page.wait_for_selector("text=My Schedule Builder", timeout=10000)
            page.locator("text=My Schedule Builder").click()
            print("Opened My Schedule Builder!")

        schedule_builder_page = new_page_info.value
        schedule_builder_page.wait_for_load_state("domcontentloaded")
        print("Switched to My Schedule Builder page!")

        term_link_xpath = "//a[@href='javascript:UU.caseTermContinue(1930);']"

        schedule_builder_page.wait_for_selector(term_link_xpath, timeout=10000)
        term_link = schedule_builder_page.locator(term_link_xpath)

        if term_link.count() > 0:
            print("Found the correct term link!")
            term_link.first.click()
        else:
            print("Could not find the term selection link.")

        input("Press ENTER to close the browser")
        browser.close()

auto_enroll()
