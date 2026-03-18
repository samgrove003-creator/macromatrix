import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import requests
import json

# --- 1. App Configuration & API Setup ---
st.set_page_config(page_title="Kei Macro Garage", page_icon="🏎️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing API Key! Please add 'GEMINI_API_KEY' to your Streamlit Secrets.")

# Initialize session states
if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Date", "Time", "Item", "Calories", "Protein"])
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2200
if 'protein_target' not in st.session_state:
    st.session_state.protein_target = 160
# NEW: State to hold the AI's scan before logging
if 'pending_scan' not in st.session_state:
    st.session_state.pending_scan = None

try:
    cover_image = Image.open('cover.png')
    st.image(cover_image, use_container_width=True)
except FileNotFoundError:
    pass # Hiding the warning for a cleaner UI if the image isn't there yet

# --- 2. Mobile-Friendly Navigation (Reordered) ---
tab_dash, tab_scan, tab_log, tab_settings, tab_alerts = st.tabs(["Dashboard", "📷 Dashcam", "Refuel", "Tuning", "🔔 Alerts"])

# --- TAB 1: Dashboard & Charts ---
with tab_dash:
    st.header("Daily Telemetry")
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = st.session_state.logs[st.session_state.logs["Date"] == today_str]
    
    total_cals = today_logs["Calories"].sum() if not today_logs.empty else 0
    total_pro = today_logs["Protein"].sum() if not today_logs.empty else 0
    
    col1, col2 = st.columns(2)
    col1.metric("Fuel Tank (kcal)", f"{total_cals} / {st.session_state.daily_target}", delta=int(st.session_state.daily_target - total_cals), delta_color="normal")
    col2.metric("Engine Block (Pro g)", f"{total_pro} / {st.session_state.protein_target}", delta=int(total_pro - st.session_state.protein_target))
    
    st.divider()
    st.subheader("Current Chassis Status")
    cal_percent = total_cals / st.session_state.daily_target if st.session_state.daily_target > 0 else 0
    
    if cal_percent == 0:
        st.info("🚛 **Subaru Sambar Truck:** You're running on empty. Time to haul some fuel!")
    elif cal_percent < 0.4:
        st.success("🚙 **Honda Beat:** Engine is warming up! Keep revving to 8,500 RPM.")
    elif cal_percent < 0.7:
        st.warning("🏎️ **Suzuki Cappuccino:** Turbo is spooling! Good mid-day progress.")
    elif cal_percent <= 1.0:
        st.error("🦅 **Autozam AZ-1:** Gullwing doors deployed! You've hit peak performance.")
    else:
        st.error("🔥 **1958 Plymouth Fury:** Redline exceeded! Absolute possessed beast mode.")
        
    st.progress(min(cal_percent, 1.0))
    st.divider()
    
    if not st.session_state.logs.empty:
        trend_data = st.session_state.logs.groupby("Date")[["Calories", "Protein"]].sum()
        st.bar_chart(trend_data["Calories"], color="#ff4b4b")
        st.caption("Today's Maintenance Log:")
        st.dataframe(today_logs[["Time", "Item", "Calories", "Protein"]], use_container_width=True, hide_index=True)
    else:
        st.info("No data logged yet. Fire up the Dashcam.")

# --- TAB 2: Vision Scanner (Moved Up & Upgraded) ---
with tab_scan:
    st.header("AI Dashcam Scanner")
    food_image = st.camera_input("Snap a picture of your fuel")
    
    if food_image is not None:
        if st.button("Run AI Diagnostics"):
            with st.spinner("Analyzing telemetry..."):
                try:
                    img = Image.open(food_image)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    # Instructing the AI to return raw JSON data
                    prompt = """
                    Analyze this food. Return ONLY a valid JSON object with these exact keys:
                    - "item": A short, punchy name for the food (string).
                    - "calories": Integer estimate of total calories.
                    - "protein": Integer estimate of total protein in grams.
                    - "tomato_warning": Boolean (true if tomatoes are visible, false otherwise).
                    Do not include any markdown formatting or extra text.
                    """
                    response = model.generate_content([prompt, img])
                    
                    # Clean the text just in case it adds markdown, then parse the JSON
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    st.session_state.pending_scan = json.loads(clean_json)
                    
                except Exception as e:
                    st.error(f"Engine fault detected: {e}")
                    
        # The Confirmation Pop-up UI
        if st.session_state.pending_scan:
            p = st.session_state.pending_scan
            st.divider()
            st.subheader("Diagnostics Complete")
            
            if p.get("tomato_warning"):
                st.error("🚨 **WARNING: RESTRICTED COMPONENT (TOMATO) DETECTED!** 🚨")
            else:
                st.success("✅ Clear of restricted components.")
                
            st.markdown(f"**Detected:** {p.get('item')}")
            st.markdown(f"**Estimates:** {p.get('calories')} kcal | {p.get('protein')}g Protein")
            
            st.write("Is this telemetry correct to log?")
            colY, colN = st.columns(2)
            
            if colY.button("✅ Yes, Log It"):
                new_entry = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Time": datetime.now().strftime("%H:%M"),
                    "Item": p.get('item'), 
                    "Calories": p.get('calories'), 
                    "Protein": p.get('protein')
                }])
                st.session_state.logs = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
                st.session_state.pending_scan = None # Clear the pending state
                st.success("Telemetry saved!")
                st.rerun() # Refresh the app to update charts
                
            if colN.button("❌ No, Discard"):
                st.session_state.pending_scan = None
                st.rerun()

# --- TAB 3: Manual Logging (Refuel) ---
with tab_log:
    st.header("Manual Refuel")
    with st.form("manual_log_form", clear_on_submit=True):
        item = st.text_input("Fuel Type (Food Item)")
        colA, colB = st.columns(2)
        cals = colA.number_input("Calories", min_value=0, step=50)
        pro = colB.number_input("Protein (g)", min_value=0, step=5)
        
        if st.form_submit_button("Pump Fuel") and item:
            new_entry = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Item": item, "Calories": cals, "Protein": pro
            }])
            st.session_state.logs = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
            st.success(f"Topped off with {item}!")

# --- TAB 4: Settings (Tuning) ---
with tab_settings:
    st.header("ECU Tuning")
    st.session_state.daily_target = st.number_input("Fuel Capacity (Calorie Budget)", value=st.session_state.daily_target, step=100)
    st.session_state.protein_target = st.number_input("Boost Pressure (Protein Goal in g)", value=st.session_state.protein_target, step=10)
    st.divider()
    st.error("Active Filter: **NO TOMATOES**")

# --- TAB 5: Alerts ---
with tab_alerts:
    st.header("Maintenance Reminders")
    st.markdown("Trigger push notifications directly to your Pixel via ntfy.sh.")
    ntfy_topic = "sams_kei_garage_telemetry_99" 
    st.info(f"Subscribe to topic: **{ntfy_topic}** in the ntfy Android app to receive these.")
    
    colA, colB = st.columns(2)
    with colA:
        if st.button("💧 Hydration Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data="Engine running hot. Drink a glass of water!".encode('utf-8'), headers={"Title": "Coolant Check", "Tags": "droplet"})
            st.success("Ping sent!")
        if st.button("🚶 Stand Up Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data="You've been idling too long. Stand up and stretch the chassis.".encode('utf-8'), headers={"Title": "Idle Warning", "Tags": "warning,walking"})
            st.success("Ping sent!")
    with colB:
        if st.button("🍎 Refuel Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data="Fuel levels dropping. Time to log a meal.".encode('utf-8'), headers={"Title": "Low Fuel", "Tags": "gas_pump,apple"})
            st.success("Ping sent!")
