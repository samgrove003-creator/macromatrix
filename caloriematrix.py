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

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing API Key! Please add 'GEMINI_API_KEY' to your Streamlit Secrets.")

# Establish the Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Read data from the "Logs" tab (now reading 7 columns instead of 5)
try:
    existing_data = conn.read(worksheet="Logs", usecols=list(range(7)), ttl=0)
    existing_data = existing_data.dropna(how="all") 
    st.session_state.logs = existing_data
except Exception as e:
    st.error(f"Database sync error: Ensure your Google Sheet has exactly 7 columns (Date, Time, Item, Calories, Protein, Carbs, Fats). Error: {e}")
    st.session_state.logs = pd.DataFrame(columns=["Date", "Time", "Item", "Calories", "Protein", "Carbs", "Fats"])

# Initialize target states
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2200
if 'protein_target' not in st.session_state:
    st.session_state.protein_target = 160
if 'pending_scan' not in st.session_state:
    st.session_state.pending_scan = None
if 'ai_advice' not in st.session_state:
    st.session_state.ai_advice = ""

try:
    cover_image = Image.open('cover.png')
    st.image(cover_image, use_container_width=True)
except FileNotFoundError:
    pass

# --- 2. Navigation ---
tab_dash, tab_scan, tab_log, tab_settings, tab_alerts = st.tabs(["Dashboard", "📷 Dashcam", "Refuel", "Tuning", "🔔 Alerts"])

# --- TAB 1: Dashboard & Charts ---
with tab_dash:
    st.header("Daily Telemetry")
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = st.session_state.logs[st.session_state.logs["Date"] == today_str]
    
    # Calculate total macros for the day
    total_cals = today_logs["Calories"].sum() if not today_logs.empty else 0
    total_pro = today_logs["Protein"].sum() if not today_logs.empty else 0
    total_carbs = today_logs["Carbs"].sum() if not today_logs.empty else 0
    total_fats = today_logs["Fats"].sum() if not today_logs.empty else 0
    
    col1, col2 = st.columns(2)
    col1.metric("Fuel Tank (kcal)", f"{total_cals} / {st.session_state.daily_target}", delta=int(st.session_state.daily_target - total_cals), delta_color="normal")
    col2.metric("Engine Block (Pro g)", f"{total_pro} / {st.session_state.protein_target}", delta=int(total_pro - st.session_state.protein_target))
    
    st.divider()
    
    # --- The Macro Pie Chart ---
    st.subheader("Fuel Mixture Breakdown")
    if total_pro > 0 or total_carbs > 0 or total_fats > 0:
        # Create a dataframe for Plotly
        macro_df = pd.DataFrame({
            "Macro": ["Protein", "Carbs", "Fats"],
            "Grams": [total_pro, total_carbs, total_fats]
        })
        # Generate the interactive pie chart
        fig = px.pie(macro_df, values='Grams', names='Macro', hole=0.4,
                     color='Macro', color_discrete_map={'Protein':'#ff4b4b', 'Carbs':'#ffa500', 'Fats':'#00bfff'})
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log fuel to see your macro breakdown.")

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
        trend_data = st.session_state.logs.groupby("Date")[["Calories", "Protein", "Carbs", "Fats"]].sum()
        st.bar_chart(trend_data["Calories"], color="#ff4b4b")
        st.caption("Today's Maintenance Log:")
        st.dataframe(today_logs[["Time", "Item", "Calories", "Protein", "Carbs", "Fats"]], use_container_width=True, hide_index=True)

# --- TAB 2: Vision Scanner ---
with tab_scan:
    st.header("AI Dashcam Scanner")
    food_image = st.camera_input("Snap a picture of your fuel")
    
    if food_image is not None:
        if st.button("Run AI Diagnostics"):
            with st.spinner("Analyzing full telemetry..."):
                try:
                    img = Image.open(food_image)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = """
                    Analyze this food. Return ONLY a valid JSON object with these keys:
                    - "item": A short name for the food (string).
                    - "calories": Integer estimate of calories.
                    - "protein": Integer estimate of protein in grams.
                    - "carbs": Integer estimate of carbohydrates in grams.
                    - "fats": Integer estimate of fats in grams.
                    - "tomato_warning": Boolean (true if tomatoes are visible, false otherwise).
                    Do not include markdown.
                    """
                    response = model.generate_content([prompt, img])
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    st.session_state.pending_scan = json.loads(clean_json)
                except Exception as e:
                    st.error(f"Engine fault detected: {e}")
                    
        if st.session_state.pending_scan:
            p = st.session_state.pending_scan
            st.divider()
            if p.get("tomato_warning"):
                st.error("🚨 **WARNING: RESTRICTED COMPONENT (TOMATO) DETECTED!** 🚨")
            else:
                st.success("✅ Clear of restricted components.")
                
            st.markdown(f"**Detected:** {p.get('item')}")
            st.markdown(f"**Macros:** {p.get('calories')} kcal | Pro: {p.get('protein')}g | Carbs: {p.get('carbs')}g | Fat: {p.get('fats')}g")
            
            colY, colN = st.columns(2)
            if colY.button("✅ Yes, Log It"):
                new_entry = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Time": datetime.now().strftime("%H:%M"),
                    "Item": p.get('item'), 
                    "Calories": p.get('calories'), 
                    "Protein": p.get('protein'),
                    "Carbs": p.get('carbs', 0),
                    "Fats": p.get('fats', 0)
                }])
                updated_data = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
                conn.update(worksheet="Logs", data=updated_data)
                st.session_state.logs = updated_data
                st.session_state.pending_scan = None 
                st.success("Telemetry saved to cloud!")
                st.rerun() 
            if colN.button("❌ No, Discard"):
                st.session_state.pending_scan = None
                st.rerun()

