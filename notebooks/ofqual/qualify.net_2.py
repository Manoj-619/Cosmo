import requests
from bs4 import BeautifulSoup
import pandas as pd

# Load the extracted Ofqual IDs and URLs from the Excel file
result_df = pd.read_excel(r"C:\Users\amith\Kenpath\zavmo-api\notebooks\ofqual\extracted_ofqual_links.xlsx")
url_dict = dict(zip(result_df['Ofqual ID'], result_df['URL']))  # Map Ofqual IDs to URLs

def scrape_pdf_link(url):
    pdf_link = None
    try:
        # Send a GET request to the URL
        response = requests.get(url, timeout=10)  # Set timeout for request (10 seconds)
        
        # Check if request was successful
        if response.status_code == 200:
            page_content = response.content

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')

            # Find the first <a> tag with a PDF link (i.e., href contains ".pdf")
            pdf_link_element = soup.find("a", href=lambda href: href and ".pdf" in href)

            if pdf_link_element:
                pdf_link = pdf_link_element['href']  # Extract the PDF link
                print(f"Found PDF link: {pdf_link}")
            else:
                print("No PDF link found on this page.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL {url}: {e}")

    return pdf_link

# Create a dictionary to store the Ofqual ID and corresponding PDF link
pdf_links = {}

# Iterate over each Ofqual ID and its corresponding URL
for ofqual_id, url in url_dict.items():
    print(f"Processing Ofqual ID: {ofqual_id} from URL: {url}")
    pdf_url = scrape_pdf_link(url)
    if pdf_url:
        pdf_links[ofqual_id] = pdf_url
    else:
        print(f"PDF link not found for Ofqual ID {ofqual_id} at {url}")

# Save the extracted PDF links to a new Excel file
pdf_links_df = pd.DataFrame(list(pdf_links.items()), columns=['Ofqual ID', 'PDF URL'])
pdf_links_df.to_excel(r"C:\Users\amith\Kenpath\zavmo-api\notebooks\ofqual\extracted_pdf_links.xlsx", index=False)

print("PDF links extraction complete and saved to Excel.")
