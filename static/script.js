let charts = {};

function makeChart(id, type, data, options = {}) {
  if (charts[id]) charts[id].destroy();
  const ctx = document.getElementById(id);
  charts[id] = new Chart(ctx, {
    type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: type === "scatter", labels: { boxWidth: 9, font: { size: 10 } } } },
      scales: type === "scatter" ? {
        x: { title: { display: true, text: options.xTitle || "Age (years)" }, ticks: { font: { size: 9 } } },
        y: { title: { display: true, text: options.yTitle || "" }, ticks: { font: { size: 9 } } }
      } : {
        x: { ticks: { font: { size: 9 } }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { font: { size: 9 } } }
      }
    }
  });
}

function showAlerts(elementId, rows, field) {
  const el = document.getElementById(elementId);
  el.innerHTML = rows.length
    ? rows.map(p => `<span>Patient ${p.Patient_ID}: ${p[field]}</span>`).join("")
    : "<span>No matching patients in this view.</span>";
}

async function loadDashboard() {
  const params = new URLSearchParams({
    gender: document.getElementById("genderFilter").value,
    search: document.getElementById("patientSearch").value.trim()
  });
  const [dashboardResponse, chartResponse] = await Promise.all([
    fetch(`/api/dashboard?${params}`),
    fetch(`/api/charts?${params}`)
  ]);
  const d = await dashboardResponse.json();
  const c = await chartResponse.json();

  document.getElementById("total").textContent = d.stats.total;
  document.getElementById("avgAge").textContent = d.stats.avg_age ?? "—";
  document.getElementById("avgBp").textContent = d.stats.avg_bp ?? "—";
  document.getElementById("avgChol").textContent = d.stats.avg_cholesterol ?? "—";
  document.getElementById("recordCount").textContent = `${d.patients.length} records`;

  const tbody = document.getElementById("patientRows");
  tbody.innerHTML = d.patients.length ? d.patients.map(p => `
    <tr><td>#${p.Patient_ID}</td><td>${p.Age}</td><td>${p.Gender}</td>
    <td>${Number(p.Blood_Pressure).toFixed(2)}</td>
    <td>${Number(p.Cholesterol).toFixed(2)}</td><td>${p.Heart_Rate}</td></tr>
  `).join("") : '<tr><td colspan="6">No patient records match these filters.</td></tr>';

  document.getElementById("highBpCount").textContent = d.high_bp.length;
  document.getElementById("highCholCount").textContent = d.high_cholesterol.length;
  showAlerts("highBpList", d.high_bp, "Blood_Pressure");
  showAlerts("highCholList", d.high_cholesterol, "Cholesterol");

  makeChart("ageChart", "bar", {
    labels: c.age.labels,
    datasets: [{ label: "Patients", data: c.age.values, backgroundColor: "#7da8f5", borderRadius: 5 }]
  });
  makeChart("genderChart", "bar", {
    labels: c.gender_bp.labels,
    datasets: [{ label: "Average BP", data: c.gender_bp.values, backgroundColor: ["#80aaf3", "#a998ed"], borderRadius: 5 }]
  });
  makeChart("bpChart", "scatter", {
    datasets: [{ label: "Patients", data: c.age_bp.x.map((x, i) => ({ x, y: c.age_bp.y[i] })), backgroundColor: "#4384e8" }]
  }, { yTitle: "Blood pressure (mmHg)" });
  makeChart("cholChart", "scatter", {
    datasets: [{ label: "Patients", data: c.age_chol.x.map((x, i) => ({ x, y: c.age_chol.y[i] })), backgroundColor: "#36a987" }]
  }, { yTitle: "Cholesterol (mg/dL)" });

  // Refresh Matplotlib download links so they respect the current filters.
  document.querySelectorAll(".download-link").forEach(link => {
    link.href = link.href.split("?")[0] + "?" + params.toString();
  });
}

document.getElementById("genderFilter").addEventListener("change", loadDashboard);
document.getElementById("patientSearch").addEventListener("input", loadDashboard);
document.getElementById("resetBtn").addEventListener("click", () => {
  document.getElementById("genderFilter").value = "All";
  document.getElementById("patientSearch").value = "";
  loadDashboard();
});
loadDashboard().catch(error => {
  console.error(error);
  document.getElementById("patientRows").innerHTML =
    '<tr><td colspan="6">Could not load data. Check that the Flask server is running.</td></tr>';
});
