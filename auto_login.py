from playwright.sync_api import sync_playwright
import time
import os
from dotenv import load_dotenv
#activate env source venv/Scripts/activate
load_dotenv()

UOFA_USERNAME = os.getenv("UOFA_USERNAME")
UOFA_PASSWORD = os.getenv("UOFA_PASSWORD")

def open_beartracks_and_login():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\Sheldon Tang\AppData\Local\Google\Chrome\User Data\Default",
        headless=False
        )
        page = browser.new_page()

        print("Opening Bear Tracks...")
        page.goto("https://www.beartracks.ualberta.ca/")
        page.wait_for_timeout(5000) 

        print("Clicking 'Single Sign-On'...")
        sign_on_button = page.locator("#button")
        if sign_on_button.count() > 0:
            sign_on_button.first.click()
            time.sleep(2)
        else:
            print("'Single Sign-On' button not found.")
            return

        username_input = page.locator("#username")
        if username_input.count() > 0:
            username_input.fill(UOFA_USERNAME)
        else:
            print("Username field not found.")
            return

        password_input = page.locator("#user_pass")
        if password_input.count() > 0:
            password_input.fill(UOFA_PASSWORD)
        else:
            print("Password field not found.")
            return
        page.keyboard.press("Enter")
        time.sleep(10)

        print("Navigating to My Schedule Builder...")
        schedule_builder_button = page.locator("text=My Schedule Builder")
        if schedule_builder_button.count() > 0:
            schedule_builder_button.click()
            print("Successfully opened My Schedule Builder!")
        else:
            print("'My Schedule Builder' button not found.")


        input("Press ENTER to close the browser after checking your schedule.")
        browser.close()

open_beartracks_and_login()
