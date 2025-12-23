import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import re
import time
import io
from googlesearch import search

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Professional Data Extractor", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; font-family: 'Segoe UI', sans-serif; }
    h1, h2 { color: #1a3a5f !important; }
    .stButton>button { background-color: #0056b3 !important; color: white !important; border-radius: 4px; border: none; font-weight: 500; width: 100%; }
    .stDownloadButton>button { background-color: #28a745 !important; color: white !important; width: 100%; font-weight: bold; border: none; }
    .stProgress > div > div > div > div { background-color: #0056b3 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SCRAPING ENGINE ---
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

# Massive Keyword Dictionary for 27 Fields
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
    "Target Gender": ["Gender", "Men", "Women", "Unisex"],
    "Product Benefits": ["Benefits", "Features", "Why use this", "Key Benefits"],
    "Specific Uses": ["Specific Uses", "Indicated for", "Used for"],
    "Ingredients list": ["Ingredients", "Supplement Facts", "Active Ingredients"],
    "Allergen Information": ["Allergen", "Contains", "Free from", "Allergy"],
    "Casepack Quantity": ["Casepack Quantity", "Case Qty", "Units per case"],
    "Quantity": ["Quantity", "Count", "Unit Count", "Size"],
    "Casepack Dimensions": ["Casepack Dimensions", "Case Size", "Case measurements"],
    "Days of use": ["Days of use", "Supply length", "Servings per container"],
    "Product Dimensions": ["Product Dimensions", "Item Dimensions", "Size"],
    "Package dimensions": ["Package dimensions", "Shipping Dimensions"],
    "Hazmat(y/n)": ["Hazmat", "Flammable", "Dangerous Goods", "Corrosive"],
    "Product description": ["Description", "About this item", "Product Detail"]
}

def smart_scrape(url):
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(5) # Allow JavaScript to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        full_text = soup.get_text().lower()
        
        results = {"URL": url}
        
        for field, keywords in KEYWORD_MAP.items():
            found = False
            for k in keywords:
                # Binary checks for Y/N fields
                if "(y/n)" in field:
                    results[field] = "Y" if k.lower() in full_text else "N"
                    found = True
                    break
                
                # Content extraction for other fields
                match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                if match:
                    val = match.find_next().get_text(strip=True) if match.find_next() else ""
                    if len(val) > 2:
                        results[field] = re.sub(r'[^\w\s.,!?-]', '', val).strip()[:400]
                        found = True
                        break
            if not found and "(y/n)" not in field:
                results[field] = "Not Found"

        # Image extraction
        imgs = soup.find_all('img', src=True)
        results["Images"] = f"{len(imgs)} images detected"
        
        return results
    except Exception as e:
        return {"Status": "Error", "Details": str(e)}

# --- UI INTERFACE ---
st.title("📋 Master Product Data Extractor")
st.write("Extract 27 key specifications by searching a specific website.")

# Top Bar for Link/Domain
target_domain = st.text_input("Enter Target Domain once (e.g., gnc.com or vitaminshoppe.com)", "gnc.com")

tab1, tab2 = st.tabs(["Input", "Output"])

with tab1:
    uploaded_file = st.file_uploader("Upload Excel with 'Item Name' column", type=["xlsx", "csv"])
    manual_names = st.text_area("Or paste Item Names manually (one per line)")
    start_btn = st.button("Start Intelligent Scraping")

if start_btn:
    items = []
    if uploaded_file:
        df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        col = next((c for c in df_in.columns if "name" in c.lower()), df_in.columns[0])
        items = df_in[col].dropna().tolist()
    elif manual_names:
        items = [i.strip() for i in manual_names.split('\n') if i.strip()]

    if items:
        st.info(f"Loaded {len(items)} items. Initializing extraction on {target_domain}...")
        progress_bar = st.progress(0)
        final_data = []

        for i, item in enumerate(items):
            st.write(f"Node {i+1}: Searching {item}...")
            try:
                query = f"site:{target_domain} {item}"
                link = next(search(query, num_results=1))
                data = smart_scrape(link)
                data["Item Identifier"] = item
                final_data.append(data)
            except:
                final_data.append({"Item Identifier": item, "Status": "Link Not Found"})
            progress_bar.progress((i + 1) / len(items))

        df_out = pd.DataFrame(final_data)
        with tab2:
            st.success("Protocol Complete.")
            st.dataframe(df_out)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_out.to_excel(writer, index=False)
            st.download_button("📥 Download Final Excel Report", output.getvalue(), "master_product_data.xlsx")
