from modules.rii import convertir_likert, calcular_rii_desde_respuestas
import streamlit as st
import pandas as pd
import plotly.express as px

from modules.evaluacion import (
    obtener_tfn_calificacion,
    defuzzificar_tfn,
    calcular_criticidad,
)

from modules.fahp import (
    generar_pares_criterios,
    obtener_tfn,
    construir_matriz_difusa,
    matriz_central_para_cr,
    calcular_pesos_crisp,
    calcular_cr,
    detectar_inconsistencias_fuertes,
    calcular_pesos_globales_fahp,
)

from modules.db import (
    guardar_respuestas,
    leer_respuestas,
    guardar_respuestas_fahp,
    leer_respuestas_fahp,
    guardar_respuestas_evaluacion,
    leer_respuestas_evaluacion,
    experto_tiene_respuestas,
    eliminar_respuestas_experto,
)

def mostrar_tabla_riesgos(df):
    html = df.to_html(
        index=False,
        escape=False,
        classes="tabla-riesgos"
    )

    tabla_html = f"""
    <style>
    table.tabla-riesgos {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 15px;
        background-color: #ffffff;
        color: #111827;
    }}

    table.tabla-riesgos th {{
        background-color: #1f2937;
        color: #ffffff;
        padding: 10px;
        border: 1px solid #d1d5db;
        text-align: left;
        font-weight: bold;
        white-space: normal;
    }}

    table.tabla-riesgos td {{
        padding: 10px;
        border: 1px solid #d1d5db;
        vertical-align: top;
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
        line-height: 1.45;
        color: #111827;
    }}

    table.tabla-riesgos tr:nth-child(even) {{
        background-color: #f9fafb;
    }}

    table.tabla-riesgos tr:nth-child(odd) {{
        background-color: #ffffff;
    }}

    table.tabla-riesgos th:nth-child(1),
    table.tabla-riesgos td:nth-child(1) {{
        width: 7%;
    }}

    table.tabla-riesgos th:nth-child(2),
    table.tabla-riesgos td:nth-child(2) {{
        width: 33%;
    }}

    table.tabla-riesgos th:nth-child(3),
    table.tabla-riesgos td:nth-child(3) {{
        width: 60%;
    }}
    </style>

    {html}
    """

    st.html(tabla_html)

def mostrar_tabla_criterios(df):
    html = df.to_html(
        index=False,
        escape=False,
        classes="tabla-criterios"
    )

    tabla_html = f"""
    <style>
    table.tabla-criterios {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 15px;
        background-color: #ffffff;
        color: #111827;
    }}

    table.tabla-criterios th {{
        background-color: #1f2937;
        color: #ffffff;
        padding: 10px;
        border: 1px solid #d1d5db;
        text-align: left;
        font-weight: bold;
        white-space: normal;
    }}

    table.tabla-criterios td {{
        padding: 10px;
        border: 1px solid #d1d5db;
        vertical-align: top;
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
        line-height: 1.45;
        color: #111827;
    }}

    table.tabla-criterios tr:nth-child(even) {{
        background-color: #f9fafb;
    }}

    table.tabla-criterios tr:nth-child(odd) {{
        background-color: #ffffff;
    }}

    table.tabla-criterios th:nth-child(1),
    table.tabla-criterios td:nth-child(1) {{
        width: 7%;
    }}

    table.tabla-criterios th:nth-child(2),
    table.tabla-criterios td:nth-child(2) {{
        width: 23%;
    }}

    table.tabla-criterios th:nth-child(3),
    table.tabla-criterios td:nth-child(3) {{
        width: 25%;
    }}

    table.tabla-criterios th:nth-child(4),
    table.tabla-criterios td:nth-child(4) {{
        width: 45%;
    }}
    </style>

    {html}
    """

    st.html(tabla_html)

