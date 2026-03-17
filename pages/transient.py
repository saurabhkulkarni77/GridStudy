"""pages/transient.py — Transient Stability Study."""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.physics import (GridParams, swing_equation, compute_cct,
                            gen_stability_status, GENERATORS, CRITICAL_ANGLE)
from utils.charts  import base_layout, PALETTE, TEXT_CLR, SUBTLE


GEN_COLORS = [PALETTE["orange"], PALETTE["blue"], PALETTE["red"]]


def render():
    p_raw = st.session_state.get("params", {})
    p = GridParams(**{k: v for k, v in p_raw.items() if k in GridParams.__dataclass_fields__})
    t_arr, deltas, freq_dev = swing_equation(p)
    cct = compute_cct(p)

    statuses = [gen_stability_status(d) for d in deltas]
    max_deltas = [float(np.max(np.abs(d))) for d in deltas]
    n_unstable  = sum(1 for s in statuses if s == "unstable")
    n_marginal  = sum(1 for s in statuses if s == "marginal")
    max_freq_dev = float(np.max(np.abs(freq_dev))) * p.frequency

    # ── KPIs ──────────────────────────────────────────────────────────────────
    cols = st.columns(4)
    kpis = [
        ("Critical Clearing Time", f"{cct:.0f} ms",
         "ok" if cct > 150 else "warn" if cct > 80 else "danger"),
        ("Fault Duration", f"{p.fault_dur:.0f} ms",
         "ok" if p.fault_dur < cct * 0.7 else "warn" if p.fault_dur < cct else "danger"),
        ("Unstable Generators", str(n_unstable),
         "ok" if n_unstable == 0 else "danger"),
        ("Max Freq. Deviation", f"{max_freq_dev:.3f} Hz",
         "ok" if max_freq_dev < 0.3 else "warn" if max_freq_dev < 0.5 else "danger"),
    ]
    for col, (label, value, cls) in zip(cols, kpis):
        sub = {
            "ok": "Acceptable", "warn": "Monitor", "danger": "Critical!"
        }[cls]
        col.markdown(f"""
        <div class="mcard">
          <div class="mcard-label">{label}</div>
          <div class="mcard-value {cls}">{value}</div>
          <div class="mcard-sub {cls}">{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Swing curve ───────────────────────────────────────────────────────────
    # Downsample for performance
    step = max(1, len(t_arr) // 600)
    t_ds = t_arr[::step]

    fig_sw = go.Figure()
    for i, (g, d, col) in enumerate(zip(GENERATORS, deltas, GEN_COLORS)):
        fig_sw.add_trace(go.Scatter(
            x=t_ds, y=d[::step], name=g["name"],
            line=dict(color=col, width=2),
        ))
    # Critical clearing angle line
    fig_sw.add_hline(y=CRITICAL_ANGLE, line_dash="dash", line_color=PALETTE["green"],
                     annotation_text=f"Critical angle ({CRITICAL_ANGLE}°)",
                     annotation_font_color=PALETTE["green"], annotation_font_size=10)
    # Fault window shading
    fig_sw.add_vrect(
        x0=0.5, x1=0.5 + p.fault_dur / 1000,
        fillcolor="rgba(248,81,73,0.12)", line_width=0,
        annotation_text="Fault", annotation_position="top left",
        annotation_font_color=PALETTE["red"], annotation_font_size=10,
    )
    fig_sw.update_layout(**base_layout("Rotor angle deviation — swing curve", h=340))
    fig_sw.update_yaxes(title_text="Rotor angle δ (degrees)")
    fig_sw.update_xaxes(title_text="Time (s)")
    st.plotly_chart(fig_sw, use_container_width=True)

    # ── Two-col: frequency + energy area ─────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        fig_fr = go.Figure()
        fig_fr.add_trace(go.Scatter(
            x=t_ds, y=(freq_dev[::step] * p.frequency),
            name="Δf", line=dict(color=PALETTE["purple"], width=2),
            fill="tozeroy", fillcolor="rgba(188,140,255,0.08)",
        ))
        fig_fr.add_hline(y=0.5,  line_dash="dot", line_color=PALETTE["amber"],
                         annotation_text="UFLS threshold (+0.5 Hz)",
                         annotation_font_size=9, annotation_font_color=PALETTE["amber"])
        fig_fr.add_hline(y=-0.5, line_dash="dot", line_color=PALETTE["amber"],
                         annotation_text="UFLS threshold (−0.5 Hz)",
                         annotation_font_size=9, annotation_font_color=PALETTE["amber"])
        fig_fr.update_layout(**base_layout("Frequency deviation", h=260, legend=False))
        fig_fr.update_yaxes(title_text="Δf (Hz)")
        fig_fr.update_xaxes(title_text="Time (s)")
        st.plotly_chart(fig_fr, use_container_width=True)

    with c2:
        # Equal area criterion visualisation for Gen 1
        d_deg   = np.linspace(0, 180, 400)
        d_rad   = np.radians(d_deg)
        Pm1     = p.gen_mw * GENERATORS[0]["Pm_frac"]
        ke      = {"3-Phase (Severe)": 0.10, "Line-to-Line": 0.35,
                   "Double Line-to-Ground": 0.25, "Single Line-to-Ground": 0.55
                   }.get(p.fault_type, 0.10)
        Pe_pre  = Pm1 * np.sin(d_rad)
        Pe_flt  = ke * Pm1 * np.sin(d_rad)
        Pe_post = 0.95 * Pm1 * np.sin(d_rad)

        fig_ea = go.Figure()
        fig_ea.add_trace(go.Scatter(x=d_deg, y=Pe_pre,  name="Pre-fault Pe",
                                    line=dict(color=PALETTE["green"], width=1.5)))
        fig_ea.add_trace(go.Scatter(x=d_deg, y=Pe_flt,  name="Fault Pe",
                                    line=dict(color=PALETTE["red"], width=1.5, dash="dash")))
        fig_ea.add_trace(go.Scatter(x=d_deg, y=Pe_post, name="Post-fault Pe",
                                    line=dict(color=PALETTE["blue"], width=1.5)))
        fig_ea.add_hline(y=Pm1, line_dash="dot", line_color=SUBTLE,
                         annotation_text="Pm (mechanical)", annotation_font_size=9)
        fig_ea.update_layout(**base_layout("Equal area criterion — Gen 1", h=260))
        fig_ea.update_yaxes(title_text="Power (MW)")
        fig_ea.update_xaxes(title_text="Rotor angle (°)", range=[0, 180])
        st.plotly_chart(fig_ea, use_container_width=True)

    # ── Generator stability table ─────────────────────────────────────────────
    st.markdown("#### Generator stability classification")
    badge = lambda s: {
        "stable":   '<span class="badge-stable">Stable</span>',
        "marginal": '<span class="badge-marginal">Marginal</span>',
        "unstable": '<span class="badge-unstable">Unstable</span>',
    }[s]

    rows = ""
    for i, g in enumerate(GENERATORS):
        rows += f"""
        <tr>
          <td style="padding:7px 10px;font-size:12px">{g["name"]}</td>
          <td style="padding:7px 10px;font-size:12px">{g["H"]} s</td>
          <td style="padding:7px 10px;font-size:12px">{g["delta0"]}°</td>
          <td style="padding:7px 10px;font-size:12px">{max_deltas[i]:.1f}°</td>
          <td style="padding:7px 10px;font-size:12px">{badge(statuses[i])}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#161b22;border-radius:8px">
      <thead>
        <tr style="background:#21262d;">
          <th style="padding:7px 10px;font-size:11px;color:#8b949e;text-align:left">Generator</th>
          <th style="padding:7px 10px;font-size:11px;color:#8b949e;text-align:left">H (s)</th>
          <th style="padding:7px 10px;font-size:11px;color:#8b949e;text-align:left">δ₀ (°)</th>
          <th style="padding:7px 10px;font-size:11px;color:#8b949e;text-align:left">δ max (°)</th>
          <th style="padding:7px 10px;font-size:11px;color:#8b949e;text-align:left">Status</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

    # ── Findings ──────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Transient stability findings")
    margin_ms = cct - p.fault_dur
    if p.fault_dur >= cct:
        st.error(f"⚠️ **System is transiently unstable!** Fault duration ({p.fault_dur} ms) "
                 f"exceeds critical clearing time ({cct:.0f} ms). "
                 "Improve relay speed or add power system stabilisers (PSS).")
    elif margin_ms < 50:
        st.warning(f"⚠️ **Marginal transient stability.** Clearing time margin is only {margin_ms:.0f} ms. "
                   "Consider faster protection relays.")
    else:
        st.success(f"✅ System is transiently stable. CCT = {cct:.0f} ms, fault cleared in "
                   f"{p.fault_dur} ms (margin = {margin_ms:.0f} ms).")

    with st.expander("Theory: Transient stability principles"):
        st.markdown("""
**Transient stability** is the ability of synchronous generators to remain in synchronism
following a severe disturbance (fault, switching).

**Swing equation:** `2H/ωs · d²δ/dt² = Pm − Pe − D·dδ/dt`
- **H** = inertia constant (MJ/MVA)
- **δ** = rotor angle
- **Pm** = mechanical power input
- **Pe** = electrical power output
- **D** = damping coefficient

**Critical Clearing Time (CCT)**: Maximum time a fault can persist before the generator loses
synchronism. Protection relays must clear faults within the CCT.

**Equal Area Criterion (EAC)**: Graphical method comparing accelerating area (fault-on) with
decelerating area (post-fault). Stability requires decelerating area ≥ accelerating area.

**NERC Reliability Standard FAC-001/002** and **IEEE Std 1110** define transient stability
study requirements for planning and operations.
        """)
