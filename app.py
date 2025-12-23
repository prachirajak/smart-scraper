
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io
from googlesearch import search

# --- 1. TECHY UI CONFIGURATION ---
st.set_page_config(page_title="NEURAL DATA EXTRACTOR", page_icon="⚡", layout="wide")

# Custom CSS for "Techy" Dark Mode Look
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #0e1117; color: #00ff41; font-family: 'Courier New', Courier, monospace; }
    
    /* Headers */
    h1, h2, h3 { color: #00ff41 !important; text-shadow: 0 0 10px #00ff41; }
    
    /* Input Boxes */
    .stTextArea textarea, .stTextInput input {
        background-color: #1a1c23 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div { background-color: #00ff41 !important; }
    
    /* Buttons */
    .stButton>button {
        background-color: transparent !important; color: #00ff41 !important;
        border: 2px solid #00ff41 !important; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #00ff41 !important; color: black !important; box-shadow: 0 0 20px #00ff41; }
    
    /* Download Button */
    .stDownloadButton>button {
        background-color: #00ff41 !important; color: black !important;
        font-weight: bold; border-radius: 2px; border: none; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. EXTRACTION CORE ---
def extract_logic(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        t = soup.get_text().lower()
        
        # Intelligence: Mapping 25+ fields
        def find_val(keys, default="N/A"):
            for k in keys:
                match = soup.find(string=re.compile(k, re.I))
                if match:
                    val = match.find_next().get_text() if match.find_next() else match
                    return re.sub(r'[^\w\s.,!?-]', '', val).strip()[:400]
            return default

        return {
            "URL": url,
            "Description": soup.title.string.replace('Product', '').strip() if soup.title else "N/A",
            "Expiration Type": find_val(["Expiration Type", "Date Code"]),
            "Expiry (y/n)": "Y" if any(x in t for x in ["expiry", "exp date"]) else "N",
            "Shelf life": find_val(["Shelf life", "Storage"]),
            "CPSIA Warning": find_val(["CPSIA", "Choking"]),
            "Legal disclaimer": find_val(["Legal disclaimer", "Disclaimer"]),
            "Safety Warning": find_val(["Safety Warning", "Warning"]),
            "Indications": find_val(["Indications", "Recommended use"]),
            "Generic Keywords": find_val(["Keywords", "Tags"]),
            "Age Range": find_val(["Age Range", "Adults", "Kids"]),
            "Item Form": find_val(["Item Form", "Format", "Liquid", "Capsule"]),
            "Primary Supplement Type": find_val(["Supplement Type", "Main Ingredient"]),
            "Directions": find_val(["Directions", "Instructions"]),
            "Flavor": find_val(["Flavor", "Taste"]),
            "Target Gender": "Men" if "men" in t else ("Women" if "women" in t else "Unisex"),
            "Benefits": find_val(["Benefits", "Why use"]),
            "Specific Uses": find_val(["Specific Uses", "Indicated for"]),
            "Ingredients list": find_val(["Ingredients", "Contains"]),
            "Casepack Qty": find_val(["Casepack", "Case Qty"], "1"),
            "Quantity": find_val(["Quantity", "Count"]),
            "Days of use": find_val(["Days of use", "Supply"]),
            "Dimensions": find_val(["Dimensions", "Size"]),
            "Package Dimensions": find_val(["Package Dimensions", "Box Size"]),
            "Hazmat(y/n)": "Y" if any(x in t for x in ["hazmat", "flammable"]) else "N",
            "Images": [img['src'] for img in soup.find_all('img', src=True)[:3]]
        }
    except: return {"Status": "System Error at Node"}

# --- 3. UI TABS ---
st.title("⚡ NEURAL DATA SCRAPER v2.0")
tab1, tab2 = st.tabs(["[ CORE_INPUT ]", "[ DATA_OUTPUT ]"])

with tab1:
    st.subheader("Target Environment")
    target_domain = st.text_input("ENTER TARGET WEBSITE (e.g., vitaminshoppe.com)", placeholder="website.com")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("UPLOAD SOURCE FILE", type=["xlsx", "csv"])
    with col2:
        manual_items = st.text_area("MANUAL ENTRY (Item Names)", height=150)

    start_engine = st.button("INITIALIZE EXTRACTION")

# --- 4. PROCESSING ---
if start_engine:
    if not target_domain:
        st.error("ERROR: TARGET DOMAIN REQUIRED FOR SCOPE LIMITING.")
    else:
        items = []
        if uploaded_file:
            df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            col = 'Item Name' if 'Item Name' in df_in.columns else df_in.columns[0]
            items = df_in[col].dropna().tolist()
        elif manual_items:
            items = [i.strip() for i in manual_items.split('\n') if i.strip()]

        if items:
            st.write(f"🔍 SCANNING {len(items)} NODES ON {target_domain}...")
            prog_bar = st.progress(0)
            dataset = []
            
            for i, item in enumerate(items):
                # SMART SEARCH: site:domain.com + item name
                query = f"site:{target_domain} {item}"
                try:
                    search_gen = search(query, num_results=1)
                    found_url = next(search_gen)
                    data = extract_logic(found_url)
                    data["Original Query"] = item
                    dataset.append(data)
                except:
                    dataset.append({"Original Query": item, "Status": "Link Not Found In Domain"})
                
                prog_bar.progress((i + 1) / len(items))
                time.sleep(1.5)

            final_df = pd.DataFrame(dataset)

            with tab2:
                st.success("PROTOCOL COMPLETE. DATA CAPTURED.")
                with st.expander("VIEW RAW HEX/DATA TABLE"):
                    st.dataframe(final_df)
                
                # Techy Green Download Bar
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 DOWNLOAD ENCRYPTED EXCEL DATA",
                    data=output.getvalue(),
                    file_name="neural_extract_results.xlsx"
                )
