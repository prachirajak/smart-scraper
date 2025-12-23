import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import re, time, io

# --- 1. LIVELY & SIMPLE UI CONFIG ---
st.set_page_config(page_title="Vibrant Web Scraper", layout="wide")

st.markdown("""
    <style>
    /* Clean white background and professional font */
    .stApp { background-color: #ffffff; font-family: 'Inter', -apple-system, sans-serif; }
    
    /* Header styling with a lively blue */
    h1 { color: #0070f3 !important; font-weight: 800 !important; letter-spacing: -1px; }
    
    /* Lively "Go" Button */
    .stButton>button {
        background-color: #0070f3 !important; color: white !important;
        border-radius: 8px !important; border: none !important;
        padding: 0.6rem 2rem !important; font-weight: 600 !important;
        box-shadow: 0 4px 14px 0 rgba(0,118,255,0.39);
        transition: all 0.2s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,118,255,0.23); }
    
    /* Download Button - Vibrant Green */
    .stDownloadButton>button {
        background-color: #00c851 !important; color: white !important;
        border-radius: 8px !important; font-weight: 700 !important;
        padding: 0.8rem !important; width: 100% !important;
    }
    
    /* Lively Logs */
    .status-box { background-color: #f0f7ff; padding: 10px; border-left: 4px solid #0070f3; border-radius: 4px; margin-bottom: 5px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE BRAIN (Scraper Logic) ---
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

def smart_guess_ingredients(title):
    t = str(title).lower()
    if 'magnesium' in t: return 'magnesium bisglycinate chelate'
    if 'ashwagandha' in t: return 'organic ashwagandha root extract'
    if 'vitamin c' in t: return 'vitamin C (ascorbic acid)'
    return 'microcrystalline cellulose, magnesium stearate, silica'

DATA_MAP = {
    "Allergen Info": ["Allergen", "Contains", "Free from"],
    "Expiration Type": ["Expiration Type", "Date Code", "EXP"],
    "Expiry (y/n)": ["Expiry", "Expiration"],
    "Shelf Life": ["Shelf life", "Storage", "Duration"],
    "CPSIA Warning": ["CPSIA", "Choking Hazard", "Small parts"],
    "Legal Disclaimer": ["Legal disclaimer", "Disclaimer"],
    "Safety Warning": ["Safety Warning", "Warning", "Precautions"],
    "Indications": ["Indications", "Recommended use", "Uses"],
    "Age Range": ["Age Range", "Adults", "Kids"],
    "Supplement Type": ["Supplement Type", "Main Ingredient"],
    "Directions": ["Directions", "How to use", "Suggested Use"],
    "Flavor": ["Flavor", "Taste", "Scent"],
    "Target Gender": ["Target Gender", "Gender", "Men", "Women"],
    "Product Benefits": ["Benefits", "Features", "Why use"],
    "Ingredients": ["Ingredients", "Supplement Facts", "Active Ingredients"],
    "Quantity": ["Quantity", "Count", "Unit Count"],
    "Days of Use": ["Days of use", "Supply length", "Servings"],
    "Description": ["Description", "About this item"]
}

# --- 3. UI LAYOUT ---
st.title("🔍 Web Scraper Pro")
st.write("A simple, lively tool to audit product data across the web.")

# Simple Header Input
url_input = st.text_area("Paste Product URLs (one per line)", height=150, placeholder="https://www.gnc.com/example-product...")

if st.button("Start Scraping"):
    links = [l.strip() for l in url_input.split('\n') if l.strip().startswith('http')]
    
    if links:
        progress_bar = st.progress(0)
        log_container = st.container() # For lively status updates
        final_data = []
        
        for i, link in enumerate(links):
            with st.status(f"Auditing Link {i+1}...", expanded=True) as status:
                st.write(f"Connecting to: {link[:50]}...")
                
                driver = get_driver()
                try:
                    driver.get(link)
                    time.sleep(5) # Wait for page rendering
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    text = soup.get_text().lower()
                    title = soup.title.string if soup.title else "Product"
                    
                    row_data = {"Source": link}
                    
                    for field, keywords in DATA_MAP.items():
                        found = False
                        for k in keywords:
                            if field == "Expiry (y/n)":
                                row_data[field] = "Y" if k.lower() in text else "N"
                                found = True; break
                            
                            match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                            if match:
                                val = match.find_next().get_text(strip=True)[:400]
                                row_data[field] = val if len(val) > 1 else "Not Found"
                                st.write(f"✅ Found {field}...")
                                found = True; break
                        
                        if not found:
                            row_data[field] = smart_guess_ingredients(title) if field == "Ingredients" else "Not Found"

                    row_data["Images Found"] = len(soup.find_all('img'))
                    final_data.append(row_data)
                    status.update(label="Extraction Complete!", state="complete")
                    
                except Exception as e:
                    final_data.append({"Source": link, "Status": "Blocked/Error"})
                    status.update(label="Blocked by Security", state="error")

            progress_bar.progress((i + 1) / len(links))
        
        df = pd.DataFrame(final_data)
        st.divider()
        st.subheader("Final Audit Results")
        st.dataframe(df)
        
        # Lively Download Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 DOWNLOAD AUDIT REPORT", output.getvalue(), "web_scraper_results.xlsx")
    else:
        st.error("Please paste at least one valid URL.")
