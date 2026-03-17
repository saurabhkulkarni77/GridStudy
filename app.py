"""
GridStability Pro — Power System Stability Analysis Platform
Deployable Streamlit application
"""

import streamlit as st

st.set_page_config(
    page_title="GridStability Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Global */
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
  [data-testid="stSidebar"] .stMarkdown h3 { color: #58a6ff; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }
  .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }

  /* Header strip */
  .header-strip {
    background: linear-gradient(90deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 22px;
    margin-bottom: 1rem;
    display: flex; align-items: center; justify-content: space-between;
  }
  .header-title { font-size: 22px; font-weight: 600; color: #e6edf3; }
  .header-sub { font-size: 12px; color: #8b949e; margin-top: 2px; }

  /* Metric cards */
  .metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 1rem; }
  .mcard { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 14px 16px; }
  .mcard-label { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
  .mcard-value { font-size: 24px; font-weight: 600; }
  .mcard-sub { font-size: 11px; margin-top: 3px; }
  .ok   { color: #3fb950; }
  .warn { color: #d29922; }
  .danger { color: #f85149; }

  /* Section card */
  .section-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
  .section-title { font-size: 13px; font-weight: 600; color: #c9d1d9; margin-bottom: 10px; }

  /* Badge */
  .badge-stable   { background:#1a4a2e; color:#3fb950; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
  .badge-marginal { background:#3d2b00; color:#d29922; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
  .badge-unstable { background:#3d1414; color:#f85149; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }

  /* Divider */
  hr { border: none; border-top: 1px solid #30363d; margin: 12px 0; }

  /* Plotly charts dark match */
  .js-plotly-plot .plotly .main-svg { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Navigation ──────────────────────────────────────────────────────────────
pages = {
    "⚡ Thermal Stability":   "pages/thermal.py",
    "🔋 Voltage Stability":   "pages/voltage.py",
    "🌀 Transient Stability": "pages/transient.py",
    "🗺️ Grid Topology":       "pages/topology.py",
    "📊 Summary Report":      "pages/report.py",
}

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ GridStability Pro")
    st.markdown("---")

    st.markdown("### System Configuration")
    gen_mw   = st.slider("Generation (MW)",   200, 1400, 850, 10)
    load_mw  = st.slider("Load (MW)",         100, 1300, 780, 10)
    base_kv  = st.selectbox("Base Voltage (kV)", [115, 230, 345, 500, 765], index=2)
    frequency= st.selectbox("Frequency (Hz)", [50, 60], index=1)

    st.markdown("---")
    st.markdown("### Fault Parameters")
    fault_type = st.selectbox("Fault Type", [
        "3-Phase (Severe)",
        "Line-to-Line",
        "Single Line-to-Ground",
        "Double Line-to-Ground",
    ])
    fault_dur  = st.slider("Fault Duration (ms)", 20, 500, 100, 5)
    fault_bus  = st.selectbox("Fault Location", [
        "Bus 1 (Generator)", "Bus 2 (Transmission)",
        "Bus 3 (Load Center)", "Mid-line",
    ])

    st.markdown("---")
    st.markdown("### Analysis Settings")
    method  = st.selectbox("Study Method", [
        "Time-Domain Simulation",
        "Equal Area Criterion",
        "Eigenvalue Analysis",
        "Continuation Power Flow",
    ])
    sim_dur = st.slider("Simulation Duration (s)", 1, 30, 10)
    damping = st.slider("Damping Ratio (D)", 0.0, 0.5, 0.05, 0.01)

    st.markdown("---")
    run = st.button("▶  Run All Studies", use_container_width=True, type="primary")

# ── Store params in session state ────────────────────────────────────────────
st.session_state["params"] = dict(
    gen_mw=gen_mw, load_mw=load_mw, base_kv=base_kv,
    frequency=frequency, fault_type=fault_type,
    fault_dur=fault_dur, fault_bus=fault_bus,
    method=method, sim_dur=sim_dur, damping=damping,
    run=run,
)

# ── Header strip ─────────────────────────────────────────────────────────────
loading_ratio = load_mw / gen_mw
status_color  = "🟢" if loading_ratio < 0.85 else ("🟡" if loading_ratio < 0.95 else "🔴")

st.markdown(f"""
<div class="header-strip">
  <div>
    <div class="header-title">⚡ GridStability Pro</div>
    <div class="header-sub">Power System Stability Analysis Platform &nbsp;|&nbsp; {method}</div>
  </div>
  <div style="text-align:right;">
    <div style="color:#8b949e;font-size:12px;">System Status</div>
    <div style="font-size:16px;font-weight:600;color:#e6edf3;">{status_color} {'Stable' if loading_ratio < 0.85 else 'Marginal' if loading_ratio < 0.95 else 'Critical'}</div>
    <div style="color:#8b949e;font-size:11px;">Gen {gen_mw} MW &nbsp;/&nbsp; Load {load_mw} MW &nbsp;/&nbsp; {base_kv} kV</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Page tabs ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Thermal", "🔋 Voltage", "🌀 Transient", "🗺️ Topology", "📊 Report"
])

# Import page modules
import importlib, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from pages import thermal, voltage, transient, topology, report

with tab1: thermal.render()
with tab2: voltage.render()
with tab3: transient.render()
with tab4: topology.render()
with tab5: report.render()
