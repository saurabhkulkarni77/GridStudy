"""pages/topology.py — Grid Topology & Power Flow."""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.physics import (GridParams, BUS_DATA, BRANCH_DATA,
                            compute_thermal, line_status)
from utils.charts  import base_layout, PALETTE, TEXT_CLR, SUBTLE, DARK_BG, GRID_CLR


# Fixed positions for the 6-bus diagram
BUS_POS = {
    1: (0.15, 0.55),
    2: (0.38, 0.80),
    3: (0.62, 0.80),
    4: (0.38, 0.30),
    5: (0.62, 0.30),
    6: (0.85, 0.55),
}
BUS_TYPE_COLOR = {"PV": PALETTE["green"], "SW": PALETTE["teal"], "PQ": PALETTE["red"]}


def render():
    p_raw = st.session_state.get("params", {})
    p = GridParams(**{k: v for k, v in p_raw.items() if k in GridParams.__dataclass_fields__})
    loadings, _, _ = compute_thermal(p)
    line_names = list(loadings.keys())
    line_vals  = list(loadings.values())

    # ── Single-line diagram ───────────────────────────────────────────────────
    st.markdown("#### Network single-line diagram")

    fig = go.Figure()

    # Draw branches
    for i, br in enumerate(BRANCH_DATA):
        x0, y0 = BUS_POS[br["from"]]
        x1, y1 = BUS_POS[br["to"]]
        lname = line_names[i] if i < len(line_names) else f"L{br['from']}-{br['to']}"
        lval  = line_vals[i]  if i < len(line_vals)  else 50.0
        col   = (PALETTE["red"]   if lval > 95 else
                 PALETTE["amber"] if lval > 80 else
                 PALETTE["green"])
        width = 4 if lval > 80 else 2.5

        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines",
            line=dict(color=col, width=width),
            hoverinfo="text",
            hovertext=f"{lname}: {lval:.1f}% loading<br>R={br['R']} X={br['X']}",
            showlegend=False,
        ))
        # Loading label at midpoint
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        fig.add_annotation(
            x=mx, y=my, text=f"{lval:.0f}%",
            font=dict(size=9, color=col), showarrow=False,
            bgcolor=DARK_BG, borderpad=2,
        )

    # Draw buses
    for bus in BUS_DATA:
        bx, by = BUS_POS[bus["id"]]
        col = BUS_TYPE_COLOR.get(bus["type"], PALETTE["blue"])
        pg  = bus.get("Pg", 0)
        pd  = bus.get("Pd", 0)
        fig.add_trace(go.Scatter(
            x=[bx], y=[by],
            mode="markers+text",
            marker=dict(size=28, color=col, opacity=0.85, line=dict(color="white", width=1.5)),
            text=[f"B{bus['id']}"],
            textposition="middle center",
            textfont=dict(size=10, color="white", family="system-ui"),
            hoverinfo="text",
            hovertext=(f"<b>{bus['name']}</b><br>Type: {bus['type']}<br>"
                       f"V = {bus['V']} pu &nbsp; θ = {bus['angle']}°<br>"
                       + (f"Pg = {pg} MW<br>" if pg else "")
                       + (f"Pd = {pd} MW<br>" if pd else "")),
            showlegend=False,
        ))
        # Bus label below node
        fig.add_annotation(
            x=bx, y=by - 0.10, text=bus["name"],
            font=dict(size=9, color=SUBTLE), showarrow=False,
        )

    # Legend annotations
    for btype, col in BUS_TYPE_COLOR.items():
        label = {"PV": "PV (gen)", "SW": "Slack/swing", "PQ": "PQ (load)"}[btype]
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=12, color=col),
            name=label,
        ))
    for lcol, llabel in [(PALETTE["green"], "Normal (<80%)"),
                          (PALETTE["amber"], "Warning (80–95%)"),
                          (PALETTE["red"],   "Overloaded (>95%)")]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            line=dict(color=lcol, width=3), name=llabel,
        ))

# Replace this:
  fig.update_layout(
      **base_layout("", h=420),
      xaxis=dict(visible=False, range=[0, 1]),
      yaxis=dict(visible=False, range=[0.05, 1.0]),
      margin=dict(l=10, r=10, t=10, b=10),
      legend=dict(x=0.01, y=0.01, font=dict(size=10),
                  bgcolor="rgba(22,27,34,0.85)", bordercolor=GRID_CLR),
  )
  
  # With this:
  _layout = base_layout("", h=420)
  _layout["xaxis"].update(dict(visible=False, range=[0, 1]))
  _layout["yaxis"].update(dict(visible=False, range=[0.05, 1.0]))
  _layout.update(
      margin=dict(l=10, r=10, t=10, b=10),
      legend=dict(x=0.01, y=0.01, font=dict(size=10),
                  bgcolor="rgba(22,27,34,0.85)", bordercolor=GRID_CLR),
  )
  fig.update_layout(**_layout)
      st.plotly_chart(fig, use_container_width=True)
