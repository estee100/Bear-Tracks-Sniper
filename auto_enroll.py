from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import time

load_dotenv()

UOFA_USERNAME = os.getenv("UOFA_USERNAME")
UOFA_PASSWORD = os.getenv("UOFA_PASSWORD")

def auto_enroll():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\Sheldon Tang\AppData\Local\Google\Chrome\User Data\Default",
            headless=False
        )
        # Keeps track of current page
        page = browser.pages[0]

        # Open up beartracks
        page.goto("https://www.beartracks.ualberta.ca/")
        page.wait_for_selector("img[alt='Click for single sign-on']", timeout=10000)
        page.locator("img[alt='Click for single sign-on']").click()

        # Enter username and password
        page.wait_for_selector("#username", timeout=10000)
        page.locator("#username").fill(UOFA_USERNAME)
        page.wait_for_selector("#user_pass", timeout=10000)
        page.locator("#user_pass").fill(UOFA_PASSWORD)

        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        print("Logged in successfully")

        with page.expect_popup() as new_page_info:
            page.wait_for_selector("text=My Schedule Builder", timeout=10000)
            page.locator("text=My Schedule Builder").click()
            print("Opened My Schedule Builder")

        schedule_builder_page = new_page_info.value
        schedule_builder_page.wait_for_load_state("domcontentloaded")
        print("Switched to My Schedule Builder page")

        term_link_xpath = "//a[@href='javascript:UU.caseTermContinue(1930);']"

        schedule_builder_page.wait_for_selector(term_link_xpath, timeout=10000)
        term_link = schedule_builder_page.locator(term_link_xpath)

        if term_link.count() > 0:
            print("Found the correct term")
            term_link.first.click()
        else:
            print("Could not find the term selection link.")
            return

        schedule_builder_page.wait_for_selector("span.seatText", timeout=10000)

        # Keep checking for available seats
        print("Waiting for seats to open...")
        while True:
            schedule_builder_page.reload()
            time.sleep(5)

            # Get all seat elements
            seat_elements = schedule_builder_page.locator("span.seatText")

            for i in range(seat_elements.count()):
                seat_text = seat_elements.nth(i).inner_text().strip()
                available_seats = seat_text.split('/')[0].strip()

                if available_seats.isdigit() and int(available_seats) > 0:
                    print("Seat found. Proceeding to enroll")

                    # Click Get Schedule button
                    get_schedule_button = schedule_builder_page.locator("text=Get this Schedule")
                    get_schedule_button.click()
                    
                    # Click Do Actions button
                    schedule_builder_page.wait_for_selector("input[value='Do Actions']", timeout=10000)
                    do_actions_button = schedule_builder_page.locator("input[value='Do Actions']")
                    do_actions_button.click()

                    # Click Continue button
                    schedule_builder_page.wait_for_selector("input.big_button.pbut1", timeout=10000)
                    continue_button = schedule_builder_page.locator("input.big_button.pbut1")
                    continue_button.click()

                    print("Classes enrolled")
                    break 
            
            else:
                time.sleep(10)
                continue 

            break

auto_enroll()