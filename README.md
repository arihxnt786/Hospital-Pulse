# 🏥 Hospital Wait Time & Overcrowding Pattern Analyzer

A production-ready Flask web application for analyzing OPD (Out-Patient Department) data, detecting overcrowding patterns, predicting wait times, and generating automated PDF reports.

---

## 🚀 Quick Start (Local)

### 1. Clone / Download the project
```bash
git clone https://github.com/your-username/hospital-analyzer.git
cd hospital-analyzer
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Generate the sample dataset
```bash
python generate_sample_data.py
```
This creates `static/sample_data.csv` with ~9,600 realistic OPD records across 90 days.

### 5. Run the app
```bash
python app.py
```
Open your browser → **http://localhost:5000**

---

## 📁 Project Structure

```
hospital-analyzer/
├── app.py                  # Flask routes & main entry point
├── analysis.py             # Data cleaning + analysis engine + chart generation
├── model.py                # ML prediction (Linear Regression)
├── database.py             # SQLite CRUD operations
├── report.py               # ReportLab PDF generator
├── generate_sample_data.py # Script to create test CSV
├── requirements.txt
├── Procfile                # For Render / Heroku
├── render.yaml             # Render.com one-click config
├── railway.toml            # Railway.app config
├── static/
│   ├── charts/             # Auto-generated PNG charts
│   ├── reports/            # Auto-generated PDF reports
│   └── sample_data.csv     # Sample OPD dataset
├── templates/
│   └── index.html          # Dashboard UI
├── uploads/                # Uploaded CSVs (temp)
└── instance/
    └── hospital.db         # SQLite database
```

---

## 📊 CSV Format

Your upload file must have these **exact columns** (case-insensitive):

| Column       | Type    | Example           |
|-------------|---------|-------------------|
| `date`       | date    | `2024-01-15`      |
| `time`       | time    | `09:30`           |
| `department` | string  | `Cardiology`      |
| `wait_time`  | number  | `45.5`            |
| `outcome`    | string  | `discharged`      |

**Valid outcomes:** `admitted`, `discharged`, `referred`, `left_ama`

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 CSV Upload | Drag & drop with schema validation |
| 🔍 Peak Hour Detection | Identifies busiest hour per department |
| 🏥 Doctor Absence Simulation | Infers and quantifies cascading delays |
| 🤖 ML Predictions | Linear Regression for 7-day wait time forecast |
| 📊 5 Chart Types | Heatmap, stacked bar, ridge plot, trend line, dept bar |
| 💡 Insights Engine | Rule-based actionable recommendations |
| 📄 PDF Report | Full automated report with charts + tables |

---

## 🌐 Deploy on Render (Free)

1. Push your project to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` and configure everything
5. Click **Deploy** — your app goes live in ~3 minutes

> ⚠️ Render free tier spins down after 15 min inactivity. First request after that takes ~30 sec.

---

## 🚂 Deploy on Railway (Free)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway init
railway up
```

Or connect your GitHub repo at [railway.app](https://railway.app).

---

## 🔧 Environment Variables (Production)

| Variable     | Default | Description |
|-------------|---------|-------------|
| `PORT`       | 5000    | Auto-set by Render/Railway |
| `FLASK_ENV`  | `production` | Set to `development` for debug mode |

---

## 🧪 API Endpoints

| Method | Endpoint       | Description |
|--------|---------------|-------------|
| GET    | `/`            | Dashboard UI |
| POST   | `/upload`      | Upload CSV (returns JSON) |
| GET    | `/analyze`     | Run full analysis (returns JSON) |
| GET    | `/report`      | Download PDF report |
| GET    | `/stats`       | DB summary stats |
| POST   | `/clear`       | Clear all data |
| GET    | `/sample-csv`  | Download sample dataset |

---

## 📦 Tech Stack

- **Backend:** Flask 3.x (Python)
- **Database:** SQLite via Python's built-in `sqlite3`
- **Data Processing:** Pandas, NumPy
- **Visualisation:** Matplotlib, Seaborn
- **ML:** scikit-learn (Linear Regression)
- **PDF:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS (no frameworks, beginner-friendly)

---

## 👨‍💻 Author

Built as a student project · BCA · JIIT Delhi
