import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import json, os, requests
from datetime import datetime, timedelta, date
from stravalib.client import Client

try:
    import anthropic as anthropic_sdk
    CLAUDE_AVAILABLE = True
except:
    CLAUDE_AVAILABLE = False

st.set_page_config(page_title="NATXO ELITE | AI Coach", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html,body,[class*="st-"]{font-family:'Inter',sans-serif;}
.stApp{background-color:#05070a;color:#ffffff;}
[data-testid="stSidebar"]{display:none;}
.block-container{padding-top:1.5rem!important;}
.premium-card{background:linear-gradient(145deg,#111418,#090b0e);border:1px solid #1e2631;border-radius:20px;padding:25px;box-shadow:0 10px 30px rgba(0,0,0,0.5);margin-bottom:20px;}
.metric-value{font-size:2.2rem;font-weight:700;color:#00f2ff;}
.metric-label{font-size:0.8rem;color:#8e9aaf;text-transform:uppercase;letter-spacing:1.5px;}
.session-card{background:linear-gradient(135deg,#0a1628,#0d1f35);border:1px solid #1e3a5f;border-left:4px solid #00f2ff;border-radius:16px;padding:16px;margin-bottom:12px;}
.stButton>button{background:linear-gradient(90deg,#00f2ff,#0072ff);color:#05070a;border:none;border-radius:12px;padding:10px 25px;font-weight:700;transition:0.3s;}
.stButton>button:hover{transform:scale(1.02);box-shadow:0 0 20px rgba(0,242,255,0.4);}
.stTabs [data-baseweb="tab-list"]{background-color:transparent;gap:15px;}
.stTabs [data-baseweb="tab"]{background-color:#111418;border:1px solid #1e2631;border-radius:30px;color:#8e9aaf;padding:8px 30px;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,#00f2ff,#0072ff);color:#05070a;border:none;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ── Persistencia ─────────────────────────────────────────────────────────────
PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_profile.json")
DEFAULT = {
    "strava_tokens": {"access_token":"","refresh_token":"","expires_at":0},
    "onboarding_done": False,
    "goals": {"objetivo":"","objetivo_tipo":"","evento_nombre":"","evento_fecha":"",
              "horas_semana":8,"lesiones":"","anos_entrenando":3,"fc_max":185,"deportes":[]},
    "daily_plans": {}, "last_checkin": {}
}

def load_profile():
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH) as f: p=json.load(f)
            for k,v in DEFAULT.items():
                if k not in p: p[k]=v
            return p
        except: pass
    return DEFAULT.copy()

def save_profile(p):
    with open(PROFILE_PATH,"w") as f: json.dump(p,f,indent=2,ensure_ascii=False)

# ── Strava ───────────────────────────────────────────────────────────────────
def get_cfg():
    try:
        return {"client_id":str(st.secrets["STRAVA_CLIENT_ID"]),"client_secret":str(st.secrets["STRAVA_CLIENT_SECRET"]),
                "redirect_uri":st.secrets.get("STRAVA_REDIRECT_URI","http://localhost:8501")}
    except: return None

def auth_url(cfg):
    return (f"https://www.strava.com/oauth/authorize?client_id={cfg['client_id']}"
            f"&response_type=code&redirect_uri={cfg['redirect_uri']}&approval_prompt=auto&scope=read,activity:read_all")

def exchange_code(code, cfg):
    r=requests.post("https://www.strava.com/oauth/token",data={"client_id":cfg["client_id"],"client_secret":cfg["client_secret"],"code":code,"grant_type":"authorization_code"},timeout=10)
    return r.json() if r.status_code==200 else None

def do_refresh(tok, cfg):
    r=requests.post("https://www.strava.com/oauth/token",data={"client_id":cfg["client_id"],"client_secret":cfg["client_secret"],"refresh_token":tok,"grant_type":"refresh_token"},timeout=10)
    return r.json() if r.status_code==200 else None

def get_client(profile, cfg):
    t=profile["strava_tokens"]
    if not t.get("refresh_token"): return None
    if t.get("expires_at",0)<datetime.now().timestamp()+60:
        data=do_refresh(t["refresh_token"],cfg)
        if not data: return None
        t.update({"access_token":data["access_token"],"refresh_token":data["refresh_token"],"expires_at":data["expires_at"]})
        save_profile(profile)
    c=Client(); c.access_token=t["access_token"]; return c

# ── Métricas ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600,show_spinner=False)
def fetch_acts(access_token, days=90):
    c=Client(); c.access_token=access_token
    after=datetime.now()-timedelta(days=days)
    try: return list(c.get_activities(after=after,limit=200)),None
    except Exception as e: return [],str(e)

def to_df(acts):
    rows=[]
    for a in acts:
        rows.append({"date":pd.Timestamp(a.start_date_local),"name":str(a.name),"type":str(a.type),
            "distance_km":float(a.distance or 0)/1000,"duration_min":float((a.moving_time or timedelta()).total_seconds())/60,
            "elevation_m":float(a.total_elevation_gain or 0),"avg_hr":float(a.average_heartrate or 0),
            "suffer":float(a.suffer_score or 0) if hasattr(a,"suffer_score") else 0,"calories":float(a.calories or 0)})
    if not rows: return pd.DataFrame(columns=["date","name","type","distance_km","duration_min","elevation_m","avg_hr","suffer","calories"])
    return pd.DataFrame(rows).sort_values("date")

def calc_tss(row, fc_max=185):
    if row.get("suffer",0)>0: return float(row["suffer"])*1.5
    dur_h=row.get("duration_min",0)/60
    if dur_h==0: return 0
    hr=row.get("avg_hr",0)
    if hr>0 and fc_max>0: return dur_h*100*(hr/fc_max)**2
    base={"run":60,"trailrun":80,"swim":50,"ride":55,"weighttraining":30}.get(row.get("type","").lower(),45)
    return dur_h*base

def calc_metrics(df, fc_max=185):
    if df.empty: return pd.DataFrame(),0.0,0.0,0.0
    df=df.copy()
    df["tss"]=df.apply(lambda r:calc_tss(r.to_dict(),fc_max),axis=1)
    daily=df.groupby(df["date"].dt.date)["tss"].sum().reset_index()
    daily.columns=["date","tss"]
    dr=pd.date_range(start=daily["date"].min(),end=date.today(),freq="D")
    full=pd.DataFrame({"date":dr})
    dm=dict(zip(daily["date"],daily["tss"]))
    full["tss"]=full["date"].dt.date.map(dm).fillna(0)
    ctl,atl=0.0,0.0; ctls,atls=[],[]
    for t in full["tss"]:
        ctl=ctl*(1-1/42)+t*(1/42); atl=atl*(1-1/7)+t*(1/7)
        ctls.append(round(ctl,1)); atls.append(round(atl,1))
    full["CTL"]=ctls; full["ATL"]=atls; full["TSB"]=[round(c-a,1) for c,a in zip(ctls,atls)]
    return full,round(ctls[-1],1),round(atls[-1],1),round(ctls[-1]-atls[-1],1)

def fstatus(ctl,atl,tsb):
    if tsb>5: return "FRESCO","#00ff80","Listo para competir"
    if tsb>-10: return "ÓPTIMO","#0072ff","Buen momento para calidad"
    if tsb>-25: return "CARGADO","#ffc107","Acumulando carga"
    return "FATIGA","#ff4b4b","Prioriza descanso"

# ── Gemini ───────────────────────────────────────────────────────────────────
def init_claude():
    if not CLAUDE_AVAILABLE: return None
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            return anthropic_sdk.Anthropic(api_key=api_key)
    except: pass
    return None

def gen_plan_rules(profile, ctl, atl, tsb, checkin, today):
    """Fallback plan generator based on metrics and training logic."""
    g = profile.get("goals", {})
    fc = g.get("fc_max", 185)
    wd = today.weekday()  # 0=Mon … 6=Sun
    energia = checkin.get("energia", 7)
    molestias = checkin.get("molestias", "ninguna").lower()
    tiene_molestias = molestias not in ("ninguna", "none", "", "no")
    day_es = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    # Decide today's session based on TSB, energy and day
    if tsb < -25 or energia <= 3 or tiene_molestias:
        sesion = {"tipo":"Recuperación activa","duracion":"30–40 min","intensidad":"Baja",
            "zonas":f"Z1 (< {int(fc*.6)} ppm)",
            "descripcion":"Rodaje muy suave o caminata. Mantén la FC por debajo de Z2. El objetivo es activar la circulación sin añadir fatiga.",
            "consejo":"Tu cuerpo necesita descanso. Menos es más hoy." }
    elif wd in (1, 4) and tsb > -15 and energia >= 6:  # Tue/Thu → quality
        sesion = {"tipo":"Series de Velocidad","duracion":"60–70 min","intensidad":"Alta",
            "zonas":f"Z4 ({int(fc*.75)}–{int(fc*.85)} ppm)",
            "descripcion":f"Calentamiento 15 min Z2. Bloque: 6×800 m a ritmo 10K (aprox. 4:10–4:20/km), recuperación 90 seg. Vuelta a la calma 10 min.",
            "consejo":"Arranca conservador en las 2 primeras series y acelera en las últimas." }
    elif wd == 5 and energia >= 5:  # Saturday → long trail
        sesion = {"tipo":"Salida Larga de Trail","duracion":"90–120 min","intensidad":"Moderada",
            "zonas":f"Z2–Z3 ({int(fc*.6)}–{int(fc*.8)} ppm)",
            "descripcion":"Sal por monte o camino con desnivel. Mantén conversación posible. Objetivo: tiempo en piernas y desnivel acumulado (+200 m mínimo).",
            "consejo":"Lleva agua y gel si superas 75 min. Camina los repechos para no pasarte de Z3." }
    elif wd == 6:  # Sunday → strength or rest
        sesion = {"tipo":"Pesas / Fuerza","duracion":"45–55 min","intensidad":"Moderada",
            "zonas":"Frecuencia cardíaca libre",
            "descripcion":"Sentadillas 4×10, peso muerto rumano 3×12, zancadas 3×10 cada pierna, plancha 3×45 seg, elevaciones de talón 3×15. Descanso 60–90 seg entre series.",
            "consejo":"Trabaja el tren inferior excéntrico para proteger rodillas en bajadas de trail." }
    else:  # default Z2 run
        sesion = {"tipo":"Rodaje Aeróbico Z2","duracion":"50–60 min","intensidad":"Baja",
            "zonas":f"Z2 ({int(fc*.6)}–{int(fc*.7)} ppm)",
            "descripcion":"Ritmo cómodo, conversación fluida. Si llevas pulsómetro, no salgas de Z2. Terreno llano o ligero.",
            "consejo":"El 80% del entrenamiento debe ser Z2. Hoy toca construir base aeróbica." }

    # Build weekly template
    plantilla = [
        {"dia":"Lunes","actividad":"Descanso","duracion":"—","detalle":"Recuperación total"},
        {"dia":"Martes","actividad":"Series Z4","duracion":"65 min","detalle":"6×800m ritmo 10K"},
        {"dia":"Miércoles","actividad":"Natación","duracion":"40 min","detalle":"1.200–1.500 m técnica"},
        {"dia":"Jueves","actividad":"Rodaje Z2","duracion":"55 min","detalle":"Fondo aeróbico cómodo"},
        {"dia":"Viernes","actividad":"Descanso","duracion":"—","detalle":"o 30 min suave"},
        {"dia":"Sábado","actividad":"Trail Largo","duracion":"100 min","detalle":"~15 km +200 m Z2-Z3"},
        {"dia":"Domingo","actividad":"Pesas","duracion":"50 min","detalle":"Core + tren inferior"},
    ]

    fase = "Semana de Base" if tsb < -10 else "Semana de Calidad" if tsb > 5 else "Semana de Mantenimiento"
    consejo = (f"TSB {tsb:+.0f} — {'Estás fresco, aprovecha para calidad.' if tsb>5 else 'Carga moderada, combina calidad y recuperación.' if tsb>-10 else 'Acumulando fatiga. Prioriza el sueño y la nutrición.'}")

    return {"sesion_hoy":sesion,"semana":plantilla,"consejo_clave":consejo,"advertencia":None,"fase":fase}

def gen_plan(model,profile,recent_summary,ctl,atl,tsb,checkin,today):
    g=profile.get("goals",{}); fst,_,_=fstatus(ctl,atl,tsb)
    day_es=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][today.weekday()]
    prompt=f"""Eres un entrenador elite de trail running. Hablas español. Sé directo y específico.

ATLETA: {g.get('objetivo_tipo','Trail runner')}, Zaragoza, {g.get('anos_entrenando',3)} años exp.
OBJETIVO: {g.get('objetivo','Trail 30km +1000m')} | EVENTO: {g.get('evento_nombre','N/A')} el {g.get('evento_fecha','N/A')}
DISPONIBILIDAD: {g.get('horas_semana',8)}h/semana | DEPORTES: {', '.join(g.get('deportes',['Trail','Running','Natación']))}
LESIONES: {g.get('lesiones','Ninguna')} | FC MAX: {g.get('fc_max',185)} ppm

MÉTRICAS ({day_es} {today.strftime('%d/%m/%Y')}):
CTL={ctl} ATL={atl} TSB={tsb:+.0f} Estado={fst}

ACTIVIDADES RECIENTES:
{recent_summary}

CHECK-IN: Energía {checkin.get('energia',7)}/10 | Ayer: {checkin.get('entreno_ayer','N/A')} | Molestias: {checkin.get('molestias','Ninguna')}
{('Notas: '+checkin.get('notas','')) if checkin.get('notas') else ''}

Devuelve SOLO JSON válido sin markdown:
{{"sesion_hoy":{{"tipo":"string","duracion":"string","descripcion":"descripción detallada con series/ritmos/zonas concretas","zonas":"string p.ej. Z2 105-128ppm","intensidad":"Baja|Moderada|Alta|Muy Alta","consejo":"consejo personal del coach"}},"semana":[{{"dia":"Lunes","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Martes","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Miércoles","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Jueves","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Viernes","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Sábado","actividad":"string","duracion":"string","detalle":"string"}},{{"dia":"Domingo","actividad":"string","duracion":"string","detalle":"string"}}],"consejo_clave":"string","advertencia":null,"fase":"string"}}"""
    try:
        msg=model.messages.create(model="claude-sonnet-4-5",max_tokens=2048,
            messages=[{"role":"user","content":prompt}])
        text=msg.content[0].text.strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except: return None

# ── Onboarding ───────────────────────────────────────────────────────────────
def render_onboarding(profile):
    step=st.session_state.get("ob_step",0)
    goals=profile.get("goals",{})
    prog="".join([f'<div style="width:35px;height:5px;border-radius:3px;background:{"#00f2ff" if i<=step else "#1e2631"};"></div>' for i in range(6)])
    st.markdown(f"""<div style="text-align:center;padding:30px 0 40px;">
    <h1 style="color:#00f2ff;font-size:2.2rem;">⚡ NATXO ELITE</h1>
    <p style="color:#8e9aaf;">Personalicemos tu plan de entrenamiento</p>
    <div style="display:flex;justify-content:center;gap:6px;margin-top:15px;">{prog}</div>
    <p style="color:#666;font-size:0.8rem;margin-top:6px;">Paso {step+1}/6</p></div>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,2,1])
    with col:
        if step==0:
            st.markdown("### ¿Cuál es tu objetivo principal?")
            tipos=["🏔️ Ultra Trail (>42km)","🏃 Trail Running (10-42km)","🚴 Ciclismo","🏊 Natación / Triatlón","💪 Fitness General"]
            ot=st.radio("",tipos,label_visibility="collapsed",index=1)
            if st.button("Continuar →",key="ob0"): goals["objetivo_tipo"]=ot; st.session_state["ob_step"]=1; st.rerun()
        elif step==1:
            st.markdown("### Tu próximo evento")
            ev=st.text_input("Nombre del evento",value=goals.get("evento_nombre",""),placeholder="Trail Moncayo 30K")
            fe=st.date_input("Fecha del evento",value=datetime.now().date()+timedelta(days=90))
            ob=st.text_input("Tu objetivo",value=goals.get("objetivo",""),placeholder="Acabar en menos de 4h")
            c1,c2=st.columns(2)
            with c1:
                if st.button("← Atrás",key="ob1b"): st.session_state["ob_step"]=0; st.rerun()
            with c2:
                if st.button("Continuar →",key="ob1"): goals.update({"evento_nombre":ev,"evento_fecha":str(fe),"objetivo":ob}); st.session_state["ob_step"]=2; st.rerun()
        elif step==2:
            st.markdown("### Disponibilidad semanal")
            h=st.slider("Horas/semana",3,25,goals.get("horas_semana",8))
            deps=st.multiselect("Deportes que practicas",["🏃 Running","🏔️ Trail Running","🚴 Ciclismo","🏊 Natación","💪 Pesas/Fuerza"],default=goals.get("deportes",["🏃 Running","🏔️ Trail Running"]))
            c1,c2=st.columns(2)
            with c1:
                if st.button("← Atrás",key="ob2b"): st.session_state["ob_step"]=1; st.rerun()
            with c2:
                if st.button("Continuar →",key="ob2"): goals.update({"horas_semana":h,"deportes":deps}); st.session_state["ob_step"]=3; st.rerun()
        elif step==3:
            st.markdown("### Lesiones o limitaciones")
            les=st.text_area("Describe cualquier lesión o limitación",value=goals.get("lesiones",""),placeholder="Ej: Tendinitis rotuliana. Sin bajadas largas.",height=100)
            c1,c2=st.columns(2)
            with c1:
                if st.button("← Atrás",key="ob3b"): st.session_state["ob_step"]=2; st.rerun()
            with c2:
                if st.button("Continuar →",key="ob3"): goals["lesiones"]=les; st.session_state["ob_step"]=4; st.rerun()
        elif step==4:
            st.markdown("### Frecuencia cardíaca máxima")
            fc=st.slider("FC Máxima (ppm) — usa 220 - tu edad si no la conoces",140,220,goals.get("fc_max",185))
            st.caption(f"Z1<{int(fc*.6)} | Z2 {int(fc*.6)}–{int(fc*.7)} | Z3 {int(fc*.7)}–{int(fc*.8)} | Z4 {int(fc*.8)}–{int(fc*.9)} | Z5>{int(fc*.9)} ppm")
            anos=st.slider("Años entrenando regularmente",0,30,goals.get("anos_entrenando",3))
            c1,c2=st.columns(2)
            with c1:
                if st.button("← Atrás",key="ob4b"): st.session_state["ob_step"]=3; st.rerun()
            with c2:
                if st.button("Continuar →",key="ob4"): goals.update({"fc_max":fc,"anos_entrenando":anos}); st.session_state["ob_step"]=5; st.rerun()
        elif step==5:
            st.markdown("### Resumen de tu perfil")
            st.markdown(f"""<div class="premium-card">
            <p><b style="color:#00f2ff;">Objetivo:</b> {goals.get('objetivo_tipo','')} — {goals.get('objetivo','')}</p>
            <p><b style="color:#00f2ff;">Evento:</b> {goals.get('evento_nombre','N/A')} · {goals.get('evento_fecha','N/A')}</p>
            <p><b style="color:#00f2ff;">Tiempo:</b> {goals.get('horas_semana',8)} h/semana · Deportes: {', '.join(goals.get('deportes',[]))}</p>
            <p><b style="color:#00f2ff;">Lesiones:</b> {goals.get('lesiones','Ninguna') or 'Ninguna'}</p>
            <p><b style="color:#00f2ff;">FC Máxima:</b> {goals.get('fc_max',185)} ppm · Experiencia: {goals.get('anos_entrenando',3)} años</p>
            </div>""",unsafe_allow_html=True)
            c1,c2=st.columns(2)
            with c1:
                if st.button("← Atrás",key="ob5b"): st.session_state["ob_step"]=4; st.rerun()
            with c2:
                if st.button("🚀 ¡Empezar!",key="ob5"):
                    profile["goals"]=goals; profile["onboarding_done"]=True
                    save_profile(profile); st.session_state.pop("ob_step",None); st.rerun()

# ── Check-in diario ───────────────────────────────────────────────────────────
def render_checkin(profile):
    st.markdown("""<div style="text-align:center;padding:20px 0 30px;">
    <h2 style="color:#00f2ff;">☀️ Check-in de hoy</h2>
    <p style="color:#8e9aaf;">¿Cómo estás? Ajustaré tu sesión en función de tu estado.</p></div>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,2,1])
    with col:
        with st.form("checkin"):
            e_labels={1:"🪫 Sin energía",2:"😴 Muy bajo",3:"😓 Bajo",4:"😐 Regular",5:"🙂 Aceptable",6:"😊 Bien",7:"😁 Bueno",8:"⚡ Muy bien",9:"🔥 Excelente",10:"🚀 Épico"}
            energia=st.slider("Nivel de energía",1,10,7)
            st.markdown(f"<p style='text-align:center;font-size:1.2rem;'>{e_labels.get(energia,'')}</p>",unsafe_allow_html=True)
            entreno_ayer=st.radio("¿Completaste el entrenamiento de ayer?",["✅ Sí, completo","⚡ Parcialmente","❌ No entrené","🛌 Era día de descanso"],label_visibility="collapsed")
            molestias=st.text_area("¿Alguna molestia o dolor?",placeholder="Ej: Gemelos tensos. O 'ninguna'.",height=70,label_visibility="collapsed")
            notas=st.text_area("Notas para el coach (opcional)",placeholder="Lo que quieras contarme...",height=55,label_visibility="collapsed")
            if st.form_submit_button("💾 Guardar y ver mi plan",use_container_width=True):
                ci={"energia":energia,"entreno_ayer":entreno_ayer,"molestias":molestias or "Ninguna","notas":notas or "","ts":datetime.now().isoformat()}
                profile["last_checkin"][date.today().isoformat()]=ci
                save_profile(profile); st.session_state["checkin_done"]=True; st.rerun()

# ── App principal ─────────────────────────────────────────────────────────────
def render_app(profile, client, model):
    today=date.today(); today_str=today.isoformat()
    fc_max=profile["goals"].get("fc_max",185)
    with st.spinner("Sincronizando Strava..."):
        acts,_=fetch_acts(client.access_token,days=90)
    df=to_df(acts)
    mdf,ctl,atl,tsb=calc_metrics(df,fc_max)
    flabel,fcolor,fdesc=fstatus(ctl,atl,tsb)
    checkin=profile.get("last_checkin",{}).get(today_str,{})

    st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:0 0 20px;">
    <h1 style="color:#00f2ff;margin:0;">⚡ NATXO ELITE</h1>
    <div style="text-align:right;"><p style="margin:0;font-weight:600;">Natxo Torrijos</p>
    <p style="margin:0;color:#8e9aaf;font-size:0.85rem;">🟢 Strava · {today.strftime('%d %b %Y')}</p></div></div>""",unsafe_allow_html=True)

    m1,m2,m3,m4=st.columns(4)
    atl_col="#ff4b4b" if atl>ctl*1.3 else "#ffc107" if atl>ctl else "#00f2ff"
    with m1: st.markdown(f'<div class="premium-card"><p class="metric-label">Fitness (CTL)</p><p class="metric-value">{ctl}</p><p style="color:#8e9aaf;font-size:0.8rem;">Carga crónica 42d</p></div>',unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="premium-card"><p class="metric-label">Fatiga (ATL)</p><p class="metric-value" style="color:{atl_col};">{atl}</p><p style="color:#8e9aaf;font-size:0.8rem;">Carga aguda 7d</p></div>',unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="premium-card"><p class="metric-label">Forma (TSB)</p><p class="metric-value" style="color:{fcolor};">{tsb:+.0f}</p><p style="color:#8e9aaf;font-size:0.8rem;">Fitness − Fatiga</p></div>',unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="premium-card"><p class="metric-label">Estado</p><p class="metric-value" style="font-size:1.4rem;color:{fcolor};">{flabel}</p><p style="color:#8e9aaf;font-size:0.8rem;">{fdesc}</p></div>',unsafe_allow_html=True)

    tab1,tab2,tab3,tab4=st.tabs(["📅 HOY","🗓️ SEMANA","📊 HISTORIAL","⚙️ PERFIL"])

    with tab1:
        if not checkin:
            c1,c2=st.columns([4,1])
            with c1: st.markdown("""<div style="background:linear-gradient(135deg,#1a0a2e,#0d1628);border:1px solid #6b3fa0;border-radius:14px;padding:12px 18px;margin-bottom:15px;">
            <p style="margin:0;color:#c084fc;font-weight:600;">☀️ Aún no has hecho el check-in de hoy</p>
            <p style="margin:4px 0 0;color:#8e9aaf;font-size:0.85rem;">Cuéntame cómo estás para personalizar tu sesión.</p></div>""",unsafe_allow_html=True)
            with c2:
                if st.button("Check-in",key="go_ci"): st.session_state["show_ci"]=True; st.rerun()
        if st.session_state.get("show_ci"):
            render_checkin(profile); return

        plan=profile.get("daily_plans",{}).get(today_str)
        if not plan:
            if model:
                recent=df.tail(7)
                lines=[f"  {r['date'].strftime('%d/%m')}: {r['type']} {r['distance_km']:.1f}km {r['duration_min']:.0f}min +{r['elevation_m']:.0f}m" for _,r in recent.iterrows()] if not df.empty else ["Sin actividades recientes"]
                with st.spinner("🤖 Generando plan con IA..."):
                    plan=gen_plan(model,profile,"\n".join(lines),ctl,atl,tsb,checkin,today)
            else:
                plan=gen_plan_rules(profile,ctl,atl,tsb,checkin,today)
            if plan:
                profile.setdefault("daily_plans",{})[today_str]=plan; save_profile(profile)
        if plan:
            s=plan.get("sesion_hoy",{})
            ic={"Baja":"#00ff80","Moderada":"#0072ff","Alta":"#ffc107","Muy Alta":"#ff4b4b"}.get(s.get("intensidad","Moderada"),"#0072ff")
            day_es=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][today.weekday()]
            st.markdown(f"""<div style="background:linear-gradient(135deg,#0a1628,#0d1f35);border:1px solid #1e3a5f;border-left:5px solid {ic};border-radius:20px;padding:28px;margin-bottom:20px;">
            <p style="margin:0;color:#8e9aaf;font-size:0.78rem;text-transform:uppercase;letter-spacing:2px;">SESIÓN DE HOY · {day_es.upper()} {today.strftime('%d %b').upper()}</p>
            <h2 style="margin:8px 0 4px;color:#fff;font-size:1.7rem;">{s.get('tipo','Entrenamiento')}</h2>
            <p style="margin:0;color:{ic};font-weight:600;">⏱ {s.get('duracion','')} &nbsp;·&nbsp; Intensidad {s.get('intensidad','')} &nbsp;·&nbsp; {s.get('zonas','')}</p>
            <hr style="border-color:#1e3a5f;margin:18px 0;">
            <p style="margin:0;color:#d0e0ff;line-height:1.7;">{s.get('descripcion','')}</p>
            {"<hr style='border-color:#1e3a5f;margin:16px 0;'><p style='margin:0;color:#ffc107;'>💬 <b>Coach:</b> "+s.get('consejo','')+"</p>" if s.get('consejo') else ""}
            </div>""",unsafe_allow_html=True)
            c1,c2=st.columns(2)
            with c1:
                if plan.get("consejo_clave"):
                    st.markdown(f"""<div class="premium-card"><p style="color:#00f2ff;font-weight:700;margin-bottom:8px;">💡 Consejo clave</p><p style="color:#d0e0ff;margin:0;">{plan['consejo_clave']}</p></div>""",unsafe_allow_html=True)
            with c2:
                content=plan.get("advertencia") or plan.get("fase","")
                border="#ff4b4b" if plan.get("advertencia") else "#1e2631"
                icon="⚠️" if plan.get("advertencia") else "📈"
                label="Atención" if plan.get("advertencia") else "Fase semanal"
                if content: st.markdown(f"""<div class="premium-card" style="border-color:{border};"><p style="color:{border};font-weight:700;margin-bottom:8px;">{icon} {label}</p><p style="color:#d0e0ff;margin:0;">{content}</p></div>""",unsafe_allow_html=True)
            if st.button("🔄 Regenerar plan"):
                profile.get("daily_plans",{}).pop(today_str,None); save_profile(profile); st.rerun()
        if not model:
            st.caption("💡 Plan generado por reglas. Añade ANTHROPIC_API_KEY en Secrets para activar el coach IA.")

    with tab2:
        plan=profile.get("daily_plans",{}).get(today_str)
        if plan and "semana" in plan:
            semana=plan["semana"]; cols=st.columns(7); wd=today.weekday()
            tbg={"descanso":"#111","rest":"#111","recupera":"#0d200d","fondo":"#0a1428","trail":"#142800","series":"#281400","natación":"#00142a","pesas":"#14001a","tempo":"#1e1000"}
            for i,(col,d) in enumerate(zip(cols,semana)):
                act=d.get("actividad",""); bg="#1e2631"
                for k,v in tbg.items():
                    if k in act.lower(): bg=v; break
                border="2px solid #00f2ff" if i==wd else "1px solid #1e2631"
                with col:
                    st.markdown(f"""<div style="background:{bg};border:{border};border-radius:14px;padding:12px 8px;text-align:center;min-height:150px;display:flex;flex-direction:column;justify-content:space-between;">
                    <p style="margin:0;color:#8e9aaf;font-size:0.68rem;text-transform:uppercase;">{d.get('dia','')[:3]}</p>
                    <p style="margin:6px 0;color:{'#00f2ff' if i==wd else '#fff'};font-size:0.82rem;font-weight:600;line-height:1.2;">{act}</p>
                    <p style="margin:0;color:#8e9aaf;font-size:0.72rem;">{d.get('duracion','')}</p>
                    <p style="margin:4px 0 0;color:#555;font-size:0.65rem;line-height:1.2;">{d.get('detalle','')[:35]}</p>
                    </div>""",unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            df_s=pd.DataFrame(semana)[["dia","actividad","duracion","detalle"]]
            df_s.columns=["Día","Actividad","Duración","Detalle"]
            st.dataframe(df_s,use_container_width=True,hide_index=True)
        else:
            st.info("Completa el check-in en **HOY** para generar el plan semanal.")

    with tab3:
        if not df.empty:
            if not mdf.empty:
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=mdf["date"],y=mdf["CTL"],name="Fitness (CTL)",fill="tozeroy",line=dict(color="#00f2ff",width=2),fillcolor="rgba(0,242,255,0.08)"))
                fig.add_trace(go.Scatter(x=mdf["date"],y=mdf["ATL"],name="Fatiga (ATL)",line=dict(color="#ff4b4b",width=2,dash="dot")))
                fig.add_trace(go.Scatter(x=mdf["date"],y=mdf["TSB"],name="Forma (TSB)",line=dict(color="#ffc107",width=1.5),yaxis="y2"))
                fig.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=320,margin=dict(l=0,r=0,t=20,b=0),legend=dict(orientation="h",y=1.12),yaxis2=dict(overlaying="y",side="right",showgrid=False,zeroline=True,zerolinecolor="#333"))
                st.plotly_chart(fig,use_container_width=True)
            c1,c2=st.columns([2,1])
            icons={"Run":"🏃","TrailRun":"🏔️","Swim":"🏊","WeightTraining":"💪","Ride":"🚴"}
            with c1:
                st.markdown("#### Sesiones recientes")
                for _,r in df.sort_values("date",ascending=False).head(15).iterrows():
                    icon=icons.get(r["type"],"🏅")
                    d_str=r["date"].strftime("%d %b")
                    dist=f"{r['distance_km']:.1f} km" if r["distance_km"]>0 else ""
                    elev=f"+{r['elevation_m']:.0f}m" if r["elevation_m"]>10 else ""
                    tv=calc_tss(r.to_dict(),fc_max)
                    st.markdown(f"""<div class="session-card">
                    <div style="display:flex;justify-content:space-between;"><span>{icon} <b>{r['name']}</b></span><span style="color:#8e9aaf;font-size:0.85rem;">{d_str}</span></div>
                    <div style="margin-top:6px;display:flex;gap:12px;flex-wrap:wrap;">
                    {f'<span style="color:#8e9aaf;font-size:0.82rem;">📍 {dist}</span>' if dist else ''}
                    <span style="color:#8e9aaf;font-size:0.82rem;">⏱ {r['duration_min']:.0f} min</span>
                    {f'<span style="color:#8e9aaf;font-size:0.82rem;">⛰ {elev}</span>' if elev else ''}
                    <span style="color:#00f2ff;font-size:0.82rem;font-weight:600;">~TSS {tv:.0f}</span>
                    </div></div>""",unsafe_allow_html=True)
            with c2:
                sc=df["type"].value_counts()
                fig2=go.Figure(go.Pie(labels=sc.index,values=sc.values,hole=0.55,marker_colors=["#00f2ff","#ff4b4b","#ffc107","#00ff80","#8b5cf6"]))
                fig2.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",height=260,margin=dict(l=0,r=0,t=0,b=0),legend=dict(font=dict(color="#8e9aaf",size=10)))
                st.plotly_chart(fig2,use_container_width=True)
                total_tss=sum(calc_tss(r.to_dict(),fc_max) for _,r in df.iterrows())
                st.markdown(f"""<div class="premium-card"><p class="metric-label">Últimos 90 días</p>
                <p style="margin:6px 0;"><b style="color:#00f2ff;">{len(df)}</b> sesiones</p>
                <p style="margin:3px 0;"><b style="color:#00f2ff;">{df['distance_km'].sum():.0f}</b> km</p>
                <p style="margin:3px 0;"><b style="color:#00f2ff;">{df['duration_min'].sum()/60:.0f}</b> horas</p>
                <p style="margin:3px 0;"><b style="color:#00f2ff;">{df['elevation_m'].sum():.0f}</b> m desnivel</p>
                <p style="margin:3px 0;"><b style="color:#00f2ff;">{total_tss:.0f}</b> TSS total</p></div>""",unsafe_allow_html=True)
        else:
            st.info("No se encontraron actividades en los últimos 90 días.")

    with tab4:
        g=profile.get("goals",{}); c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Perfil de atleta")
            st.markdown(f"""<div class="premium-card">
            <p><b style="color:#00f2ff;">Objetivo:</b> {g.get('objetivo_tipo','N/A')}</p>
            <p><b style="color:#00f2ff;">Meta:</b> {g.get('objetivo','N/A')}</p>
            <p><b style="color:#00f2ff;">Evento:</b> {g.get('evento_nombre','N/A')} · {g.get('evento_fecha','N/A')}</p>
            <p><b style="color:#00f2ff;">Tiempo:</b> {g.get('horas_semana',8)} h/semana</p>
            <p><b style="color:#00f2ff;">Deportes:</b> {', '.join(g.get('deportes',[]))}</p>
            <p><b style="color:#00f2ff;">Lesiones:</b> {g.get('lesiones','Ninguna') or 'Ninguna'}</p>
            <p><b style="color:#00f2ff;">FC Máxima:</b> {g.get('fc_max',185)} ppm · Experiencia: {g.get('anos_entrenando',3)} años</p>
            </div>""",unsafe_allow_html=True)
            if st.button("✏️ Editar perfil"):
                profile["onboarding_done"]=False; save_profile(profile); st.rerun()
        with c2:
            fc=g.get("fc_max",185); st.markdown("#### Zonas de entrenamiento")
            z_df=pd.DataFrame({"Zona":["Z1 Recuperación","Z2 Aeróbico","Z3 Tempo","Z4 Umbral","Z5 VO2max"],
                "FC (ppm)":[f"< {int(fc*.6)}",f"{int(fc*.6)}–{int(fc*.7)}",f"{int(fc*.7)}–{int(fc*.8)}",f"{int(fc*.8)}–{int(fc*.9)}",f"> {int(fc*.9)}"],
                "Objetivo":["Descanso activo","Fondo aeróbico base","Ritmo maratón","Umbral anaeróbico","Velocidad máxima"]})
            st.dataframe(z_df,use_container_width=True,hide_index=True)
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🔗 Reconectar Strava"):
                profile["strava_tokens"]={}; save_profile(profile); st.rerun()

    st.markdown('<p style="text-align:center;color:#333;margin-top:50px;font-size:0.75rem;">⚡ Natxo Elite Coaching System · Claude AI & Strava</p>',unsafe_allow_html=True)

# ── Bienvenida ────────────────────────────────────────────────────────────────
def render_welcome(cfg):
    st.markdown("""<div style="text-align:center;padding:70px 40px;background:radial-gradient(ellipse at center,#0d1f35 0%,#05070a 70%);border-radius:30px;border:1px solid #1e2631;margin:30px 0;">
    <h1 style="color:#00f2ff;font-size:3rem;margin-bottom:10px;">⚡ NATXO ELITE</h1>
    <p style="color:#8e9aaf;font-size:1.15rem;max-width:480px;margin:0 auto 35px;">Tu coach de IA para trail running y resistencia.<br>Conecta con Strava para empezar.</p>
    <div style="display:flex;justify-content:center;gap:50px;margin-bottom:40px;flex-wrap:wrap;">
    <div><p style="font-size:2rem;margin:0;">🏔️</p><p style="color:#8e9aaf;font-size:0.85rem;margin:5px 0 0;">Analiza tu historial<br>de Strava</p></div>
    <div><p style="font-size:2rem;margin:0;">🤖</p><p style="color:#8e9aaf;font-size:0.85rem;margin:5px 0 0;">Plan IA personalizado<br>cada día</p></div>
    <div><p style="font-size:2rem;margin:0;">📊</p><p style="color:#8e9aaf;font-size:0.85rem;margin:5px 0 0;">CTL / ATL / TSB<br>reales</p></div>
    <div><p style="font-size:2rem;margin:0;">☀️</p><p style="color:#8e9aaf;font-size:0.85rem;margin:5px 0 0;">Check-in diario<br>adaptativo</p></div>
    </div></div>""",unsafe_allow_html=True)
    _,col,_=st.columns([1,1,1])
    with col:
        if cfg:
            st.markdown(f"""<a href="{auth_url(cfg)}" target="_self" style="text-decoration:none;">
            <div style="background:linear-gradient(90deg,#fc4c02,#ff7043);color:white;text-align:center;padding:14px 30px;border-radius:12px;font-weight:700;font-size:1.05rem;margin-top:10px;box-shadow:0 4px 20px rgba(252,76,2,0.4);">
            🟠 Conectar con Strava</div></a>""",unsafe_allow_html=True)
        else:
            st.error("Configura STRAVA_CLIENT_ID y STRAVA_CLIENT_SECRET en Streamlit Secrets.")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    profile=load_profile(); cfg=get_cfg(); model=init_claude()
    # Auto-bootstrap tokens from Secrets (bypasses OAuth flow)
    if cfg and not profile["strava_tokens"].get("refresh_token"):
        rt=st.secrets.get("STRAVA_REFRESH_TOKEN","")
        at=st.secrets.get("STRAVA_ACCESS_TOKEN","")
        if rt:
            profile["strava_tokens"]={"access_token":at,"refresh_token":rt,"expires_at":0}
            save_profile(profile)
    params=st.query_params
    if "code" in params and cfg:
        code=params["code"]
        if code!=st.session_state.get("proc_code"):
            with st.spinner("Conectando con Strava..."):
                data=exchange_code(code,cfg)
            if data and "access_token" in data:
                profile["strava_tokens"]={"access_token":data["access_token"],"refresh_token":data["refresh_token"],"expires_at":data["expires_at"]}
                save_profile(profile); st.session_state["proc_code"]=code
                st.query_params.clear(); st.rerun()
            else:
                st.error("Error al conectar con Strava. Inténtalo de nuevo."); st.stop()
    if not profile["strava_tokens"].get("refresh_token"):
        render_welcome(cfg); return
    client=get_client(profile,cfg)
    if not client:
        st.warning("Sesión expirada. Vuelve a conectar.")
        profile["strava_tokens"]={};save_profile(profile);render_welcome(cfg);return
    if not profile.get("onboarding_done"):
        render_onboarding(profile); return
    today_str=date.today().isoformat()
    if today_str not in profile.get("last_checkin",{}) and not st.session_state.get("skip_ci"):
        render_checkin(profile)
        _,col,_=st.columns([1,1,1])
        with col:
            if st.button("Saltar check-in →",key="skip_ci_btn"):
                st.session_state["skip_ci"]=True; st.rerun()
        return
    render_app(profile,client,model)

if __name__=="__main__":
    main()
