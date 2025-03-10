from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
import pandas as pd
import time
from webdriver_manager.chrome import ChromeDriverManager

def scrape_tquk():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Navigate to the page
        print("Navigating to page...")
        driver.get("https://www.tquk.org/qualifications-search-engine")
        
        # Wait for page to load
        time.sleep(3)
        
        # Handle cookie popup if present
        try:
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "hs-eu-confirmation-button"))
            )
            cookie_button.click()
            print("Cookie popup accepted")
            time.sleep(2)
        except Exception:
            print("No cookie popup detected.")
        
        # Switch to the iframe where the content is loaded
        print("Switching to searchFrame iframe...")
        iframe = driver.find_element(By.ID, "searchFrame")
        driver.switch_to.frame(iframe)

        # Click "Show More" button repeatedly until no more results
        clicks = 0
        max_attempts = 50  # Set a maximum number of attempts

        while clicks < max_attempts:
            try:
                # Wait for the button to be present
                show_more = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Show More')]"))
                )

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", show_more)
                    time.sleep(1)
                    
                    try:
                        show_more.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)
                        show_more.click()
                        
                except ElementClickInterceptedException:
                    print("Click intercepted, trying JavaScript click...")
                    driver.execute_script("arguments[0].click();", show_more)

                clicks += 1
                print(f"Clicked 'Show More' button {clicks} times")
                time.sleep(3)  # Wait for new results to load

            except Exception:
                print(f"\nNo more 'Show More' buttons after {clicks} clicks.")
                break

        print("\nFinished clicking. Extracting qualification data...")

        # Extract the data
        qualifications = []

        # Find all qualification tiles
        tiles = driver.find_elements(By.CSS_SELECTOR, ".sv-tile.sv-imageless")

        print(f"Found {len(tiles)} qualification tiles")

        for tile in tiles:
            try:
                # Extract Ofqual ID
                ofqual_id_element = tile.find_element(By.CSS_SELECTOR, "h4.sv-tile__subtitle")
                ofqual_id = ofqual_id_element.text.strip()

                # Extract PDF URL (Download Specifications link)
                pdf_link_element = tile.find_elements(By.XPATH, ".//div[@class='sv-tile__btn-wrap']/a[contains(text(), 'Download specifications')]")
                pdf_url = pdf_link_element[0].get_attribute("href") if pdf_link_element else "No PDF"

                qualifications.append({"Ofqual ID": ofqual_id, "PDF URL": pdf_url})

            except NoSuchElementException:
                print("Error extracting data from tile, skipping...")

        # Save results to Excel
        df = pd.DataFrame(qualifications)
        df.to_excel("tquk_qualifications.xlsx", index=False)
        print("\nExcel file 'tquk_qualifications.xlsx' created successfully.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_tquk()