def mostrar_ranking_global():
    st.header("Ranking global actual de riesgos críticos")

    st.write(
        "Este ranking se calcula con las respuestas registradas hasta el momento "
        "por los expertos en la plataforma."
    )

    # Leer respuestas globales de evaluación riesgo-criterio
    respuestas_eval_global = leer_respuestas_evaluacion()

    if respuestas_eval_global.empty:
        st.warning("Todavía no hay evaluaciones riesgo-criterio registradas.")
        return

    # Leer respuestas FAHP globales
    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp_global = leer_respuestas_fahp()

    if respuestas_fahp_global.empty:
        st.warning("Todavía no hay respuestas FAHP registradas.")
        return

    # Calcular pesos globales FAHP
    df_pesos_globales, matriz_texto_global, matriz_crisp_global, lambda_max, ci, cr, ri = (
        calcular_pesos_globales_fahp(
            criterios=criterios,
            respuestas_fahp=respuestas_fahp_global
        )
    )

    st.subheader("Pesos globales de criterios")
    st.dataframe(df_pesos_globales, width="stretch")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Lambda máx.", f"{lambda_max:.4f}")
    col2.metric("CI", f"{ci:.4f}")
    col3.metric("RI", f"{ri:.2f}")
    col4.metric("CR global", f"{cr:.4f}")

    if cr <= 0.30:
        st.success(f"Matriz FAHP global aceptable: CR = {cr:.4f}")
    else:
        st.warning(f"Matriz FAHP global con CR = {cr:.4f}. Revisar consistencia global.")

    # Calcular ranking global
    ranking_global = calcular_criticidad(
        respuestas_evaluacion=respuestas_eval_global,
        pesos_criterios=df_pesos_globales
    )

    # Ordenar ranking global una sola vez
    ranking_global = ranking_global.sort_values(
        "puntaje_criticidad",
        ascending=False
    ).reset_index(drop=True)

    ranking_global["puntaje_criticidad"] = ranking_global["puntaje_criticidad"].round(4)

    # Agregar columna Ranking
    ranking_global.insert(0, "Ranking", range(1, len(ranking_global) + 1))

    st.subheader("Ranking global de riesgos críticos")

    # Resumen ejecutivo
    if len(ranking_global) >= 1:
        top1 = ranking_global.iloc[0]

        st.markdown(f"""
### Resumen ejecutivo

**Riesgo más crítico:**  
{top1['codigo_riesgo']} - {top1['riesgo']}

**Puntaje de criticidad:** {top1['puntaje_criticidad']}
""")

    if len(ranking_global) >= 3:
        top2 = ranking_global.iloc[1]
        top3 = ranking_global.iloc[2]

        st.markdown(f"""
**Segundo riesgo crítico:**  
{top2['codigo_riesgo']} - {top2['riesgo']}

**Tercer riesgo crítico:**  
{top3['codigo_riesgo']} - {top3['riesgo']}
""")

    # Tabla completa
    st.dataframe(ranking_global, width="stretch")

    # Gráfico horizontal Top 5
    st.subheader("Top 5 riesgos críticos")

    top5 = ranking_global.head(5)

    fig = graficar_ranking_riesgos(top5)
    st.plotly_chart(fig, use_container_width=True)

    csv = ranking_global.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar ranking global",
        data=csv,
        file_name="ranking_global_riesgos_criticos.csv",
        mime="text/csv"
    )


def graficar_ranking_riesgos(ranking_df):
    df = ranking_df.copy()

    # Asegurar orden de mayor a menor
    df = df.sort_values("puntaje_criticidad", ascending=False).reset_index(drop=True)

    def resumir_texto(texto, max_len=75):
        texto = str(texto)
        if len(texto) <= max_len:
            return texto
        return texto[:max_len] + "..."

    codigo_col = "codigo_riesgo" if "codigo_riesgo" in df.columns else None

    if codigo_col:
        df["etiqueta_grafico"] = df.apply(
            lambda x: f"{x[codigo_col]} - {resumir_texto(x['riesgo'])}",
            axis=1
        )
    else:
        df["etiqueta_grafico"] = df["riesgo"].apply(resumir_texto)

    # Para que el mayor aparezca arriba en barras horizontales
    df = df.sort_values("puntaje_criticidad", ascending=True)

    fig = px.bar(
        df,
        x="puntaje_criticidad",
        y="etiqueta_grafico",
        orientation="h",
        text="puntaje_criticidad",
        title="Top 5 riesgos críticos"
    )

    fig.update_traces(
        texttemplate="%{text:.4f}",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Puntaje: %{x:.4f}<extra></extra>"
    )

    fig.update_layout(
        xaxis_title="Puntaje de criticidad",
        yaxis_title="",
        height=max(450, 60 * len(df)),
        margin=dict(l=120, r=40, t=60, b=20),
        title_x=0.02
    )

    return fig




st.set_page_config(
    page_title="Modelo de riesgos de cierre de mina",
    layout="wide"
)

st.title("Modelo multicriterio para riesgos críticos")
st.subheader("Proyecto de diseño de cierre de mina")

