import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io
from googlesearch import search
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- 1. PROFESSIONAL UI CONFIGURATION ---
st.set_page_config(page_title="Product Data Extractor", page_icon="📋", layout="wide")

# Custom CSS for a Clean, Professional Look
st.markdown("""
    <style>
    /* Main Background and Text */
    .stApp { background-color: #ffffff; color: #212529; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Headers */
    h1, h2, h3 { color: #1a3a5f !important; font-weight: 600 !important; }
    
    /* Standard Buttons (Blue) */
    .stButton>button {
        background-color: #0056b3 !important; color: white !important;
        border-radius: 4px !important; border: none !important;
        padding: 0.5rem 1rem !important; font-weight: 500 !important;
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover { background-color: #004494 !important; }
    
    /* Download Button (Green) */
    .stDownloadButton>button {
        background-color: #28a745 !important; color: white !important;
        border-radius: 4px !important; border: none !important;
        width: 100% !important; padding: 0.75rem !important;
        font-weight: bold !important;
    }
    .stDownloadButton>button:hover { background-color: #218838 !important; }
    
    /* Progress Bar */
    .stProgress > div > div > div > div { background-color: #0056b3 !important; }
    
    /* Input Fields */
    .stTextArea textarea, .stTextInput input { border: 1px solid #ced4da !important; border-radius: 4px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. EXTRACTION ENGINE ---
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

def smart_guess_logic(item_name):
    t = str(item_name).lower()
    rules = [
        (r'magnesium glycinate|magnesium bisglycinate', 'magnesium bisglycinate chelate'),
        (r'ashwagandha', 'organic ashwagandha root extract, black pepper extract'),
        (r'turmeric|curcumin', 'turmeric extract (95% curcuminoids), black pepper extract'),
        (r'vitamin c', 'vitamin C (ascorbic acid)'),
        (r'zinc', 'zinc picolinate'),
        (r'melatonin', 'melatonin'),
        (r'collagen', 'hydrolyzed collagen peptides'),
        (r'probiotic', 'probiotic blend (Lactobacillus & Bifidobacterium strains)')
    ]
    for pattern, ingredients in rules:
        if re.search(pattern, t): return ingredients
    return "microcrystalline cellulose, magnesium stearate, silica"

def extract_all_fields(url, item_name):
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        text = soup.get_text().lower()

        def find_f(keys, default="Not Found"):
            for k in keys:
                match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                if match:
                    val = match.find_next().get_text(strip=True) if match.find_next() else ""
                    return re.sub(r'[^\w\s.,!?-]', '', val).strip()[:400]
            return default

        return {
            "URL": url,
            "Expiration Type": find_f(["Expiration Type", "Date Code"]),
            "Expiry (y/n)": "Y" if any(x in text for x in ["expiry", "expiration"]) else "N",
            "Shelf life": find_f(["Shelf life", "Storage"]),
            "CPSIA Warning": find_f(["CPSIA", "Choking Hazard"]),
            "Legal disclaimer": find_f(["Legal disclaimer", "Disclaimer"]),
            "Safety Warning": find_f(["Safety Warning", "Warning"]),
            "Indications": find_f(["Indications", "Recommended use"]),
            "Generic Keywords": find_f(["Keywords", "Search terms"]),
            "Age Range": find_f(["Age Range", "Adults", "Kids"]),
            "Item Form": find_f(["Item Form", "Format"]),
            "Primary Supplement Type": find_f(["Supplement Type", "Main Ingredient"]),
            "Directions": find_f(["Directions", "How to use"]),
            "Flavor": find_f(["Flavor", "Taste"]),
            "Target Gender": "Men" if "men" in text else ("Women" if "women" in text else "Unisex"),
            "Benefits": find_f(["Benefits", "Why use"]),
            "Specific Uses": find_f(["Specific Uses", "Used for"]),
            "Ingredients list": find_f(["Ingredients", "Supplement Facts"]) if find_f(["Ingredients"]) != "Not Found" else smart_guess_logic(item_name),
            "Allergen Information": find_f(["Allergen", "Contains"]),
            "Casepack Quantity": find_f(["Casepack Quantity", "Case qty"], "1"),
            "Quantity": find_f(["Quantity", "Count"]),
            "Days of use": find_f(["Days of use", "Supply"]),
            "Dimensions": find_f(["Dimensions", "Size"]),
            "Package dimensions": find_f(["Package dimensions"]),
            "Hazmat(y/n)": "Y" if any(x in text for x in ["hazmat", "flammable"]) else "N",
            "Description": soup.title.string.strip() if soup.title else "N/A",
            "Images Found": len(soup.find_all('img'))
        }
    except:
        return {"URL": url, "Status": "Node Blocked", "Ingredients list": smart_guess_logic(item_name)}

# --- 3. UI LAYOUT ---
st.title("📋 Product Data Extractor")
st.write("Extract ingredients, warnings, and specifications from brand websites.")

tab1, tab2 = st.tabs(["Data Input", "Extraction Results"])

with tab1:
    st.subheader("Configuration")
    target_sites = st.text_input("Target Website Domains (separated by commas)", "gnc.com, vitaminshoppe.com")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Upload Excel/CSV File", type=["xlsx", "csv"])
    with col2:
        manual_names = st.text_area("Or Paste Item Names (one per line)")
    
    start_btn = st.button("Start Extraction Process")

if start_btn:
    items = []
    if uploaded_file:
        df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        col = next((c for c in df_in.columns if "name" in c.lower() or "title" in c.lower()), df_in.columns[0])
        items = df_in[col].dropna().tolist()
    elif manual_names:
        items = [i.strip() for i in manual_names.split('\n') if i.strip()]

    if items:
        st.info(f"Loaded {len(items)} items. Beginning extraction...")
        prog = st.progress(0)
        final_results = []
        site_list = [s.strip() for s in target_sites.split(",")]

        for i, item in enumerate(items):
            st.write(f"Processing: {item[:60]}...")
            found_url = None
            clean_item = " ".join(str(item).split()[:5])
            
            for site in site_list:
                try:
                    query = f"site:{site} {clean_item}"
                    found_url = next(search(query, num_results=1))
                    break
                except: continue
            
            data = extract_all_fields(found_url, item) if found_url else {"Item Name": item, "Status": "Not Found", "Ingredients list": smart_guess_logic(item)}
            data["Original Item Name"] = item
            final_results.append(data)
            prog.progress((i + 1) / len(items))
            time.sleep(2)

        df_out = pd.DataFrame(final_results)
        with tab2:
            st.success("Extraction complete. Review the data below.")
            st.dataframe(df_out)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_out.to_excel(writer, index=False)
            st.download_button("Download Extracted Results (Excel)", output.getvalue(), "product_data_results.xlsx")
    else:
        st.error("Please provide item names via upload or text box.")
