"""pages/report.py — Summary Report & Data Export."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io, csv, datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.physics import (GridParams, compute_thermal, compute_voltage,
                            swing_equation, compute_cct, gen_stability_status,
                            GENERATORS, LINES, line_status)
from utils.charts  import base_layout, PALETTE, TEXT_CLR, DARK_BG


def _overall_status(items: list) -> str:
    if "danger" in items: return ("danger", "⛔ Critical — immediate action required")
    if "warn"   in items: return ("warn",   "⚠️ Marginal — monitor and prepare mitigation")
    return ("ok", "✅ System secure under all study criteria")


def render():
    p_raw = st.session_state.get("params", {})
    p = GridParams(**{k: v for k, v in p_raw.items() if k in GridParams.__dataclass_fields__})

    # Run all studies
    loadings, t_arr, temp_arr     = compute_thermal(p)
    lam, V_up, V_lo, c_idx, margin, bus_v, q_res = compute_voltage(p)
    t_sw, deltas, freq_dev        = swing_equation(p)
    cct                           = compute_cct(p)
    statuses                      = [gen_stability_status(d) for d in deltas]

    max_loading = max(loadings.values())
    v_min       = min(bus_v.values())
    n_unstable  = sum(1 for s in statuses if s == "unstable")

    # Classify each study
    th_cls = "danger" if max_loading > 95 else "warn" if max_loading > 80 else "ok"
    vo_cls = "danger" if margin < 100   else "warn" if margin < 200    else "ok"
    tr_cls = ("danger" if p.fault_dur >= cct else
              "warn"   if cct - p.fault_dur < 50 else "ok")
    overall_cls, overall_msg = _overall_status([th_cls, vo_cls, tr_cls])

    # ── Overall status banner ─────────────────────────────────────────────────
    banner_bg = {"ok": "#1a3a2e", "warn": "#3d2b00", "danger": "#3d1414"}[overall_cls]
    banner_cl = {"ok": "#3fb950", "warn": "#d29922", "danger": "#f85149"}[overall_cls]
    st.markdown(f"""
    <div style="background:{banner_bg};border:1px solid {banner_cl};border-radius:10px;
                padding:16px 20px;margin-bottom:16px;font-size:15px;font-weight:600;color:{banner_cl}">
      {overall_msg}
    </div>""", unsafe_allow_html=True)

    # ── Study summary grid ────────────────────────────────────────────────────
    study_cols = st.columns(3)
    studies = [
        ("⚡ Thermal Stability", th_cls,
         f"Max loading: {max_loading:.1f}%",
         "ok" if max_loading < 80 else "warn" if max_loading < 95 else "Lines overloaded"),
        ("🔋 Voltage Stability", vo_cls,
         f"Load margin: {margin:.0f} MW",
         f"Min bus V: {v_min:.3f} pu"),
        ("🌀 Transient Stability", tr_cls,
         f"CCT: {cct:.0f} ms  |  Fault: {p.fault_dur} ms",
         f"Unstable gen: {n_unstable}  |  Margin: {max(0, cct - p.fault_dur):.0f} ms"),
    ]
    for col, (title, cls, line1, line2) in zip(study_cols, studies):
        icon = {"ok": "✅", "warn": "⚠️", "danger": "⛔"}[cls]
        clr  = {"ok": PALETTE["green"], "warn": PALETTE["amber"], "danger": PALETTE["red"]}[cls]
        col.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px">
          <div style="font-size:13px;font-weight:600;color:#c9d1d9;margin-bottom:8px">{icon} {title}</div>
          <div style="font-size:12px;color:{clr};margin-bottom:4px">{line1}</div>
          <div style="font-size:11px;color:#8b949e">{line2}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 4-panel overview chart ────────────────────────────────────────────────
    st.markdown("#### Study overview — combined results")
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Line thermal loading (%)",
            "Bus voltage profile (pu)",
            "Rotor angle swing (°)",
            "Frequency deviation (Hz)",
        ],
        vertical_spacing=0.18, horizontal_spacing=0.12,
    )

    # 1 — Thermal bar
    names  = list(loadings.keys())
    vals   = list(loadings.values())
    colors = [PALETTE["red"] if v > 95 else PALETTE["amber"] if v > 80 else PALETTE["green"]
              for v in vals]
    fig.add_trace(go.Bar(x=names, y=vals, marker_color=colors, showlegend=False), row=1, col=1)

    # 2 — Bus voltages
    bnames = list(bus_v.keys()); bvals = list(bus_v.values())
    bcolors = [PALETTE["red"] if v < 0.90 else PALETTE["amber"] if v < 0.95 else PALETTE["green"]
               for v in bvals]
    fig.add_trace(go.Bar(x=bnames, y=bvals, marker_color=bcolors, showlegend=False), row=1, col=2)

    # 3 — Swing curves (downsample)
    step = max(1, len(t_sw)//400)
    gen_colors = [PALETTE["orange"], PALETTE["blue"], PALETTE["red"]]
    for i, (g, d) in enumerate(zip(GENERATORS, deltas)):
        fig.add_trace(go.Scatter(x=t_sw[::step], y=d[::step], name=g["name"],
                                 line=dict(color=gen_colors[i], width=1.5)), row=2, col=1)

    # 4 — Freq deviation
    fig.add_trace(go.Scatter(x=t_sw[::step],
                             y=freq_dev[::step] * p.frequency,
                             line=dict(color=PALETTE["purple"], width=1.5),
                             showlegend=False), row=2, col=2)

    fig.update_layout(
        paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
        font=dict(color=TEXT_CLR, size=10), height=500,
        margin=dict(l=40, r=20, t=50, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
    )
    for i in range(1, 5):
        r, c = (1, i) if i <= 2 else (2, i-2)
        fig.update_xaxes(gridcolor="#30363d", linecolor="#30363d", row=r, col=c)
        fig.update_yaxes(gridcolor="#30363d", linecolor="#30363d", row=r, col=c)
    st.plotly_chart(fig, use_container_width=True)

    # ── Recommendations ───────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Engineering recommendations")
    recs = []
    if max_loading > 95:
        recs.append(("⛔", "Thermal", "Re-dispatch generation to relieve overloaded lines. "
                     "Activate FACTS devices if available, or shed non-critical load."))
    elif max_loading > 80:
        recs.append(("⚠️", "Thermal", "Monitor line temperatures in real time. "
                     "Pre-position switching to allow rapid load transfer if lines approach thermal limit."))
    if margin < 200:
        recs.append(("⚠️" if margin > 100 else "⛔", "Voltage",
                     f"Install shunt capacitor banks or STATCOMs to improve reactive power margin "
                     f"(current margin: {margin:.0f} MW). Activate generator AVRs in voltage control mode."))
    if tr_cls != "ok":
        recs.append(("⛔" if tr_cls == "danger" else "⚠️", "Transient",
                     f"Fault clearing time ({p.fault_dur} ms) is {'near' if tr_cls=='warn' else 'above'} "
                     f"CCT ({cct:.0f} ms). Upgrade protection relay speed. Add power system stabilisers (PSS)."))
    if not recs:
        recs.append(("✅", "All studies", "No corrective actions required under current operating conditions."))

    for icon, category, text in recs:
        st.markdown(f"""
        <div style="background:#161b22;border-left:3px solid {'#3fb950' if icon=='✅' else '#d29922' if icon=='⚠️' else '#f85149'};
             border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:8px;font-size:12px">
          <span style="font-weight:600;color:#c9d1d9">{icon} {category}:</span>
          <span style="color:#8b949e"> {text}</span>
        </div>""", unsafe_allow_html=True)

    # ── Data export ───────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Export study results")
    ec1, ec2, ec3 = st.columns(3)

    # CSV export
    def make_csv() -> bytes:
        buf = io.StringIO()
        w = csv.writer(buf)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        w.writerow(["GridStability Pro — Study Report", ts])
        w.writerow([])
        w.writerow(["System Parameters"])
        w.writerow(["Generation (MW)", p.gen_mw])
        w.writerow(["Load (MW)", p.load_mw])
        w.writerow(["Base Voltage (kV)", p.base_kv])
        w.writerow(["Frequency (Hz)", p.frequency])
        w.writerow(["Fault Type", p.fault_type])
        w.writerow(["Fault Duration (ms)", p.fault_dur])
        w.writerow([])
        w.writerow(["Thermal Study"])
        w.writerow(["Line", "Loading (%)", "Status"])
        for nm, ld in loadings.items():
            w.writerow([nm, f"{ld:.2f}", line_status(ld)])
        w.writerow([])
        w.writerow(["Voltage Study"])
        w.writerow(["Bus", "Voltage (pu)"])
        for bus, v in bus_v.items():
            w.writerow([bus, f"{v:.4f}"])
        w.writerow(["Load margin (MW)", f"{margin:.1f}"])
        w.writerow([])
        w.writerow(["Transient Study"])
        w.writerow(["CCT (ms)", f"{cct:.1f}"])
        w.writerow(["Fault Duration (ms)", p.fault_dur])
        w.writerow(["Generator", "δ max (°)", "Status"])
        for i, g in enumerate(GENERATORS):
            mx = float(np.max(np.abs(deltas[i])))
            w.writerow([g["name"], f"{mx:.2f}", statuses[i]])
        return buf.getvalue().encode()

    with ec1:
        st.download_button(
            "⬇ Download CSV Report",
            data=make_csv(),
            file_name=f"gridstability_report_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Swing data CSV
    def make_swing_csv() -> bytes:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Time (s)", "Gen 1 δ (°)", "Gen 2 δ (°)", "Gen 3 δ (°)", "Δf (Hz)"])
        step = max(1, len(t_sw) // 500)
        for j in range(0, len(t_sw), step):
            w.writerow([f"{t_sw[j]:.4f}",
                        f"{deltas[0][j]:.4f}",
                        f"{deltas[1][j]:.4f}",
                        f"{deltas[2][j]:.4f}",
                        f"{freq_dev[j] * p.frequency:.6f}"])
        return buf.getvalue().encode()

    with ec2:
        st.download_button(
            "⬇ Download Swing Data",
            data=make_swing_csv(),
            file_name=f"swing_curves_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # System parameters JSON
    with ec3:
        import json
        params_json = json.dumps({
            "study_date": str(datetime.date.today()),
            "system": {k: v for k, v in p.__dict__.items()},
            "results": {
                "thermal": {"max_loading_pct": round(max_loading, 2)},
                "voltage": {"load_margin_mw": round(margin, 1), "v_min_pu": round(v_min, 4)},
                "transient": {"cct_ms": round(cct, 1), "unstable_generators": n_unstable},
                "overall_status": overall_cls,
            }
        }, indent=2)
        st.download_button(
            "⬇ Download JSON Summary",
            data=params_json.encode(),
            file_name=f"gridstability_summary_{datetime.date.today()}.json",
            mime="application/json",
            use_container_width=True,
        )