st.markdown("""
Esta plataforma permite registrar el juicio experto para la priorización de riesgos críticos
en un proyecto de diseño de cierre de mina. El proceso se desarrolla de manera secuencial:
primero se califican los riesgos mediante escala Likert, luego se comparan los criterios mediante
FAHP y finalmente se evalúan los riesgos frente a los criterios ponderados.
""")

if "paso" not in st.session_state:
    st.session_state["paso"] = 1

if "experto" not in st.session_state:
    st.session_state["experto"] = ""

if "modo" not in st.session_state:
    st.session_state["modo"] = ""

if not st.session_state["modo"]:

    st.header("Seleccione una opción")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Completar encuesta")
        st.write(
            "Ingrese como experto para responder la evaluación Likert, la comparación FAHP "
            "y la evaluación riesgo-criterio."
        )

        if st.button("Iniciar encuesta como experto"):
            st.session_state["modo"] = "encuesta"
            st.rerun()

    with col2:
        st.subheader("Ver ranking global")
        st.write(
            "Consulte el ranking global de riesgos críticos calculado con las respuestas "
            "registradas hasta el momento."
        )

        if st.button("Mostrar ranking global actual"):
            st.session_state["modo"] = "ranking"
            st.rerun()

    st.stop()

if st.session_state["modo"] == "ranking":

    if st.button("Volver al inicio"):
        st.session_state["modo"] = ""
        st.session_state["experto"] = ""
        st.session_state["paso"] = 1
        st.rerun()

    mostrar_ranking_global()
    st.stop()

if not st.session_state["experto"]:

    st.header("Identificación del experto")

    experto_input = st.text_input(
        "Ingrese su nombre o código de experto",
        placeholder="Ejemplo: E01, Especialista Geotecnia, Experto 1"
    )

    if experto_input.strip():

        experto_normalizado = experto_input.strip()

        estado_respuestas = experto_tiene_respuestas(experto_normalizado)

        if estado_respuestas["alguna"]:

            st.warning(
                "Este experto ya registra respuestas anteriores en la plataforma. "
                "Si continúa, se eliminarán sus respuestas anteriores y serán reemplazadas por las nuevas."
            )

            st.write("Respuestas existentes detectadas:")

            st.write(f"- Encuesta Likert de riesgos: {'Sí' if estado_respuestas['rii'] else 'No'}")
            st.write(f"- Comparación FAHP de criterios: {'Sí' if estado_respuestas['fahp'] else 'No'}")
            st.write(f"- Evaluación riesgo-criterio: {'Sí' if estado_respuestas['evaluacion'] else 'No'}")

            confirmar_reemplazo = st.checkbox(
                "Confirmo que deseo reemplazar mis respuestas anteriores."
            )

            if st.button("Reemplazar respuestas e iniciar evaluación"):
                if confirmar_reemplazo:
                    eliminar_respuestas_experto(experto_normalizado)
                    st.session_state["experto"] = experto_normalizado
                    st.session_state["paso"] = 1
                    st.success("Respuestas anteriores eliminadas. Puede iniciar nuevamente.")
                    st.rerun()
                else:
                    st.error("Debe confirmar que desea reemplazar sus respuestas anteriores.")

            st.stop()

        else:

            if st.button("Iniciar evaluación"):
                st.session_state["experto"] = experto_normalizado
                st.session_state["paso"] = 1
                st.rerun()

    else:
        st.info("Ingrese su nombre o código para iniciar la evaluación.")

    st.stop()

experto = st.session_state["experto"]
paso = st.session_state["paso"]

st.info(f"Experto actual: {experto}")

total_pasos = 4
progreso = min(paso / total_pasos, 1.0)

st.progress(progreso)

if paso <= 3:
    st.write(f"Paso {paso} de 3")
else:
    st.write("Evaluación completada")

