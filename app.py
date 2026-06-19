from modules.rii import convertir_likert, calcular_rii_desde_respuestas
import streamlit as st
import pandas as pd

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
)

from modules.db import (
    guardar_respuestas,
    leer_respuestas,
    guardar_respuestas_fahp,
    leer_respuestas_fahp,
    guardar_respuestas_evaluacion,
    leer_respuestas_evaluacion,
)


def obtener_pesos_fahp_automaticos():
    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp = leer_respuestas_fahp()

    if respuestas_fahp.empty:
        return None, None, None

    expertos = respuestas_fahp["experto"].unique().tolist()

    experto_seleccionado = st.selectbox(
        "Seleccione el experto FAHP para usar sus pesos",
        expertos,
        key="experto_fahp_automatico"
    )

    respuestas_experto = respuestas_fahp[
        respuestas_fahp["experto"] == experto_seleccionado
    ]

    matriz_l, matriz_m, matriz_u, matriz_texto = construir_matriz_difusa(
        criterios,
        respuestas_experto
    )

    matriz_crisp = matriz_central_para_cr(matriz_m)

    lambda_max, ci, cr, ri = calcular_cr(matriz_crisp)

    pesos = calcular_pesos_crisp(matriz_crisp)

    df_pesos = pd.DataFrame({
        "Codigo": criterios["Codigo"],
        "Criterio": criterios["Criterio"],
        "Peso": pesos
    })

    df_pesos["Peso_normalizado"] = df_pesos["Peso"] / df_pesos["Peso"].sum()

    return df_pesos, cr, experto_seleccionado

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

if not st.session_state["experto"]:

    st.header("Identificación del experto")

    experto_input = st.text_input(
        "Ingrese su nombre o código de experto",
        placeholder="Ejemplo: E01, Especialista Geotecnia, Experto 1"
    )

    if st.button("Iniciar evaluación"):
        if experto_input.strip():
            st.session_state["experto"] = experto_input.strip()
            st.session_state["paso"] = 1
            st.rerun()
        else:
            st.warning("Debe ingresar un nombre o código para continuar.")

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
    st.dataframe(riesgos, width="stretch")

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
    st.dataframe(criterios, width="stretch")

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

    # 2. Calcular pesos FAHP del mismo experto
    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp = leer_respuestas_fahp()

    respuestas_fahp_experto = respuestas_fahp[
        respuestas_fahp["experto"] == experto
    ]

    if respuestas_fahp_experto.empty:
        st.warning("No hay respuestas FAHP registradas para este experto.")
        st.stop()

    matriz_l, matriz_m, matriz_u, matriz_texto = construir_matriz_difusa(
        criterios,
        respuestas_fahp_experto
    )

    matriz_crisp = matriz_central_para_cr(matriz_m)
    lambda_max, ci, cr, ri = calcular_cr(matriz_crisp)

    pesos = calcular_pesos_crisp(matriz_crisp)

    df_pesos = pd.DataFrame({
        "Codigo": criterios["Codigo"],
        "Criterio": criterios["Criterio"],
        "Peso": pesos
    })

    df_pesos["Peso_normalizado"] = df_pesos["Peso"] / df_pesos["Peso"].sum()

    st.subheader("Pesos FAHP del experto")
    st.dataframe(df_pesos, width="stretch")

    if cr <= 0.30:
        st.success(f"Matriz FAHP aceptable: CR = {cr:.4f}")
    else:
        st.error(f"Matriz FAHP no aceptable: CR = {cr:.4f}")
        st.stop()

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

    st.subheader("Resumen de evaluación riesgo-criterio")
    st.dataframe(df_respuestas_eval, width="stretch")

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

    if "ranking_final" in st.session_state:
        st.subheader("Ranking preliminar de riesgos críticos según sus respuestas")
        st.dataframe(st.session_state["ranking_final"], width="stretch")

        st.bar_chart(
            st.session_state["ranking_final"].set_index("riesgo")["puntaje_criticidad"]
        )

    st.write(
        "Gracias por participar en la evaluación. La información registrada será utilizada "
        "para consolidar el juicio experto del modelo multicriterio."
    )
