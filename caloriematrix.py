import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import requests

# --- 1. App Configuration & API Setup ---
st.set_page_config(page_title="Kei Macro Garage", page_icon="🏎️", layout="centered")

# Configure Gemini AI 
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing API Key! Please add 'GEMINI_API_KEY' to your Streamlit Secrets.")

# Initialize session state for data persistence 
if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Date", "Time", "Item", "Calories", "Protein"])
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2200
if 'protein_target' not in st.session_state:
    st.session_state.protein_target = 160

# --- 2. Load and Display the Cover Photo ---
try:
    # Looks for the file named cover.jpg in your repo
    cover_image = Image.open('cover.jpg')
    st.image(cover_image, use_container_width=True)
except FileNotFoundError:
    st.warning("Missing cover.jpg. Please upload the sketch to your GitHub repo.")

# --- 3. Mobile-Friendly Navigation ---
tab_dash, tab_log, tab_scan, tab_settings, tab_alerts = st.tabs(["Dashboard", "Refuel", "📷 Dashcam", "Tuning", "🔔 Alerts"])

# --- TAB 1: Dashboard & Charts (Themed) ---
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
    
    # --- Status Upgrades Based on Calories ---
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
        st.info("No data logged yet. Head to the 'Refuel' or 'Dashcam' tab.")

# --- TAB 2: Manual Logging (Refuel) ---
with tab_log:
    st.header("Manual Refuel")
    with st.form("manual_log_form", clear_on_submit=True):
        item = st.text_input("Fuel Type (Food Item)", placeholder="e.g., Chicken Bowl")
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

# --- TAB 3: Vision Scanner (Dashcam AI) ---
with tab_scan:
    st.header("AI Dashcam Scanner")
    st.markdown("Use your Pixel's camera to run diagnostics on your meal.")
    
    food_image = st.camera_input("Snap a picture of your fuel")
    
    if food_image is not None:
        st.image(food_image, caption="Dashcam Feed", use_container_width=True)
        if st.button("Run AI Diagnostics"):
            with st.spinner("Analyzing telemetry..."):
                try:
                    img = Image.open(food_image)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = """
                    Look at this food. 
                    1. Tell me what it is in one short sentence.
                    2. Estimate the total Calories and Protein (g). 
                    3. EXTREMELY IMPORTANT: Explicitly state if you detect any tomatoes so I know to avoid them.
                    Format the output as a clean bulleted list.
                    """
                    response = model.generate_content([prompt, img])
                    st.success("Diagnostics Complete!")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Engine fault detected: {e}")
                    
        st.divider()
        with st.form("quick_ai_log", clear_on_submit=True):
            ai_item = st.text_input("Item Name")
            ai_cals = st.number_input("Estimated Calories", min_value=0, step=10)
            ai_pro = st.number_input("Estimated Protein (g)", min_value=0, step=1)
            if st.form_submit_button("Log AI Estimate"):
                 new_entry = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Time": datetime.now().strftime("%H:%M"),
                    "Item": ai_item, "Calories": ai_cals, "Protein": ai_pro
                 }])
                 st.session_state.logs = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
                 st.success("Telemetry saved!")

# --- TAB 4: Settings & Dietary Filters (Tuning) ---
with tab_settings:
    st.header("ECU Tuning")
    st.session_state.daily_target = st.number_input("Fuel Capacity (Calorie Budget)", value=st.session_state.daily_target, step=100)
    st.session_state.protein_target = st.number_input("Boost Pressure (Protein Goal in g)", value=st.session_state.protein_target, step=10)
    
    st.divider()
    st.subheader("Restricted Components")
    st.error("Active Filter: **NO TOMATOES**")
    
    st.divider()
    st.subheader("Garage Manifest")
    st.markdown("* **Daily:** WRX \n* **Classic:** Studebaker \n* **Track Toys:** AZ-1, Cappuccino, Beat")

# --- TAB 5: Maintenance Alerts (ntfy Integration) ---
with tab_alerts:
    st.header("Maintenance Reminders")
    st.markdown("Trigger push notifications directly to your Pixel via ntfy.sh.")
    
    # IMPORTANT: Change this to a unique string that only you know!
    ntfy_topic = "sams_kei_garage_telemetry_99" 
    
    st.info(f"Subscribe to topic: **{ntfy_topic}** in the ntfy Android app to receive these.")
    
    colA, colB = st.columns(2)
    with colA:
        if st.button("💧 Hydration Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", 
                          data="Engine running hot. Drink a glass of water!".encode('utf-8'),
                          headers={"Title": "Coolant Check", "Tags": "droplet"})
            st.success("Ping sent!")
            
        if st.button("🚶 Stand Up Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", 
                          data="You've been idling too long. Stand up and stretch the chassis.".encode('utf-8'),
                          headers={"Title": "Idle Warning", "Tags": "warning,walking"})
            st.success("Ping sent!")
    with colB:
        if st.button("🍎 Refuel Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", 
                          data="Fuel levels dropping. Time to log a meal.".encode('utf-8'),
                          headers={"Title": "Low Fuel", "Tags": "gas_pump,apple"})
            st.success("Ping sent!")
