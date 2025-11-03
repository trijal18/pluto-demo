const MAX_POINTS = 50;
let charts = {};
let ws = null;

// === Notifications ===
function showNotification(message, type = 'info') {
  const container = document.getElementById('notification-container');
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  container.appendChild(notification);
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 4000);
}

// === Connection Status ===
function updateConnectionStatus(connected) {
  const indicator = document.getElementById('statusIndicator');
  const status = document.getElementById('connectionStatus');
  indicator.className = connected ? 'status-indicator status-connected' : 'status-indicator status-disconnected';
  status.textContent = connected ? 'Connected' : 'Disconnected';
}

// === Command Sender ===
async function sendCommand(command) {
  try {
    showNotification(`Sending command: ${command}`, 'info');
    const res = await fetch(`/${command}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const json = await res.json();
    showNotification(json.status || `Executed: ${command}`, res.ok ? 'success' : 'error');
  } catch (e) {
    console.error(e);
    showNotification("Failed to send command: " + e.message, "error");
  }
}

// === Animate Value ===
function animateValueChange(el) {
  el.classList.add('updating');
  setTimeout(() => el.classList.remove('updating'), 300);
}

// === Chart Helpers ===
function createChart(ctx, label, color, unit = '') {
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        data: [],
        tension: 0.4,
        pointRadius: 0,
        fill: true,
        pointHoverRadius: 5,
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      scales: {
        x: { display: false },
        y: {
          beginAtZero: false,
          ticks: {
            color: '#fff',
            font: { size: 11 },
            callback: val => unit ? `${val}${unit}` : val
          },
          grid: { color: '#4444' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${label}: ${ctx.parsed.y.toFixed(2)}${unit}`
          }
        }
      }
    }
  });
}

function pushData(chart, value) {
  const now = new Date().toLocaleTimeString();
  chart.data.labels.push(now);
  chart.data.datasets[0].data.push(value);
  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}

// === RC Bar Update ===
function updateRCBar(index, value) {
  const bar = document.getElementById(`rcBar${index}`);
  if (bar) {
    const percent = Math.min(100, Math.max(0, ((value - 1000) / 1000) * 100));
    bar.style.width = `${percent}%`;
    bar.style.background = percent < 30
      ? 'linear-gradient(90deg, #f44336, #ff5722)'
      : percent > 70
      ? 'linear-gradient(90deg, #4CAF50, #00d4ff)'
      : 'linear-gradient(90deg, #ff9800, #ffc107)';
  }
}

// === Telemetry Update Handler ===
function updateTelemetry(data) {
  const fields = ['roll', 'pitch', 'yaw', 'height', 'battery'];

  fields.forEach(f => {
    const el = document.getElementById(f);
    if (el && data[f] !== undefined) {
      let val = data[f];
      el.textContent = typeof val === 'number'
        ? (f === 'battery' ? val.toFixed(2) + ' V'
        : f === 'height' ? val.toFixed(0) + ' cm'
        : val.toFixed(1) + '°') : val;
      animateValueChange(el);
      const chartKey = f + 'Chart';
      if (charts[chartKey]) pushData(charts[chartKey], data[f]);
    }
  });

  // RC Channel Values
  if (Array.isArray(data.rc)) {
    data.rc.forEach((val, i) => {
      const rcVal = document.getElementById(`rc${i}`);
      if (rcVal) {
        rcVal.textContent = Math.round(val);
        animateValueChange(rcVal);
      }
      updateRCBar(i, val);
      if (i === 2 && charts.throttleChart) {
        pushData(charts.throttleChart, val);
      }
    });
  }
}

// === WebSocket Connection ===
function connectTelemetryWS() {
  ws = new WebSocket(`ws://${location.host}/ws/telemetry`);

  ws.onopen = () => {
    updateConnectionStatus(true);
    showNotification("WebSocket connected", "success");
  };

  ws.onclose = () => {
    updateConnectionStatus(false);
    showNotification("WebSocket disconnected", "warning");
    setTimeout(connectTelemetryWS, 3000); // retry
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.error) return;
      updateTelemetry(data);
    } catch (e) {
      console.error("Invalid telemetry JSON", e);
    }
  };

  ws.onerror = err => {
    console.error("WebSocket error", err);
    showNotification("WebSocket error", "error");
  };
}

// === On Load Init ===
window.addEventListener("load", () => {
  connectTelemetryWS();

  charts.rollChart     = createChart(document.getElementById("rollChart"),     "Roll",     "#ff6384", "°");
  charts.pitchChart    = createChart(document.getElementById("pitchChart"),    "Pitch",    "#36a2eb", "°");
  charts.yawChart      = createChart(document.getElementById("yawChart"),      "Yaw",      "#9966ff", "°");
  charts.heightChart   = createChart(document.getElementById("heightChart"),   "Altitude", "#4bc0c0", "cm");
  charts.batteryChart  = createChart(document.getElementById("batteryChart"),  "Battery",  "#ffcd56", " V");
  charts.throttleChart = createChart(document.getElementById("throttleChart"), "Throttle", "#ff9f40");
});
