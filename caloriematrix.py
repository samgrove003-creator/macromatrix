Python 3.12.4 (tags/v3.12.4:8e8a4ba, Jun  6 2024, 19:30:16) [MSC v.1940 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. App Configuration & State Management ---
st.set_page_config(page_title="Macro Matrix", page_icon="📊", layout="centered")

# Initialize session state for data persistence
if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Date", "Time", "Item", "Calories", "Protein"])
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2200
if 'protein_target' not in st.session_state:
    st.session_state.protein_target = 160

# --- 2. Mobile-Friendly Navigation ---
st.title("📊 Macro Matrix")
tab_dash, tab_log, tab_scan, tab_settings = st.tabs(["Dashboard", "Log Food", "📷 Scanner", "Settings"])

# --- TAB 1: Dashboard & Charts ---
with tab_dash:
    st.header("Daily Overview")
    
    # Filter logs for today
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = st.session_state.logs[st.session_state.logs["Date"] == today_str]
    
    total_cals = today_logs["Calories"].sum() if not today_logs.empty else 0
    total_pro = today_logs["Protein"].sum() if not today_logs.empty else 0
    
    # Top-level metrics
    col1, col2 = st.columns(2)
    col1.metric("Calories", f"{total_cals} / {st.session_state.daily_target}", delta=int(st.session_state.daily_target - total_cals), delta_color="normal")
    col2.metric("Protein (g)", f"{total_pro} / {st.session_state.protein_target}", delta=int(total_pro - st.session_state.protein_target))
    
    st.divider()
    
    # Calorie Burn Down Chart
    st.subheader("Intake Visualization")
    if not st.session_state.logs.empty:
        # Group by Date to show a trend over time
        trend_data = st.session_state.logs.groupby("Date")[["Calories", "Protein"]].sum()
        st.bar_chart(trend_data["Calories"], color="#ff4b4b")
        
        st.caption("Recent Entries:")
        st.dataframe(today_logs[["Time", "Item", "Calories", "Protein"]], use_container_width=True, hide_index=True)
    else:
        st.info("No data logged yet. Head to the 'Log Food' or 'Scanner' tab.")

# --- TAB 2: Manual Logging ---
with tab_log:
    st.header("Manual Entry")
    with st.form("manual_log_form", clear_on_submit=True):
        item = st.text_input("Food Item", placeholder="e.g., Grilled Chicken Bowl")
        colA, colB = st.columns(2)
        cals = colA.number_input("Calories", min_value=0, step=50)
        pro = colB.number_input("Protein (g)", min_value=0, step=5)
        
        submitted = st.form_submit_button("Add to Database")
        if submitted and item:
            new_entry = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Item": item,
                "Calories": cals,
                "Protein": pro
            }])
            st.session_state.logs = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
            st.success(f"Logged {item} successfully!")

# --- TAB 3: Vision Scanner (Camera Integration) ---
with tab_scan:
    st.header("AI Food Scanner")
    st.markdown("Use your Pixel's camera to analyze a meal.")
    
    # Hooks into the device hardware
    food_image = st.camera_input("Take a picture of your food")
...     
...     if food_image is not None:
...         # Display the captured image buffer
...         st.image(food_image, caption="Captured Image", use_column_width=True)
...         
...         # Placeholder for ML Vision Processing
...         with st.spinner("Running Vision Analysis..."):
...             # In a production app, we would send 'food_image.getvalue()' to an API here.
...             st.success("Analysis Complete (Simulated)")
...             
...         # Simulated Output for the Prototype
...         st.write("**Detected:** Mixed Grill Plate (No Tomato detected)")
...         st.write("**Estimated Macros:** 650 kcal | 45g Protein")
...         
...         if st.button("Log Simulated Detection"):
...             new_entry = pd.DataFrame([{
...                 "Date": datetime.now().strftime("%Y-%m-%d"),
...                 "Time": datetime.now().strftime("%H:%M"),
...                 "Item": "Auto-Scanned Meal",
...                 "Calories": 650,
...                 "Protein": 45
...             }])
...             st.session_state.logs = pd.concat([st.session_state.logs, new_entry], ignore_index=True)
...             st.success("Logged!")
... 
... # --- TAB 4: Settings & Dietary Filters ---
... with tab_settings:
...     st.header("App Configuration")
...     st.session_state.daily_target = st.number_input("Daily Calorie Budget", value=st.session_state.daily_target, step=100)
...     st.session_state.protein_target = st.number_input("Daily Protein Goal (g)", value=st.session_state.protein_target, step=10)
...     
...     st.divider()
...     st.subheader("Dietary Aversions")
...     st.error("Active Filter: **NO TOMATOES**")