# ---------------------------------------------------------
# ETAPA 1: ENCUESTA LIKERT
# ---------------------------------------------------------
if st.session_state["paso"] == 1:

    st.header("Paso 1: Evaluación Likert de riesgos")

    st.write(
        "Califique cada riesgo según su importancia para generar criticidad e impacto presupuestal "
        "en un proyecto de diseño de cierre de mina."
    )

    riesgos = pd.read_csv("data/riesgos_filtrados.csv")

    st.subheader("Riesgos a evaluar")
    mostrar_tabla_riesgos(riesgos)

    escala = ["Muy baja", "Baja", "Media", "Alta", "Muy alta"]

    respuestas = []

    for _, row in riesgos.iterrows():

        codigo = row["Codigo"]
        riesgo = row["Riesgo"]
        descripcion = row.get("Descripcion", "")

        st.markdown(f"### {codigo}. {riesgo}")
        st.write(descripcion)

        calificacion = st.selectbox(
            "¿Qué tan importante considera este riesgo?",
            escala,
            key=f"likert_{experto}_{codigo}"
        )

        respuestas.append({
            "experto": experto,
            "codigo": codigo,
            "riesgo": riesgo,
            "calificacion": calificacion,
            "valor": convertir_likert(calificacion)
        })

    df_respuestas = pd.DataFrame(respuestas)

    st.subheader("Resumen de respuestas")
    st.dataframe(df_respuestas, width="stretch")

    if st.button("Guardar respuestas y continuar a FAHP"):
        guardar_respuestas(df_respuestas)
        st.session_state["paso"] = 2
        st.success("Respuestas Likert guardadas correctamente.")
        st.rerun()
# ---------------------------------------------------------
# ETAPA 2: CÁLCULO RII
# ---------------------------------------------------------

elif st.session_state["paso"] == 2:

    st.header("Paso 2: Comparación FAHP de criterios")

    st.write(
        "Compare los criterios de evaluación entre sí. Para cada par, seleccione qué criterio "
        "considera más importante y con qué intensidad."
    )

    criterios = pd.read_csv("data/criterios.csv")

    st.subheader("Criterios de evaluación")
    mostrar_tabla_criterios(criterios)

    pares = generar_pares_criterios(criterios)

    intensidad_opciones = [
        "Igual importancia",
        "Moderada",
        "Fuerte",
        "Muy fuerte",
        "Extrema",
    ]

    respuestas_fahp = []

    pares_conflictivos = st.session_state.get("pares_conflictivos_fahp", set())

    if pares_conflictivos:
        st.warning(
            "Se detectaron posibles contradicciones en sus respuestas anteriores. "
            "Revise especialmente las comparaciones marcadas en rojo."
        )

    for c_i, c_j in pares:

        codigo_i = c_i["Codigo"]
        codigo_j = c_j["Codigo"]

        nombre_i = c_i["Criterio"]
        nombre_j = c_j["Criterio"]

        par_actual = tuple(sorted([codigo_i, codigo_j]))

        if par_actual in pares_conflictivos:
            st.error(f"Debe corregir esta comparación: {codigo_i} vs {codigo_j}")

        st.markdown(f"### Comparación: {codigo_i} vs {codigo_j}")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**{codigo_i}: {nombre_i}**")
            st.caption(c_i["Que_mide"])

        with col2:
            st.write(f"**{codigo_j}: {nombre_j}**")
            st.caption(c_j["Que_mide"])

        criterio_preferido = st.radio(
            "¿Cuál criterio considera más importante?",
            [
                codigo_i,
                codigo_j,
                "Ambos tienen igual importancia",
            ],
            key=f"preferido_{experto}_{codigo_i}_{codigo_j}",
            horizontal=True,
        )

        if criterio_preferido == "Ambos tienen igual importancia":
            intensidad = "Igual importancia"
            tfn = (1.0, 1.0, 1.0)
            criterio_preferido_guardado = "igual"
        else:
            intensidad = st.selectbox(
                "¿Con qué intensidad?",
                intensidad_opciones[1:],
                key=f"intensidad_{experto}_{codigo_i}_{codigo_j}",
            )
            tfn = obtener_tfn(intensidad)
            criterio_preferido_guardado = criterio_preferido

        respuestas_fahp.append({
            "experto": experto,
            "criterio_i": codigo_i,
            "criterio_j": codigo_j,
            "criterio_i_nombre": nombre_i,
            "criterio_j_nombre": nombre_j,
            "criterio_preferido": criterio_preferido_guardado,
            "intensidad": intensidad,
            "l": tfn[0],
            "m": tfn[1],
            "u": tfn[2],
        })

    df_respuestas_fahp = pd.DataFrame(respuestas_fahp)

    st.subheader("Resumen FAHP")
    st.dataframe(df_respuestas_fahp, width="stretch")

    if st.button("Guardar FAHP y continuar a evaluación riesgo-criterio"):

        matriz_l, matriz_m, matriz_u, matriz_texto = construir_matriz_difusa(
            criterios,
            df_respuestas_fahp
        )

        matriz_crisp = matriz_central_para_cr(matriz_m)

        lambda_max, ci, cr, ri = calcular_cr(matriz_crisp)

        st.subheader("Validación de consistencia FAHP")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lambda máx.", f"{lambda_max:.4f}")
        col2.metric("CI", f"{ci:.4f}")
        col3.metric("RI", f"{ri:.2f}")
        col4.metric("CR", f"{cr:.4f}")

        if cr <= 0.30:

            guardar_respuestas_fahp(df_respuestas_fahp)

            if "pares_conflictivos_fahp" in st.session_state:
                del st.session_state["pares_conflictivos_fahp"]

            st.session_state["paso"] = 3
            st.success(f"Matriz aceptable. CR = {cr:.4f} ≤ 0.30")
            st.rerun()

        else:

            inconsistencias = detectar_inconsistencias_fuertes(
                matriz_crisp=matriz_crisp,
                criterios=criterios,
                top_n=5
            )

            st.error(
                f"La matriz FAHP no es aceptable. CR = {cr:.4f} > 0.30. "
                "Revise las comparaciones señaladas."
            )

            if not inconsistencias.empty:

                nuevos_pares_conflictivos = set()

                for _, row in inconsistencias.iterrows():
                    for col in ["Comparación 1", "Comparación 2", "Comparación 3"]:
                        c_a, c_b = row[col].split(" vs ")
                        nuevos_pares_conflictivos.add(tuple(sorted([c_a, c_b])))

                st.session_state["pares_conflictivos_fahp"] = nuevos_pares_conflictivos

                st.subheader("Comparaciones sugeridas para corregir")

                st.write(
                    "La matriz presenta inconsistencias fuertes. Revise especialmente las siguientes comparaciones:"
                )

                pares_ordenados = sorted(list(nuevos_pares_conflictivos))

                for c_a, c_b in pares_ordenados:
                    st.error(f"Corregir: {c_a} vs {c_b}")

                with st.expander("Ver detalle técnico de las inconsistencias"):
                    st.dataframe(inconsistencias, width="stretch")
                st.warning(
                    "Corrija las comparaciones marcadas arriba y luego vuelva a presionar "
                    "“Guardar FAHP y continuar a evaluación riesgo-criterio”."
                )

            st.stop()

