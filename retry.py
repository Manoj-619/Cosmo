import time
import os
from multiprocessing import Pool, Manager
from functools import partial
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

base_url = 'https://www.ukstandards.org.uk/en/nos-finder'

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")           # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def process_option(option_text, failed_options):
    # Each process creates its own headless driver instance.
    driver = create_driver()
    try:
        driver.get(base_url)
        # Accept cookies if present.
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="ccc-notify-accept"]'))
            )
            driver.find_element(By.XPATH, '//*[@id="ccc-notify-accept"]').click()
        except Exception:
            pass

        # Click advanced search.
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="nos-finder-detailed"]/div[1]/div[6]/button'))
        )
        adv_search_button = driver.find_element(By.XPATH, '//*[@id="nos-finder-detailed"]/div[1]/div[6]/button')
        driver.execute_script("arguments[0].click();", adv_search_button)

        # Wait for dropdown and select the option.
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, 'suites')))
        first_dropdown = driver.find_element(By.ID, 'suites')
        select = Select(first_dropdown)
        select.select_by_visible_text(option_text)
        time.sleep(1)

        # Click the "Find NOS" button.
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="nos-finder-detailed"]/div[3]/div[1]/button'))
        )
        find_nos_button = driver.find_element(By.XPATH, '//*[@id="nos-finder-detailed"]/div[3]/div[1]/button')
        driver.execute_script("arguments[0].click();", find_nos_button)
        
        # Click the "Download" button.
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/main/section[3]/div[2]/div[2]/button'))
        )
        download_button = driver.find_element(By.XPATH, '/html/body/main/section[3]/div[2]/div[2]/button')
        driver.execute_script("arguments[0].click();", download_button)
        
        print(f"Processed option: {option_text}")
    except Exception as e:
        error_message = str(e)
        print(f"Error processing {option_text}: {error_message}")
        # Append a tuple of the option text and error message to the shared list.
        failed_options.append((option_text, error_message))
    finally:
        time.sleep(2)
        driver.quit()

def retry_failed_options(file_path="failed_options.txt"):
    # Read failed options from the file.
    with open(file_path, "r") as f:
        lines = f.readlines()
    options_to_retry = []
    for line in lines:
        # Each line is expected to be "option_text: error_message"
        parts = line.split(":", 1)
        if parts:
            option = parts[0].strip()
            if option:
                options_to_retry.append(option)
    if not options_to_retry:
        print("No options to retry.")
        return

    print("Retrying options:", options_to_retry)
    with Manager() as manager:
        new_failed_options = manager.list()
        with Pool(processes=4) as pool:
            pool.map(partial(process_option, failed_options=new_failed_options), options_to_retry)
        if new_failed_options:
            with open("failed_options_retry.txt", "w") as f:
                for option, error in new_failed_options:
                    f.write(f"{option}: {error}\n")
            print("Retry: Failed options written to 'failed_options_retry.txt'.")
        else:
            print("All retried options processed successfully.")

if __name__ == "__main__":
    # Check if the failed_options.txt file exists and is not empty.
    if os.path.exists("failed_options.txt"):
        with open("failed_options.txt", "r") as f:
            content = f.read().strip()
        if content:
            print("Processing only the options listed in 'failed_options.txt'...")
            retry_failed_options("failed_options.txt")
        else:
            print("No failed options found in 'failed_options.txt'.")
    else:
        print("'failed_options.txt' does not exist. Nothing to process.")

    print("Processing complete.")
