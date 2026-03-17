# ⚡ GridStability Pro

**A deployable power system stability analysis platform built with Streamlit.**

Performs three core stability studies:
- **Thermal Stability** — line loading, conductor temperature, N-1 contingency
- **Voltage Stability** — P-V nose curve, bus voltage profile, Q reserve, V-Q sensitivity
- **Transient Stability** — swing equations, rotor angle, frequency deviation, equal area criterion

---

## 📁 Project structure

```
gridstability/
├── app.py                  ← Main Streamlit entry point
├── requirements.txt
├── .streamlit/
│   └── config.toml         ← Dark theme + server config
├── pages/
│   ├── thermal.py          ← Thermal stability study
│   ├── voltage.py          ← Voltage stability study
│   ├── transient.py        ← Transient stability study
│   ├── topology.py         ← Grid single-line diagram
│   └── report.py           ← Summary report + CSV/JSON export
└── utils/
    ├── physics.py           ← Core power system models
    └── charts.py            ← Plotly dark-theme helpers
```

---

## 🚀 Local deployment

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## ☁️ Cloud deployment

### Streamlit Community Cloud (free)
1. Push this folder to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in.
3. Click **New app** → select your repo → set **Main file path** to `app.py`.
4. Click **Deploy**. Your app gets a public URL instantly.

### Render.com
Create a `render.yaml` in the project root:
```yaml
services:
  - type: web
    name: gridstability-pro
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```
Then connect your GitHub repo at [render.com](https://render.com).

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```
```bash
docker build -t gridstability .
docker run -p 8501:8501 gridstability
```

### Railway / Heroku
Set start command to:
```
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## 🔧 Usage

1. **Configure system** in the left sidebar:
   - Set generation and load (MW)
   - Choose base voltage and frequency
   - Define fault type, duration, and location
   - Select analysis method
2. **Run Analysis** — all studies update simultaneously.
3. **Explore tabs**: Thermal / Voltage / Transient / Topology / Report
4. **Export** results as CSV or JSON from the Report tab.

---

## 📐 Physics models

| Study | Method | Key equation |
|-------|--------|-------------|
| Thermal | First-order thermal model | T(t) = T_amb + ΔT(1 − e^{−t/τ}) |
| Voltage | Continuation power flow / P-V curve | V = f(λ) via Newton-Raphson |
| Transient | Numerical integration of swing equation | 2H/ωs · δ̈ = Pm − Pe − D·δ̇ |

---

## 🔮 Extending the platform

- **Add real network data**: Replace `BUS_DATA` and `BRANCH_DATA` in `utils/physics.py` with your system data.
- **Newton-Raphson power flow**: Plug in `pandapower` or `PyPSA` for full AC power flow.
- **PSCAD / PSS/E integration**: Replace physics models with co-simulation API calls.
- **Real-time data**: Connect sidebar sliders to a SCADA API or OSIsoft PI.

---

## 📜 Standards reference

- **IEEE Std 738** — Conductor thermal rating calculations
- **IEEE Std 1110** — Generator stability models
- **NERC FAC-001/002** — Stability study requirements
- **WECC Voltage Stability Criteria** — Voltage stability planning standards