# ---------------------------------------------------------
# ETAPA 3: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif st.session_state["paso"] == 3:

    st.header("Paso 3: Evaluación de riesgos frente a criterios")

    st.write(
        "Evalúe cada uno de los cuatro riesgos con mayor RII frente a cada criterio "
        "mediante la escala lingüística difusa."
    )

    # 1. Calcular automáticamente los 4 riesgos con mayor RII
    respuestas_rii = leer_respuestas()

    if respuestas_rii.empty:
        st.warning("No hay respuestas RII registradas.")
        st.stop()

    resultado_rii = calcular_rii_desde_respuestas(respuestas_rii)

    riesgos_seleccionados = resultado_rii.sort_values("RII", ascending=False).head(4).copy()

    if riesgos_seleccionados.empty:
        st.warning("No hay riesgos seleccionados.")
        st.stop()

    st.subheader("Cuatro riesgos seleccionados automáticamente por mayor RII")
    st.dataframe(riesgos_seleccionados, width="stretch")

    # 2. Calcular pesos FAHP globales
    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp = leer_respuestas_fahp()

    if respuestas_fahp.empty:
        st.warning("Todavía no hay respuestas FAHP registradas.")
        st.stop()

    df_pesos, matriz_texto_global, matriz_crisp_global, lambda_max, ci, cr, ri = (
        calcular_pesos_globales_fahp(
            criterios=criterios,
            respuestas_fahp=respuestas_fahp
        )
    )
    
    st.subheader("Pesos FAHP globales de criterios")
    st.dataframe(df_pesos, width="stretch")

    st.subheader("Consistencia de la matriz FAHP global")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Lambda máx.", f"{lambda_max:.4f}")
    col2.metric("CI", f"{ci:.4f}")
    col3.metric("RI", f"{ri:.2f}")
    col4.metric("CR global", f"{cr:.4f}")

    if cr <= 0.30:
        st.success(f"Matriz FAHP global aceptable: CR = {cr:.4f}")
    else:
        st.warning(
            f"La matriz FAHP global tiene CR = {cr:.4f}. "
            "Se recomienda revisar las respuestas individuales, pero se continuará mostrando el cálculo."
        )
    # 3. Evaluación matricial riesgo-criterio
    escala = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]

    respuestas_eval = []

    for _, riesgo_row in riesgos_seleccionados.iterrows():

        codigo_riesgo = riesgo_row.get("codigo", riesgo_row.get("Codigo", ""))
        riesgo_nombre = riesgo_row.get("riesgo", riesgo_row.get("Riesgo", ""))

        st.markdown(f"### {codigo_riesgo}. {riesgo_nombre}")

        columnas = st.columns(len(df_pesos))

        for idx, criterio_row in df_pesos.iterrows():

            codigo_criterio = criterio_row["Codigo"]
            criterio_nombre = criterio_row["Criterio"]

            with columnas[idx]:

                calificacion = st.selectbox(
                    f"{codigo_criterio}",
                    escala,
                    key=f"eval_{experto}_{codigo_riesgo}_{codigo_criterio}"
                )

                st.caption(criterio_nombre)

                l, m, u = obtener_tfn_calificacion(calificacion)
                defuzzificado = defuzzificar_tfn(l, m, u)

                respuestas_eval.append({
                    "experto": experto,
                    "codigo_riesgo": codigo_riesgo,
                    "riesgo": riesgo_nombre,
                    "codigo_criterio": codigo_criterio,
                    "criterio": criterio_nombre,
                    "calificacion": calificacion,
                    "l": l,
                    "m": m,
                    "u": u,
                    "defuzzificado": defuzzificado,
                })

    df_respuestas_eval = pd.DataFrame(respuestas_eval)

    #st.subheader("Resumen de evaluación riesgo-criterio")
    #st.dataframe(df_respuestas_eval, width="stretch")

    if st.button("Finalizar evaluación"):

        guardar_respuestas_evaluacion(df_respuestas_eval)

        ranking = calcular_criticidad(
            respuestas_evaluacion=df_respuestas_eval,
            pesos_criterios=df_pesos
        )

        st.session_state["ranking_final"] = ranking
        st.session_state["paso"] = 4
        st.success("Evaluación final guardada correctamente.")
        st.rerun()

