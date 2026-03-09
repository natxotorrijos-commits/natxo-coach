// CONFIGURACIÓN STRAVA - RELLENA CON TUS DATOS
const CLIENT_ID = 'TU_CLIENT_ID';
const REDIRECT_URI = window.location.href.split('?')[0];

// Estado global
let athleteData = null;
let activities = [];

// Cambiar Secciones
function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    event.target.classList.add('active');
}

// Inicializar Planificador Editable
function initPlanner() {
    const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    const body = document.getElementById('planner-body');
    body.innerHTML = days.map(day => 
        `<tr><td>${day}</td><td>Trote suave</td><td>Zona 2 - 130ppm</td><td>50 min</td></tr>`
    ).join('');
}

// Simular Carga de Gráfico
function initChart() {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Fitness (CTL)',
                data: [80, 81, 81, 82, 82, 83, 84],
                borderColor: '#00f2ff',
                backgroundColor: 'rgba(0, 242, 255, 0.1)',
                fill: true,
                tension: 0.4
            }, {
                label: 'Fatiga (ATL)',
                data: [90, 85, 105, 100, 95, 110, 101],
                borderColor: '#ff4b4b',
                borderDash: [5, 5],
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                }
            },
            scales: {
                y: {
                    grid: { color: '#1e2631' },
                    ticks: { color: '#8e9aaf' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#8e9aaf' }
                }
            }
        }
    });
}

// Lógica de Conexión Strava
document.getElementById('strava-connect').addEventListener('click', () => {
    const authUrl = `https://www.strava.com/oauth/authorize?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=activity:read_all`;
    window.location.href = authUrl;
});

// Manejar el retorno de OAuth
async function handleOAuth() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (code) {
        document.getElementById('strava-connect').innerText = "Cargando...";
        console.log("Código de autorización recibido:", code);
        setTimeout(renderActivities, 1000);
    }
}

function renderActivities() {
    const container = document.getElementById('activities-container');
    const mockActivities = [
        { name: "Rodaje Z2", dist: "12.5km", time: "1h 05m", elevation: "120m" },
        { name: "Series 1000m", dist: "8.0km", time: "45m", elevation: "20m" },
        { name: "Trail Pirineos", dist: "25.0km", time: "3h 15m", elevation: "1200m" }
    ];
    container.innerHTML = mockActivities.map(act => 
        `<div class="activity-card">
            <h4>🏃 ${act.name}</h4>
            <div class="activity-stats">
                <span><strong>Dist:</strong> ${act.dist}</span>
                <span><strong>D+:</strong> ${act.elevation}</span>
                <span><strong>Time:</strong> ${act.time}</span>
            </div>
        </div>`
    ).join('');
}

// Arrancar App
window.onload = () => {
    initPlanner();
    initChart();
    handleOAuth();
};
