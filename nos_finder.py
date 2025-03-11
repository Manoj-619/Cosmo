import time
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
    # You can add more options if needed
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )
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
        # Append a tuple of the option text and the error message to the shared list
        failed_options.append((option_text, error_message))
    finally:
        time.sleep(2)
        driver.quit()

def get_dropdown_options():
    driver = create_driver()
    driver.get(base_url)
    # Accept cookies and click advanced search.
    try:
        WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="ccc-notify-accept"]'))
        )
        driver.find_element(By.XPATH, '//*[@id="ccc-notify-accept"]').click()
    except Exception:
        pass
    WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="nos-finder-detailed"]/div[1]/div[6]/button'))
    )
    adv_search_button = driver.find_element(By.XPATH, '//*[@id="nos-finder-detailed"]/div[1]/div[6]/button')
    driver.execute_script("arguments[0].click();", adv_search_button)
    
    WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.ID, 'suites')))
    first_dropdown = driver.find_element(By.ID, 'suites')
    options = first_dropdown.find_elements(By.TAG_NAME, 'option')
    option_texts = [opt.text for opt in options if opt.text.strip() != '']
    driver.quit()
    return option_texts

if __name__ == "__main__":
    # First, get all dropdown options.
    options = get_dropdown_options()
    print("Total options:", len(options))
    
    # Create a Manager list to store failed options.
    with Manager() as manager:
        failed_options = manager.list()
        
        # Use a pool of workers with 4 processes.
        with Pool(processes=4) as pool:
            pool.map(partial(process_option, failed_options=failed_options), options)
        
        # Write the failed options to a file for later review.
        if failed_options:
            with open("failed_options.txt", "w") as f:
                for option, error in failed_options:
                    f.write(f"{option}: {error}\n")
            print(f"Failed options written to 'failed_options.txt'.")
        else:
            print("All options processed successfully.")
    
    print("Processing complete.")
