
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

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00ff41; font-family: 'Courier New', Courier, monospace; }
    h1, h2, h3 { color: #00ff41 !important; text-shadow: 0 0 10px #00ff41; }
    .stTextArea textarea, .stTextInput input { background-color: #1a1c23 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; }
    .stProgress > div > div > div > div { background-color: #00ff41 !important; }
    .stButton>button { background-color: transparent !important; color: #00ff41 !important; border: 2px solid #00ff41 !important; font-weight: bold; width: 100%; }
    .stButton>button:hover { background-color: #00ff41 !important; color: black !important; box-shadow: 0 0 20px #00ff41; }
    .stDownloadButton>button { background-color: #00ff41 !important; color: black !important; font-weight: bold; width: 100%; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. EXTRACTION ENGINE ---
def extract_logic(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        t = soup.get_text().lower()
        
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
            "Item Form": find_val(["Item Form", "Format"]),
            "Primary Supplement Type": find_val(["Supplement Type", "Main Ingredient"]),
            "Directions": find_val(["Directions", "Instructions"]),
            "Flavor": find_val(["Flavor", "Taste"]),
            "Target Gender": "Men" if "men" in t else ("Women" if "women" in t else "Unisex"),
            "Benefits": find_val(["Benefits", "Why use"]),
            "Specific Uses": find_val(["Specific Uses", "Indicated for"]),
            "Ingredients list": find_val(["Ingredients", "Contains"]),
            "Casepack Qty": find_val(["Casepack", "Case Qty"], "1"),
            "Quantity": find_val(["Quantity", "Count"]),
            "Casepack Dimensions": find_val(["Casepack Dimensions"]),
            "Days of use": find_val(["Days of use", "Supply"]),
            "Dimensions": find_val(["Dimensions", "Size"]),
            "Package Dimensions": find_val(["Package Dimensions"]),
            "Hazmat(y/n)": "Y" if any(x in t for x in ["hazmat", "flammable"]) else "N",
            "Images Found": len(soup.find_all('img'))
        }
    except: return {"Status": "System Error at Node"}

# --- 3. UI LAYOUT ---
st.title("⚡ NEURAL DATA SCRAPER v3.0")
tab1, tab2 = st.tabs(["[ CORE_INPUT ]", "[ DATA_OUTPUT ]"])

with tab1:
    st.subheader("Global Scope Configuration")
    # Master Site List Bar
    master_sites = st.text_input("ENTER DOMAINS TO SEARCH (separated by commas)", placeholder="gnc.com, vitaminshoppe.com, brand.com")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("UPLOAD EXCEL (Item Name column required)", type=["xlsx", "csv"])
    with col2:
        manual_items = st.text_area("OR MANUALLY PASTE ITEM NAMES", height=150)

    start_engine = st.button("INITIALIZE EXTRACTION")

# --- 4. PROCESSING LOGIC ---
if start_engine:
    if not master_sites:
        st.error("SYSTEM ERROR: PLEASE PROVIDE AT LEAST ONE DOMAIN IN THE TOP BAR.")
    else:
        # Prepare list of items
        items = []
        if uploaded_file:
            df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            col = 'Item Name' if 'Item Name' in df_in.columns else df_in.columns[0]
            items = df_in[col].dropna().tolist()
        elif manual_items:
            items = [i.strip() for i in manual_items.split('\n') if i.strip()]

        # Prepare site list
        site_list = [s.strip() for s in master_sites.split(",")]

        if items:
            st.write(f"🔍 SCANNING {len(items)} ITEMS ACROSS {len(site_list)} DOMAINS...")
            prog_bar = st.progress(0)
            dataset = []
            
            for i, item in enumerate(items):
                st.caption(f"PROCESSING: {item}")
                clean_name = " ".join(str(item).split()[:5])
                found_url = None
                
                # Check each site in the master list until a link is found
                for site in site_list:
                    query = f"site:{site} {clean_name}"
                    try:
                        search_results = list(search(query, num_results=1))
                        if search_results:
                            found_url = search_results[0]
                            break # Stop searching other sites once found
                    except: continue
                
                if found_url:
                    data = extract_logic(found_url)
                    data["Original Query"] = item
                    dataset.append(data)
                else:
                    dataset.append({"Original Query": item, "Status": "Not Found in Provided Domains"})
                
                prog_bar.progress((i + 1) / len(items))
                time.sleep(2) # Prevent Google blocking

            final_df = pd.DataFrame(dataset)
            with tab2:
                st.success("PROTOCOL COMPLETE.")
                st.dataframe(final_df)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False)
                st.download_button(label="📥 DOWNLOAD FINAL EXCEL DATA", data=output.getvalue(), file_name="neural_results.xlsx")
