import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from stravalib.client import Client
from datetime import datetime, timedelta
import numpy as np

# --- CONFIGURACIÓN DE ALTO NIVEL ---
st.set_page_config(page_title="NATXO ELITE | Coaching System", page_icon="🏔️", layout="wide")

# CSS Avanzado para Interfaz "Carbon & Neon"
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #05070a; color: #ffffff; }
        .main-header { font-size: 2.5rem; font-weight: 700; color: #00f2ff; margin-bottom: 0.5rem; }
        .metric-container { background: linear-gradient(145deg, #10141b, #0d1016); border: 1px solid #1e2631; border-radius: 15px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
        .stTabs [data-baseweb="tab"] { background-color: #10141b; border: 1px solid #1e2631; border-radius: 8px; color: #8e9aaf; padding: 10px 30px; }
        .stTabs [data-baseweb="tab"]:hover { border-color: #00f2ff; color: #fff; }
        .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #00f2ff; color: #05070a; border-color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE DATOS (STRAVA API) ---
@st.cache_data(ttl=600)
def get_performance_data():
    try:
        client = Client()
        token = client.refresh_access_token(
            client_id=st.secrets["STRAVA_CLIENT_ID"],
            client_secret=st.secrets["STRAVA_CLIENT_SECRET"],
            refresh_token=st.secrets["STRAVA_REFRESH_TOKEN"]
        )
        client.access_token = token['access_token']
        atleta = client.get_athlete()
        actividades = list(client.get_activities(limit=20))
        return atleta, actividades, None
    except Exception as e:
        return None, [], str(e)

atleta, actividades, error = get_performance_data()

# --- SIDEBAR PROFESIONAL ---
with st.sidebar:
    st.markdown("<h2 style='color:#00f2ff;'>SISTEMA ELITE</h2>", unsafe_allow_html=True)
    if atleta:
        st.success(f"Atleta: {atleta.firstname} {atleta.lastname}")
        st.write(f"ID Strava: {atleta.id}")
    else:
        st.error("Esperando conexión Strava...")
    
    st.divider()
    st.markdown("### Configuración de Carrera")
    dist_obj = st.number_input("Distancia Objetivo (km)", value=20.0)
    desn_obj = st.number_input("Desnivel Positivo (+m)", value=1000)
    ritmo_10k = st.text_input("Ritmo 10k Actual (min/km)", "4:25")

# --- DASHBOARD PRINCIPAL ---
st.markdown("<h1 class='main-header'>CENTRO DE RENDIMIENTO</h1>", unsafe_allow_html=True)
st.write(f"Bienvenido, Natxo. Analizando datos del **{datetime.now().strftime('%d de marzo, 2026')}**")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance Analysis", "🏔️ Pyrenees Strategy", "📅 Smart Planner", "👟 Strava Feed"])

# --- TAB 1: MÉTRICAS DE CARGA ---
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        st.metric("Fitness (CTL)", "84", "OPTIMAL")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        st.metric("Fatiga (ATL)", "101", "HIGH", delta_color="inverse")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        st.metric("Forma (TSB)", "-17", "TAPER")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        st.metric("RPE Medio", "7.2", "MODERADO")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Gráfica de Rendimiento Pro
    dias = pd.date_range(end=datetime.now() + timedelta(days=7), periods=30)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dias, y=np.random.normal(84, 1, 30), name="CTL", fill='tozeroy', line=dict(color='#00f2ff', width=2)))
    fig.add_trace(go.Scatter(x=dias, y=np.random.normal(101-15, 8, 30), name="ATL", line=dict(color='#ff4b4b', width=2)))
    fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=400)
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: ESTRATEGIA DE CARRERA (PIRINEOS) ---
with tab2:
    st.subheader(f"Simulación Técnica: {dist_obj}km +{desn_obj}m")
    
    st.info("🏔️ Análisis de estrategia para ultra trail de montaña")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Tiempo Estimado", "2h 45min")
        st.metric("Ritmo Medio Plano", "5:15 min/km")
    
    with col2:
        st.metric("Calorías Estimadas", "1,850 kcal")
        st.metric("Desnivel/km", f"{int(desn_obj/dist_obj)}m/km")

# --- TAB 3: SMART PLANNER ---
with tab3:
    st.subheader("📅 Planificador Inteligente")
    st.info("Próximas sesiones de entrenamiento basadas en tu carga actual")
    
    plan_data = pd.DataFrame({
        "Fecha": pd.date_range(start=datetime.now(), periods=7),
        "Tipo": ["Recuperación", "Fondo", "Series", "Descanso", "Tempo", "Long Run", "Descanso"],
        "Duración": ["45min", "1h 30min", "1h", "-", "1h 15min", "2h 30min", "-"],
        "Intensidad": ["Baja", "Media", "Alta", "-", "Media-Alta", "Media", "-"]
    })
    
    st.dataframe(plan_data, use_container_width=True, hide_index=True)

# --- TAB 4: STRAVA FEED ---
with tab4:
    st.subheader("👟 Feed de Actividades Strava")
    
    if error:
        st.error(f"Error conectando con Strava: {error}")
    elif not actividades:
        st.warning("No se encontraron actividades recientes")
    else:
        st.success(f"✅ Mostrando {len(actividades)} actividades recientes")
        
        for act in actividades:
            with st.expander(f"🏃 {act.name} - {act.start_date_local.strftime('%d/%m/%Y')}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    distancia_km = float(act.distance) / 1000 if act.distance else 0
                    st.metric("Distancia", f"{distancia_km:.2f} km")
                
                with col2:
                    try:
                        minutos = int(act.moving_time.total_seconds() // 60)
                        st.metric("Tiempo", f"{minutos} min")
                    except (AttributeError, TypeError):
                        st.metric("Tiempo", "N/A")
                
                with col3:
                    if act.total_elevation_gain:
                        st.metric("Desnivel+", f"{int(act.total_elevation_gain)} m")
                    else:
                        st.metric("Desnivel+", "N/A")
                
                with col4:
                    if act.average_heartrate:
                        st.metric("FC Media", f"{int(act.average_heartrate)} bpm")
                    else:
                        st.metric("FC Media", "N/A")
                
                st.write(f"**Tipo:** {act.type}")
                try:
                    desc = getattr(act, 'description', None)
                        if desc:
                            st.write(f"**Descripción:** {desc}")
                except (AttributeError, TypeError):
                    pass
