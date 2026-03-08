import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from stravalib.client import Client
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Natxo Pro-Coach", page_icon="🏔️", layout="wide")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 12px; border: 1px solid #3e445b; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1e2130; border-radius: 5px; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE CONEXIÓN A STRAVA ---
def get_strava_data():
    try:
        client = Client()
        # Estos datos los cogerá de la pestaña 'Secrets' de Streamlit Cloud
        client_id = st.secrets["STRAVA_CLIENT_ID"]
        client_secret = st.secrets["STRAVA_CLIENT_SECRET"]
        refresh_token = st.secrets["STRAVA_REFRESH_TOKEN"]

        # Refrescar el token de acceso
        token_response = client.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )
        client.access_token = token_response['access_token']
        return client, client.get_athlete()
    except Exception as e:
        st.error(f"Error conectando a Strava: {e}")
        return None, None

# Intentar conexión
strava_client, atleta = get_strava_data()

# --- SIDEBAR (Centro de Control) ---
st.sidebar.title("🏔️ Natxo Pro-Coach")
if atleta:
    st.sidebar.success(f"Conectado: {atleta.firstname}")
else:
    st.sidebar.warning("Strava: No conectado (Configura los Secrets)")

st.sidebar.divider()
st.sidebar.header("🎯 Define tu Gran Objetivo")
meta_distancia = st.sidebar.number_input("Distancia (km)", value=20)
meta_desnivel = st.sidebar.number_input("Desnivel (+m)", value=1000)
fecha_meta = st.sidebar.date_input("Fecha del objetivo", value=datetime(2026, 3, 15))

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 ESTADO DE FORMA", "📅 PLAN SEMANAL", "🔮 PROYECTOR FUTURO"])

# --- TAB 1: DASHBOARD DE RENDIMIENTO ---
with tab1:
    st.header("Análisis de Carga y Forma")
    
    # Datos actuales (Basados en tu informe de hoy)
    fitness_actual = 84
    fatiga_actual = 101
    forma_actual = fitness_actual - fatiga_actual

    col1, col2, col3 = st.columns(3)
    col1.metric("Fitness (CTL)", fitness_actual, "+1.5")
    col2.metric("Fatiga (ATL)", fatiga_actual, "-4.2", delta_color="inverse")
    col3.metric("Forma (TSB)", forma_actual, "Recuperando", delta_color="normal")

    # Gráfica de Forma Proyectada
    dias = pd.date_range(end=fecha_meta + timedelta(days=2), periods=30)
    # Simulación de curva de tapering
    curva_forma = np.linspace(forma_actual, 10, 30) 
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dias, y=curva_forma, name="Evolución Forma (TSB)", line=dict(color='#00ffcc', width=3)))
    fig.add_hline(y=0, line_dash="dash", line_color="white", annotation_text="Zona de Rendimiento")
    fig.update_layout(template="plotly_dark", height=350)
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: TU SEMANA HACIA EL PIRINEO ---
with tab2:
    st.header("Semana 9 - 15 Marzo: Tapering Pirineos")
    
    # Tabla interactiva
    plan_semanal = {
        "Día": ["Lunes 9", "Martes 10", "Miércoles 11", "Jueves 12", "Viernes 13", "Sábado 14", "Domingo 15"],
        "Actividad": ["🏃 Trote Recup.", "💤 DESCANSO", "🏊 Natación", "🏃 Z2 + Chispa", "🏊 Natación Suave", "🧘 Pre-Race", "🏔️ PIRINEOS"],
        "Objetivo Detallado": [
            "6-7km @ 5:30-5:45 min/km. Pulso < 134",
            "Descanso Total - Imprescindible",
            "1500m (Foco técnica y soltura)",
            "8km @ 5:15-5:25 + 4x100m progresivos",
            "800m muy relajados + estiramientos",
            "Carga de hidratos (6g/kg peso)",
            f"{meta_distancia}km / +{meta_desnivel}m. ¡A disfrutar!"
        ]
    }
    st.table(pd.DataFrame(plan_semanal))
    
    st.info("💡 **Consejo del Coach:** El martes es el día más importante. Tu fatiga de 101 necesita ese respiro para que el miércoles te sientas 'eléctrico' en la piscina.")

# --- TAB 3: PROYECTOR DE ENTRENAMIENTO A FUTURO ---
with tab3:
    st.header("Generador de Bloques (Siguientes 4 semanas)")
    st.write(f"Preparando: {meta_distancia}km con +{meta_desnivel}m de desnivel.")
    
    semanas_proyectar = st.slider("¿Cuántas semanas quieres ver?", 1, 8, 4)
    
    if st.button("Generar Plan a Largo Plazo"):
        # Lógica de periodización simple
        proyeccion = []
        for s in range(1, semanas_proyectar + 1):
            intensidad = "Descarga" if s % 4 == 0 else "Carga"
            km_aprox = 40 + (s * 5) if intensidad == "Carga" else 30
            proyeccion.append({
                "Semana": f"Semana {s}",
                "Tipo": intensidad,
                "Volumen Estimado": f"{km_aprox} km",
                "Sesión Clave": "Trail con D+ progresivo" if intensidad == "Carga" else "Natación + Rodaje Suave"
            })
        st.write(pd.DataFrame(proyeccion))

# --- FOOTER ---
st.divider()
st.caption("Natxo Pro-Coach v4.0 | Datos de Strava sincronizados mediante API segura.")
