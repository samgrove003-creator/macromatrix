import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import requests
import json
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. App Configuration & API Setup ---
st.set_page_config(page_title="Kei Macro Garage", page_icon="🏎️", layout="centered")

# Configure AI
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing GEMINI_API_KEY in Secrets!")

# Establish Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Read Data from Cloud (7 Columns: Date, Time, Item, Calories, Protein, Carbs, Fats)
try:
    existing_data = conn.read(worksheet="Logs", usecols=list(range(7)), ttl=0)
    existing_data = existing_data.dropna(how="all")
    st.session_state.logs = existing_data
except Exception as e:
    st.error(f"Database Error: Check your 7 columns and Secret permissions. {e}")
    st.session_state.logs = pd.DataFrame(columns=["Date", "Time", "Item", "Calories", "Protein", "Carbs", "Fats"])

# Initialize Targets and States
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2200
if 'protein_target' not in st.session_state:
    st.session_state.protein_target = 160
if 'pending_scan' not in st.session_state:
    st.session_state.pending_scan = None
if 'ai_advice' not in st.session_state:
    st.session_state.ai_advice = ""

# --- 2. Visual Header ---
try:
    cover_image = Image.open('cover.png')
    st.image(cover_image, use_container_width=True)
except FileNotFoundError:
    st.info("Upload 'cover.png' to GitHub to see your garage branding.")

# --- 3. Navigation ---
tab_dash, tab_scan, tab_log, tab_settings, tab_alerts = st.tabs(["Dashboard", "📷 Dashcam", "Refuel", "Tuning", "🔔 Alerts"])

# --- TAB 1: Dashboard & Charts ---
with tab_dash:
    st.header("Daily Telemetry")
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = st.session_state.logs[st.session_state.logs["Date"] == today_str]
    
    total_cals = today_logs["Calories"].sum() if not today_logs.empty else 0
    total_pro = today_logs["Protein"].sum() if not today_logs.empty else 0
    total_carbs = today_logs["Carbs"].sum() if not today_logs.empty else 0
    total_fats = today_logs["Fats"].sum() if not today_logs.empty else 0
    
    col1, col2 = st.columns(2)
    col1.metric("Fuel Tank (kcal)", f"{int(total_cals)} / {st.session_state.daily_target}")
    col2.metric("Engine Block (Pro g)", f"{int(total_pro)} / {st.session_state.protein_target}")
    
    st.divider()
    
    # Macro Pie Chart
    if total_pro > 0 or total_carbs > 0 or total_fats > 0:
        st.subheader("Fuel Mixture Breakdown")
        macro_df = pd.DataFrame({
            "Macro": ["Protein", "Carbs", "Fats"],
            "Grams": [total_pro, total_carbs, total_fats]
        })
        fig = px.pie(macro_df, values='Grams', names='Macro', hole=0.4,
                     color='Macro', color_discrete_map={'Protein':'#ff4b4b', 'Carbs':'#ffa500', 'Fats':'#00bfff'})
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Chassis Status
    st.subheader("Current Chassis Status")
    cal_percent = total_cals / st.session_state.daily_target if st.session_state.daily_target > 0 else 0
    if cal_percent == 0: st.info("🚛 **Subaru Sambar:** Tank empty.")
    elif cal_percent < 0.7: st.success("🚙 **Honda Beat:** Warming up.")
    elif cal_percent <= 1.0: st.warning("🏎️ **Autozam AZ-1:** Peak performance.")
    else: st.error("🔥 **1958 Plymouth Fury:** Redline exceeded!")
    st.progress(min(cal_percent, 1.0))

