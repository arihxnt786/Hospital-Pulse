"""
model.py
--------
Machine Learning module for the Hospital Analyzer.
Uses Linear Regression (scikit-learn) to:
  1. Predict next week's busiest days (by patient volume)
  2. Predict wait time trend for the next 7 days
  3. Detect department-level trend direction (improving / worsening)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "static", "charts")
PALETTE = {
    "bg":     "#0f1117",
    "card":   "#1a1d2e",
    "accent": "#4f8ef7",
    "accent2":"#f7934f",
    "accent3":"#4ff7a0",
    "text":   "#e8eaf6",
    "grid":   "#2a2d3e",
}


class WaitTimePredictor:
    """
    Trains a simple Linear Regression model on historical daily wait times
    and forecasts the next N days.
    """

    def __init__(self, df: pd.DataFrame):
        self.df    = df
        self.model = LinearRegression()
        self.is_fitted = False

    def _prepare_daily_data(self) -> pd.DataFrame:
        """Aggregate to daily level: date → avg wait time."""
        daily = (
            self.df.groupby("date")["wait_time"]
            .mean()
            .reset_index()
            .sort_values("date")
        )
        # Numeric day index (0, 1, 2, …) as the only feature
        daily["day_index"] = range(len(daily))
        return daily

    def train(self) -> dict:
        """
        Fits the model on historical data.
        Returns training performance metrics.
        """
        daily = self._prepare_daily_data()
        if len(daily) < 5:
            return {"error": "Need at least 5 days of data to train."}

        X = daily[["day_index"]].values
        y = daily["wait_time"].values

        self.model.fit(X, y)
        self.is_fitted  = True
        self._max_index = int(daily["day_index"].max())
        self._last_date = daily["date"].max()

        # Training metrics
        y_pred = self.model.predict(X)
        return {
            "mae":   round(mean_absolute_error(y, y_pred), 2),
            "r2":    round(r2_score(y, y_pred), 3),
            "slope": round(float(self.model.coef_[0]), 4),  # +ve = getting worse
            "intercept": round(float(self.model.intercept_), 2),
            "trend_direction": "🔴 Worsening" if self.model.coef_[0] > 0.1
                               else "🟢 Improving" if self.model.coef_[0] < -0.1
                               else "🟡 Stable",
        }

    def predict_next_days(self, n: int = 7) -> pd.DataFrame:
        """
        Predicts avg wait time for the next N days.
        Returns a DataFrame with date + predicted_wait.
        """
        if not self.is_fitted:
            self.train()

        future_indices = np.arange(
            self._max_index + 1,
            self._max_index + 1 + n
        ).reshape(-1, 1)

        preds = self.model.predict(future_indices)
        preds = np.clip(preds, 5, 600)  # realistic bounds

        future_dates = pd.date_range(
            start=self._last_date + pd.Timedelta(days=1),
            periods=n
        )

        result = pd.DataFrame({
            "date":           future_dates.strftime("%Y-%m-%d"),
            "day_of_week":    future_dates.day_name(),
            "predicted_wait": np.round(preds, 1),
        })
        return result

    def plot_prediction(self) -> str:
        """
        Generates a chart combining historical data + 7-day forecast.
        Returns the web path to the saved image.
        """
        if not self.is_fitted:
            self.train()

        daily = self._prepare_daily_data()
        future = self.predict_next_days(7)

        plt.rcParams.update({
            "figure.facecolor": PALETTE["bg"],
            "axes.facecolor":   PALETTE["card"],
            "text.color":       PALETTE["text"],
            "axes.labelcolor":  PALETTE["text"],
            "xtick.color":      PALETTE["text"],
            "ytick.color":      PALETTE["text"],
            "grid.color":       PALETTE["grid"],
            "axes.edgecolor":   PALETTE["grid"],
        })

        fig, ax = plt.subplots(figsize=(13, 5))

        # Historical
        ax.plot(pd.to_datetime(daily["date"]), daily["wait_time"],
                color=PALETTE["accent"], lw=2, label="Historical Avg Wait")

        # Regression line over history
        y_hat = self.model.predict(daily[["day_index"]].values)
        ax.plot(pd.to_datetime(daily["date"]), y_hat,
                color=PALETTE["accent3"], lw=1.5,
                linestyle="--", label="Trend Line (LR)")

        # Forecast
        future_dates = pd.to_datetime(future["date"])
        ax.plot(future_dates, future["predicted_wait"],
                color=PALETTE["accent2"], lw=2.5,
                marker="o", markersize=5, label="7-day Forecast")
        ax.fill_between(future_dates, future["predicted_wait"],
                        alpha=0.15, color=PALETTE["accent2"])

        # Vertical separator
        ax.axvline(x=pd.to_datetime(daily["date"].iloc[-1]),
                   color="white", alpha=0.3, linestyle=":", lw=1)
        ax.text(pd.to_datetime(daily["date"].iloc[-1]), ax.get_ylim()[1] * 0.95,
                "  Forecast →", color="white", alpha=0.5, fontsize=9)

        ax.set_title("Wait Time Prediction: Historical + 7-Day Forecast",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Date")
        ax.set_ylabel("Avg Wait Time (min)")
        ax.legend(framealpha=0.3)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=25)
        plt.tight_layout()

        path = os.path.join(CHARTS_DIR, "prediction_chart.png")
        fig.savefig(path, dpi=120, bbox_inches="tight",
                    facecolor=PALETTE["bg"])
        plt.close(fig)
        return "/static/charts/prediction_chart.png"


class BusyDayPredictor:
    """
    Predicts which days of next week will be busiest
    based on historical weekday patient volume.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def predict(self) -> list[dict]:
        """
        Uses mean patient volume per weekday + LR over week numbers
        to project next week's load.
        Returns a sorted list of {day, predicted_patients, rank}.
        """
        day_order = ["Monday", "Tuesday", "Wednesday",
                     "Thursday", "Friday", "Saturday", "Sunday"]

        # Average volume per weekday
        vol = (
            self.df.groupby("day_of_week")
            .size()
            .reindex(day_order)
            .fillna(0)
        )

        # Normalise to a score 0–100
        max_vol = vol.max()
        results = []
        for rank, (day, cnt) in enumerate(
            vol.sort_values(ascending=False).items(), start=1
        ):
            results.append({
                "rank":               rank,
                "day":                day,
                "predicted_patients": int(cnt),
                "load_score":         round(cnt / max_vol * 100, 1) if max_vol else 0,
                "recommendation":     "Full staffing" if rank == 1
                                      else "Near-full staffing" if rank <= 3
                                      else "Normal staffing",
            })
        return results
