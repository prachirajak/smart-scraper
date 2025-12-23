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

# --- TECHY UI CONFIG ---
st.set_page_config(page_title="NEURAL DATA EXTRACTOR v5.0", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00ff41; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ff41 !important; text-shadow: 0 0 10px #00ff41; }
    .stDownloadButton>button { background-color: #00ff41 !important; color: black !important; font-weight: bold; width: 100%; border: none; }
    .stButton>button { background-color: transparent !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; width: 100%; }
    .stButton>button:hover { background-color: #00ff41 !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SMART GUESS LOGIC (from your HTML) ---
def smart_guess(title):
    t = str(title).lower()
    rules = [
        (r'ashwagandha', 'Organic Ashwagandha Root Extract, Black Pepper Extract'),
        (r'magnesium', 'Magnesium Bisglycinate Chelate, Magnesium Stearate'),
        (r'turmeric|curcumin', 'Turmeric Extract (95% Curcuminoids), Black Pepper Extract'),
        (r'vitamin c', 'Vitamin C (ascorbic acid)'),
        (r'melatonin', 'Melatonin, Silica'),
        (r'collagen', 'Hydrolyzed Collagen Peptides'),
        (r'zinc', 'Zinc Picolinate')
    ]
    for pattern, ingredients in rules:
        if re.search(pattern, t):
            return ingredients
    return "Microcrystalline Cellulose, Magnesium Stearate, Silica" # Your Generic Fallback

# --- EXTRACTION ENGINE ---
def extract_logic(url, item_name):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"Status": "Site Blocked", "Ingredients list": smart_guess(item_name)}
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        def find_val(keys):
            for k in keys:
                match = soup.find(string=re.compile(rf"\b{k}\b", re.I))
                if match:
                    val = match.find_next().get_text(strip=True) if match.find_next() else ""
                    return val[:400]
            return None

        ingredients = find_val(["Ingredients", "Supplement Facts", "What's inside"])
        
        return {
            "URL": url,
            "Ingredients list": ingredients if ingredients else smart_guess(item_name),
            "Safety Warning": find_val(["Safety Warning", "Warning", "Precautions"]),
            "Directions": find_val(["Directions", "How to use", "Suggested Use"]),
            "Item Form": find_val(["Item Form", "Capsule", "Tablet", "Powder"]),
            "Hazmat(y/n)": "Y" if any(x in soup.get_text().lower() for x in ["flammable", "hazmat"]) else "N"
        }
    except:
        return {"Status": "Search failed", "Ingredients list": smart_guess(item_name)}

# --- UI LAYOUT ---
st.title("⚡ MASTER INGREDIENT GENERATOR")
tab1, tab2 = st.tabs(["[ INPUT ]", "[ OUTPUT ]"])

with tab1:
    master_site = st.text_input("TARGET WEBSITE (e.g., gnc.com)", "gnc.com")
    uploaded_file = st.file_uploader("UPLOAD SOURCE FILE", type=["xlsx", "csv"])
    manual_input = st.text_area("OR PASTE ITEM NAMES")
    start_btn = st.button("INITIALIZE GENERATION")

if start_btn:
    items = []
    if uploaded_file:
        df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        col = next((c for c in df_in.columns if "name" in c.lower() or "title" in c.lower()), df_in.columns[0])
        items = df_in[col].dropna().tolist()
    elif manual_input:
        items = [i.strip() for i in manual_input.split('\n') if i.strip()]

    if items:
        prog = st.progress(0)
        results = []
        for i, item in enumerate(items):
            st.caption(f"PROCESSING NODE: {item[:50]}...")
            try:
                # Clean name for searching (first 5 words)
                clean_name = " ".join(str(item).split()[:5])
                query = f"site:{master_site} {clean_name}"
                link = next(search(query, num_results=1))
                data = extract_logic(link, item)
            except:
                # If search fails, use the Smart Guess logic instantly
                data = {"Status": "Search failed", "Ingredients list": smart_guess(item)}
            
            data["Item Name"] = item
            results.append(data)
            prog.progress((i + 1) / len(items))
            time.sleep(1.5)

        final_df = pd.DataFrame(results)
        with tab2:
            st.success("PROTOCOL COMPLETE")
            st.dataframe(final_df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False)
            st.download_button("📥 DOWNLOAD INGREDIENTS CSV", output.getvalue(), "ingredients_results.xlsx")
