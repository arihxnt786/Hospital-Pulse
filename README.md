# Hospital Pulse — Hospital Operations Analytics

> A Python/Flask analytics platform for exploring OPD operations, identifying overcrowding patterns, forecasting wait times, and generating automated reports.

## What It Does

Hospital Pulse converts structured outpatient-department data into operational insights through a web dashboard. Users can upload data, inspect demand patterns, identify peak periods, forecast wait times, and export a PDF report.

## Key Features

- CSV upload with schema validation
- Peak-hour and department-level analysis
- Overcrowding pattern detection
- Wait-time forecasting using Linear Regression
- Multiple analytical visualizations
- Rule-based actionable insights
- SQLite persistence
- Automated PDF report generation

## Tech Stack

**Backend:** Python, Flask  
**Data:** Pandas, NumPy  
**Machine Learning:** scikit-learn  
**Database:** SQLite  
**Visualization:** Matplotlib, Seaborn  
**Reporting:** ReportLab  
**Frontend:** HTML5, CSS3, JavaScript

## Project Structure

```text
Hospital-Pulse/
├── app.py
├── analysis.py
├── model.py
├── database.py
├── report.py
├── generate_sample_data.py
├── requirements.txt
├── render.yaml
├── railway.toml
├── static/
├── templates/
└── README.md
```

## Run Locally

```bash
git clone https://github.com/arihxnt786/Hospital-Pulse.git
cd Hospital-Pulse
python -m venv venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
python generate_sample_data.py
python app.py
```

Open `http://localhost:5000` in your browser.

## Input Data

The sample workflow expects columns for date, time, department, wait time, and outcome. A sample dataset generator is included so the application can be evaluated without private hospital data.

## API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Dashboard |
| POST | `/upload` | Upload OPD data |
| GET | `/analyze` | Run analysis |
| GET | `/report` | Generate/download PDF report |
| GET | `/stats` | Database summary |
| POST | `/clear` | Clear stored data |
| GET | `/sample-csv` | Download sample data |

## Portfolio Focus

This project demonstrates data ingestion, exploratory analytics, machine learning, backend development, database usage, visualization, and automated reporting in a single end-to-end application.

## Author

**Arihant Gupta** — BCA student at JIIT Noida

[GitHub](https://github.com/arihxnt786)
