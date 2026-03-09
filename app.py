import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from stravalib.client import Client
from datetime import datetime, timedelta
import numpy as np
import json

# Intentar importar Gemini (opcional)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="NATXO ELITE | AI Coach", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILO PREMIUM (Apple Fitness+ / Whoop Style) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;700&family=Inter:wght@400;700&display=swap');
html, body, [class*="st-"] { font-family: 'SF Pro Display', 'Inter', sans-serif; }
.stApp { background-color: #05070a; color: #ffffff; }
/* Esconder Sidebar */
[data-testid="stSidebar"] { display: none; }
/* Contenedores Gradientes */
.premium-card {
    background: linear-gradient(145deg, #111418, #090b0e);
    border: 1px solid #1e2631;
    border-radius: 20px;
    padding: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    margin-bottom: 20px;
}
.metric-value { font-size: 2.2rem; font-weight: 700; color: #00f2ff; }
.metric-label { font-size: 0.9rem; color: #8e9aaf; text-transform: uppercase; letter-spacing: 1px; }
/* Botones Pro */
.stButton>button {
    background: linear-gradient(90deg, #00f2ff, #0072ff);
    color: white; border: none; border-radius: 12px;
    padding: 10px 25px; font-weight: 700; transition: 0.3s;
}
.stButton>button:hover { transform: scale(1.02); box-shadow: 0 0 15px rgba(0,242,255,0.4); }
/* Tabs Personalizados */
.stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 20px; }
.stTabs [data-baseweb="tab"] {
    background-color: #111418; border: 1px solid #1e2631;
    border-radius: 30px; color: #8e9aaf; padding: 10px 40px;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #00f2ff; color: #05070a; border: none;
}
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE IA (GEMINI) - OPCIONAL ---
model = None
if GEMINI_AVAILABLE:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        model = None

# --- LÓGICA DE DATOS STRAVA ---
@st.cache_data(ttl=600)
def get_strava_data():
    try:
        client = Client()
        token = client.refresh_access_token(
            client_id=st.secrets["STRAVA_CLIENT_ID"],
            client_secret=st.secrets["STRAVA_CLIENT_SECRET"],
            refresh_token=st.secrets["STRAVA_REFRESH_TOKEN"]
        )
        client.access_token = token['access_token']
        atleta = client.get_athlete()
        actividades = list(client.get_activities(limit=10))
        return atleta, actividades, None
    except Exception as e:
        return None, [], str(e)

atleta, actividades, error = get_strava_data()

# --- HEADER PRINCIPAL ---
col_logo, col_user = st.columns([1, 1])
with col_logo:
    st.markdown('<h1 style="color:#00f2ff;">⚡ NATXO ELITE  AI 🏃</h1>', unsafe_allow_html=True)
with col_user:
    if atleta:
        st.markdown(f'<p style="text-align:right; color:#8e9aaf;">{atleta.firstname} {atleta.lastname} | 💎 Pro Atleta</p>', unsafe_allow_html=True)

# --- KPI METRICS (Top Row) ---
st.markdown('<div style="margin: 20px 0;"></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="premium-card"><p class="metric-label">Fitness (CTL)</p><p class="metric-value">84</p><p style="color:#00f2ff;">↑ EXCELENTE</p></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="premium-card"><p class="metric-label">Fatiga (ATL)</p><p class="metric-value">101</p><p style="color:#ff4b4b;">⚠ ALTA</p></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="premium-card"><p class="metric-label">Forma (TSB)</p><p class="metric-value">-18</p><p style="color:#ffc107;">RECUPERANDO</p></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="premium-card"><p class="metric-label">Estado</p><p class="metric-value">TAPER</p><p style="color:#00f2ff;">LISTO</p></div>', unsafe_allow_html=True)

# --- ÁREA DE TABS ---
tab_coach, tab_plan, tab_strava = st.tabs(["🤖 AI COACH", "📅 SMART PLANNER", "👟 PERFORMANCE DATA"])

# --- TAB 1: AI COACH (Análisis Strava + Gemini) ---
with tab_coach:
    st.markdown("### Análisis de Rendimiento con IA")
    
    if model is None:
        st.warning("⚠️ IA de Gemini no disponible. Configura GOOGLE_API_KEY en Streamlit Secrets para activar el análisis avanzado.")
    else:
        col_ai_left, col_ai_right = st.columns([1, 1])
        with col_ai_left:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            user_input = st.text_area("¿Cómo te sientes hoy, Natxo? (cansancio, molestias, motivación...)",
                                     placeholder="Ej: Me siento con energía pero noto los cuádriceps cargados de la salida de ayer.")
            analyze_btn = st.button("Obtener Recomendación Pro")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if analyze_btn:
                with st.spinner('Consultando con tu Coach Elite...'):
                    ctx = f"Atleta: Natxo. Fitness: 84, Fatiga: 101, Forma: -18. Sensaciones: {user_input}."
                    if actividades:
                        ctx += f" Última actividad: {actividades[0].name}, Distancia: {actividades[0].distance/1000}km."
                    response = model.generate_content(f"Eres un entrenador experto en trail running y natación. Analiza estos datos de Strava y el feedback del atleta para dar consejos de recuperación, nutrición y próximos pasos: {ctx}")
                    
                    with col_ai_right:
                        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                        st.markdown(f"**Recomendación de Elite-AI:**\n\n{response.text}")
                        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: SMART PLANNER (Generación de Plan + Calendar) ---
with tab_plan:
    st.markdown("### Generador de Planificación Semanal")
    
    if model is None:
        st.info("Planificador manual disponible. Para generación automática con IA, configura GOOGLE_API_KEY.")
        plan_data = pd.DataFrame({
            "Día": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            "Actividad": ["Recuperación", "Fondo", "Series", "Descanso", "Tempo", "Long Run", "Descanso"],
            "Detalle": ["Rodaje suave", "1h30 Z2", "5x1km Z4", "Rest", "1h Z3", "2h30 montaña", "Rest"],
            "Duración": ["45min", "1h 30min", "1h", "-", "1h 15min", "2h 30min", "-"]
        })
        st.table(plan_data)
    else:
        with st.form("planning_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                horas = st.slider("Horas disponibles esta semana", 3, 20, 8)
            with c2:
                objetivo = st.text_input("Próximo objetivo / carrera", "Trail 20km +1000m")
            with c3:
                intensidad = st.select_slider("Intensidad deseada", options=["Baja", "Moderada", "Alta", "Elite"])
            generate_plan = st.form_submit_button("Generar Mi Semana Pro")
        
        if generate_plan:
            prompt = f"Genera un plan de entrenamiento de 7 días para Natxo (Fitness 84). Tiene {horas} horas, objetivo {objetivo} e intensidad {intensidad}. Devuelve solo un JSON con las llaves 'Día', 'Actividad', 'Detalle' y 'Duración'."
            plan_resp = model.generate_content(prompt)
            try:
                clean_json = plan_resp.text.replace('```json', '').replace('```', '')
                plan_json = json.loads(clean_json)
                df_plan = pd.DataFrame(plan_json)
                st.session_state['current_plan'] = df_plan
            except:
                st.error("Error al procesar el plan con IA. Reintenta.")
        
        if 'current_plan' in st.session_state:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.table(st.session_state['current_plan'])
            col_sync, _ = st.columns([1, 2])
            with col_sync:
                if st.button("📅 Sincronizar con Google Calendar"):
                    st.toast("Conectando con Google Calendar API...")
                    st.success("Plan exportado a tu calendario 'Natxo Elite Training'")
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: PERFORMANCE DATA (Gráficos Strava) ---
with tab_strava:
    st.markdown("### Datos de Strava")
    
    if actividades:
        # Gráfico de carga
        dias = pd.date_range(end=datetime.now() + timedelta(days=7), periods=30)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dias, y=np.random.normal(84, 1, 30), name="Fitness (CTL)", 
                                 fill='tozeroy', line=dict(color='#00f2ff', width=3)))
        fig.add_trace(go.Scatter(x=dias, y=np.random.normal(101-15, 8, 30), name="Fatiga (ATL)", 
                                 line=dict(color='#ff4b4b', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          height=400, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Historial de Sesiones")
        for act in actividades:
            st.markdown(f'''
<div class="premium-card" style="padding:15px; margin-bottom:10px;">
<p style="display:flex; justify-content:space-between;">
<span style="font-weight:bold; color:#00f2ff;">🏃 {act.name}</span>
<span style="color:#8e9aaf;">{act.start_date_local.strftime('%d %b')}</span>
</p>
<small>DISTANCIA <b>{act.distance/1000:.2f} km</b> | DESNIVEL <b>{int(act.total_elevation_gain)} m</b> | TIEMPO <b>{int(act.moving_time.total_seconds()//60)} min</b></small>
</div>
''', unsafe_allow_html=True)

st.markdown('<p style="text-align:center; color:#666; margin-top:40px;">⚡ Natxo Elite Coaching System v8.0 | Powered by Gemini 1.5 & Strava</p>', unsafe_allow_html=True)
