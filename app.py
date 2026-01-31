import streamlit as st
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from scipy.stats import zscore

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Troubleshooting Agent", page_icon="🤖", layout="wide")

# --- CUSTOM LOGGING TO UI ---
if 'logs' not in st.session_state:
    st.session_state.logs = []


def ui_log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    st.session_state.logs.append(entry)


# --- STEP 1: GENERATE SYNTHETIC DATA ---
@st.cache_data
def generate_system_data(n_samples=1000):
    """Generates server logs with normal behavior and injected anomalies."""
    np.random.seed(42)

    # Normal Data
    data = {
        'cpu_usage': np.random.normal(30, 5, n_samples),  # Mean 30%, SD 5
        'memory_usage': np.random.normal(40, 5, n_samples),  # Mean 40%, SD 5
        'network_latency': np.random.normal(50, 10, n_samples),  # Mean 50ms, SD 10
        'error_rate': np.random.poisson(1, n_samples)  # rare errors
    }
    df = pd.DataFrame(data)

    # Inject Anomalies (The "Problems")
    # 1. High CPU (Cause: Runaway Process)
    df.loc[900:920, 'cpu_usage'] = np.random.normal(90, 5, 21)

    # 2. Network Spike (Cause: DDoS Attack)
    df.loc[930:940, 'network_latency'] = np.random.normal(500, 50, 11)

    # 3. Memory Leak (Cause: App Bug)
    df.loc[950:960, 'memory_usage'] = np.random.normal(95, 2, 11)

    # Create Labels for Root Cause Training (Simplified for activity)
    # 0=Normal, 1=High CPU, 2=Network, 3=Memory
    conditions = [
        (df['cpu_usage'] > 80),
        (df['network_latency'] > 200),
        (df['memory_usage'] > 85)
    ]
    choices = ['High_CPU', 'Network_Lag', 'Memory_Leak']
    df['root_cause'] = np.select(conditions, choices, default='Normal')

    return df


# --- STEP 2: BUILD MODELS ---
def train_models(df):
    # A. Anomaly Detector (Unsupervised)
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    X = df.drop('root_cause', axis=1)
    iso_forest.fit(X)

    # B. Root Cause Classifier (Supervised)
    # We train this to learn MAPPING from metrics -> Label
    clf = DecisionTreeClassifier()
    y = df['root_cause']
    clf.fit(X, y)

    return iso_forest, clf


# --- SOLUTION RECOMMENDER ---
def recommend_solution(root_cause):
    solutions = {
        "High_CPU": "⚠️ Action: Auto-scale CPU cores or kill process PID 990.",
        "Network_Lag": "⚠️ Action: Reroute traffic via CDN and check firewall.",
        "Memory_Leak": "⚠️ Action: Restart Application Service (Safe Mode).",
        "Normal": "✅ System Healthy. No action needed."
    }
    return solutions.get(root_cause, "Unknown Issue")


# --- UI LAYOUT ---
st.title("🤖 MCert Troubleshooting Agent")
st.markdown("Automated AIOps: Detects, Diagnoses, and Resolves system anomalies.")
st.divider()

col1, col2 = st.columns([2, 1])

# --- MAIN DASHBOARD ---
with col1:
    st.subheader("📡 Live System Monitor")

    # 1. Load Data
    df = generate_system_data()

    if st.button("▶️ Start Monitoring Simulation"):
        st.session_state.logs = []  # Clear logs
        ui_log("Connecting to server telemetry stream...", "INIT")
        time.sleep(1)

        # Train Models
        ui_log("Training Isolation Forest (Anomaly Detection)...", "TRAIN")
        time.sleep(1)
        iso_model, cause_model = train_models(df)
        ui_log("Models trained and deployed.", "SUCCESS")

        # Simulate Live Check on specific "bad" rows we created
        test_indices = [10, 915, 935, 955]  # 1 Normal, 3 Anomalous

        for i in test_indices:
            row = df.iloc[[i]].drop('root_cause', axis=1)

            # A. Detect Anomaly
            is_anomaly = iso_model.predict(row)[0] == -1
            status = "🔴 ANOMALY DETECTED" if is_anomaly else "🟢 Normal"

            st.markdown(f"**Timestamp T-{i}:** {status}")
            st.dataframe(row)

            if is_anomaly:
                ui_log(f"Anomaly detected at T-{i}. Initiating diagnostics...", "WARNING")
                time.sleep(1)

                # B. Root Cause Analysis
                predicted_cause = cause_model.predict(row)[0]
                ui_log(f"Root Cause Identified: {predicted_cause}", "ANALYSIS")

                # C. Z-Score Confirmation (Which column is weird?)
                # Calculate Z-score against entire dataset mean
                z_scores = (row - df.drop('root_cause', axis=1).mean()) / df.drop('root_cause', axis=1).std()
                bad_col = z_scores.abs().idxmax(axis=1).values[0]
                ui_log(f"Culprit Metric: {bad_col} (Z-Score High)", "DEBUG")

                # D. Recommendation
                time.sleep(1)
                solution = recommend_solution(predicted_cause)
                st.success(f"**Recommendation:** {solution}")
                ui_log(f"Auto-Remediation: {solution}", "ACTION")

            else:
                ui_log(f"System Check T-{i}: Nominal.", "INFO")

            st.markdown("---")
            time.sleep(1.5)  # Delay for effect

# --- SIDEBAR LOGS ---
with col2:
    st.subheader("📝 Agent Logs")
    log_text = "\n".join(st.session_state.logs)
    st.text_area("Console", log_text, height=600, disabled=True)