elif st.session_state["paso"] == 4:

    st.header("Evaluación completada")

    st.success("Sus respuestas fueron registradas correctamente.")

    st.write(
        "A continuación se muestra el ranking global de riesgos críticos, calculado con las respuestas "
        "registradas por todos los expertos disponibles en la plataforma."
    )

    # 1. Leer respuestas globales de evaluación riesgo-criterio
    respuestas_eval_global = leer_respuestas_evaluacion()

    if respuestas_eval_global.empty:
        st.warning("Todavía no hay evaluaciones riesgo-criterio registradas.")
        st.stop()

    # 2. Leer respuestas FAHP globales
    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp_global = leer_respuestas_fahp()

    if respuestas_fahp_global.empty:
        st.warning("Todavía no hay respuestas FAHP registradas.")
        st.stop()

    # 3. Calcular pesos globales FAHP
    df_pesos_globales, matriz_texto_global, matriz_crisp_global, lambda_max, ci, cr, ri = (
        calcular_pesos_globales_fahp(
            criterios=criterios,
            respuestas_fahp=respuestas_fahp_global
        )
    )

    st.subheader("Pesos globales de criterios FAHP")
    st.dataframe(df_pesos_globales, width="stretch")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Lambda máx.", f"{lambda_max:.4f}")
    col2.metric("CI", f"{ci:.4f}")
    col3.metric("RI", f"{ri:.2f}")
    col4.metric("CR global", f"{cr:.4f}")

    if cr <= 0.30:
        st.success(f"Matriz FAHP global aceptable: CR = {cr:.4f}")
    else:
        st.warning(f"Matriz FAHP global con CR = {cr:.4f}. Revisar consistencia global.")

    # 4. Calcular ranking global de riesgos
    ranking_global = calcular_criticidad(
        respuestas_evaluacion=respuestas_eval_global,
        pesos_criterios=df_pesos_globales
    )

    st.subheader("Ranking global de riesgos críticos")
    st.dataframe(ranking_global, width="stretch")

    fig = graficar_ranking_riesgos(ranking_global)
    st.plotly_chart(fig, use_container_width=True)

    csv = ranking_global.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar ranking global",
        data=csv,
        file_name="ranking_global_riesgos_criticos.csv",
        mime="text/csv"
    )

    st.info(
        "El ranking global se actualiza automáticamente cada vez que un nuevo experto completa "
        "las tres encuestas."
    )
    if st.button("Volver al inicio"):
        st.session_state["modo"] = ""
        st.session_state["experto"] = ""
        st.session_state["paso"] = 1
        st.rerun()
