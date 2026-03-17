"""pages/voltage.py — Voltage Stability Study."""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.physics import GridParams, compute_voltage, bus_v_status, BUSES
from utils.charts  import base_layout, PALETTE, DARK_BG, TEXT_CLR, SUBTLE, GRID_CLR


def render():
    p_raw = st.session_state.get("params", {})
    p = GridParams(**{k: v for k, v in p_raw.items() if k in GridParams.__dataclass_fields__})
    lam, V_up, V_lo, c_idx, margin, bus_voltages, q_res = compute_voltage(p)

    v_min   = min(bus_voltages.values())
    v_max   = max(bus_voltages.values())
    v_avg   = sum(bus_voltages.values()) / len(bus_voltages)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    cols = st.columns(4)
    kpis = [
        ("Min Bus Voltage", f"{v_min:.3f} pu",
         "ok" if v_min >= 0.95 else "warn" if v_min >= 0.90 else "danger"),
        ("Max Bus Voltage", f"{v_max:.3f} pu",
         "ok" if v_max <= 1.05 else "warn"),
        ("Load Margin", f"{margin:.0f} MW",
         "ok" if margin > 200 else "warn" if margin > 100 else "danger"),
        ("Voltage Stability Index", f"{v_avg:.3f} pu",
         "ok" if v_avg >= 0.95 else "warn" if v_avg >= 0.90 else "danger"),
    ]
    for col, (label, value, cls) in zip(cols, kpis):
        sub = {"ok": "Secure", "warn": "Marginal", "danger": "Critical!"}[cls]
        col.markdown(f"""
        <div class="mcard">
          <div class="mcard-label">{label}</div>
          <div class="mcard-value {cls}">{value}</div>
          <div class="mcard-sub {cls}">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── P-V nose curve ─────────────────────────────────────────────────────
    fig_pv = go.Figure()
    fig_pv.add_trace(go.Scatter(
        x=lam[:c_idx], y=V_up[:c_idx], name="Upper operating point",
        line=dict(color=PALETTE["blue"], width=2.5),
    ))
    fig_pv.add_trace(go.Scatter(
        x=lam[:c_idx], y=V_lo[:c_idx], name="Lower operating point",
        line=dict(color=PALETTE["blue"], width=1.5, dash="dash"),
    ))
    # Nose / collapse point
    fig_pv.add_trace(go.Scatter(
        x=[lam[c_idx]], y=[V_up[c_idx]], name="Voltage collapse point",
        mode="markers", marker=dict(color=PALETTE["red"], size=12, symbol="x"),
    ))
    # Operating point
    op_lam = p.load_mw / p.gen_mw
    op_v   = float(V_up[np.argmin(np.abs(lam - op_lam))])
    fig_pv.add_trace(go.Scatter(
        x=[op_lam], y=[op_v], name="Current operating point",
        mode="markers", marker=dict(color=PALETTE["green"], size=10, symbol="circle"),
    ))
    # Margin arrow annotation
    fig_pv.add_annotation(
        x=lam[c_idx], y=V_up[c_idx],
        text=f"Collapse\n{margin:.0f} MW margin",
        showarrow=True, arrowhead=2, arrowcolor=PALETTE["red"],
        font=dict(color=PALETTE["red"], size=10), ax=40, ay=-30,
    )
    fig_pv.add_hline(y=0.90, line_dash="dot", line_color=PALETTE["amber"],
                     annotation_text="Min voltage (0.90 pu)",
                     annotation_font_color=PALETTE["amber"], annotation_font_size=10)

    fig_pv.update_layout(**base_layout("P-V nose curve — voltage collapse analysis", h=340))
    fig_pv.update_yaxes(title_text="Voltage (pu)", range=[0.45, 1.15])
    fig_pv.update_xaxes(title_text="Load parameter λ (p.u.)")
    st.plotly_chart(fig_pv, use_container_width=True)

    # ── Two-col: bus profile + Q reserve ──────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        bus_names = list(bus_voltages.keys())
        v_vals    = list(bus_voltages.values())
        b_colors  = [
            PALETTE["red"]   if v < 0.90 else
            PALETTE["amber"] if v < 0.95 or v > 1.05 else
            PALETTE["green"]
            for v in v_vals
        ]
        fig_bv = go.Figure(go.Bar(
            x=bus_names, y=v_vals, marker_color=b_colors, marker_line_width=0,
            text=[f"{v:.3f}" for v in v_vals], textposition="outside",
            textfont=dict(size=10, color=TEXT_CLR),
        ))
        fig_bv.add_hline(y=1.05, line_dash="dot", line_color=PALETTE["amber"],
                         annotation_text="Max (1.05)", annotation_font_size=9,
                         annotation_font_color=PALETTE["amber"])
        fig_bv.add_hline(y=0.95, line_dash="dot", line_color=PALETTE["amber"],
                         annotation_text="Min (0.95)", annotation_font_size=9,
                         annotation_font_color=PALETTE["amber"])
        fig_bv.update_layout(**base_layout("Bus voltage profile", h=280, legend=False))
        fig_bv.update_yaxes(range=[0.78, 1.12], title_text="Voltage (pu)")
        st.plotly_chart(fig_bv, use_container_width=True)

    with c2:
        gen_names  = ["Gen 1", "Gen 2", "Gen 3"]
        q_max      = [250, 200, 180]
        q_colors   = [
            PALETTE["red"]   if q_res[i] < 30 else
            PALETTE["amber"] if q_res[i] < 60 else
            PALETTE["green"]
            for i in range(3)
        ]
        fig_qr = go.Figure()
        fig_qr.add_trace(go.Bar(
            name="Q reserve", x=gen_names, y=q_res,
            marker_color=q_colors, marker_line_width=0,
            text=[f"{v:.0f} Mvar" for v in q_res], textposition="outside",
            textfont=dict(size=10, color=TEXT_CLR),
        ))
        fig_qr.add_trace(go.Bar(
            name="Q used", x=gen_names,
            y=[q_max[i] - q_res[i] for i in range(3)],
            marker_color="rgba(88,166,255,0.25)", marker_line_width=0,
        ))
        fig_qr.update_layout(
            **base_layout("Generator reactive power reserve (Mvar)", h=280),
            barmode="stack",
        )
        fig_qr.update_yaxes(title_text="Reactive power (Mvar)")
        st.plotly_chart(fig_qr, use_container_width=True)

    # ── VQS curve (V vs Q at weakest bus) ────────────────────────────────────
    q_injected = np.linspace(-100, 200, 200)
    weakest_v  = v_min + 0.04 * np.log1p(q_injected / 50 + 1)
    weakest_v  = np.clip(weakest_v, 0.75, 1.10)

    fig_vq = go.Figure()
    fig_vq.add_trace(go.Scatter(
        x=q_injected, y=weakest_v, name="V–Q curve (weakest bus)",
        line=dict(color=PALETTE["purple"], width=2),
        fill="tozeroy", fillcolor="rgba(188,140,255,0.06)",
    ))
    fig_vq.add_hline(y=0.90, line_dash="dot", line_color=PALETTE["amber"],
                     annotation_text="Min acceptable voltage",
                     annotation_font_color=PALETTE["amber"], annotation_font_size=10)
    fig_vq.add_vline(x=0, line_dash="dash", line_color=SUBTLE,
                     annotation_text="Q = 0", annotation_font_size=9)
    fig_vq.update_layout(**base_layout("V–Q curve — reactive power sensitivity at weakest bus", h=250, legend=False))
    fig_vq.update_xaxes(title_text="Reactive power injection Q (Mvar)")
    fig_vq.update_yaxes(title_text="Bus voltage (pu)", range=[0.70, 1.15])
    st.plotly_chart(fig_vq, use_container_width=True)

    # ── Findings ──────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Voltage stability findings")
    if margin < 100:
        st.error(f"⚠️ **Voltage collapse risk.** Load margin of {margin:.0f} MW is critically low. "
                 "Install reactive compensation or reduce load immediately.")
    elif margin < 200:
        st.warning(f"⚠️ **Marginal voltage stability.** Load margin is {margin:.0f} MW. "
                   "Consider installing shunt capacitors or activating generator reactive reserves.")
    else:
        st.success(f"✅ Voltage stability secure. Load margin to collapse: **{margin:.0f} MW**.")

    with st.expander("Theory: Voltage stability principles"):
        st.markdown("""
**Voltage stability** is the ability of a system to maintain acceptable voltages at all buses
following a disturbance. Instability leads to progressive voltage collapse.

**Key methods:**
- **P-V curve (nose curve)**: Plots bus voltage vs. load power. The tip of the nose is the
  maximum loadability point — exceeding it causes voltage collapse.
- **Q-V curve**: Shows reactive power required to maintain a given voltage. The minimum of the
  Q-V curve defines the reactive power margin.
- **Continuation power flow**: Parametric load increase traces the entire P-V curve through
  the nose, locating the exact collapse point.
- **Static voltage stability index (VSI)**: L-index or voltage collapse proximity index
  computed from the power flow Jacobian.

**IEEE PES Std 1110** and the **WECC Voltage Stability Criteria** define planning standards.
        """)
