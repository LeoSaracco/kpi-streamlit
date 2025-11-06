import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# Configuración de la página
st.set_page_config(
    page_title="Sistema de KPIs - Equipo Java",
    page_icon="📊",
    layout="wide"
)

# Conexión a la base de datos
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="aws-1-us-east-2.pooler.supabase.com",
        database="postgres",
        user="postgres.fvueocvxawgrddeggmyj",
        password="Bocajuniors1905!",
        port=5432,
        sslmode='require'
    )

# Inicializar la base de datos
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Tabla de integrantes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS integrantes (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            rol VARCHAR(100),
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de KPIs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpis (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            descripcion TEXT,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de evaluaciones
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id SERIAL PRIMARY KEY,
            integrante_id INTEGER REFERENCES integrantes(id),
            kpi_id INTEGER REFERENCES kpis(id),
            calificacion INTEGER CHECK (calificacion BETWEEN 1 AND 4),
            comentario TEXT,
            fecha_evaluacion DATE NOT NULL,
            evaluador VARCHAR(100),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()

# Funciones CRUD Integrantes
def agregar_integrante(nombre, rol):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO integrantes (nombre, rol) VALUES (%s, %s)",
        (nombre, rol)
    )
    conn.commit()
    cur.close()

def obtener_integrantes(solo_activos=True):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM integrantes"
    if solo_activos:
        query += " WHERE activo = TRUE"
    query += " ORDER BY nombre"
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_integrante(integrante_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE integrantes SET activo = FALSE WHERE id = %s", (integrante_id,))
    conn.commit()
    cur.close()

# Funciones CRUD KPIs
def agregar_kpi(nombre, descripcion):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO kpis (nombre, descripcion) VALUES (%s, %s)",
        (nombre, descripcion)
    )
    conn.commit()
    cur.close()

def obtener_kpis(solo_activos=True):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM kpis"
    if solo_activos:
        query += " WHERE activo = TRUE"
    query += " ORDER BY nombre"
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_kpi(kpi_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE kpis SET activo = FALSE WHERE id = %s", (kpi_id,))
    conn.commit()
    cur.close()

# Funciones evaluaciones
def agregar_evaluacion(integrante_id, kpi_id, calificacion, fecha, evaluador, comentario=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO evaluaciones 
           (integrante_id, kpi_id, calificacion, fecha_evaluacion, evaluador, comentario) 
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (integrante_id, kpi_id, calificacion, fecha, evaluador, comentario)
    )
    conn.commit()
    cur.close()

def obtener_evaluaciones(fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT e.*, i.nombre as integrante, k.nombre as kpi_nombre
        FROM evaluaciones e
        JOIN integrantes i ON e.integrante_id = i.id
        JOIN kpis k ON e.kpi_id = k.id
        WHERE 1=1
    """
    params = []
    
    if fecha_inicio:
        query += " AND e.fecha_evaluacion >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND e.fecha_evaluacion <= %s"
        params.append(fecha_fin)
    
    query += " ORDER BY e.fecha_evaluacion DESC"
    
    cur.execute(query, params)
    result = cur.fetchall()
    cur.close()
    return result

# Calificaciones
CALIFICACIONES = {1: "⭐ Excelente", 2: "👍 Bueno", 3: "⚠️ Regular", 4: "❌ Deficiente"}
def calcular_puntuacion_invertida(calificacion): return 5 - calificacion

# Inicializar DB
init_db()

# Sidebar navegación
st.sidebar.title("📊 Sistema de KPIs")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegación",
    ["📝 Nueva Evaluación", "👥 Gestión de Integrantes", "📋 Gestión de KPIs", "📈 Reportes y Análisis"]
)

# ---------------------------------------------------
# 📝 Nueva Evaluación
# ---------------------------------------------------
if menu == "📝 Nueva Evaluación":
    st.title("📝 Registrar Nueva Evaluación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos de la Evaluación")
        integrantes = obtener_integrantes()
        if not integrantes:
            st.warning("⚠️ Primero debes agregar integrantes al sistema")
        else:
            integrante_options = {i['nombre']: i['id'] for i in integrantes}
            integrante_seleccionado = st.selectbox("Integrante a evaluar", list(integrante_options.keys()))
            fecha_eval = st.date_input("Fecha de evaluación", value=date.today())
            evaluador = st.text_input("Evaluador", value=st.session_state.get('evaluador', ''))
            if evaluador:
                st.session_state['evaluador'] = evaluador
    
    with col2:
        st.subheader("KPIs a Evaluar")
        kpis = obtener_kpis()
        if not kpis:
            st.warning("⚠️ Primero debes agregar KPIs al sistema")
        else:
            st.info(f"📊 Total de KPIs activos: {len(kpis)}")
    
    if integrantes and kpis and evaluador:
        st.markdown("---")
        st.subheader("Calificaciones")
        evaluaciones_temp = {}
        for kpi in kpis:
            with st.expander(f"📌 {kpi['nombre']}", expanded=True):
                if kpi['descripcion']:
                    st.caption(kpi['descripcion'])
                col_cal, col_com = st.columns([1,2])
                with col_cal:
                    calificacion = st.radio(
                        "Calificación",
                        options=[1,2,3,4],
                        format_func=lambda x: f"{x} - {CALIFICACIONES[x]}",
                        key=f"cal_{kpi['id']}",
                        horizontal=True
                    )
                with col_com:
                    comentario = st.text_area(
                        "Comentario (opcional)",
                        key=f"com_{kpi['id']}",
                        height=80
                    )
                evaluaciones_temp[kpi['id']] = {'calificacion': calificacion, 'comentario': comentario}
        
        if 'evaluacion_guardada' not in st.session_state:
            st.session_state.evaluacion_guardada = False
        
        if st.button("💾 Guardar Evaluación", type="primary"):
            if not st.session_state.evaluacion_guardada:
                try:
                    integrante_id = integrante_options[integrante_seleccionado]
                    for kpi_id, datos in evaluaciones_temp.items():
                        agregar_evaluacion(integrante_id, kpi_id, datos['calificacion'], fecha_eval, evaluador, datos['comentario'])
                    st.success(f"✅ Evaluación de {integrante_seleccionado} guardada exitosamente!")
                    st.balloons()
                    st.session_state.evaluacion_guardada = True
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")

# ---------------------------------------------------
# 👥 Gestión de Integrantes
# ---------------------------------------------------
elif menu == "👥 Gestión de Integrantes":
    st.title("👥 Gestión de Integrantes del Equipo")
    
    tab1, tab2 = st.tabs(["➕ Agregar Integrante", "📋 Ver Integrantes"])
    
    with tab1:
        st.subheader("Agregar Nuevo Integrante")
        if 'mensaje_integrante' not in st.session_state:
            st.session_state.mensaje_integrante = None
        
        if st.session_state.mensaje_integrante:
            st.success(st.session_state.mensaje_integrante)
            st.session_state.mensaje_integrante = None
        
        with st.form(key='form_integrante', clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo")
            with col2:
                rol = st.text_input("Rol/Posición")
            submitted = st.form_submit_button("➕ Agregar Integrante", type="primary")
            if submitted and nombre:
                try:
                    agregar_integrante(nombre, rol)
                    st.session_state.mensaje_integrante = f"✅ Integrante '{nombre}' agregado exitosamente!"
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            elif submitted:
                st.warning("⚠️ El nombre es obligatorio")
    
    with tab2:
        st.subheader("Integrantes Registrados")
        mostrar_inactivos = st.checkbox("Mostrar integrantes inactivos")
        integrantes = obtener_integrantes(solo_activos=not mostrar_inactivos)
        if integrantes:
            df = pd.DataFrame(integrantes)
            df['Estado'] = df['activo'].apply(lambda x: '✅ Activo' if x else '❌ Inactivo')
            st.dataframe(df[['nombre','rol','Estado','fecha_creacion']], hide_index=True, use_container_width=True)
            # Desactivar integrantes
            integrantes_activos = [i for i in integrantes if i['activo']]
            if integrantes_activos:
                opciones = {i['nombre']: i['id'] for i in integrantes_activos}
                seleccionado = st.selectbox("Seleccionar integrante a desactivar", list(opciones.keys()))
                if st.button("❌ Desactivar"):
                    try:
                        desactivar_integrante(opciones[seleccionado])
                        st.success(f"✅ Integrante '{seleccionado}' desactivado")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# ---------------------------------------------------
# 📋 Gestión de KPIs
# ---------------------------------------------------
elif menu == "📋 Gestión de KPIs":
    st.title("📋 Gestión de KPIs")
    
    tab1, tab2 = st.tabs(["➕ Agregar KPI", "📋 Ver KPIs"])
    
    with tab1:
        st.subheader("Agregar Nuevo KPI")
        if 'mensaje_kpi' not in st.session_state:
            st.session_state.mensaje_kpi = None
        if st.session_state.mensaje_kpi:
            st.success(st.session_state.mensaje_kpi)
            st.session_state.mensaje_kpi = None
        with st.form(key='form_kpi', clear_on_submit=True):
            nombre_kpi = st.text_input("Nombre del KPI")
            descripcion_kpi = st.text_area("Descripción (opcional)")
            submitted = st.form_submit_button("➕ Agregar KPI", type="primary")
            if submitted and nombre_kpi:
                try:
                    agregar_kpi(nombre_kpi, descripcion_kpi)
                    st.session_state.mensaje_kpi = f"✅ KPI '{nombre_kpi}' agregado exitosamente!"
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            elif submitted:
                st.warning("⚠️ El nombre del KPI es obligatorio")

    with tab2:
        st.subheader("KPIs Registrados")
        mostrar_inactivos_kpi = st.checkbox("Mostrar KPIs inactivos")
        kpis = obtener_kpis(solo_activos=not mostrar_inactivos_kpi)
        if kpis:
            for kpi in kpis:
                with st.expander(f"{'✅' if kpi['activo'] else '❌'} {kpi['nombre']}", expanded=False):
                    if kpi['descripcion']:
                        st.write(f"**Descripción:** {kpi['descripcion']}")
                    st.caption(f"Creado: {kpi['fecha_creacion']}")
                    if kpi['activo']:
                        if st.button(f"❌ Desactivar", key=f"deactivate_{kpi['id']}"):
                            try:
                                desactivar_kpi(kpi['id'])
                                st.success(f"✅ KPI desactivado")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

# ---------------------------------------------------
# 📈 Reportes y Análisis
# ---------------------------------------------------
elif menu == "📈 Reportes y Análisis":
    st.title("📈 Reportes y Análisis de Desempeño")
    # Aquí puedes mantener tu código de reportes igual, sin cambios significativos
    st.info("Aquí van los gráficos y análisis de KPIs y evaluaciones.")
