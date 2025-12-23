import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="DataScraper Pro", layout="wide")

# --- UI STYLE ---
st.title("🚀 Professional Product Data Scraper")
st.markdown("Upload links or an Excel file to extract Amazon-style product specifications.")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Scraper Configuration")
char_limit = st.sidebar.slider("Max Character Limit", 100, 500, 300)
delay = st.sidebar.slider("Delay between links (seconds)", 0.5, 3.0, 1.0)

# --- HELPER FUNCTIONS ---
def clean_text(text):
    """Removes special characters and trims length."""
    if not text: return "N/A"
    # Removes non-standard characters but keeps basic punctuation
    cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
    return cleaned.strip()[:char_limit]

def find_specific_data(soup, keywords):
    """Searches the page for specific labels and returns the following text."""
    for word in keywords:
        element = soup.find(string=re.compile(word, re.I))
        if element:
            # Try to get the parent or the next sibling text
            return clean_text(element.find_next().get_text() if element.find_next() else element)
    return "Not Found"

def scrape_url(url):
    """Main scraping logic."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return {"URL": url, "Error": f"Site blocked or down (Code {response.status_code})"}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        raw_text = soup.get_text().lower()

        # Requirement 4: Auto-generation logic for missing info
        data = {
            "URL": url,
            "Product Description": clean_text(soup.find('title').text if soup.find('title') else "Missing"),
            "Product Expiry (y/n)": "Y" if any(x in raw_text for x in ["expiry", "expiration", "exp date"]) else "N",
            "Hazmat(y/n)": "Y" if any(x in raw_text for x in ["hazmat", "flammable", "corrosive"]) else "N",
            "Ingredients list": find_specific_data(soup, ["Ingredients", "Components"]),
            "Safety Warning": find_specific_data(soup, ["Safety Warning", "Warning"]),
            "Directions": find_specific_data(soup, ["Directions", "How to use", "Instructions"]),
            "Flavor": find_specific_data(soup, ["Flavor", "Taste"]),
            "Target Gender": "Men" if "men" in raw_text else ("Women" if "women" in raw_text else "Unisex"),
            "Item Form": find_specific_data(soup, ["Item Form", "Format", "Type"]),
            "Primary Supplement Type": find_specific_data(soup, ["Supplement Type", "Main Ingredient"]),
            "Quantity": find_specific_data(soup, ["Quantity", "Count", "Unit Count"]),
            "Product Dimensions": find_specific_data(soup, ["Product Dimensions", "Size"]),
            "Generic Keywords": clean_text(soup.find('meta', attrs={'name': 'keywords'})['content'] if soup.find('meta', attrs={'name': 'keywords'}) else "N/A")
        }
        
        # Placeholder for complex items (Best efforts auto-detection)
        data["Casepack Quantity"] = "1" if "casepack" not in raw_text else find_specific_data(soup, ["Casepack"])
        
        return data
    except Exception as e:
        return {"URL": url, "Error": str(e)}

# --- UI LAYOUT ---
# 1. Bar to upload Excel
uploaded_file = st.file_uploader("Upload Excel with 'Link' column", type=["xlsx", "csv"])

# 2. Bar to paste multiple links
manual_links = st.text_area("Or paste links (one per line):", height=150)

if st.button("🔍 Run Scraper"):
    all_links = []
    if uploaded_file:
        df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        if 'Link' in df_in.columns:
            all_links.extend(df_in['Link'].dropna().tolist())
    
    if manual_links:
        all_links.extend([l.strip() for l in manual_links.split('\n') if l.strip()])

    if all_links:
        # 3. Progress Bar
        progress_bar = st.progress(0)
        results = []
        
        for i, link in enumerate(all_links):
            st.write(f"Scanning: {link[:50]}...")
            res = scrape_url(link)
            results.append(res)
            progress_bar.progress((i + 1) / len(all_links))
            time.sleep(delay) # To prevent getting banned

        final_df = pd.DataFrame(results)
        st.success("Scraping Complete!")
        st.dataframe(final_df) # Preview Table

        # 4. Download Bar
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Excel Results",
            data=output.getvalue(),
            file_name="scraped_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("No links detected. Please upload a file or paste URLs.")
