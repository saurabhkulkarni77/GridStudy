"""pages/thermal.py — Thermal Stability Study."""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.physics import GridParams, compute_thermal, line_status, LINES, THERMAL_LIMIT_C, AMBIENT_C
from utils.charts  import base_layout, PALETTE, DARK_BG, GRID_CLR, SUBTLE, TEXT_CLR, status_color


def render():
    p_raw = st.session_state.get("params", {})
    p = GridParams(**{k: v for k, v in p_raw.items() if k in GridParams.__dataclass_fields__})
    loadings, t_arr, temp_arr = compute_thermal(p)

    # ── Top KPIs ──────────────────────────────────────────────────────────────
    max_loading  = max(loadings.values())
    n_overloaded = sum(1 for v in loadings.values() if v > 95)
    n_warning    = sum(1 for v in loadings.values() if 80 < v <= 95)
    max_temp     = float(np.max(temp_arr))
    thermal_margin = max(0, THERMAL_LIMIT_C - max_temp)

    cols = st.columns(4)
    kpis = [
        ("Max Line Loading", f"{max_loading:.1f}%",
         "ok" if max_loading < 80 else "warn" if max_loading < 95 else "danger"),
        ("Overloaded Lines", str(n_overloaded),
         "ok" if n_overloaded == 0 else "danger"),
        ("Max Conductor Temp", f"{max_temp:.1f} °C",
         "ok" if max_temp < 75 else "warn" if max_temp < 90 else "danger"),
        ("Thermal Margin", f"{thermal_margin:.1f} °C",
         "ok" if thermal_margin > 15 else "warn" if thermal_margin > 5 else "danger"),
    ]
    for col, (label, value, cls) in zip(cols, kpis):
        sub = {"ok": "Within limits", "warn": "Near limit", "danger": "Exceeded!"}[cls]
        col.markdown(f"""
        <div class="mcard">
          <div class="mcard-label">{label}</div>
          <div class="mcard-value {cls}">{value}</div>
          <div class="mcard-sub {cls}">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Bar chart: Line loading ───────────────────────────────────────────────
    names  = list(loadings.keys())
    values = list(loadings.values())
    colors = [
        PALETTE["red"] if v > 95 else PALETTE["amber"] if v > 80 else PALETTE["green"]
        for v in values
    ]

    fig_bar = go.Figure(go.Bar(
        x=names, y=values,
        marker_color=colors,
        marker_line_width=0,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=10, color=TEXT_CLR),
    ))
    fig_bar.add_hline(y=100, line_dash="dash", line_color=PALETTE["red"],
                      annotation_text="Thermal limit (100%)",
                      annotation_font_color=PALETTE["red"], annotation_font_size=10)
    fig_bar.add_hline(y=80, line_dash="dot",  line_color=PALETTE["amber"],
                      annotation_text="Warning (80%)",
                      annotation_font_color=PALETTE["amber"], annotation_font_size=10)
    fig_bar.update_layout(**base_layout("Line thermal loading — % of rated capacity", h=300, legend=False))
    fig_bar.update_yaxes(range=[0, 115], title_text="% of thermal limit")
    fig_bar.update_xaxes(title_text="Transmission line")
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Two-col: temperature curve + detail table ─────────────────────────────
    c1, c2 = st.columns([3, 2])

    with c1:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=t_arr, y=temp_arr, name="Conductor temp",
            line=dict(color=PALETTE["orange"], width=2),
            fill="tozeroy", fillcolor="rgba(240,136,62,0.08)",
        ))
        fig_temp.add_hline(y=THERMAL_LIMIT_C, line_dash="dash",
                           line_color=PALETTE["red"],
                           annotation_text=f"Limit {THERMAL_LIMIT_C}°C",
                           annotation_font_color=PALETTE["red"], annotation_font_size=10)
        fig_temp.add_hline(y=75, line_dash="dot", line_color=PALETTE["amber"],
                           annotation_text="Warning 75°C",
                           annotation_font_color=PALETTE["amber"], annotation_font_size=10)
        fig_temp.update_layout(**base_layout("Conductor temperature over time", h=280, legend=False))
        fig_temp.update_yaxes(title_text="Temperature (°C)", range=[20, 105])
        fig_temp.update_xaxes(title_text="Time (s)")
        st.plotly_chart(fig_temp, use_container_width=True)

    with c2:
        st.markdown("#### Line loading detail")
        rows = []
        for name, fr, to, cap in LINES:
            loading = loadings[name]
            status  = line_status(loading)
            badge   = {
                "normal":     '<span class="badge-stable">Normal</span>',
                "warning":    '<span class="badge-marginal">Warning</span>',
                "overloaded": '<span class="badge-unstable">Overloaded</span>',
            }[status]
            rows.append(f"""
            <tr>
              <td style="padding:6px 8px;font-size:12px">{name}</td>
              <td style="padding:6px 8px;font-size:12px">{fr}→{to}</td>
              <td style="padding:6px 8px;font-size:12px">{loading:.1f}%</td>
              <td style="padding:6px 8px;font-size:12px">{badge}</td>
            </tr>""")
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;overflow:hidden">
          <thead>
            <tr style="background:#21262d;">
              <th style="padding:6px 8px;font-size:11px;color:#8b949e;text-align:left">Line</th>
              <th style="padding:6px 8px;font-size:11px;color:#8b949e;text-align:left">Route</th>
              <th style="padding:6px 8px;font-size:11px;color:#8b949e;text-align:left">Load%</th>
              <th style="padding:6px 8px;font-size:11px;color:#8b949e;text-align:left">Status</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>""", unsafe_allow_html=True)

    # ── Thermal recommendations ───────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Thermal study findings")
    if n_overloaded > 0:
        st.error(f"⚠️ **{n_overloaded} line(s) exceed thermal rating.** "
                 "Immediate re-dispatch or load shedding required to prevent conductor damage.")
    elif n_warning > 0:
        st.warning(f"⚠️ **{n_warning} line(s) approaching thermal limit.** "
                   "Monitor closely and prepare contingency re-dispatch.")
    else:
        st.success("✅ All lines within thermal limits. System is thermally secure under current loading.")

    with st.expander("Theory: Thermal stability principles"):
        st.markdown("""
**Thermal stability** concerns the ability of power system components to carry electrical current
without exceeding their rated temperature. Key concepts:

- **Conductor heating**: Current flow generates I²R losses → Joule heating. Conductor temperature
  follows a first-order thermal model: `T(t) = T_amb + ΔT_rated × (1 − e^{−t/τ})`
- **Thermal time constant (τ)**: Typically 3–15 minutes for overhead lines depending on conductor
  cross-section and thermal mass.
- **Emergency ratings**: Conductors can usually carry 115–125% of normal rating for short periods
  (< 15 min) before permanent damage (annealing) occurs.
- **N-1 security**: The system must remain thermally secure after loss of any single element.

**IEEE Std 738** defines the heat balance equation used in conductor ampacity calculations.
        """)
