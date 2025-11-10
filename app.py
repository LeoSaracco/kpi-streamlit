import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# Configuración de la página
st.set_page_config(
    page_title="Sistema de KPIs - Equipos",
    page_icon="📊",
    layout="wide"
)

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="kpi",
        user="postgres",
        password="postgres"
    )

# Inicializar la base de datos
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Tabla de equipos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            descripcion TEXT,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de integrantes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS integrantes (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            rol VARCHAR(100),
            equipo_id INTEGER REFERENCES equipos(id),
            es_lider BOOLEAN DEFAULT FALSE,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de KPIs con tipo
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpis (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            descripcion TEXT,
            tipo VARCHAR(20) CHECK (tipo IN ('cualitativo', 'cuantitativo')),
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
            valor_cuantitativo DECIMAL(10,2),
            comentario TEXT,
            fecha_evaluacion DATE NOT NULL,
            evaluador VARCHAR(100),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()

# ==================== FUNCIONES CRUD EQUIPOS ====================
def agregar_equipo(nombre, descripcion):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO equipos (nombre, descripcion) VALUES (%s, %s)",
        (nombre, descripcion)
    )
    conn.commit()
    cur.close()

def obtener_equipos(solo_activos=True):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if solo_activos:
        cur.execute("SELECT * FROM equipos WHERE activo = TRUE ORDER BY nombre")
    else:
        cur.execute("SELECT * FROM equipos ORDER BY nombre")
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_equipo(equipo_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE equipos SET activo = FALSE WHERE id = %s", (equipo_id,))
    conn.commit()
    cur.close()

# ==================== FUNCIONES CRUD INTEGRANTES ====================
def agregar_integrante(nombre, rol, equipo_id, es_lider):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO integrantes (nombre, rol, equipo_id, es_lider) VALUES (%s, %s, %s, %s)",
        (nombre, rol, equipo_id, es_lider)
    )
    conn.commit()
    cur.close()

def obtener_integrantes(solo_activos=True, equipo_id=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT i.*, e.nombre as equipo_nombre 
        FROM integrantes i
        LEFT JOIN equipos e ON i.equipo_id = e.id
        WHERE 1=1
    """
    params = []
    
    if solo_activos:
        query += " AND i.activo = TRUE"
    if equipo_id:
        query += " AND i.equipo_id = %s"
        params.append(equipo_id)
    
    query += " ORDER BY i.nombre"
    
    cur.execute(query, params)
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_integrante(integrante_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE integrantes SET activo = FALSE WHERE id = %s", (integrante_id,))
    conn.commit()
    cur.close()

# ==================== FUNCIONES CRUD KPIS ====================
def agregar_kpi(nombre, descripcion, tipo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO kpis (nombre, descripcion, tipo) VALUES (%s, %s, %s)",
        (nombre, descripcion, tipo)
    )
    conn.commit()
    cur.close()

def obtener_kpis(solo_activos=True, tipo=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM kpis WHERE 1=1"
    params = []
    
    if solo_activos:
        query += " AND activo = TRUE"
    if tipo:
        query += " AND tipo = %s"
        params.append(tipo)
    
    query += " ORDER BY tipo, nombre"
    
    cur.execute(query, params)
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_kpi(kpi_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE kpis SET activo = FALSE WHERE id = %s", (kpi_id,))
    conn.commit()
    cur.close()

# ==================== FUNCIONES EVALUACIONES ====================
def agregar_evaluacion(integrante_id, kpi_id, calificacion, fecha, evaluador, comentario="", valor_cuantitativo=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO evaluaciones 
           (integrante_id, kpi_id, calificacion, fecha_evaluacion, evaluador, comentario, valor_cuantitativo) 
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (integrante_id, kpi_id, calificacion, fecha, evaluador, comentario, valor_cuantitativo)
    )
    conn.commit()
    cur.close()

def obtener_evaluaciones(fecha_inicio=None, fecha_fin=None, equipo_id=None, tipo_kpi=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT e.*, 
               i.nombre as integrante, 
               i.equipo_id,
               eq.nombre as equipo_nombre,
               k.nombre as kpi_nombre,
               k.tipo as kpi_tipo
        FROM evaluaciones e
        JOIN integrantes i ON e.integrante_id = i.id
        JOIN kpis k ON e.kpi_id = k.id
        JOIN equipos eq ON i.equipo_id = eq.id
        WHERE 1=1
    """
    params = []
    
    if fecha_inicio:
        query += " AND e.fecha_evaluacion >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND e.fecha_evaluacion <= %s"
        params.append(fecha_fin)
    if equipo_id:
        query += " AND i.equipo_id = %s"
        params.append(equipo_id)
    if tipo_kpi:
        query += " AND k.tipo = %s"
        params.append(tipo_kpi)
    
    query += " ORDER BY e.fecha_evaluacion DESC"
    
    cur.execute(query, params)
    result = cur.fetchall()
    cur.close()
    return result

# Mapeo de calificaciones (de MEJOR a PEOR)
CALIFICACIONES = {
    1: "⭐ Excelente",
    2: "👍 Bueno", 
    3: "⚠️ Regular",
    4: "❌ Deficiente"
}

TIPOS_KPI = {
    'cualitativo': '🎭 Cualitativo (Soft Skills)',
    'cuantitativo': '📊 Cuantitativo (Objetivos)'
}

# Función para calcular puntuación invertida (mayor = mejor)
def calcular_puntuacion_invertida(calificacion):
    return 5 - calificacion

# Inicializar base de datos
init_db()

# Sidebar - Navegación
st.sidebar.title("📊 Sistema de KPIs")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegación",
    [
        "📝 Nueva Evaluación",
        "🏢 Gestión de Equipos", 
        "👥 Gestión de Integrantes", 
        "📋 Gestión de KPIs", 
        "📈 Reportes y Análisis"
    ]
)

# ==================== PÁGINA: GESTIÓN DE EQUIPOS ====================
if menu == "🏢 Gestión de Equipos":
    st.title("🏢 Gestión de Equipos")
    
    tab1, tab2 = st.tabs(["➕ Agregar Equipo", "📋 Ver Equipos"])
    
    with tab1:
        st.subheader("Agregar Nuevo Equipo")
        
        if 'mensaje_equipo' not in st.session_state:
            st.session_state.mensaje_equipo = None
        
        if st.session_state.mensaje_equipo:
            st.success(st.session_state.mensaje_equipo)
            st.session_state.mensaje_equipo = None
        
        with st.form(key='form_equipo', clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_equipo = st.text_input("Nombre del Equipo", placeholder="Ej: Squad Backend")
            
            with col2:
                descripcion_equipo = st.text_area("Descripción (opcional)", placeholder="Describe el equipo")
            
            submitted = st.form_submit_button("➕ Agregar Equipo", type="primary", use_container_width=True)
            
            if submitted:
                if nombre_equipo:
                    try:
                        agregar_equipo(nombre_equipo, descripcion_equipo)
                        st.session_state.mensaje_equipo = f"✅ Equipo '{nombre_equipo}' agregado exitosamente!"
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ El nombre del equipo es obligatorio")
    
    with tab2:
        st.subheader("Equipos Registrados")
        
        mostrar_inactivos = st.checkbox("Mostrar equipos inactivos")
        equipos = obtener_equipos(solo_activos=not mostrar_inactivos)
        
        if equipos:
            for equipo in equipos:
                # Contar integrantes del equipo
                integrantes_equipo = obtener_integrantes(solo_activos=True, equipo_id=equipo['id'])
                lideres = [i for i in integrantes_equipo if i['es_lider']]
                
                with st.expander(f"{'✅' if equipo['activo'] else '❌'} {equipo['nombre']} ({len(integrantes_equipo)} integrantes)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if equipo['descripcion']:
                            st.write(f"**Descripción:** {equipo['descripcion']}")
                        st.caption(f"Creado: {equipo['fecha_creacion']}")
                        st.write(f"**Total integrantes:** {len(integrantes_equipo)}")
                        if lideres:
                            st.write(f"**Líder(es):** {', '.join([l['nombre'] for l in lideres])}")
                    
                    with col2:
                        if equipo['activo']:
                            if st.button(f"❌ Desactivar Equipo", key=f"deactivate_team_{equipo['id']}"):
                                try:
                                    desactivar_equipo(equipo['id'])
                                    st.success(f"✅ Equipo desactivado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No hay equipos registrados")

# ==================== PÁGINA: GESTIÓN DE INTEGRANTES ====================
elif menu == "👥 Gestión de Integrantes":
    st.title("👥 Gestión de Integrantes del Equipo")
    
    tab1, tab2 = st.tabs(["➕ Agregar Integrante", "📋 Ver Integrantes"])
    
    with tab1:
        st.subheader("Agregar Nuevo Integrante")
        
        equipos = obtener_equipos()
        if not equipos:
            st.warning("⚠️ Primero debes crear al menos un equipo")
        else:
            if 'mensaje_integrante' not in st.session_state:
                st.session_state.mensaje_integrante = None
            
            if st.session_state.mensaje_integrante:
                st.success(st.session_state.mensaje_integrante)
                st.session_state.mensaje_integrante = None
            
            with st.form(key='form_integrante', clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    nombre = st.text_input("Nombre completo")
                    rol = st.text_input("Rol/Posición", placeholder="Ej: Senior Developer, Tech Lead")
                
                with col2:
                    equipo_options = {e['nombre']: e['id'] for e in equipos}
                    equipo_seleccionado = st.selectbox("Equipo", options=list(equipo_options.keys()))
                    es_lider = st.checkbox("¿Es líder del equipo?")
                
                submitted = st.form_submit_button("➕ Agregar Integrante", type="primary", use_container_width=True)
                
                if submitted:
                    if nombre:
                        try:
                            agregar_integrante(nombre, rol, equipo_options[equipo_seleccionado], es_lider)
                            st.session_state.mensaje_integrante = f"✅ Integrante '{nombre}' agregado exitosamente!"
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                    else:
                        st.warning("⚠️ El nombre es obligatorio")
    
    with tab2:
        st.subheader("Integrantes Registrados")
        
        col1, col2 = st.columns(2)
        with col1:
            mostrar_inactivos = st.checkbox("Mostrar integrantes inactivos")
        with col2:
            equipos = obtener_equipos()
            if equipos:
                equipo_options = {"Todos": None}
                equipo_options.update({e['nombre']: e['id'] for e in equipos})
                filtro_equipo = st.selectbox("Filtrar por equipo", options=list(equipo_options.keys()))
        
        integrantes = obtener_integrantes(
            solo_activos=not mostrar_inactivos, 
            equipo_id=equipo_options.get(filtro_equipo) if equipos else None
        )
        
        if integrantes:
            df = pd.DataFrame(integrantes)
            df['Estado'] = df['activo'].apply(lambda x: '✅ Activo' if x else '❌ Inactivo')
            df['Líder'] = df['es_lider'].apply(lambda x: '👑 Sí' if x else 'No')
            
            st.dataframe(
                df[['nombre', 'rol', 'equipo_nombre', 'Líder', 'Estado', 'fecha_creacion']],
                column_config={
                    "nombre": "Nombre",
                    "rol": "Rol",
                    "equipo_nombre": "Equipo",
                    "fecha_creacion": st.column_config.DatetimeColumn(
                        "Fecha de Creación",
                        format="DD/MM/YYYY"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("Desactivar Integrante")
            integrantes_activos = [i for i in integrantes if i['activo']]
            
            if integrantes_activos:
                integrante_options = {f"{i['nombre']} ({i['equipo_nombre']})": i['id'] for i in integrantes_activos}
                integrante_desactivar = st.selectbox(
                    "Seleccionar integrante a desactivar",
                    options=list(integrante_options.keys())
                )
                
                if st.button("❌ Desactivar", type="secondary"):
                    try:
                        desactivar_integrante(integrante_options[integrante_desactivar])
                        st.success(f"✅ Integrante desactivado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No hay integrantes registrados")

# ==================== PÁGINA: GESTIÓN DE KPIS ====================
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
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_kpi = st.text_input("Nombre del KPI", placeholder="Ej: Calidad del Código")
                tipo_kpi = st.selectbox(
                    "Tipo de KPI",
                    options=['cualitativo', 'cuantitativo'],
                    format_func=lambda x: TIPOS_KPI[x]
                )
            
            with col2:
                descripcion_kpi = st.text_area(
                    "Descripción (opcional)",
                    placeholder="Describe qué se evalúa en este KPI",
                    height=100
                )
            
            # Ayuda según el tipo
            if tipo_kpi == 'cualitativo':
                st.info("💡 **KPI Cualitativo:** Evalúa soft skills como comunicación, trabajo en equipo, liderazgo, etc.")
            else:
                st.info("💡 **KPI Cuantitativo:** Evalúa objetivos medibles como finalización de tareas, cumplimiento de plazos, etc.")
            
            submitted = st.form_submit_button("➕ Agregar KPI", type="primary", use_container_width=True)
            
            if submitted:
                if nombre_kpi:
                    try:
                        agregar_kpi(nombre_kpi, descripcion_kpi, tipo_kpi)
                        st.session_state.mensaje_kpi = f"✅ KPI '{nombre_kpi}' ({TIPOS_KPI[tipo_kpi]}) agregado exitosamente!"
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ El nombre del KPI es obligatorio")
    
    with tab2:
        st.subheader("KPIs Registrados")
        
        col1, col2 = st.columns(2)
        with col1:
            mostrar_inactivos_kpi = st.checkbox("Mostrar KPIs inactivos")
        with col2:
            filtro_tipo = st.selectbox(
                "Filtrar por tipo",
                options=['todos', 'cualitativo', 'cuantitativo'],
                format_func=lambda x: 'Todos' if x == 'todos' else TIPOS_KPI[x]
            )
        
        kpis = obtener_kpis(
            solo_activos=not mostrar_inactivos_kpi,
            tipo=None if filtro_tipo == 'todos' else filtro_tipo
        )
        
        if kpis:
            # Agrupar por tipo
            kpis_cualitativo = [k for k in kpis if k['tipo'] == 'cualitativo']
            kpis_cuantitativo = [k for k in kpis if k['tipo'] == 'cuantitativo']
            
            if kpis_cualitativo and (filtro_tipo in ['todos', 'cualitativo']):
                st.markdown("### 🎭 KPIs Cualitativos (Soft Skills)")
                for kpi in kpis_cualitativo:
                    with st.expander(f"{'✅' if kpi['activo'] else '❌'} {kpi['nombre']}", expanded=False):
                        if kpi['descripcion']:
                            st.write(f"**Descripción:** {kpi['descripcion']}")
                        st.caption(f"Creado: {kpi['fecha_creacion']}")
                        
                        if kpi['activo']:
                            if st.button(f"❌ Desactivar", key=f"deactivate_{kpi['id']}"):
                                try:
                                    desactivar_kpi(kpi['id'])
                                    st.success(f"✅ KPI desactivado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
            
            if kpis_cuantitativo and (filtro_tipo in ['todos', 'cuantitativo']):
                st.markdown("### 📊 KPIs Cuantitativos (Objetivos)")
                for kpi in kpis_cuantitativo:
                    with st.expander(f"{'✅' if kpi['activo'] else '❌'} {kpi['nombre']}", expanded=False):
                        if kpi['descripcion']:
                            st.write(f"**Descripción:** {kpi['descripcion']}")
                        st.caption(f"Creado: {kpi['fecha_creacion']}")
                        
                        if kpi['activo']:
                            if st.button(f"❌ Desactivar", key=f"deactivate_{kpi['id']}"):
                                try:
                                    desactivar_kpi(kpi['id'])
                                    st.success(f"✅ KPI desactivado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No hay KPIs registrados")

# ==================== PÁGINA: NUEVA EVALUACIÓN ====================
elif menu == "📝 Nueva Evaluación":
    st.title("📝 Registrar Nueva Evaluación")
    
    equipos = obtener_equipos()
    if not equipos:
        st.warning("⚠️ Primero debes crear al menos un equipo")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Datos de la Evaluación")
            
            equipo_options = {e['nombre']: e['id'] for e in equipos}
            equipo_seleccionado = st.selectbox("Seleccionar Equipo", options=list(equipo_options.keys()))
            equipo_id = equipo_options[equipo_seleccionado]
            
            integrantes = obtener_integrantes(solo_activos=True, equipo_id=equipo_id)
            
            if not integrantes:
                st.warning(f"⚠️ El equipo '{equipo_seleccionado}' no tiene integrantes")
            else:
                integrante_options = {i['nombre']: i['id'] for i in integrantes}
                integrante_seleccionado = st.selectbox(
                    "Integrante a evaluar",
                    options=list(integrante_options.keys())
                )
                
                fecha_eval = st.date_input(
                    "Fecha de evaluación",
                    value=date.today()
                )
                
                evaluador = st.text_input("Evaluador", value=st.session_state.get('evaluador', ''))
                if evaluador:
                    st.session_state['evaluador'] = evaluador
        
        with col2:
            st.subheader("KPIs a Evaluar")
            kpis = obtener_kpis()
            
            if not kpis:
                st.warning("⚠️ Primero debes agregar KPIs al sistema")
            else:
                kpis_cualitativo = [k for k in kpis if k['tipo'] == 'cualitativo']
                kpis_cuantitativo = [k for k in kpis if k['tipo'] == 'cuantitativo']
                
                st.info(f"📊 KPIs Cualitativos: {len(kpis_cualitativo)} | KPIs Cuantitativos: {len(kpis_cuantitativo)}")
        
        if integrantes and kpis and evaluador:
            st.markdown("---")
            
            # Separar por tipo de KPI
            tab1, tab2 = st.tabs(["🎭 KPIs Cualitativos (Soft Skills)", "📊 KPIs Cuantitativos (Objetivos)"])
            
            evaluaciones_temp = {}
            
            with tab1:
                st.subheader("Evaluación de Soft Skills")
                
                if not kpis_cualitativo:
                    st.info("No hay KPIs cualitativos configurados")
                
                for kpi in kpis_cualitativo:
                    with st.expander(f"📌 {kpi['nombre']}", expanded=True):
                        if kpi['descripcion']:
                            st.caption(kpi['descripcion'])
                        
                        col_cal, col_com = st.columns([1, 2])
                        
                        with col_cal:
                            calificacion = st.radio(
                                "Calificación",
                                options=[1, 2, 3, 4],
                                format_func=lambda x: CALIFICACIONES[x],
                                key=f"cal_{kpi['id']}",
                                horizontal=True
                            )
                        
                        with col_com:
                            comentario = st.text_area(
                                "Comentario (opcional)",
                                key=f"com_{kpi['id']}",
                                height=80
                            )
                        
                        evaluaciones_temp[kpi['id']] = {
                            'calificacion': calificacion,
                            'comentario': comentario,
                            'valor_cuantitativo': None
                        }
            
            with tab2:
                st.subheader("Evaluación de Objetivos y Metas")
                
                if not kpis_cuantitativo:
                    st.info("No hay KPIs cuantitativos configurados")
                
                for kpi in kpis_cuantitativo:
                    with st.expander(f"📌 {kpi['nombre']}", expanded=True):
                        if kpi['descripcion']:
                            st.caption(kpi['descripcion'])
                        
                        col_val, col_cal, col_com = st.columns([1, 1, 2])
                        
                        with col_val:
                            valor_cuantitativo = st.number_input(
                                "Valor/Porcentaje (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=0.0,
                                step=1.0,
                                key=f"val_{kpi['id']}",
                                help="Ejemplo: 85% de cumplimiento"
                            )
                        
                        with col_cal:
                            # Sugerir calificación basada en el valor
                            if valor_cuantitativo >= 90:
                                cal_sugerida = 1
                            elif valor_cuantitativo >= 75:
                                cal_sugerida = 2
                            elif valor_cuantitativo >= 50:
                                cal_sugerida = 3
                            else:
                                cal_sugerida = 4
                            
                            calificacion = st.radio(
                                "Calificación",
                                options=[1, 2, 3, 4],
                                format_func=lambda x: CALIFICACIONES[x],
                                index=cal_sugerida - 1,
                                key=f"cal_{kpi['id']}",
                                horizontal=True
                            )
                        
                        with col_com:
                            comentario = st.text_area(
                                "Comentario (opcional)",
                                key=f"com_{kpi['id']}",
                                height=80,
                                placeholder="Explica el cumplimiento del objetivo..."
                            )
                        
                        evaluaciones_temp[kpi['id']] = {
                            'calificacion': calificacion,
                            'comentario': comentario,
                            'valor_cuantitativo': valor_cuantitativo
                        }
            
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
            
            with col_btn1:
                if st.button("💾 Guardar Evaluación", type="primary", use_container_width=True):
                    try:
                        integrante_id = integrante_options[integrante_seleccionado]
                        for kpi_id, datos in evaluaciones_temp.items():
                            agregar_evaluacion(
                                integrante_id,
                                kpi_id,
                                datos['calificacion'],
                                fecha_eval,
                                evaluador,
                                datos['comentario'],
                                datos['valor_cuantitativo']
                            )
                        st.success(f"✅ Evaluación de {integrante_seleccionado} ({equipo_seleccionado}) guardada exitosamente!")
                        st.balloons()
                        st.session_state.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar: {str(e)}")
            
            with col_btn2:
                if st.button("🔄 Limpiar", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()

# ==================== PÁGINA: REPORTES Y ANÁLISIS ====================
elif menu == "📈 Reportes y Análisis":
    st.title("📈 Reportes y Análisis de Desempeño")
    
    # Filtros principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=date.today().replace(day=1))
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=date.today())
    with col3:
        equipos = obtener_equipos()
        equipo_options = {"Todos los equipos": None}
        equipo_options.update({e['nombre']: e['id'] for e in equipos})
        filtro_equipo = st.selectbox("Equipo", options=list(equipo_options.keys()))
    with col4:
        filtro_tipo_kpi = st.selectbox(
            "Tipo de KPI",
            options=['todos', 'cualitativo', 'cuantitativo'],
            format_func=lambda x: 'Todos' if x == 'todos' else TIPOS_KPI[x]
        )
    
    equipo_id_filtro = equipo_options[filtro_equipo]
    tipo_kpi_filtro = None if filtro_tipo_kpi == 'todos' else filtro_tipo_kpi
    
    evaluaciones = obtener_evaluaciones(
        fecha_inicio=fecha_inicio, 
        fecha_fin=fecha_fin,
        equipo_id=equipo_id_filtro,
        tipo_kpi=tipo_kpi_filtro
    )
    
    if evaluaciones:
        df_eval = pd.DataFrame(evaluaciones)
        df_eval['calificacion_texto'] = df_eval['calificacion'].map(CALIFICACIONES)
        df_eval['puntuacion_invertida'] = df_eval['calificacion'].apply(calcular_puntuacion_invertida)
        df_eval['tipo_kpi_texto'] = df_eval['kpi_tipo'].map(TIPOS_KPI)
        
        # Métricas generales
        st.subheader("📊 Resumen General")
        
        if equipo_id_filtro:
            st.info(f"📍 Mostrando resultados del equipo: **{filtro_equipo}**")
        else:
            st.info(f"🌐 Mostrando resultados de **todos los equipos**")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Evaluaciones", len(df_eval))
        with col2:
            promedio_invertido = df_eval['puntuacion_invertida'].mean()
            st.metric("Puntuación Promedio", f"{promedio_invertido:.2f}")
        with col3:
            excelentes = len(df_eval[df_eval['calificacion'] == 1])
            st.metric("⭐ Excelentes", excelentes)
        with col4:
            deficientes = len(df_eval[df_eval['calificacion'] == 4])
            st.metric("❌ Deficientes", deficientes)
        with col5:
            equipos_evaluados = df_eval['equipo_nombre'].nunique()
            st.metric("🏢 Equipos", equipos_evaluados)
        
        st.markdown("---")
        
        # Tabs principales
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🏆 Ranking General",
            "🏢 Por Equipo",
            "👥 Por Integrante", 
            "📋 Por KPI", 
            "📅 Histórico",
            "⚠️ Análisis de Riesgos"
        ])
        
        # ==================== TAB 1: RANKING GENERAL ====================
        with tab1:
            st.subheader("🏆 Ranking General de Desempeño")
            
            # Ranking por integrante
            promedio_integrante = df_eval.groupby(['integrante', 'equipo_nombre']).agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_integrante.columns = ['Integrante', 'Equipo', 'Puntuación', 'Total Evaluaciones']
            promedio_integrante = promedio_integrante.sort_values('Puntuación', ascending=False)
            promedio_integrante['Posición'] = range(1, len(promedio_integrante) + 1)
            promedio_integrante['Desempeño'] = promedio_integrante['Puntuación'].apply(
                lambda x: '⭐ Excelente' if x >= 3.5 else ('👍 Bueno' if x >= 2.5 else ('⚠️ Regular' if x >= 1.5 else '❌ Deficiente'))
            )
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_ranking = go.Figure()
                
                colors = promedio_integrante['Puntuación'].apply(
                    lambda x: 'green' if x >= 3.5 else ('lightgreen' if x >= 2.5 else ('orange' if x >= 1.5 else 'red'))
                )
                
                fig_ranking.add_trace(go.Bar(
                    y=promedio_integrante['Integrante'] + ' (' + promedio_integrante['Equipo'] + ')',
                    x=promedio_integrante['Puntuación'],
                    orientation='h',
                    text=promedio_integrante['Puntuación'].apply(lambda x: f'{x:.2f}'),
                    textposition='outside',
                    marker_color=colors,
                    hovertemplate='<b>%{y}</b><br>Puntuación: %{x:.2f}<extra></extra>'
                ))
                
                fig_ranking.update_layout(
                    title='Ranking de Desempeño (mayor puntuación = mejor)',
                    xaxis_title='Puntuación (mayor es mejor)',
                    yaxis_title='',
                    height=max(400, len(promedio_integrante) * 25),
                    showlegend=False
                )
                st.plotly_chart(fig_ranking, use_container_width=True)
            
            with col2:
                st.markdown("### 🏅 Top 5 Mejores")
                for idx, row in promedio_integrante.head(5).iterrows():
                    emoji = "🥇" if row['Posición'] == 1 else ("🥈" if row['Posición'] == 2 else ("🥉" if row['Posición'] == 3 else "📈"))
                    color = "green" if row['Puntuación'] >= 3.5 else ("lightgreen" if row['Puntuación'] >= 2.5 else ("orange" if row['Puntuación'] >= 1.5 else "red"))
                    
                    st.markdown(f"""
                    <div style='background-color: {color}; padding: 10px; margin: 5px 0; border-radius: 5px; color: white;'>
                        {emoji} <b>{row['Posición']}. {row['Integrante']}</b><br>
                        Equipo: {row['Equipo']}<br>
                        Puntuación: {row['Puntuación']:.2f}<br>
                        {row['Desempeño']}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### ⚠️ Necesitan Mejora")
                for idx, row in promedio_integrante.tail(3).iterrows():
                    emoji = "🔴" if row['Puntuación'] < 1.5 else "🟡"
                    color = "red" if row['Puntuación'] < 1.5 else "orange"
                    
                    st.markdown(f"""
                    <div style='background-color: {color}; padding: 10px; margin: 5px 0; border-radius: 5px; color: white;'>
                        {emoji} <b>{row['Posición']}. {row['Integrante']}</b><br>
                        Equipo: {row['Equipo']}<br>
                        Puntuación: {row['Puntuación']:.2f}<br>
                        {row['Desempeño']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Distribución general
            st.markdown("---")
            st.subheader("📊 Distribución General de Calificaciones")
            
            col1, col2 = st.columns(2)
            
            with col1:
                dist_general = df_eval['calificacion_texto'].value_counts()
                
                fig_pie = px.pie(
                    values=dist_general.values,
                    names=dist_general.index,
                    title='Proporción de Calificaciones',
                    color=dist_general.index,
                    color_discrete_map={
                        '⭐ Excelente': 'green',
                        '👍 Bueno': 'lightgreen',
                        '⚠️ Regular': 'orange',
                        '❌ Deficiente': 'red'
                    },
                    hole=0.4
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                dist_tipo = df_eval['tipo_kpi_texto'].value_counts()
                
                fig_pie_tipo = px.pie(
                    values=dist_tipo.values,
                    names=dist_tipo.index,
                    title='Evaluaciones por Tipo de KPI',
                    hole=0.4
                )
                fig_pie_tipo.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie_tipo, use_container_width=True)
        
        # ==================== TAB 2: POR EQUIPO ====================
        with tab2:
            st.subheader("🏢 Desempeño por Equipo")
            
            # Ranking de equipos
            promedio_equipo = df_eval.groupby('equipo_nombre').agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count',
                'integrante': 'nunique'
            }).reset_index()
            promedio_equipo.columns = ['Equipo', 'Puntuación', 'Total Evaluaciones', 'Integrantes']
            promedio_equipo = promedio_equipo.sort_values('Puntuación', ascending=False)
            
            fig_equipos = px.bar(
                promedio_equipo,
                x='Puntuación',
                y='Equipo',
                orientation='h',
                title='Ranking de Equipos (mayor = mejor)',
                text='Puntuación',
                color='Puntuación',
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green'],
                hover_data=['Total Evaluaciones', 'Integrantes']
            )
            fig_equipos.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_equipos.update_layout(height=400)
            st.plotly_chart(fig_equipos, use_container_width=True)
            
            # Comparación por tipo de KPI
            st.markdown("---")
            st.subheader("📊 Comparación: Cualitativos vs Cuantitativos por Equipo")
            
            df_tipo_equipo = df_eval.groupby(['equipo_nombre', 'kpi_tipo']).agg({
                'puntuacion_invertida': 'mean'
            }).reset_index()
            df_tipo_equipo['tipo_texto'] = df_tipo_equipo['kpi_tipo'].apply(
                lambda x: 'Cualitativos' if x == 'cualitativo' else 'Cuantitativos'
            )
            
            fig_comp = px.bar(
                df_tipo_equipo,
                x='equipo_nombre',
                y='puntuacion_invertida',
                color='tipo_texto',
                title='Puntuación por Equipo y Tipo de KPI',
                barmode='group',
                labels={'puntuacion_invertida': 'Puntuación', 'equipo_nombre': 'Equipo'}
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Desglose por equipo
            st.markdown("---")
            st.subheader("📋 Desglose Detallado por Equipo")
            
            for equipo in promedio_equipo['Equipo']:
                df_equipo = df_eval[df_eval['equipo_nombre'] == equipo]
                
                with st.expander(f"🏢 {equipo} - Puntuación: {promedio_equipo[promedio_equipo['Equipo']==equipo]['Puntuación'].values[0]:.2f}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Evaluaciones", len(df_equipo))
                    with col2:
                        integrantes_evaluados = df_equipo['integrante'].nunique()
                        st.metric("Integrantes Evaluados", integrantes_evaluados)
                    with col3:
                        promedio_equipo_val = df_equipo['puntuacion_invertida'].mean()
                        st.metric("Puntuación Promedio", f"{promedio_equipo_val:.2f}")
                    
                    # Mini ranking del equipo
                    st.write("**Ranking interno del equipo:**")
                    rank_interno = df_equipo.groupby('integrante')['puntuacion_invertida'].mean().sort_values(ascending=False).reset_index()
                    rank_interno.columns = ['Integrante', 'Puntuación']
                    rank_interno['Posición'] = range(1, len(rank_interno) + 1)
                    
                    st.dataframe(
                        rank_interno,
                        hide_index=True,
                        use_container_width=True
                    )
        
        # ==================== TAB 3: POR INTEGRANTE ====================
        with tab3:
            st.subheader("👥 Desempeño por Integrante")
            
            promedio_integrante = df_eval.groupby(['integrante', 'equipo_nombre']).agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_integrante.columns = ['Integrante', 'Equipo', 'Puntuación', 'Evaluaciones']
            promedio_integrante = promedio_integrante.sort_values('Puntuación', ascending=False)
            
            fig = px.bar(
                promedio_integrante,
                x='Puntuación',
                y='Integrante',
                orientation='h',
                title='Puntuación por Integrante (mayor = mejor)',
                text='Puntuación',
                color='Puntuación',
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green'],
                hover_data=['Equipo', 'Evaluaciones']
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(height=max(400, len(promedio_integrante) * 25))
            st.plotly_chart(fig, use_container_width=True)
            
            # Distribución de calificaciones por integrante
            st.markdown("---")
            dist_cal = df_eval.groupby(['integrante', 'calificacion_texto']).size().reset_index(name='count')
            fig2 = px.bar(
                dist_cal,
                x='integrante',
                y='count',
                color='calificacion_texto',
                title='Distribución de Calificaciones por Integrante',
                barmode='stack',
                color_discrete_map={
                    '⭐ Excelente': 'green',
                    '👍 Bueno': 'lightgreen',
                    '⚠️ Regular': 'orange',
                    '❌ Deficiente': 'red'
                }
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Comparación Cualitativos vs Cuantitativos
            st.markdown("---")
            st.subheader("🎭 vs 📊 Comparación por Tipo de KPI")
            
            df_tipo_int = df_eval.groupby(['integrante', 'kpi_tipo']).agg({
                'puntuacion_invertida': 'mean'
            }).reset_index()
            df_tipo_int['tipo_texto'] = df_tipo_int['kpi_tipo'].apply(
                lambda x: 'Soft Skills' if x == 'cualitativo' else 'Objetivos'
            )
            
            fig_comp_int = px.bar(
                df_tipo_int,
                x='integrante',
                y='puntuacion_invertida',
                color='tipo_texto',
                title='Puntuación: Soft Skills vs Objetivos por Integrante',
                barmode='group',
                labels={'puntuacion_invertida': 'Puntuación', 'integrante': 'Integrante'}
            )
            st.plotly_chart(fig_comp_int, use_container_width=True)
        
        # ==================== TAB 4: POR KPI ====================
        with tab4:
            st.subheader("📋 Desempeño por KPI")
            
            promedio_kpi = df_eval.groupby(['kpi_nombre', 'kpi_tipo']).agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_kpi.columns = ['KPI', 'Tipo', 'Puntuación', 'Evaluaciones']
            promedio_kpi = promedio_kpi.sort_values('Puntuación', ascending=False)
            promedio_kpi['Tipo_texto'] = promedio_kpi['Tipo'].apply(
                lambda x: '🎭 Cualitativo' if x == 'cualitativo' else '📊 Cuantitativo'
            )
            
            fig = px.bar(
                promedio_kpi,
                x='Puntuación',
                y='KPI',
                orientation='h',
                title='Puntuación por KPI (mayor = mejor)',
                text='Puntuación',
                color='Tipo_texto',
                hover_data=['Evaluaciones']
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(height=max(400, len(promedio_kpi) * 25))
            st.plotly_chart(fig, use_container_width=True)
            
            # Matriz de calor
            st.markdown("---")
            st.subheader("📊 Matriz: KPI vs Integrante")
            
            pivot_data = df_eval.pivot_table(
                values='puntuacion_invertida',
                index='kpi_nombre',
                columns='integrante',
                aggfunc='mean'
            ).round(2)
            
            fig_heatmap = px.imshow(
                pivot_data,
                labels=dict(x="Integrante", y="KPI", color="Puntuación"),
                title="Mapa de Calor: Puntuación Promedio (mayor = mejor)",
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green'],
                aspect='auto'
            )
            fig_heatmap.update_xaxes(side="bottom")
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Análisis de KPIs Cuantitativos
            df_cuantitativo = df_eval[df_eval['kpi_tipo'] == 'cuantitativo']
            if len(df_cuantitativo) > 0:
                st.markdown("---")
                st.subheader("📊 Análisis de KPIs Cuantitativos (% de Cumplimiento)")
                
                promedio_cumplimiento = df_cuantitativo.groupby('kpi_nombre')['valor_cuantitativo'].mean().reset_index()
                promedio_cumplimiento.columns = ['KPI', 'Cumplimiento Promedio (%)']
                promedio_cumplimiento = promedio_cumplimiento.sort_values('Cumplimiento Promedio (%)', ascending=False)
                
                fig_cumpl = px.bar(
                    promedio_cumplimiento,
                    x='Cumplimiento Promedio (%)',
                    y='KPI',
                    orientation='h',
                    title='Cumplimiento Promedio de Objetivos (%)',
                    text='Cumplimiento Promedio (%)',
                    color='Cumplimiento Promedio (%)',
                    color_continuous_scale=['red', 'orange', 'lightgreen', 'green']
                )
                fig_cumpl.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig_cumpl, use_container_width=True)
        
        # ==================== TAB 5: HISTÓRICO ====================
        with tab5:
            st.subheader("📅 Tendencia Histórica")
            
            df_eval['fecha_evaluacion'] = pd.to_datetime(df_eval['fecha_evaluacion'])
            
            # Tendencia general
            tendencia = df_eval.groupby('fecha_evaluacion')['puntuacion_invertida'].mean().reset_index()
            
            fig = px.line(
                tendencia,
                x='fecha_evaluacion',
                y='puntuacion_invertida',
                title='Tendencia de Puntuación Promedio (mayor = mejor)',
                markers=True
            )
            fig.update_yaxes(range=[0.5, 4.5], title='Puntuación Promedio')
            fig.update_xaxes(title='Fecha')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tendencia por equipo
            st.markdown("---")
            st.subheader("📈 Evolución por Equipo")
            
            tendencia_equipo = df_eval.groupby(['fecha_evaluacion', 'equipo_nombre'])['puntuacion_invertida'].mean().reset_index()
            
            fig_tend_eq = px.line(
                tendencia_equipo,
                x='fecha_evaluacion',
                y='puntuacion_invertida',
                color='equipo_nombre',
                title='Evolución de Puntuación por Equipo (mayor = mejor)',
                markers=True
            )
            fig_tend_eq.update_yaxes(range=[0.5, 4.5], title='Puntuación Promedio')
            fig_tend_eq.update_xaxes(title='Fecha')
            st.plotly_chart(fig_tend_eq, use_container_width=True)
            
            # Tendencia por integrante
            st.markdown("---")
            st.subheader("📈 Evolución por Integrante")
            
            tendencia_int = df_eval.groupby(['fecha_evaluacion', 'integrante'])['puntuacion_invertida'].mean().reset_index()
            
            fig_tend_int = px.line(
                tendencia_int,
                x='fecha_evaluacion',
                y='puntuacion_invertida',
                color='integrante',
                title='Evolución de Puntuación por Integrante (mayor = mejor)',
                markers=True
            )
            fig_tend_int.update_yaxes(range=[0.5, 4.5], title='Puntuación Promedio')
            fig_tend_int.update_xaxes(title='Fecha')
            st.plotly_chart(fig_tend_int, use_container_width=True)
            
            # Tendencia Cualitativos vs Cuantitativos
            st.markdown("---")
            st.subheader("🎭 vs 📊 Evolución por Tipo de KPI")
            
            tendencia_tipo = df_eval.groupby(['fecha_evaluacion', 'kpi_tipo'])['puntuacion_invertida'].mean().reset_index()
            tendencia_tipo['tipo_texto'] = tendencia_tipo['kpi_tipo'].apply(
                lambda x: 'Soft Skills' if x == 'cualitativo' else 'Objetivos'
            )
            
            fig_tend_tipo = px.line(
                tendencia_tipo,
                x='fecha_evaluacion',
                y='puntuacion_invertida',
                color='tipo_texto',
                title='Evolución: Soft Skills vs Objetivos',
                markers=True
            )
            fig_tend_tipo.update_yaxes(range=[0.5, 4.5], title='Puntuación Promedio')
            fig_tend_tipo.update_xaxes(title='Fecha')
            st.plotly_chart(fig_tend_tipo, use_container_width=True)
        
        # ==================== TAB 6: ANÁLISIS DE RIESGOS ====================
        with tab6:
            st.subheader("⚠️ Análisis de Riesgos y Alertas")
            
            # Alertas por equipo
            st.markdown("### 🚨 Alertas por Equipo")
            
            promedio_equipo_riesgo = df_eval.groupby('equipo_nombre')['puntuacion_invertida'].mean().reset_index()
            equipos_riesgo = promedio_equipo_riesgo[promedio_equipo_riesgo['puntuacion_invertida'] < 2.5]
            
            if len(equipos_riesgo) > 0:
                st.error(f"⚠️ **{len(equipos_riesgo)} equipo(s) con desempeño bajo**")
                for _, row in equipos_riesgo.iterrows():
                    st.warning(f"🏢 **{row['equipo_nombre']}** - Puntuación: {row['puntuacion_invertida']:.2f}")
            else:
                st.success("✅ Todos los equipos tienen buen desempeño")
            
            st.markdown("---")
            
            # Integrantes en riesgo
            st.markdown("### 🚨 Integrantes que Necesitan Atención")
            
            promedio_integrante_riesgo = df_eval.groupby(['integrante', 'equipo_nombre'])['puntuacion_invertida'].mean().reset_index()
            integrantes_riesgo = promedio_integrante_riesgo[promedio_integrante_riesgo['puntuacion_invertida'] < 2.0]
            
            if len(integrantes_riesgo) > 0:
                st.error(f"⚠️ **{len(integrantes_riesgo)} integrante(s) con desempeño bajo**")
                
                for _, row in integrantes_riesgo.iterrows():
                    calificacion_original = 5 - row['puntuacion_invertida']
                    st.warning(f"🔴 **{row['integrante']}** ({row['equipo_nombre']}) - Puntuación: {row['puntuacion_invertida']:.2f}")
            else:
                st.success("✅ No hay integrantes en zona de riesgo crítico")
            
            st.markdown("---")
            
            # KPIs problemáticos
            st.markdown("### 📉 KPIs con Bajo Rendimiento")
            
            promedio_kpi_riesgo = df_eval.groupby(['kpi_nombre', 'kpi_tipo'])['puntuacion_invertida'].mean().reset_index()
            kpis_riesgo = promedio_kpi_riesgo[promedio_kpi_riesgo['puntuacion_invertida'] < 2.5]
            
            if len(kpis_riesgo) > 0:
                kpis_riesgo = kpis_riesgo.sort_values('puntuacion_invertida', ascending=True)
                kpis_riesgo['Tipo_texto'] = kpis_riesgo['kpi_tipo'].apply(
                    lambda x: '🎭 Cualitativo' if x == 'cualitativo' else '📊 Cuantitativo'
                )
                
                fig_riesgo_kpi = px.bar(
                    kpis_riesgo,
                    x='puntuacion_invertida',
                    y='kpi_nombre',
                    orientation='h',
                    title='KPIs que Requieren Atención (menor puntuación = peor)',
                    text='puntuacion_invertida',
                    color='Tipo_texto',
                    hover_data=['Tipo_texto']
                )
                fig_riesgo_kpi.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig_riesgo_kpi, use_container_width=True)
            else:
                st.success("✅ Todos los KPIs tienen buen desempeño")
            
            st.markdown("---")
            
            # Análisis detallado por tipo de KPI
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🎭 Riesgos en Soft Skills")
                df_cualitativo = df_eval[df_eval['kpi_tipo'] == 'cualitativo']
                if len(df_cualitativo) > 0:
                    riesgo_cualitativo = df_cualitativo[df_cualitativo['calificacion'] >= 3]
                    if len(riesgo_cualitativo) > 0:
                        st.warning(f"⚠️ {len(riesgo_cualitativo)} evaluaciones bajas en soft skills")
                        
                        kpis_cual_problema = riesgo_cualitativo.groupby('kpi_nombre').size().reset_index(name='cantidad')
                        kpis_cual_problema = kpis_cual_problema.sort_values('cantidad', ascending=False).head(5)
                        
                        for _, row in kpis_cual_problema.iterrows():
                            st.write(f"- **{row['kpi_nombre']}**: {row['cantidad']} evaluaciones bajas")
                    else:
                        st.success("✅ Sin problemas en soft skills")
                else:
                    st.info("No hay evaluaciones de soft skills")
            
            with col2:
                st.markdown("### 📊 Riesgos en Objetivos")
                df_cuantitativo = df_eval[df_eval['kpi_tipo'] == 'cuantitativo']
                if len(df_cuantitativo) > 0:
                    riesgo_cuantitativo = df_cuantitativo[df_cuantitativo['calificacion'] >= 3]
                    if len(riesgo_cuantitativo) > 0:
                        st.warning(f"⚠️ {len(riesgo_cuantitativo)} objetivos no cumplidos")
                        
                        kpis_cuant_problema = riesgo_cuantitativo.groupby('kpi_nombre').size().reset_index(name='cantidad')
                        kpis_cuant_problema = kpis_cuant_problema.sort_values('cantidad', ascending=False).head(5)
                        
                        for _, row in kpis_cuant_problema.iterrows():
                            promedio_cumpl = df_cuantitativo[df_cuantitativo['kpi_nombre']==row['kpi_nombre']]['valor_cuantitativo'].mean()
                            st.write(f"- **{row['kpi_nombre']}**: {promedio_cumpl:.1f}% cumplimiento promedio")
                    else:
                        st.success("✅ Todos los objetivos cumplidos")
                else:
                    st.info("No hay evaluaciones de objetivos")
            
            st.markdown("---")
            
            # Análisis detallado de personas en riesgo
            st.markdown("### 🔍 Análisis Detallado de Integrantes en Riesgo")
            
            promedio_integrante_analisis = df_eval.groupby(['integrante', 'equipo_nombre']).agg({
                'puntuacion_invertida': 'mean'
            }).reset_index()
            peores_3 = promedio_integrante_analisis.sort_values('puntuacion_invertida', ascending=True).head(3)
            
            for idx, row in peores_3.iterrows():
                with st.expander(f"📋 {row['integrante']} ({row['equipo_nombre']}) - Puntuación: {row['puntuacion_invertida']:.2f}", expanded=idx==0):
                    df_integrante = df_eval[df_eval['integrante'] == row['integrante']]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🎭 Soft Skills:**")
                        df_cual = df_integrante[df_integrante['kpi_tipo'] == 'cualitativo']
                        if len(df_cual) > 0:
                            problemas_cual = df_cual[df_cual['calificacion'] >= 3]
                            if len(problemas_cual) > 0:
                                for _, eval_row in problemas_cual.iterrows():
                                    st.write(f"❌ {eval_row['kpi_nombre']}: {CALIFICACIONES[eval_row['calificacion']]}")
                                    if eval_row['comentario']:
                                        st.caption(f"💬 {eval_row['comentario']}")
                            else:
                                st.success("✅ Soft skills OK")
                        else:
                            st.info("Sin evaluaciones")
                    
                    with col2:
                        st.markdown("**📊 Objetivos:**")
                        df_cuant = df_integrante[df_integrante['kpi_tipo'] == 'cuantitativo']
                        if len(df_cuant) > 0:
                            problemas_cuant = df_cuant[df_cuant['calificacion'] >= 3]
                            if len(problemas_cuant) > 0:
                                for _, eval_row in problemas_cuant.iterrows():
                                    st.write(f"❌ {eval_row['kpi_nombre']}: {eval_row['valor_cuantitativo']:.1f}% - {CALIFICACIONES[eval_row['calificacion']]}")
                                    if eval_row['comentario']:
                                        st.caption(f"💬 {eval_row['comentario']}")
                            else:
                                st.success("✅ Objetivos OK")
                        else:
                            st.info("Sin evaluaciones")
                    
                    # Evolución temporal
                    st.markdown("**📈 Evolución temporal:**")
                    df_evo = df_integrante.sort_values('fecha_evaluacion')
                    if len(df_evo) > 1:
                        fig_evo = px.line(
                            df_evo, 
                            x='fecha_evaluacion', 
                            y='puntuacion_invertida',
                            title=f'Evolución de {row["integrante"]}',
                            markers=True
                        )
                        fig_evo.update_yaxes(range=[0.5, 4.5], title='Puntuación (mayor = mejor)')
                        fig_evo.update_xaxes(title='Fecha')
                        st.plotly_chart(fig_evo, use_container_width=True)
                    else:
                        st.info("Se necesitan más evaluaciones para ver la evolución")
            
            st.markdown("---")
            
            # Métricas de riesgo
            st.markdown("### 📊 Indicadores de Riesgo Globales")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_deficiente = len(df_eval[df_eval['calificacion'] == 4])
                pct_deficiente = (total_deficiente / len(df_eval) * 100) if len(df_eval) > 0 else 0
                st.metric(
                    "❌ Evaluaciones Deficientes",
                    f"{total_deficiente}",
                    f"{pct_deficiente:.1f}%",
                    delta_color="inverse"
                )
            
            with col2:
                total_regular = len(df_eval[df_eval['calificacion'] == 3])
                pct_regular = (total_regular / len(df_eval) * 100) if len(df_eval) > 0 else 0
                st.metric(
                    "⚠️ Evaluaciones Regulares",
                    f"{total_regular}",
                    f"{pct_regular:.1f}%",
                    delta_color="inverse"
                )
            
            with col3:
                riesgo_total = total_deficiente + total_regular
                pct_riesgo = (riesgo_total / len(df_eval) * 100) if len(df_eval) > 0 else 0
                st.metric(
                    "🚨 Total en Riesgo",
                    f"{riesgo_total}",
                    f"{pct_riesgo:.1f}%",
                    delta_color="inverse"
                )
            
            with col4:
                # Objetivos no cumplidos (<75%)
                if len(df_cuantitativo) > 0:
                    obj_no_cumplidos = len(df_cuantitativo[df_cuantitativo['valor_cuantitativo'] < 75])
                    pct_obj = (obj_no_cumplidos / len(df_cuantitativo) * 100) if len(df_cuantitativo) > 0 else 0
                    st.metric(
                        "📉 Objetivos <75%",
                        f"{obj_no_cumplidos}",
                        f"{pct_obj:.1f}%",
                        delta_color="inverse"
                    )
                else:
                    st.metric("📉 Objetivos <75%", "N/A")
        
        st.markdown("---")
        st.subheader("📋 Últimas Evaluaciones")
        
        df_display = df_eval[[
            'fecha_evaluacion', 
            'equipo_nombre',
            'integrante', 
            'kpi_nombre',
            'tipo_kpi_texto',
            'calificacion_texto',
            'valor_cuantitativo',
            'evaluador', 
            'comentario'
        ]].head(30)
        
        # Formatear valor cuantitativo
        df_display['valor_cuantitativo'] = df_display['valor_cuantitativo'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
        
        st.dataframe(
            df_display,
            column_config={
                "fecha_evaluacion": "Fecha",
                "equipo_nombre": "Equipo",
                "integrante": "Integrante",
                "kpi_nombre": "KPI",
                "tipo_kpi_texto": "Tipo",
                "calificacion_texto": "Calificación",
                "valor_cuantitativo": "Cumplimiento",
                "evaluador": "Evaluador",
                "comentario": "Comentario"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("📭 No hay evaluaciones registradas en el período seleccionado")

st.sidebar.markdown("---")
st.sidebar.caption("💡 Sistema de KPIs")
st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")