##
  
##
    # ── Bus data table + Branch data table ──────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Bus data")
        bus_rows = ""
        for bus in BUS_DATA:
            pg  = bus.get("Pg", "—")
            pd  = bus.get("Pd", "—")
            col = BUS_TYPE_COLOR.get(bus["type"], PALETTE["blue"])
            v_cls = ("danger" if bus["V"] < 0.90 else
                     "warn"   if bus["V"] < 0.95 or bus["V"] > 1.05 else "ok")
            bus_rows += f"""
            <tr>
              <td style="padding:6px 8px;font-size:11px">{bus['id']}</td>
              <td style="padding:6px 8px;font-size:11px">{bus['name']}</td>
              <td style="padding:6px 8px;font-size:11px;color:{col}">{bus['type']}</td>
              <td style="padding:6px 8px;font-size:11px" class="{v_cls}">{bus['V']:.3f}</td>
              <td style="padding:6px 8px;font-size:11px">{bus['angle']:.1f}°</td>
              <td style="padding:6px 8px;font-size:11px">{pg}</td>
              <td style="padding:6px 8px;font-size:11px">{pd}</td>
            </tr>"""
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;font-size:11px">
          <thead><tr style="background:#21262d">
            <th style="padding:6px 8px;color:#8b949e;text-align:left">ID</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Name</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Type</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">V (pu)</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Angle</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Pg (MW)</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Pd (MW)</th>
          </tr></thead>
          <tbody>{bus_rows}</tbody>
        </table>""", unsafe_allow_html=True)

    with c2:
        st.markdown("#### Branch data")
        br_rows = ""
        for i, br in enumerate(BRANCH_DATA):
            lv = line_vals[i] if i < len(line_vals) else 0.0
            lname = line_names[i] if i < len(line_names) else f"L{br['from']}-{br['to']}"
            cls = ("danger" if lv > 95 else "warn" if lv > 80 else "ok")
            col = (PALETTE["red"] if lv > 95 else PALETTE["amber"] if lv > 80 else PALETTE["green"])
            br_rows += f"""
            <tr>
              <td style="padding:6px 8px;font-size:11px">{lname}</td>
              <td style="padding:6px 8px;font-size:11px">{br['from']}→{br['to']}</td>
              <td style="padding:6px 8px;font-size:11px">{br['R']:.3f}</td>
              <td style="padding:6px 8px;font-size:11px">{br['X']:.3f}</td>
              <td style="padding:6px 8px;font-size:11px">{br['rating']}</td>
              <td style="padding:6px 8px;font-size:11px;color:{col}">{lv:.1f}%</td>
            </tr>"""
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;font-size:11px">
          <thead><tr style="background:#21262d">
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Line</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Route</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">R (pu)</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">X (pu)</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Rating (MW)</th>
            <th style="padding:6px 8px;color:#8b949e;text-align:left">Loading</th>
          </tr></thead>
          <tbody>{br_rows}</tbody>
        </table>""", unsafe_allow_html=True)

    # ── N-1 contingency ───────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### N-1 contingency analysis")
    rng = np.random.default_rng(seed=42)
    n1_results = []
    for i, br in enumerate(BRANCH_DATA):
        lname  = line_names[i] if i < len(line_names) else f"L{br['from']}-{br['to']}"
        max_ld = min(108, (line_vals[i] + rng.uniform(5, 25)) * 1.15)
        status = "unstable" if max_ld > 100 else "marginal" if max_ld > 85 else "stable"
        n1_results.append((f"Trip {lname}", f"Max post-contingency: {max_ld:.1f}%", status))

    n1_rows = "".join(
        f"""<tr>
          <td style="padding:6px 10px;font-size:12px">{r[0]}</td>
          <td style="padding:6px 10px;font-size:12px;color:#8b949e">{r[1]}</td>
          <td style="padding:6px 10px;font-size:12px"><span class="badge-{r[2]}">{r[2].capitalize()}</span></td>
        </tr>"""
        for r in n1_results
    )
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#161b22;border-radius:8px">
      <thead><tr style="background:#21262d">
        <th style="padding:6px 10px;font-size:11px;color:#8b949e;text-align:left">Contingency</th>
        <th style="padding:6px 10px;font-size:11px;color:#8b949e;text-align:left">Impact</th>
        <th style="padding:6px 10px;font-size:11px;color:#8b949e;text-align:left">N-1 status</th>
      </tr></thead>
      <tbody>{n1_rows}</tbody>
    </table>""", unsafe_allow_html=True)
