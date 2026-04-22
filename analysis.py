"""
analysis.py
-----------
Core data analysis engine for the Hospital Analyzer.
Handles data cleaning, peak hour detection, anomaly detection,
doctor absence simulation, and insight generation.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

# Where all generated charts are saved
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "static", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── Colour palette ──────────────────────────────────────────────────
PALETTE = {
    "bg":      "#0f1117",
    "card":    "#1a1d2e",
    "accent":  "#4f8ef7",
    "accent2": "#f7934f",
    "accent3": "#4ff7a0",
    "text":    "#e8eaf6",
    "grid":    "#2a2d3e",
}


# ════════════════════════════════════════════════════════════════════
#  DATA CLEANING
# ════════════════════════════════════════════════════════════════════

class DataCleaner:
    """Validates and cleans the uploaded CSV."""

    REQUIRED_COLUMNS = {"date", "time", "department", "wait_time", "outcome"}
    VALID_OUTCOMES    = {"admitted", "discharged", "referred", "left_ama"}

    def validate(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Check that required columns exist."""
        missing = self.REQUIRED_COLUMNS - set(df.columns.str.lower())
        if missing:
            return False, f"Missing columns: {', '.join(missing)}"
        return True, "OK"

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardise column names, fix types, drop bad rows,
        and engineer helper columns (hour, day_of_week, time_slot).
        """
        # Lower-case column names
        df.columns = df.columns.str.strip().str.lower()

        # Parse date + time
        df["date"]      = pd.to_datetime(df["date"], errors="coerce")
        df["wait_time"] = pd.to_numeric(df["wait_time"], errors="coerce")

        # Drop rows where critical fields are null
        df.dropna(subset=["date", "wait_time", "department"], inplace=True)

        # Trim string columns
        df["department"] = df["department"].str.strip().str.title()
        df["outcome"]    = df["outcome"].str.strip().str.lower()

        # Fill unknown outcomes
        df["outcome"] = df["outcome"].where(
            df["outcome"].isin(self.VALID_OUTCOMES), other="discharged"
        )

        # Clip unreasonable wait times (0–600 min)
        df["wait_time"] = df["wait_time"].clip(0, 600)

        # Engineer helper columns
        df["hour"]        = pd.to_datetime(df["time"], format="%H:%M",
                                           errors="coerce").dt.hour
        df["hour"]        = df["hour"].fillna(df["date"].dt.hour)
        df["day_of_week"] = df["date"].dt.day_name()
        df["week"]        = df["date"].dt.isocalendar().week.astype(int)
        df["time_slot"]   = df["hour"].apply(self._hour_to_slot)

        return df.reset_index(drop=True)

    @staticmethod
    def _hour_to_slot(hour):
        if pd.isna(hour):
            return "Unknown"
        hour = int(hour)
        if hour < 9:
            return "Early Morning (0-9)"
        elif hour < 13:
            return "Morning (9-13)"
        elif hour < 17:
            return "Afternoon (13-17)"
        elif hour < 21:
            return "Evening (17-21)"
        else:
            return "Night (21-24)"


# ════════════════════════════════════════════════════════════════════
#  ANALYSIS ENGINE
# ════════════════════════════════════════════════════════════════════

class AnalysisEngine:
    """Runs all statistical analyses on the cleaned DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    # ── 1. Peak Hours ────────────────────────────────────────────────
    def peak_hours_by_department(self) -> pd.DataFrame:
        """
        Returns the peak hour (highest average wait time)
        for each department.
        """
        grouped = (
            self.df.groupby(["department", "hour"])["wait_time"]
            .mean()
            .reset_index()
        )
        # Find the hour with max avg wait per department
        idx = grouped.groupby("department")["wait_time"].idxmax()
        peak = grouped.loc[idx].copy()
        peak.columns = ["department", "peak_hour", "avg_wait_at_peak"]
        peak["avg_wait_at_peak"] = peak["avg_wait_at_peak"].round(1)
        return peak.sort_values("avg_wait_at_peak", ascending=False)

    # ── 2. Avg Wait by Department + Time Slot ───────────────────────
    def avg_wait_by_dept_slot(self) -> pd.DataFrame:
        """Average wait time grouped by department and time_slot."""
        return (
            self.df.groupby(["department", "time_slot"])["wait_time"]
            .mean()
            .round(1)
            .reset_index()
            .rename(columns={"wait_time": "avg_wait"})
        )

    # ── 3. Anomaly Detection ─────────────────────────────────────────
    def detect_anomalies(self, z_threshold: float = 2.5) -> pd.DataFrame:
        """
        Flags rows where wait_time is more than z_threshold standard
        deviations above the department mean (IQR + Z-score combo).
        """
        df = self.df.copy()
        df["z_score"] = df.groupby("department")["wait_time"].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-9)
        )
        anomalies = df[df["z_score"] > z_threshold].copy()
        anomalies = anomalies[
            ["date", "time", "department", "wait_time", "z_score"]
        ].sort_values("wait_time", ascending=False)
        return anomalies.head(50)  # top 50 worst

    # ── 4. Doctor Absence Simulation ────────────────────────────────
    def doctor_absence_impact(self) -> dict:
        """
        Simulates what happens if a department loses a doctor.
        We infer it by looking at days where wait_time suddenly spikes
        (top 10% days per dept = "doctor absent" days).
        Returns cascading delay info per department.
        """
        results = []
        for dept, grp in self.df.groupby("department"):
            daily_avg   = grp.groupby("date")["wait_time"].mean()
            threshold   = daily_avg.quantile(0.90)  # top 10% = stressed days
            normal_avg  = daily_avg[daily_avg < threshold].mean()
            stressed_avg = daily_avg[daily_avg >= threshold].mean()
            impact       = stressed_avg - normal_avg if not np.isnan(stressed_avg) else 0
            results.append({
                "department":        dept,
                "normal_avg_wait":   round(normal_avg, 1),
                "stressed_avg_wait": round(stressed_avg, 1),
                "cascading_delay":   round(impact, 1),
                "stressed_days":     int((daily_avg >= threshold).sum()),
            })

        results_df = pd.DataFrame(results).sort_values(
            "cascading_delay", ascending=False
        )
        # Department causing most cascading delay
        worst = results_df.iloc[0]
        return {
            "table":        results_df.to_dict("records"),
            "worst_dept":   worst["department"],
            "worst_impact": worst["cascading_delay"],
        }

    # ── 5. Weekly Busy Days ──────────────────────────────────────────
    def weekday_volume(self) -> pd.DataFrame:
        """Average patient volume (rows) per weekday."""
        order = ["Monday", "Tuesday", "Wednesday",
                 "Thursday", "Friday", "Saturday", "Sunday"]
        vol = (
            self.df.groupby("day_of_week")
            .size()
            .reindex(order)
            .fillna(0)
            .reset_index()
        )
        vol.columns = ["day_of_week", "patient_count"]
        return vol

    # ── 6. Daily Trend ───────────────────────────────────────────────
    def daily_trend(self) -> pd.DataFrame:
        """Average wait time per day for trend line."""
        return (
            self.df.groupby("date")["wait_time"]
            .mean()
            .round(1)
            .reset_index()
            .rename(columns={"wait_time": "avg_wait"})
        )

    # ── 7. Actionable Insights ───────────────────────────────────────
    def generate_insights(self) -> list[dict]:
        """
        Rule-based insight generator.
        Returns a list of insight dicts with title, detail, severity.
        """
        insights = []
        peak     = self.peak_hours_by_department()
        anomalies = self.detect_anomalies()
        absence  = self.doctor_absence_impact()

        # Insight 1 – highest wait department
        top_dept = (
            self.df.groupby("department")["wait_time"]
            .mean()
            .idxmax()
        )
        top_wait = self.df.groupby("department")["wait_time"].mean().max()
        insights.append({
            "title":    f"🚨 {top_dept} has the highest average wait",
            "detail":   f"Average wait time is {top_wait:.0f} min. "
                        f"Recommend adding 1–2 extra staff during peak hours.",
            "severity": "high",
            "icon":     "⚠️",
        })

        # Insight 2 – worst cascading delay
        insights.append({
            "title":    f"🏥 {absence['worst_dept']} causes max cascading delay",
            "detail":   f"On stressed days, wait time jumps by "
                        f"~{absence['worst_impact']:.0f} min extra. "
                        f"Doctor cover plan needed.",
            "severity": "high",
            "icon":     "🔴",
        })

        # Insight 3 – anomalies count
        insights.append({
            "title":    f"📊 {len(anomalies)} extreme delay events detected",
            "detail":   "Extreme delays (>2.5σ above dept mean) suggest occasional "
                        "system failures or data entry errors. Audit required.",
            "severity": "medium",
            "icon":     "🟡",
        })

        # Insight 4 – peak hour
        for _, row in peak.head(3).iterrows():
            insights.append({
                "title":    f"🕐 {row['department']}: peak at {int(row['peak_hour'])}:00",
                "detail":   f"Avg wait reaches {row['avg_wait_at_peak']} min. "
                            f"Schedule extra consultants between "
                            f"{int(row['peak_hour'])-1}:00–{int(row['peak_hour'])+2}:00.",
                "severity": "low",
                "icon":     "🟢",
            })

        # Insight 5 – staffing recommendation
        busiest_day = self.weekday_volume().sort_values(
            "patient_count", ascending=False
        ).iloc[0]
        insights.append({
            "title":    f"📅 {busiest_day['day_of_week']} is the busiest day",
            "detail":   f"~{int(busiest_day['patient_count'])} patients on average. "
                        f"Consider full staffing + floating doctors on this day.",
            "severity": "medium",
            "icon":     "🟡",
        })

        return insights


