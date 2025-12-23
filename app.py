import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import pandas as pd
import time
import io
import re
from googlesearch import search

# --- BROWSER CONFIGURATION ---
@st.cache_resource
def get_driver():
    """Sets up a headless Chrome browser for the cloud server."""
    options = Options()
    options.add_argument("--headless") # Essential for Cloud deployment
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
        options=options
    )

# --- EXPANDED KEYWORD MAPPING ---
# We solve 'Keyword Mismatch' by listing all possible synonyms for your fields.
KEYWORD_MAP = {
    "Ingredients": ["Ingredients", "Supplement Facts", "What's inside", "Active Ingredients", "Composition", "Formula"],
    "Safety Warning": ["Safety Warning", "Warning", "Precautions", "Cautions", "Contraindications", "Attention"],
    "Directions": ["Directions", "How to use", "Suggested Use", "Dosage", "Instructions", "Administration"],
    "Shelf Life": ["Shelf life", "Storage", "Expiration", "Best before", "Keep until"],
    "Item Form": ["Item Form", "Format", "Capsule", "Tablet", "Powder", "Softgel", "Liquid", "Gummy"],
    "Quantity": ["Quantity", "Count", "Size", "Net Wt", "Volume", "Weight", "Amount per container"],
    "Flavor": ["Flavor", "Taste", "Scent", "Aroma"],
    "Target Gender": ["Gender", "Target Audience", "For Men", "For Women", "Unisex"],
    "Benefits": ["Benefits", "Product Features", "Key Features", "Why you'll love it"],
    "Indications": ["Indications", "Usage", "Used for", "Health concern"]
}

# --- DATA EXTRACTION WITH RETRY LOGIC ---
def smart_extract(url, retry_attempt=1):
    driver = get_driver()
    try:
        driver.get(url)
        # We wait 5-10 seconds for JavaScript to load
        wait_time = 5 if retry_attempt == 1 else 10
        time.sleep(wait_time) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text().lower()
        
        results = {"URL": url}
        
        # Search for each bucket in the Keyword Map
        for field, synonyms in KEYWORD_MAP.items():
            found = False
            for k in synonyms:
                match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                if match:
                    # Capture the text directly following the label
                    val = match.find_next().get_text(strip=True) if match.find_next() else ""
                    if len(val) > 2:
                        results[field] = re.sub(r'[^\w\s.,!?-]', '', val).strip()[:400]
                        found = True
                        break
            if not found:
                results[field] = "N/A"

        # Check for Hazmat clues
        results["Hazmat(y/n)"] = "Y" if any(x in page_text for x in ["flammable", "corrosive", "hazmat", "danger"]) else "N"
        
        # --- RETRY FEATURE ---
        # If the main fields are N/A, try one more time with a longer wait
        if results["Ingredients"] == "N/A" and retry_attempt == 1:
            st.warning(f"Retrying Node: {url[:40]}...")
            return smart_extract(url, retry_attempt=2)
            
        return results
    except Exception as e:
        return {"Status": f"Error: {str(e)}"}

# --- TECHY UI ---
st.title("⚡ NEURAL DATA EXTRACTOR v4.0")
st.markdown("<style>.stApp { background-color: #0e1117; color: #00ff41; }</style>", unsafe_allow_html=True)

domain = st.text_input("ENTER DOMAIN (e.g. gnc.com)", "gnc.com")
item_input = st.text_area("PASTE ITEM NAMES")

if st.button("INITIALIZE"):
    items = [i.strip() for i in item_input.split('\n') if i.strip()]
    final_data = []
    
    prog = st.progress(0)
    for i, item in enumerate(items):
        st.caption(f"SCANNING: {item}")
        try:
            query = f"site:{domain} {item}"
            link = next(search(query, num_results=1))
            data = smart_extract(link)
            data["Item Name"] = item
            final_data.append(data)
        except:
            final_data.append({"Item Name": item, "Status": "Link Not Found"})
        prog.progress((i + 1) / len(items))

    df = pd.DataFrame(final_data)
    st.success("SCAN COMPLETE.")
    st.dataframe(df)
    
    # Download excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 DOWNLOAD RESULTS", output.getvalue(), "extracted_data.xlsx")
