from flask import Flask, jsonify, render_template, request, send_file, abort
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO

app = Flask(__name__)

# Synthetic sample patient data for educational use only.
DATA = {
    "Patient_ID": range(1, 16),
    "Age": [22, 35, 45, 52, 28, 60, 41, 33, 55, 48, 25, 67, 39, 58, 31],
    "Gender": [
        "Male", "Female", "Male", "Female", "Male",
        "Female", "Male", "Female", "Male", "Female",
        "Male", "Female", "Male", "Female", "Male"
    ],
    "Blood_Pressure": [
        118, 125, 140, 135, 115, 155, 130, np.nan,
        145, 138, 110, 160, 128, 150, 122
    ],
    "Cholesterol": [
        180, 195, 230, 210, 175, 260, 220, 190,
        np.nan, 225, 170, 270, 205, 245, 185
    ],
    "Heart_Rate": [
        72, 78, 85, 80, 70, 92, 82, 75,
        88, 84, 68, 95, 79, 90, 74
    ]
}

df = pd.DataFrame(DATA)

# Clean missing readings using the mean, matching the original project logic.
df["Blood_Pressure"] = df["Blood_Pressure"].fillna(df["Blood_Pressure"].mean())
df["Cholesterol"] = df["Cholesterol"].fillna(df["Cholesterol"].mean())


def filtered_data():
    result = df.copy()
    gender = request.args.get("gender", "All")
    search = request.args.get("search", "").strip()
    if gender in ("Male", "Female"):
        result = result[result["Gender"] == gender]
    if search:
        result = result[result["Patient_ID"].astype(str).str.contains(search, case=False)]
    return result


def records_to_json(frame):
    return frame.round(2).replace({np.nan: None}).to_dict(orient="records")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    current = filtered_data()
    if current.empty:
        return jsonify({
            "patients": [],
            "stats": {"total": 0, "avg_age": None, "avg_bp": None,
                      "avg_cholesterol": None, "avg_heart_rate": None},
            "high_bp": [], "high_cholesterol": [],
            "correlation": {}
        })

    stats = {
        "total": int(len(current)),
        "avg_age": round(float(np.mean(current["Age"])), 2),
        "avg_bp": round(float(np.mean(current["Blood_Pressure"])), 2),
        "avg_cholesterol": round(float(np.mean(current["Cholesterol"])), 2),
        "avg_heart_rate": round(float(np.mean(current["Heart_Rate"])), 2)
    }
    corr = current[["Age", "Blood_Pressure", "Cholesterol", "Heart_Rate"]].corr().round(2)
    return jsonify({
        "patients": records_to_json(current),
        "stats": stats,
        "high_bp": records_to_json(current[current["Blood_Pressure"] >= 140]),
        "high_cholesterol": records_to_json(current[current["Cholesterol"] >= 240]),
        "correlation": corr.to_dict()
    })


@app.route("/api/charts")
def charts():
    current = filtered_data()
    if current.empty:
        return jsonify({"age": {"labels": [], "values": []},
                        "gender_bp": {"labels": [], "values": []},
                        "age_bp": {"x": [], "y": []},
                        "age_chol": {"x": [], "y": []}})

    counts, edges = np.histogram(current["Age"], bins=5)
    age_labels = [
        f"{int(edges[i])}-{int(edges[i+1])}" for i in range(len(edges)-1)
    ]
    avg_bp = current.groupby("Gender")["Blood_Pressure"].mean()
    return jsonify({
        "age": {"labels": age_labels, "values": counts.tolist()},
        "gender_bp": {"labels": avg_bp.index.tolist(),
                      "values": avg_bp.round(2).tolist()},
        "age_bp": {"x": current["Age"].tolist(),
                   "y": current["Blood_Pressure"].round(2).tolist()},
        "age_chol": {"x": current["Age"].tolist(),
                     "y": current["Cholesterol"].round(2).tolist()}
    })


@app.route("/api/matplotlib/<chart_name>.png")
def matplotlib_chart(chart_name):
    current = filtered_data()
    if current.empty:
        abort(404)

    fig, ax = plt.subplots(figsize=(7, 4))
    if chart_name == "age":
        ax.hist(current["Age"], bins=5, edgecolor="black")
        ax.set(title="Age Distribution of Patients", xlabel="Age (years)",
               ylabel="Number of Patients")
    elif chart_name == "gender-bp":
        avg = current.groupby("Gender")["Blood_Pressure"].mean()
        ax.bar(avg.index, avg.values)
        ax.set(title="Average Blood Pressure by Gender", xlabel="Gender",
               ylabel="Average Blood Pressure (mmHg)")
    elif chart_name == "age-bp":
        ax.scatter(current["Age"], current["Blood_Pressure"])
        ax.set(title="Age vs Blood Pressure", xlabel="Age (years)",
               ylabel="Blood Pressure (mmHg)")
    elif chart_name == "age-cholesterol":
        ax.scatter(current["Age"], current["Cholesterol"])
        ax.set(title="Age vs Cholesterol", xlabel="Age (years)",
               ylabel="Cholesterol (mg/dL)")
    else:
        plt.close(fig)
        abort(404)

    fig.tight_layout()
    output = BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return send_file(output, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)
