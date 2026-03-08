import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Natxo Ultra-Coach Pro", layout="wide", page_icon="🏃‍♂️")

# Estilo Dark Pro
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE DATOS (Simulación de Strava + Informe) ---
if 'fitness' not in st.session_state:
    st.session_state.fitness = 84
    st.session_state.fatiga = 101

# --- SIDEBAR: CONEXIÓN Y OBJETIVOS ---
st.sidebar.title("🛠️ Centro de Control")
with st.sidebar.expander("🔗 Conexión Strava", expanded=False):
    st.write("Estado: 🟢 Sincronizado")
    st.button("Forzar actualización de datos")
    st.caption("Token: b78...90as (Válido)")

st.sidebar.divider()
st.sidebar.header("🎯 Define tu Objetivo")
distancia_obj = st.sidebar.slider("Distancia (km)", 10, 100, 20)
desnivel_obj = st.sidebar.slider("Desnivel (+m)", 0, 5000, 1000)
fecha_obj = st.sidebar.date_input("Fecha del evento", datetime(2026, 3, 15))

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard de Forma", "📅 Plan de Entrenamiento", "🏔️ Análisis de Objetivo", "⚙️ Ajustes"])

# --- TAB 1: GRÁFICAS DE ESTADO DE FORMA ---
with tab1:
    st.header("Análisis de Rendimiento (CTL / ATL / TSB)")
    
    # Simulación de gráfica de los últimos 30 días
    dias = pd.date_range(end=datetime.now(), periods=30)
    ctl = np.linspace(75, 84, 30)  # Fitness
    atl = np.random.randint(80, 110, 30) # Fatiga
    tsb = ctl - atl # Forma
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dias, y=ctl, name="Fitness (CTL)", line=dict(color='#00ffcc', width=3)))
    fig.add_trace(go.Scatter(x=dias, y=atl, name="Fatiga (ATL)", line=dict(color='#ff4b4b', width=2, dash='dot')))
    fig.add_trace(go.Bar(x=dias, y=tsb, name="Forma (TSB)", marker_color='rgba(255, 255, 255, 0.2)'))
    
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Fitness", f"{st.session_state.fitness}", "+1.2")
    c2.metric("Fatiga", f"{st.session_state.fatiga}", "-3.5", delta_color="inverse")
    c3.metric("Forma (TSB)", f"{st.session_state.fitness - st.session_state.fatiga}", "+4.7")

# --- TAB 2: PLAN ADAPTATIVO ---
with tab2:
    hoy = datetime.now()
    semana_actual = hoy.isocalendar()[1]
    st.header(f"📅 Semana {semana_actual} - Bloque: Tapering")
    
    # Lógica de entrenamiento basada en los objetivos del sidebar
    col_d, col_e = st.columns(2)
    with col_d:
        st.write(f"**Próxima sesión:** Lunes 9 de Marzo")
        st.info("🏃 Trote Recuperación: 7km @ 5:35 min/km")
    with col_e:
        st.write("**Foco de la semana:**")
        st.success("Reducción de fatiga (Supercompensación)")

    st.divider()
    st.subheader("Proyección a Futuro")
    # Aquí iría el generador de semanas que hicimos antes
    st.write("El plan se ajusta automáticamente según tu desnivel objetivo:", desnivel_obj, "m")

# --- TAB 3: ANÁLISIS DE OBJETIVO ---
with tab3:
    st.header(f"Análisis Técnico: {distancia_obj}km +{desnivel_obj}m")
    
    # Cálculo de tiempo estimado (modelo simple de trail)
    ritmo_base = 4.4 # min/km para Natxo (4:25/km)
    penalizacion_desnivel = (desnivel_obj / 100) * 8 # 8 min extra por cada 100m+
    tiempo_total_min = (distancia_obj * ritmo_base) + penalizacion_desnivel
    
    horas = int(tiempo_total_min // 60)
    minutos = int(tiempo_total_min % 60)
    
    st.subheader(f"⏱️ Tiempo Estimado: {horas}h {minutos}min")
    st.progress(st.session_state.fitness / 100)
    st.write(f"Probabilidad de éxito basada en Fitness (84): **Alta**")
    
    st.divider()
    st.subheader("🔋 Estrategia Nutricional")
    st.write(f"- Hidratos totales: {int(tiempo_total_min / 60 * 70)}g (70g/h)")
    st.write(f"- Sodio: {int(tiempo_total_min / 60 * 600)}mg")

# --- TAB 4: AJUSTES DE USUARIO ---
with tab4:
    st.subheader("Configuración de Atleta")
    st.text_input("Nombre", "Natxo Torrijos")
    st.number_input("Peso (kg)", 70.0)
    st.number_input("Umbral Anaeróbico (ppm)", 162)
    if st.button("Guardar Cambios"):
        st.toast("Perfil actualizado")
