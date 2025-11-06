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
        host="localhost",
        database="kpi",
        user="postgres",
        password="postgres"
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

# Funciones CRUD para Integrantes
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
    if solo_activos:
        cur.execute("SELECT * FROM integrantes WHERE activo = TRUE ORDER BY nombre")
    else:
        cur.execute("SELECT * FROM integrantes ORDER BY nombre")
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_integrante(integrante_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE integrantes SET activo = FALSE WHERE id = %s", (integrante_id,))
    conn.commit()
    cur.close()

# Funciones CRUD para KPIs
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
    if solo_activos:
        cur.execute("SELECT * FROM kpis WHERE activo = TRUE ORDER BY nombre")
    else:
        cur.execute("SELECT * FROM kpis ORDER BY nombre")
    result = cur.fetchall()
    cur.close()
    return result

def desactivar_kpi(kpi_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE kpis SET activo = FALSE WHERE id = %s", (kpi_id,))
    conn.commit()
    cur.close()

# Funciones para Evaluaciones
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

# Mapeo de calificaciones (de MEJOR a PEOR)
CALIFICACIONES = {
    1: "⭐ Excelente",
    2: "👍 Bueno", 
    3: "⚠️ Regular",
    4: "❌ Deficiente"
}

# Función para calcular puntuación invertida (mayor = mejor)
def calcular_puntuacion_invertida(calificacion):
    # Invertimos la escala: 1 se convierte en 4, 2 en 3, 3 en 2, 4 en 1
    return 5 - calificacion

# Inicializar base de datos
init_db()

# Sidebar - Navegación
st.sidebar.title("📊 Sistema de KPIs")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegación",
    ["📝 Nueva Evaluación", "👥 Gestión de Integrantes", "📋 Gestión de KPIs", "📈 Reportes y Análisis"]
)

# PÁGINA: Nueva Evaluación
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
            st.info(f"📊 Total de KPIs activos: {len(kpis)}")
    
    if integrantes and kpis and evaluador:
        st.markdown("---")
        st.subheader("Calificaciones")
        
        evaluaciones_temp = {}
        
        for kpi in kpis:
            with st.expander(f"📌 {kpi['nombre']}", expanded=True):
                if kpi['descripcion']:
                    st.caption(kpi['descripcion'])
                
                col_cal, col_com = st.columns([1, 2])
                
                with col_cal:
                    calificacion = st.radio(
                        "Calificación",
                        options=[1, 2, 3, 4],
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
                
                evaluaciones_temp[kpi['id']] = {
                    'calificacion': calificacion,
                    'comentario': comentario
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
                            datos['comentario']
                        )
                    st.success(f"✅ Evaluación de {integrante_seleccionado} guardada exitosamente!")
                    st.balloons()
                    st.session_state.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")
        
        with col_btn2:
            if st.button("🔄 Limpiar", use_container_width=True):
                st.session_state.clear()
                st.rerun()

# PÁGINA: Gestión de Integrantes
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
                rol = st.text_input("Rol/Posición", placeholder="Ej: Senior Developer, Tech Lead")
            
            submitted = st.form_submit_button("➕ Agregar Integrante", type="primary", use_container_width=True)
            
            if submitted:
                if nombre:
                    try:
                        agregar_integrante(nombre, rol)
                        st.session_state.mensaje_integrante = f"✅ Integrante '{nombre}' agregado exitosamente!"
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ El nombre es obligatorio")
    
    with tab2:
        st.subheader("Integrantes Registrados")
        
        mostrar_inactivos = st.checkbox("Mostrar integrantes inactivos")
        integrantes = obtener_integrantes(solo_activos=not mostrar_inactivos)
        
        if integrantes:
            df = pd.DataFrame(integrantes)
            df['Estado'] = df['activo'].apply(lambda x: '✅ Activo' if x else '❌ Inactivo')
            
            st.dataframe(
                df[['nombre', 'rol', 'Estado', 'fecha_creacion']],
                column_config={
                    "nombre": "Nombre",
                    "rol": "Rol",
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
                integrante_options = {i['nombre']: i['id'] for i in integrantes_activos}
                integrante_desactivar = st.selectbox(
                    "Seleccionar integrante a desactivar",
                    options=list(integrante_options.keys())
                )
                
                if st.button("❌ Desactivar", type="secondary"):
                    try:
                        desactivar_integrante(integrante_options[integrante_desactivar])
                        st.success(f"✅ Integrante '{integrante_desactivar}' desactivado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No hay integrantes registrados")

# PÁGINA: Gestión de KPIs
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
            nombre_kpi = st.text_input("Nombre del KPI", placeholder="Ej: Calidad del Código")
            descripcion_kpi = st.text_area(
                "Descripción (opcional)",
                placeholder="Describe qué se evalúa en este KPI"
            )
            
            submitted = st.form_submit_button("➕ Agregar KPI", type="primary", use_container_width=True)
            
            if submitted:
                if nombre_kpi:
                    try:
                        agregar_kpi(nombre_kpi, descripcion_kpi)
                        st.session_state.mensaje_kpi = f"✅ KPI '{nombre_kpi}' agregado exitosamente!"
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
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
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        else:
            st.info("No hay KPIs registrados")

# PÁGINA: Reportes y Análisis
elif menu == "📈 Reportes y Análisis":
    st.title("📈 Reportes y Análisis de Desempeño")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=date.today().replace(day=1))
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=date.today())
    
    evaluaciones = obtener_evaluaciones(fecha_inicio, fecha_fin)
    
    if evaluaciones:
        df_eval = pd.DataFrame(evaluaciones)
        df_eval['calificacion_texto'] = df_eval['calificacion'].map(CALIFICACIONES)
        
        # Calcular puntuación invertida para ranking (mayor = mejor)
        df_eval['puntuacion_invertida'] = df_eval['calificacion'].apply(calcular_puntuacion_invertida)
        
        # Métricas generales
        st.subheader("📊 Resumen General")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Evaluaciones", len(df_eval))
        with col2:
            # Usar puntuación invertida para el promedio (mayor = mejor)
            promedio_invertido = df_eval['puntuacion_invertida'].mean()
            st.metric("Puntuación Promedio", f"{promedio_invertido:.2f}")
        with col3:
            excelentes = len(df_eval[df_eval['calificacion'] == 1])
            st.metric("⭐ Excelentes", excelentes)
        with col4:
            deficientes = len(df_eval[df_eval['calificacion'] == 4])
            st.metric("❌ Deficientes", deficientes)
        
        st.markdown("---")
        
        # Gráficos
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏆 Ranking General", 
            "👥 Por Integrante", 
            "📋 Por KPI", 
            "📅 Histórico",
            "⚠️ Análisis de Riesgos"
        ])
        
        with tab1:
            st.subheader("🏆 Ranking General de Desempeño")
            
            # Calcular promedio de PUNTUACIÓN INVERTIDA por integrante (mayor = mejor)
            promedio_integrante = df_eval.groupby('integrante').agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_integrante.columns = ['Integrante', 'Puntuación', 'Total Evaluaciones']
            
            # Ordenar por puntuación invertida (mayor primero = mejores primero)
            promedio_integrante = promedio_integrante.sort_values('Puntuación', ascending=False)
            promedio_integrante['Posición'] = range(1, len(promedio_integrante) + 1)
            
            # Categorizar desempeño basado en puntuación invertida
            promedio_integrante['Desempeño'] = promedio_integrante['Puntuación'].apply(
                lambda x: '⭐ Excelente' if x >= 3.5 else ('👍 Bueno' if x >= 2.5 else ('⚠️ Regular' if x >= 1.5 else '❌ Deficiente'))
            )
            
            # Tabla de ranking general
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_ranking = go.Figure()
                
                colors = promedio_integrante['Puntuación'].apply(
                    lambda x: 'green' if x >= 3.5 else ('lightgreen' if x >= 2.5 else ('orange' if x >= 1.5 else 'red'))
                )
                
                fig_ranking.add_trace(go.Bar(
                    y=promedio_integrante['Integrante'],
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
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_ranking, use_container_width=True)
            
            with col2:
                st.markdown("### 🏅 Top Mejores")
                for idx, row in promedio_integrante.head(5).iterrows():
                    emoji = "🥇" if row['Posición'] == 1 else ("🥈" if row['Posición'] == 2 else ("🥉" if row['Posición'] == 3 else "📈"))
                    color = "green" if row['Puntuación'] >= 3.5 else ("lightgreen" if row['Puntuación'] >= 2.5 else ("orange" if row['Puntuación'] >= 1.5 else "red"))
                    
                    st.markdown(f"""
                    <div style='background-color: {color}; padding: 10px; margin: 5px 0; border-radius: 5px; color: white;'>
                        {emoji} <b>{row['Posición']}. {row['Integrante']}</b><br>
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
                        Puntuación: {row['Puntuación']:.2f}<br>
                        {row['Desempeño']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Gráfico de torta - Distribución general de calificaciones
            st.markdown("---")
            st.subheader("📊 Distribución General de Calificaciones")
            
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
        
        with tab2:
            st.subheader("👥 Desempeño por Integrante")
            
            # Promedio por integrante usando PUNTUACIÓN INVERTIDA (mejores primero)
            promedio_integrante = df_eval.groupby('integrante').agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_integrante.columns = ['Integrante', 'Puntuación', 'Evaluaciones']
            promedio_integrante = promedio_integrante.sort_values('Puntuación', ascending=False)  # Mayores primero (mejores)
            
            fig = px.bar(
                promedio_integrante,
                x='Puntuación',
                y='Integrante',
                orientation='h',
                title='Puntuación por Integrante (mayor = mejor)',
                text='Puntuación',
                color='Puntuación',
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green']
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Distribución de calificaciones por integrante
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
            
            # Gráfico de torta por integrante
            st.markdown("---")
            st.subheader("📊 Comparación de Distribución por Integrante")
            
            integrantes_list = df_eval['integrante'].unique()
            cols = st.columns(min(3, len(integrantes_list)))
            
            for idx, integrante in enumerate(integrantes_list):
                with cols[idx % 3]:
                    df_integrante = df_eval[df_eval['integrante'] == integrante]
                    dist_integrante = df_integrante['calificacion_texto'].value_counts()
                    
                    fig_pie_int = px.pie(
                        values=dist_integrante.values,
                        names=dist_integrante.index,
                        title=integrante,
                        color=dist_integrante.index,
                        color_discrete_map={
                            '⭐ Excelente': 'green',
                            '👍 Bueno': 'lightgreen',
                            '⚠️ Regular': 'orange',
                            '❌ Deficiente': 'red'
                        }
                    )
                    fig_pie_int.update_traces(textposition='inside', textinfo='percent')
                    fig_pie_int.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig_pie_int, use_container_width=True)
        
        with tab3:
            st.subheader("📋 Desempeño por KPI")
            
            # Usar puntuación invertida para KPIs también
            promedio_kpi = df_eval.groupby('kpi_nombre').agg({
                'puntuacion_invertida': 'mean',
                'calificacion': 'count'
            }).reset_index()
            promedio_kpi.columns = ['KPI', 'Puntuación', 'Evaluaciones']
            promedio_kpi = promedio_kpi.sort_values('Puntuación', ascending=False)  # Mayores primero (mejores KPIs)
            
            fig = px.bar(
                promedio_kpi,
                x='Puntuación',
                y='KPI',
                orientation='h',
                title='Puntuación por KPI (mayor = mejor)',
                text='Puntuación',
                color='Puntuación',
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green']
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Gráfico de barras agrupadas - KPI vs Integrantes
            st.markdown("---")
            st.subheader("📊 Matriz de Calificaciones: KPI vs Integrante")
            
            pivot_data = df_eval.pivot_table(
                values='puntuacion_invertida',
                index='kpi_nombre',
                columns='integrante',
                aggfunc='mean'
            ).round(2)
            
            fig_heatmap = px.imshow(
                pivot_data,
                labels=dict(x="Integrante", y="KPI", color="Puntuación"),
                title="Mapa de Calor: Puntuación Promedio por KPI e Integrante (mayor = mejor)",
                color_continuous_scale=['red', 'orange', 'lightgreen', 'green'],
                aspect='auto'
            )
            fig_heatmap.update_xaxes(side="bottom")
            st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with tab4:
            st.subheader("📅 Tendencia Histórica")
            
            df_eval['fecha_evaluacion'] = pd.to_datetime(df_eval['fecha_evaluacion'])
            
            # Usar puntuación invertida para la tendencia
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
        
        with tab5:
            st.subheader("⚠️ Análisis de Riesgos y Alertas")
            
            # Identificar áreas de riesgo usando PUNTUACIÓN INVERTIDA (baja puntuación = riesgo)
            st.markdown("### 🚨 Alertas de Riesgo")
            
            # Integrantes con bajo desempeño (puntuación invertida baja)
            promedio_integrante = df_eval.groupby('integrante')['puntuacion_invertida'].mean().reset_index()
            integrantes_riesgo = promedio_integrante[promedio_integrante['puntuacion_invertida'] < 2.0]
            
            if len(integrantes_riesgo) > 0:
                st.error(f"⚠️ **{len(integrantes_riesgo)} integrante(s) con desempeño bajo** (puntuación < 2.0)")
                for _, row in integrantes_riesgo.iterrows():
                    # Convertir puntuación invertida a calificación original para mostrar
                    calificacion_original = 5 - row['puntuacion_invertida']
                    st.warning(f"🔴 **{row['integrante']}** - Puntuación: {row['puntuacion_invertida']:.2f} - {CALIFICACIONES[round(calificacion_original)]}")
            else:
                st.success("✅ No hay integrantes en zona de riesgo")
            
            st.markdown("---")
            
            # KPIs problemáticos (puntuación invertida baja)
            st.markdown("### 📉 KPIs con Bajo Desempeño")
            promedio_kpi = df_eval.groupby('kpi_nombre')['puntuacion_invertida'].mean().reset_index()
            kpis_riesgo = promedio_kpi[promedio_kpi['puntuacion_invertida'] < 2.5]
            
            if len(kpis_riesgo) > 0:
                # Ordenar de menor a mayor puntuación (peores primero)
                kpis_riesgo = kpis_riesgo.sort_values('puntuacion_invertida', ascending=True)
                
                fig_riesgo_kpi = px.bar(
                    kpis_riesgo,
                    x='puntuacion_invertida',
                    y='kpi_nombre',
                    orientation='h',
                    title='KPIs que Requieren Atención (menor puntuación = peor)',
                    text='puntuacion_invertida',
                    color='puntuacion_invertida',
                    color_continuous_scale=['red', 'orange']
                )
                fig_riesgo_kpi.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig_riesgo_kpi, use_container_width=True)
            else:
                st.success("✅ Todos los KPIs tienen buen desempeño")
            
            st.markdown("---")
            
            # Análisis detallado de los que necesitan mejora
            st.markdown("### 🔍 Análisis Detallado de los que Necesitan Mejora")
            
            # Tomar los 3 peores integrantes (menor puntuación invertida)
            promedio_integrante_peores = df_eval.groupby('integrante')['puntuacion_invertida'].mean().reset_index()
            promedio_integrante_peores = promedio_integrante_peores.sort_values('puntuacion_invertida', ascending=True).head(3)
            
            for idx, row in promedio_integrante_peores.iterrows():
                with st.expander(f"📋 Análisis de {row['integrante']} (Puntuación: {row['puntuacion_invertida']:.2f})", expanded=idx==0):
                    df_integrante = df_eval[df_eval['integrante'] == row['integrante']]
                    
                    # KPIs problemáticos (calificación original 3 o 4)
                    kpis_problematicos = df_integrante[df_integrante['calificacion'] >= 3]
                    
                    if len(kpis_problematicos) > 0:
                        st.warning(f"**KPIs que necesitan mejora:** {len(kpis_problematicos)}")
                        
                        for _, eval_row in kpis_problematicos.iterrows():
                            col_kpi1, col_kpi2 = st.columns([2, 1])
                            with col_kpi1:
                                st.write(f"**{eval_row['kpi_nombre']}** - {CALIFICACIONES[eval_row['calificacion']]}")
                            with col_kpi2:
                                if eval_row['comentario']:
                                    st.info(f"💬 {eval_row['comentario']}")
                    else:
                        st.success("✅ No hay KPIs críticos")
                    
                    # Evolución temporal
                    st.write("**Evolución temporal:**")
                    df_evo = df_integrante.sort_values('fecha_evaluacion')
                    if len(df_evo) > 1:
                        # Usar puntuación invertida para la evolución también
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
            
            st.markdown("---")
            
            # Indicadores de riesgo
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_deficiente = len(df_eval[df_eval['calificacion'] == 4])
                pct_deficiente = (total_deficiente / len(df_eval) * 100) if len(df_eval) > 0 else 0
                st.metric(
                    "📊 Evaluaciones Deficientes",
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
        
        st.markdown("---")
        st.subheader("📋 Últimas Evaluaciones")
        
        df_display = df_eval[['fecha_evaluacion', 'integrante', 'kpi_nombre', 'calificacion_texto', 'evaluador', 'comentario']].head(20)
        st.dataframe(
            df_display,
            column_config={
                "fecha_evaluacion": "Fecha",
                "integrante": "Integrante",
                "kpi_nombre": "KPI",
                "calificacion_texto": "Calificación",
                "evaluador": "Evaluador",
                "comentario": "Comentario"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("📭 No hay evaluaciones registradas en el período seleccionado")

st.sidebar.markdown("---")
st.sidebar.caption("💡 KPI Metrics")
st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")