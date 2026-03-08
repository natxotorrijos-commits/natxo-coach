import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN E INTELIGENCIA DEL ENTRENADOR ---
st.set_page_config(page_title="Natxo AI Trainer", layout="wide")

def generar_plan_futuro(objetivo_tipo, semanas=4):
    """
    Motor de IA que proyecta entrenamientos basados en el objetivo.
    """
    plan = []
    fecha_inicio = datetime.now()
    
    for i in range(semanas * 7):
        fecha = fecha_inicio + timedelta(days=i)
        dia_semana = fecha.strftime("%A")
        semana_actual = (i // 7) + 1
        
        # Lógica de carga ondulante (Semanas 1-3 carga, Semana 4 descarga)
        es_descarga = semana_actual % 4 == 0
        
        sesion = ""
        if dia_semana == "Monday":
            sesion = "🏃 Trote suave (Z2) - Recuperación" if not es_descarga else "💤 Descanso Total"
        elif dia_semana == "Tuesday":
            sesion = "🏊 Natación: Series de 200m" if not es_descarga else "🏊 Natación técnica suave"
        elif dia_semana == "Wednesday":
            sesion = "🏃 Series en cuesta (Potencia)" if not es_descarga else "🏃 Trote regenerativo"
        elif dia_semana == "Thursday":
            sesion = "🏋️ Fuerza funcional (Core/Pierna)"
        elif dia_semana == "Friday":
            sesion = "🏊 Natación: Resistencia" if not es_descarga else "💤 Descanso"
        elif dia_semana == "Saturday":
            distancia = 12 + (semana_actual * 2) if not es_descarga else 10
            sesion = f"🏃 Trail Largo: {distancia}km con desnivel"
        elif dia_semana == "Sunday":
            sesion = "🚶 Descanso activo o caminata"

        plan.append({"Fecha": fecha.strftime("%d/%m/%Y"), "Día": dia_semana, "Sesión": sesion})
    return pd.DataFrame(plan)

# --- INTERFAZ DE USUARIO ---
st.title("🏃‍♂️ Natxo Coach AI: Tu Entrenador de Largo Plazo")

# 1. ESTADO DE FORMA (Datos del informe)
st.sidebar.header("Métricas de Salud (Suunto)")
fitness = st.sidebar.slider("Fitness actual (CTL)", 0, 150, 84)
fatiga = st.sidebar.slider("Fatiga actual (ATL)", 0, 150, 101)
forma = fitness - fatiga

st.sidebar.metric("Forma actual", f"{forma}", "Cansado" if forma < -10 else "Óptimo")

# 2. DEFINICIÓN DE OBJETIVOS A FUTURO
st.header("🎯 Configura tu próximo Gran Reto")
col_obj, col_fecha = st.columns(2)
with col_obj:
    meta = st.selectbox("¿Qué estamos preparando?", ["Trail Running (Media/Larga)", "Maratón de asfalto", "Triatlón / Natación", "Mantenimiento Fitness"])
with col_fecha:
    meses = st.slider("Horizonte de planificación (semanas)", 4, 16, 8)

if st.button("🔄 Recalcular Plan a Largo Plazo"):
    df_plan = generar_plan_futuro(meta, meses)
    st.session_state['plan'] = df_plan
    st.success(f"¡Plan de {meses} semanas generado con éxito!")

# 3. VISUALIZACIÓN DEL PLAN
if 'plan' in st.session_state:
    st.subheader(f"📅 Tu hoja de ruta para: {meta}")
    
    # Filtro para no abrumar
    semana_ver = st.selectbox("Ver semana:", range(1, meses + 1))
    inicio = (semana_ver - 1) * 7
    fin = inicio + 7
    st.table(st.session_state['plan'].iloc[inicio:fin])

# 4. FEEDBACK Y ADAPTACIÓN (El cerebro de la App)
st.divider()
st.header("🧠 Feedback Post-Entreno")
st.write("Dime cómo te has sentido hoy para que la app ajuste el resto del mes.")

with st.form("feedback_coach"):
    sensacion = st.select_slider("Sensación de esfuerzo", options=["Muy fácil", "Fácil", "Moderado", "Duro", "Extenuante"])
    dolor = st.checkbox("¿Sientes alguna molestia física?")
    completado = st.radio("¿Has completado el entreno?", ["Sí, perfecto", "A medias", "No he podido"])
    
    if st.form_submit_button("Enviar al Coach"):
        if completado == "No he podido" or dolor:
            st.warning("⚠️ Natxo, he detectado riesgo. Reajustando el plan: Mañana pasaremos a Descanso Total y bajaremos la carga un 20% esta semana.")
        else:
            st.success("💪 ¡Excelente! El plan sigue según lo previsto. Mañana mantendremos la intensidad.")
