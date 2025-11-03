async function post(endpoint) {
  try {
    const res = await fetch(endpoint, { method: "POST" });
    const json = await res.json();
    alert(json.status);
  } catch (e) {
    alert("Request failed: " + e);
  }
}

const MAX_POINTS = 50;

function createChart(ctx, label, color) {
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label,
        borderColor: color,
        borderWidth: 1.5,
        data: [],
        tension: 0.3,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: false }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function pushData(chart, value) {
  const ts = new Date().toLocaleTimeString();
  chart.data.labels.push(ts);
  chart.data.datasets[0].data.push(value);
  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update();
}

let charts = {};

window.addEventListener("load", () => {
  charts.roll     = createChart(document.getElementById("rollChart"),     "Roll",     "red");
  charts.pitch    = createChart(document.getElementById("pitchChart"),    "Pitch",    "blue");
  charts.height   = createChart(document.getElementById("heightChart"),   "Altitude", "green");
  charts.battery  = createChart(document.getElementById("batteryChart"),  "Battery",  "orange");
  charts.throttle = createChart(document.getElementById("throttleChart"), "Throttle", "purple");
});

const ws = new WebSocket(`ws://${location.host}/ws/telemetry`);

ws.onmessage = (event) => {
  const d = JSON.parse(event.data);
  if (d.error) {
    console.error("Telemetry error:", d.error);
    return;
  }

  // Update telemetry text
  ["roll", "pitch", "yaw", "height", "battery"].forEach(key => {
    const el = document.getElementById(key);
    if (el && d[key] !== undefined) el.textContent = d[key];
  });

  // RC values and throttle chart
  if (Array.isArray(d.rc)) {
    d.rc.forEach((val, idx) => {
      const el = document.getElementById(`rc${idx}`);
      if (el) el.textContent = val;
    });
    pushData(charts.throttle, d.rc[2]);  // Throttle = RC channel 2
  }

  // Graph the rest
  if (charts.roll)     pushData(charts.roll, d.roll);
  if (charts.pitch)    pushData(charts.pitch, d.pitch);
  if (charts.height)   pushData(charts.height, d.height);
  if (charts.battery)  pushData(charts.battery, d.battery);
};

ws.onerror = err => console.error("WebSocket error:", err);
