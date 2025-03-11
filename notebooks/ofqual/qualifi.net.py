import pandas as pd
from playwright.sync_api import sync_playwright
import re  # For regex pattern matching

# # Load the DataFrame with Ofqual IDs (this is still used to load/filter data but not for validation)
# df3 = pd.read_csv(r"C:\Users\amith\Downloads\ofqual_details_20250127.csv\ofqual_details_20250127.csv")
# new_df = df3[df3['status'] == "Available to learners"]
# qualifi_df = new_df[new_df["specification"] == "https://qualifi.net/qualifications/"]

# The list of Ofqual IDs is no longer used for validation
# ofqual_ids = qualifi_df["qualification_number"].astype(str).tolist()  

# Updated regex pattern to handle digits or a letter after the last slash
ofqual_pattern = r"\b\d{3}/\d{4}/[\dA-Za-z]\b"

def scrape_ofqual_links(url):
    extracted_links = []  # We'll store each extracted pair in a list of dictionaries

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True if you don't need the browser window
        page = browser.new_page()
        page.goto(url)

        # Find all dropdowns using the class "eael-accordion-list"
        dropdowns = page.locator(".eael-accordion-list").all()

        for dropdown in dropdowns:
            dropdown.click()  # Click dropdown to reveal links
            page.wait_for_timeout(1000)  # Wait for content to load

            # Find all options inside the dropdown
            items = page.locator(".elementor-icon-list-item").all()

            for item in items:
                text_element = item.locator(".elementor-icon-list-text")
                text = text_element.inner_text()
                href = item.locator("a").get_attribute("href")  # Find link inside the item

                # Extract Ofqual ID from text using the regex pattern
                match = re.search(ofqual_pattern, text)
                if match:
                    extracted_id = match.group()  # Use the matched Ofqual ID
                else:
                    extracted_id = text  # If no match, use the full text

                extracted_links.append({"Ofqual ID": extracted_id, "URL": href})

        browser.close()

    return extracted_links

# Run the scraper
url = "https://qualifi.net/qualifications/"
result = scrape_ofqual_links(url)

# Output the result dictionary (list of dictionaries)
print(result)

# Save the result to Excel
result_df = pd.DataFrame(result)
result_df.to_excel("extracted_ofqual_links.xlsx", index=False)

print("Extraction complete and results saved to Excel.")