# ════════════════════════════════════════════════════════════════════
#  CHART GENERATOR
# ════════════════════════════════════════════════════════════════════

class ChartGenerator:
    """Creates all charts and saves them to static/charts/."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._set_style()

    def _set_style(self):
        """Dark theme global style."""
        plt.rcParams.update({
            "figure.facecolor":  PALETTE["bg"],
            "axes.facecolor":    PALETTE["card"],
            "axes.edgecolor":    PALETTE["grid"],
            "axes.labelcolor":   PALETTE["text"],
            "xtick.color":       PALETTE["text"],
            "ytick.color":       PALETTE["text"],
            "text.color":        PALETTE["text"],
            "grid.color":        PALETTE["grid"],
            "font.family":       "DejaVu Sans",
            "axes.grid":         True,
            "grid.alpha":        0.4,
        })

    def _save(self, fig, name: str) -> str:
        """Saves figure and returns web path."""
        path = os.path.join(CHARTS_DIR, name)
        fig.savefig(path, dpi=120, bbox_inches="tight",
                    facecolor=PALETTE["bg"])
        plt.close(fig)
        return f"/static/charts/{name}"

    # ── Chart 1 – Heatmap ────────────────────────────────────────────
    def heatmap_volume(self) -> str:
        """Heatmap: patient count per hour × department."""
        pivot = (
            self.df.groupby(["department", "hour"])
            .size()
            .unstack(fill_value=0)
        )
        fig, ax = plt.subplots(figsize=(14, max(5, len(pivot) * 0.7)))
        sns.heatmap(
            pivot,
            ax=ax,
            cmap="YlOrRd",
            linewidths=0.5,
            linecolor=PALETTE["bg"],
            annot=True,
            fmt="d",
            cbar_kws={"label": "Patient Count"},
        )
        ax.set_title("Patient Volume: Hour × Department",
                     fontsize=15, fontweight="bold", pad=15)
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Department")
        return self._save(fig, "heatmap_volume.png")

    # ── Chart 2 – Stacked Bar (wait time breakdown) ──────────────────
    def stacked_bar_waittime(self) -> str:
        """Stacked bar: average wait time by department × time slot."""
        slot_order = [
            "Early Morning (0-9)", "Morning (9-13)",
            "Afternoon (13-17)", "Evening (17-21)", "Night (21-24)"
        ]
        pivot = (
            self.df.groupby(["department", "time_slot"])["wait_time"]
            .mean()
            .unstack(fill_value=0)
        )
        # Reorder columns that actually exist
        cols = [c for c in slot_order if c in pivot.columns]
        pivot = pivot[cols]

        colors = ["#4f8ef7", "#f7934f", "#4ff7a0", "#f74f8e", "#c7f74f"]
        fig, ax = plt.subplots(figsize=(12, 6))
        pivot.plot(kind="bar", stacked=True, ax=ax,
                   color=colors[:len(cols)], edgecolor=PALETTE["bg"], width=0.7)
        ax.set_title("Wait Time Breakdown by Department & Time Slot",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Department")
        ax.set_ylabel("Avg Wait Time (min)")
        ax.legend(title="Time Slot", bbox_to_anchor=(1.01, 1),
                  loc="upper left", framealpha=0.3)
        plt.xticks(rotation=30, ha="right")
        return self._save(fig, "stacked_bar_wait.png")

    # ── Chart 3 – Ridge / Joy Plot ────────────────────────────────────
    def ridge_plot_weekday(self) -> str:
        """
        Ridge (joy) plot: distribution of wait times per weekday.
        Simulated by plotting overlapping KDE curves.
        """
        day_order = ["Monday", "Tuesday", "Wednesday",
                     "Thursday", "Friday", "Saturday", "Sunday"]
        days_present = [d for d in day_order if d in self.df["day_of_week"].unique()]

        fig, axes = plt.subplots(
            len(days_present), 1,
            figsize=(12, len(days_present) * 1.6),
            sharex=True,
        )
        if len(days_present) == 1:
            axes = [axes]

        cmap = plt.cm.cool
        for i, (ax, day) in enumerate(zip(axes, days_present)):
            data = self.df[self.df["day_of_week"] == day]["wait_time"].dropna()
            color = cmap(i / max(len(days_present) - 1, 1))
            if len(data) > 1:
                data.plot.kde(ax=ax, color=color, lw=2)
                ax.fill_between(
                    ax.lines[0].get_xdata(),
                    ax.lines[0].get_ydata(),
                    alpha=0.25, color=color,
                )
            ax.set_ylabel(day, rotation=0, labelpad=80,
                          va="center", fontsize=9, color=PALETTE["text"])
            ax.set_yticks([])
            ax.set_facecolor(PALETTE["card"])
            for spine in ax.spines.values():
                spine.set_edgecolor(PALETTE["grid"])

        axes[-1].set_xlabel("Wait Time (min)")
        fig.suptitle("Wait Time Distribution by Weekday (Ridge Plot)",
                     fontsize=14, fontweight="bold", y=1.01)
        plt.tight_layout()
        return self._save(fig, "ridge_weekday.png")

    # ── Chart 4 – Daily Trend Line ────────────────────────────────────
    def line_daily_trend(self) -> str:
        """Line chart: daily average wait time over the dataset period."""
        daily = (
            self.df.groupby("date")["wait_time"]
            .mean()
            .reset_index()
        )
        fig, ax = plt.subplots(figsize=(13, 5))
        ax.plot(daily["date"], daily["wait_time"],
                color=PALETTE["accent"], lw=2.5, alpha=0.9, label="Avg Wait")
        ax.fill_between(daily["date"], daily["wait_time"],
                        alpha=0.15, color=PALETTE["accent"])

        # 7-day rolling average
        if len(daily) >= 7:
            daily["rolling"] = daily["wait_time"].rolling(7).mean()
            ax.plot(daily["date"], daily["rolling"],
                    color=PALETTE["accent2"], lw=2,
                    linestyle="--", label="7-day Rolling Avg")

        ax.set_title("Daily Average Wait Time Trend",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Date")
        ax.set_ylabel("Avg Wait Time (min)")
        ax.legend(framealpha=0.3)
        plt.xticks(rotation=25)
        return self._save(fig, "line_trend.png")

    # ── Chart 5 – Department Avg Bar ─────────────────────────────────
    def bar_dept_avg(self) -> str:
        """Horizontal bar: avg wait per department."""
        dept_avg = (
            self.df.groupby("department")["wait_time"]
            .mean()
            .sort_values(ascending=True)
        )
        fig, ax = plt.subplots(figsize=(10, max(4, len(dept_avg) * 0.55)))
        colors = [PALETTE["accent"] if v < dept_avg.median()
                  else PALETTE["accent2"] for v in dept_avg.values]
        bars = ax.barh(dept_avg.index, dept_avg.values,
                       color=colors, edgecolor=PALETTE["bg"], height=0.6)
        for bar, val in zip(bars, dept_avg.values):
            ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f} min", va="center", fontsize=9,
                    color=PALETTE["text"])
        ax.set_title("Average Wait Time by Department",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Avg Wait Time (min)")
        blue_p  = mpatches.Patch(color=PALETTE["accent"],  label="≤ Median")
        orange_p = mpatches.Patch(color=PALETTE["accent2"], label="> Median")
        ax.legend(handles=[blue_p, orange_p], framealpha=0.3)
        return self._save(fig, "bar_dept_avg.png")

    def generate_all(self) -> dict:
        """Runs all chart generators and returns a dict of web paths."""
        return {
            "heatmap":    self.heatmap_volume(),
            "stacked_bar": self.stacked_bar_waittime(),
            "ridge":      self.ridge_plot_weekday(),
            "trend":      self.line_daily_trend(),
            "dept_bar":   self.bar_dept_avg(),
        }
