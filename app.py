
import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import re, time, io

# --- PROFESSIONAL UI CONFIG ---
st.set_page_config(page_title="Bulk Product Data Extractor", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; font-family: 'Segoe UI', sans-serif; }
    h1, h2 { color: #1a3a5f !important; }
    .stButton>button { background-color: #0056b3 !important; color: white !important; border-radius: 4px; border: none; font-weight: 500; width: 100%; height: 3em; }
    .stDownloadButton>button { background-color: #28a745 !important; color: white !important; width: 100%; font-weight: bold; border: none; padding: 0.75rem; }
    .stTextArea textarea { border: 1px solid #ced4da !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SCRAPING ENGINE SETUP ---
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

# Comprehensive Keyword Map for 27 Fields
KEYWORD_MAP = {
    "Product Expiration Type": ["Expiration Type", "Date Code Type", "EXP Format"],
    "Product Expiry (y/n)": ["Expiry", "Expiration", "EXP Date"],
    "Shelf life": ["Shelf life", "Storage Life", "Duration"],
    "CPSIA Warning": ["CPSIA", "Choking Hazard", "Small parts"],
    "Legal disclaimer": ["Legal disclaimer", "Disclaimer", "FDA Statement"],
    "Safety Warning": ["Safety Warning", "Warning", "Precautions", "Cautions"],
    "Indications": ["Indications", "Recommended use", "Uses"],
    "Generic Keywords": ["Keywords", "Search Terms", "Tags"],
    "Age Range Description": ["Age Range", "Recommended Age", "Adult", "Kids"],
    "Item Form": ["Item Form", "Format", "Capsule", "Tablet", "Powder", "Liquid"],
    "Primary Supplement Type": ["Supplement Type", "Main Ingredient", "Primary Ingredient"],
    "Directions": ["Directions", "How to use", "Suggested Use", "Dosage"],
    "Flavor": ["Flavor", "Taste", "Scent"],
    "Target Gender": ["Target Gender", "Gender", "For Men", "For Women"],
    "Product Benefits": ["Benefits", "Features", "Why use this", "Key Benefits"],
    "Specific Uses": ["Specific Uses", "Indicated for", "Used for"],
    "Ingredients list": ["Ingredients", "Supplement Facts", "Active Ingredients"],
    "Allergen Information": ["Allergen", "Contains", "Free from", "Allergy"],
    "Casepack Quantity": ["Casepack Quantity", "Case qty", "Units per case"],
    "Quantity": ["Quantity", "Count", "Unit Count", "Size"],
    "Casepack Dimensions": ["Casepack Dimensions", "Case Size"],
    "Days of use": ["Days of use", "Supply length", "Servings per container"],
    "Product Dimensions": ["Product Dimensions", "Item Dimensions", "Size"],
    "Package dimensions": ["Package dimensions", "Shipping Dimensions"],
    "Hazmat(y/n)": ["Hazmat", "Flammable", "Dangerous Goods"],
    "Product description": ["Description", "About this item", "Product Detail"]
}

def extract_node_data(url):
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(5) # Wait for JS to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        full_text = soup.get_text().lower()
        
        results = {"Source URL": url}
        
        for field, keywords in KEYWORD_MAP.items():
            found = False
            for k in keywords:
                # Binary checks
                if "(y/n)" in field:
                    results[field] = "Y" if k.lower() in full_text else "N"
                    found = True
                    break
                # Content extraction
                match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                if match:
                    val = match.find_next().get_text(strip=True) if match.find_next() else ""
                    if len(val) > 2:
                        results[field] = re.sub(r'[^\w\s.,!?-]', '', val).strip()[:500]
                        found = True
                        break
            if not found and "(y/n)" not in field:
                results[field] = "Not Found"

        results["Images Detected"] = len(soup.find_all('img'))
        results["Page Title"] = soup.title.string.strip() if soup.title else "N/A"
        
        return results
    except Exception as e:
        return {"Source URL": url, "Status": "Error", "Details": str(e)}

# --- UI LAYOUT ---
st.title("📋 Professional Bulk Data Extractor")
st.write("Paste multiple product links below to extract 27 data fields simultaneously.")

# Bulk Link Input
url_input = st.text_area("Paste Product URLs (one per line)", height=250, placeholder="https://www.brand.com/product-1\nhttps://www.brand.com/product-2")

start_btn = st.button("Initialize Extraction")

if start_btn:
    # Clean and split links
    links = [link.strip() for link in url_input.split('\n') if link.strip().startswith('http')]
    
    if links:
        st.info(f"Loaded {len(links)} links. Beginning extraction...")
        progress_bar = st.progress(0)
        final_results = []
        
        for i, link in enumerate(links):
            st.write(f"Scraping Link {i+1}: {link[:60]}...")
            data = extract_node_data(link)
            final_results.append(data)
            progress_bar.progress((i + 1) / len(links))
        
        df_out = pd.DataFrame(final_results)
        
        st.success("Extraction Complete.")
        st.dataframe(df_out)
        
        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False)
        st.download_button("📥 Download Final Excel Report", output.getvalue(), "bulk_extracted_data.xlsx")
    else:
        st.error("Please enter valid URLs starting with http:// or https://")