# --- TAB 2: Vision Scanner ---
with tab_scan:
    st.header("AI Dashcam Scanner")
    food_image = st.camera_input("Snap your fuel")
    
    if food_image is not None:
        if st.button("Run AI Diagnostics"):
            with st.spinner("Analyzing..."):
                try:
                    img = Image.open(food_image)
                    model = genai.GenerativeModel('gemini-2.0-flash') # Using the latest stable
                    prompt = """Return ONLY a JSON object: {"item": string, "calories": int, "protein": int, "carbs": int, "fats": int, "tomato_warning": bool}"""
                    response = model.generate_content([prompt, img])
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    st.session_state.pending_scan = json.loads(clean_json)
                except Exception as e:
                    st.error(f"Scanner fault: {e}")
                    
        if st.session_state.pending_scan:
            p = st.session_state.pending_scan
            st.divider()
            if p.get("tomato_warning"): st.error("🚨 **TOMATO DETECTED!** 🚨")
            st.markdown(f"**Detected:** {p.get('item')} | {p.get('calories')} kcal")
            st.markdown(f"P: {p.get('protein')}g | C: {p.get('carbs')}g | F: {p.get('fats')}g")
            
            if st.button("✅ Confirm & Log to Cloud"):
                new_entry = pd.DataFrame([{
                    "Date": today_str, "Time": datetime.now().strftime("%H:%M"),
                    "Item": p.get('item'), "Calories": p.get('calories'), 
                    "Protein": p.get('protein'), "Carbs": p.get('carbs'), "Fats": p.get('fats')
                }])
                updated_data = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
                conn.update(worksheet="Logs", data=updated_data)
                st.session_state.logs = updated_data
                st.session_state.pending_scan = None
                st.success("Logged!")
                st.rerun()

# --- TAB 3: Manual Logging ---
with tab_log:
    st.header("Manual Refuel")
    with st.form("manual_log", clear_on_submit=True):
        item = st.text_input("Fuel Type")
        c1, c2, c3, c4 = st.columns(4)
        cals = c1.number_input("Cals", min_value=0, step=50)
        pro = c2.number_input("Pro", min_value=0, step=5)
        carbs = c3.number_input("Carb", min_value=0, step=5)
        fats = c4.number_input("Fat", min_value=0, step=5)
        if st.form_submit_button("Pump Fuel"):
            new_entry = pd.DataFrame([{"Date": today_str, "Time": datetime.now().strftime("%H:%M"), "Item": item, "Calories": cals, "Protein": pro, "Carbs": carbs, "Fats": fats}])
            updated_data = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
            conn.update(worksheet="Logs", data=updated_data)
            st.session_state.logs = updated_data
            st.success("Cloud Updated!")

# --- TAB 4: Tuning (AI Settings) ---
with tab_settings:
    st.header("Driver Dyno Tune")
    with st.form("dyno_form"):
        age = st.number_input("Age", value=22)
        height = st.text_input("Height", value="5'10\"")
        weight = st.number_input("Weight (lbs)", value=180)
        goal = st.number_input("Goal Weight (lbs)", value=170)
        if st.form_submit_button("Flash ECU (Calculate Goals)"):
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"User: {age}, {height}, {weight}lbs, Goal: {goal}lbs. Return JSON only: {{'calories': int, 'protein': int, 'advice': string}}"
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
            st.session_state.daily_target, st.session_state.protein_target, st.session_state.ai_advice = data['calories'], data['protein'], data['advice']
            st.success("Targets Updated!")
    
    st.metric("Daily Target", f"{st.session_state.daily_target} kcal")
    if st.session_state.ai_advice: st.info(f"Advice: {st.session_state.ai_advice}")

# --- TAB 5: Alerts ---
with tab_alerts:
    st.header("Maintenance Reminders")
    ntfy_topic = "sams_kei_garage_telemetry_99" 
    if st.button("💧 Hydration Alert"):
        requests.post(f"https://ntfy.sh/{ntfy_topic}", data="Engine running hot. Drink water!".encode('utf-8'))
    if st.button("🍽️ AI Meal Suggestion"):
        model = genai.GenerativeModel('gemini-2.0-flash')
        idea = model.generate_content("Suggest a healthy, high-protein, NO-TOMATO meal under 500 cals. 1 sentence.").text
        requests.post(f"https://ntfy.sh/{ntfy_topic}", data=idea.encode('utf-8'))
        st.write(f"Sent: {idea}")