# --- TAB 3: Manual Logging ---
with tab_log:
    st.header("Manual Refuel")
    with st.form("manual_log_form", clear_on_submit=True):
        item = st.text_input("Fuel Type (Food Item)")
        colA, colB = st.columns(2)
        cals = colA.number_input("Calories", min_value=0, step=50)
        pro = colB.number_input("Protein (g)", min_value=0, step=5)
        
        colC, colD = st.columns(2)
        carbs = colC.number_input("Carbs (g)", min_value=0, step=5)
        fats = colD.number_input("Fats (g)", min_value=0, step=5)
        
        if st.form_submit_button("Pump Fuel") and item:
            new_entry = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Item": item, 
                "Calories": cals, 
                "Protein": pro,
                "Carbs": carbs,
                "Fats": fats
            }])
            updated_data = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
            conn.update(worksheet="Logs", data=updated_data)
            st.session_state.logs = updated_data
            st.success(f"Topped off with {item} and saved to cloud!")

# --- TAB 4: Settings (AI Driver Tuning) ---
with tab_settings:
    st.header("Driver Dyno Tune")
    st.markdown("Input your chassis specs to calculate exact macro targets.")
    with st.form("ai_tune_form"):
        col1, col2 = st.columns(2)
        age = col1.number_input("Age", min_value=16, max_value=100, value=22)
        height = col2.text_input("Height (e.g., 5'10\")", value="5'10\"")
        weight = col1.number_input("Current Weight (lbs)", min_value=80, value=180)
        goal_weight = col2.number_input("Goal Weight (lbs)", min_value=80, value=170)
        
        if st.form_submit_button("Run AI Diagnostics"):
            with st.spinner("Calculating optimal telemetry..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"""
                    The user is {age} years old, {height} tall, weighs {weight} lbs, and wants to reach {goal_weight} lbs.
                    1. Calculate a healthy daily calorie target for weight loss.
                    2. Calculate a daily protein goal (in grams) to maintain muscle.
                    3. Write a 2-sentence piece of advice on what specific types of foods or habits they should cut back on to hit this goal.
                    Return ONLY a JSON object: {{"calories": int, "protein": int, "advice": "string"}}
                    """
                    response = model.generate_content(prompt)
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    tune_data = json.loads(clean_json)
                    
                    st.session_state.daily_target = tune_data['calories']
                    st.session_state.protein_target = tune_data['protein']
                    st.session_state.ai_advice = tune_data['advice']
                    st.success("ECU Flashed Successfully!")
                except Exception as e:
                    st.error(f"Calculation error: {e}")
                    
    st.divider()
    st.subheader("Current ECU Map")
    colA, colB = st.columns(2)
    st.session_state.daily_target = colA.number_input("Daily Calorie Budget", value=st.session_state.daily_target, step=100)
    st.session_state.protein_target = colB.number_input("Protein Goal (g)", value=st.session_state.protein_target, step=10)
    
    if st.session_state.ai_advice:
        st.info(f"**Chief Mechanic's Advice:** {st.session_state.ai_advice}")
    st.divider()
    st.error("Active Filter: **NO TOMATOES**")

# --- TAB 5: Alerts (AI Push Notifications) ---
with tab_alerts:
    st.header("Maintenance Reminders")
    st.markdown("Trigger push notifications directly to your Pixel via ntfy.sh.")
    ntfy_topic = "sams_kei_garage_telemetry_99" 
    st.info(f"Subscribe to topic: **{ntfy_topic}** in the ntfy Android app.")
    
    colA, colB = st.columns(2)
    with colA:
        if st.button("💧 Hydration Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data="Engine running hot. Drink a glass of water!".encode('utf-8'), headers={"Title": "Coolant Check", "Tags": "droplet"})
            st.success("Ping sent!")
        if st.button("🚶 Stand Up Alert"):
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data="You've been idling too long. Stand up and stretch the chassis.".encode('utf-8'), headers={"Title": "Idle Warning", "Tags": "warning,walking"})
            st.success("Ping sent!")
            
    st.divider()
    st.subheader("Smart Meal Planning")
    st.markdown("Simulate an automated alert sent 1 hour before mealtime.")
    if st.button("🍽️ Generate & Send Pre-Meal Alert"):
        with st.spinner("Consulting the chef..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = "Suggest one quick, healthy, high-protein meal idea (under 500 calories). IT MUST STRICTLY NOT CONTAIN TOMATOES. Keep the response to one single, punchy sentence."
                meal_idea = model.generate_content(prompt).text.strip()
                requests.post(f"https://ntfy.sh/{ntfy_topic}", data=meal_idea.encode('utf-8'), headers={"Title": "Upcoming Refuel Suggestion", "Tags": "bento,robot"})
                st.success("AI meal suggestion sent to your Pixel 9 Pro!")
                st.write(f"**Payload Sent:** {meal_idea}")
            except Exception as e:
                st.error(f"Comms failure: {e}")
