"""
app.py
------
Main Flask application for the Hospital Wait Time Analyzer.
Handles:
  - File upload + validation
  - Running analysis
  - Serving chart data
  - PDF report download
  - REST-like JSON endpoints for the dashboard
"""

import os
import json
import traceback
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_file, flash
)
from werkzeug.utils import secure_filename

# ── Local imports ─────────────────────────────────────────────────────
from database  import Database
from analysis  import DataCleaner, AnalysisEngine, ChartGenerator
from model     import WaitTimePredictor, BusyDayPredictor
from report    import ReportGenerator

# ── App Setup ────────────────────────────────────────────────────────
app     = Flask(__name__)
app.secret_key = "hospital-analyzer-secret-2024"  # change in production

UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXT     = {"csv"}
MAX_FILE_BYTES  = 10 * 1024 * 1024  # 10 MB limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"]  = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES

# Global database instance
db = Database()


# ── Helpers ──────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def run_full_analysis(df):
    """
    Runs the complete analysis + chart + ML pipeline on a DataFrame.
    Returns a big dict with all results.
    """
    engine  = AnalysisEngine(df)
    charts  = ChartGenerator(df)
    chart_paths = charts.generate_all()

    # ML modules
    predictor   = WaitTimePredictor(df)
    metrics     = predictor.train()
    next_7      = predictor.predict_next_days(7)
    pred_chart  = predictor.plot_prediction()
    chart_paths["prediction"] = pred_chart

    busy_predictor = BusyDayPredictor(df)
    busy_days      = busy_predictor.predict()

    # Analysis results
    peak_hours  = engine.peak_hours_by_department()
    dept_slot   = engine.avg_wait_by_dept_slot()
    anomalies   = engine.detect_anomalies()
    absence     = engine.doctor_absence_impact()
    weekday_vol = engine.weekday_volume()
    insights    = engine.generate_insights()

    return {
        "chart_paths":   chart_paths,
        "peak_hours":    peak_hours.to_dict("records"),
        "dept_slot":     dept_slot.to_dict("records"),
        "anomalies":     anomalies.head(10).to_dict("records"),
        "absence":       absence,
        "weekday_vol":   weekday_vol.to_dict("records"),
        "insights":      insights,
        "busy_days":     busy_days,
        "predictions": {
            "next_7_days": next_7.to_dict("records"),
            "metrics":     metrics,
        },
    }


# ════════════════════════════════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Landing / dashboard page."""
    has_data   = db.has_data()
    stats      = db.get_summary_stats() if has_data else {}
    return render_template("index.html", has_data=has_data, stats=stats)


@app.route("/upload", methods=["POST"])
def upload():
    """
    Handles CSV file upload.
    Validates schema, cleans data, stores to SQLite.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only CSV files allowed."}), 400

    try:
        import pandas as pd
        filename   = secure_filename(file.filename)
        filepath   = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Read CSV
        df = pd.read_csv(filepath)

        # Validate schema
        cleaner = DataCleaner()
        valid, msg = cleaner.validate(df)
        if not valid:
            os.remove(filepath)
            return jsonify({"success": False, "error": msg}), 422

        # Clean
        df_clean = cleaner.clean(df)

        # Store to DB
        db.insert_dataframe(df_clean, filename)

        return jsonify({
            "success": True,
            "rows":    len(df_clean),
            "message": f"✅ Uploaded {len(df_clean)} records successfully!",
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/analyze", methods=["GET"])
def analyze():
    """
    Runs the full analysis pipeline on stored data.
    Returns JSON with all charts, insights, predictions.
    """
    if not db.has_data():
        return jsonify({"success": False,
                        "error": "No data found. Please upload a CSV first."}), 404

    try:
        df      = db.get_all_records()
        import pandas as pd
        df["date"] = pd.to_datetime(df["date"])
        results    = run_full_analysis(df)

        # Convert any non-serializable types
        def safe(obj):
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return jsonify({"success": True, **results}), 200,\
               {"Content-Type": "application/json"}

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/report", methods=["GET"])
def generate_report():
    """
    Generates and returns the PDF report.
    Triggers file download in the browser.
    """
    if not db.has_data():
        flash("No data available. Please upload a CSV first.", "error")
        return redirect(url_for("index"))

    try:
        df  = db.get_all_records()
        import pandas as pd
        df["date"] = pd.to_datetime(df["date"])

        engine   = AnalysisEngine(df)
        predictor = WaitTimePredictor(df)
        metrics   = predictor.train()
        next_7    = predictor.predict_next_days(7)

        report_gen = ReportGenerator(
            stats       = db.get_summary_stats(),
            insights    = engine.generate_insights(),
            predictions = {
                "next_7_days": next_7.to_dict("records"),
                "metrics":     metrics,
            },
            absence     = engine.doctor_absence_impact(),
            peak_hours  = engine.peak_hours_by_department(),
        )

        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename    = f"hospital_report_{timestamp}.pdf"
        web_path    = report_gen.generate(filename)
        file_path   = os.path.join(
            os.path.dirname(__file__), "static", "reports", filename
        )

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        traceback.print_exc()
        flash(f"Report generation failed: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/stats", methods=["GET"])
def stats():
    """Quick endpoint to check DB stats."""
    return jsonify(db.get_summary_stats())


@app.route("/clear", methods=["POST"])
def clear_data():
    """Clears all stored data (for testing/demo purposes)."""
    db.clear_records()
    return jsonify({"success": True, "message": "All data cleared."})


@app.route("/sample-csv")
def sample_csv():
    """Serves the sample dataset for download."""
    path = os.path.join(os.path.dirname(__file__), "static", "sample_data.csv")
    if os.path.exists(path):
        return send_file(path, as_attachment=True,
                         download_name="sample_hospital_data.csv")
    return jsonify({"error": "Sample file not found."}), 404


# ── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
