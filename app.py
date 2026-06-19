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

menu = st.sidebar.radio(
    "Seleccione una etapa",
    [
        "1. Encuesta Likert a expertos",
        "2. Cálculo RII",
        "3. Selección de riesgos principales",
        "4. Encuesta FAHP de criterios",
        "5. Matriz difusa FAHP",
        "6. Evaluación matricial riesgo-criterio",
        "7. Ranking final de riesgos críticos",
    ]
)

# ---------------------------------------------------------
# ETAPA 1: ENCUESTA LIKERT
# ---------------------------------------------------------

if menu == "1. Encuesta Likert a expertos":

    st.header("1. Encuesta Likert para evaluación de riesgos")

    riesgos = pd.read_csv("data/riesgos_filtrados.csv")

    st.success("Lista de riesgos filtrados cargada automáticamente.")
    st.dataframe(riesgos, use_container_width=True)

    experto = st.text_input("Nombre o código del experto")

    escala = ["Muy baja", "Baja", "Media", "Alta", "Muy alta"]

    respuestas = []

    if experto:
        for _, row in riesgos.iterrows():
            codigo = row["Codigo"]
            riesgo = row["Riesgo"]
            descripcion = row.get("Descripcion", "")

            st.markdown(f"### {codigo}. {riesgo}")
            st.write(descripcion)

            calificacion = st.selectbox(
                "Seleccione su calificación:",
                escala,
                key=f"{experto}_{codigo}"
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
        st.dataframe(df_respuestas, use_container_width=True)

        if st.button("Enviar respuestas"):
            guardar_respuestas(df_respuestas)
            st.success("Respuestas guardadas correctamente.")
    else:
        st.warning("Ingrese el nombre o código del experto para iniciar.")
# ---------------------------------------------------------
# ETAPA 2: CÁLCULO RII
# ---------------------------------------------------------

elif menu == "2. Cálculo RII":

    st.header("2. Cálculo del Índice de Importancia Relativa")

    if st.button("Cargar respuestas guardadas"):
        respuestas_totales = leer_respuestas()

        if respuestas_totales.empty:
            st.warning("Todavía no hay respuestas registradas.")
        else:
            st.subheader("Respuestas registradas")
            st.dataframe(respuestas_totales, use_container_width=True)

            resultado_rii = calcular_rii_desde_respuestas(respuestas_totales)

            st.subheader("Ranking de riesgos según RII")
            st.dataframe(resultado_rii, use_container_width=True)

            st.session_state["resultado_rii"] = resultado_rii

            csv = resultado_rii.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Descargar ranking RII",
                data=csv,
                file_name="ranking_rii.csv",
                mime="text/csv"
            )

# ---------------------------------------------------------
# ETAPA 3: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif menu == "3. Selección de riesgos principales":

    st.header("3. Selección de riesgos principales")

    if "resultado_rii" not in st.session_state:
        st.warning("Primero debe calcular el RII en la etapa anterior.")
    else:
        resultado_rii = st.session_state["resultado_rii"]

        umbral = st.slider(
            "Seleccione el umbral mínimo de RII",
            min_value=0.0,
            max_value=1.0,
            value=0.70,
            step=0.01
        )

        riesgos_seleccionados = resultado_rii[resultado_rii["RII"] >= umbral]

        st.subheader("Riesgos seleccionados")
        st.dataframe(riesgos_seleccionados, use_container_width=True)

        csv = riesgos_seleccionados.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Descargar riesgos seleccionados",
            data=csv,
            file_name="riesgos_seleccionados.csv",
            mime="text/csv"
        )


# ---------------------------------------------------------
# ETAPA 4: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif menu == "4. Encuesta FAHP de criterios":

    st.header("4. Encuesta FAHP de comparación por pares entre criterios")

    st.write(
        "En esta sección, el experto compara los criterios de evaluación entre sí. "
        "El objetivo es determinar qué criterio es más importante para evaluar la criticidad "
        "de los riesgos en un proyecto de diseño de cierre de mina."
    )

    criterios = pd.read_csv("data/criterios.csv")

    st.subheader("Criterios de evaluación")
    st.dataframe(criterios, width="stretch")

    experto = st.text_input("Nombre o código del experto FAHP")

    pares = generar_pares_criterios(criterios)

    intensidad_opciones = [
        "Igual importancia",
        "Moderada",
        "Fuerte",
        "Muy fuerte",
        "Extrema",
    ]

    respuestas = []

    if experto:

        for c_i, c_j in pares:

            codigo_i = c_i["Codigo"]
            codigo_j = c_j["Codigo"]

            nombre_i = c_i["Criterio"]
            nombre_j = c_j["Criterio"]

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

            respuestas.append({
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

        df_respuestas_fahp = pd.DataFrame(respuestas)

        st.subheader("Resumen de respuestas FAHP")
        st.dataframe(df_respuestas_fahp, width="stretch")

        if st.button("Enviar respuestas FAHP"):
            guardar_respuestas_fahp(df_respuestas_fahp)
            st.success("Respuestas FAHP guardadas correctamente.")

    else:
        st.warning("Ingrese el nombre o código del experto para iniciar la encuesta FAHP.")

# ---------------------------------------------------------
# ETAPA 5: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif menu == "5. Matriz difusa FAHP":

    st.header("5. Construcción de matriz difusa recíproca de comparación por pares")

    criterios = pd.read_csv("data/criterios.csv")
    respuestas_fahp = leer_respuestas_fahp()

    if respuestas_fahp.empty:
        st.warning("Todavía no hay respuestas FAHP registradas.")
    else:
        st.subheader("Respuestas FAHP registradas")
        st.dataframe(respuestas_fahp, width="stretch")

        expertos = respuestas_fahp["experto"].unique().tolist()

        experto_seleccionado = st.selectbox(
            "Seleccione el experto para construir su matriz FAHP",
            expertos
        )

        respuestas_experto = respuestas_fahp[
            respuestas_fahp["experto"] == experto_seleccionado
        ]

        matriz_l, matriz_m, matriz_u, matriz_texto = construir_matriz_difusa(
            criterios,
            respuestas_experto
        )

        st.subheader("Matriz difusa recíproca FAHP")
        st.dataframe(matriz_texto, width="stretch")

        st.subheader("Matriz crisp para validación de consistencia")
        matriz_crisp = matriz_central_para_cr(matriz_m)

        df_crisp = pd.DataFrame(
            matriz_crisp,
            index=criterios["Codigo"],
            columns=criterios["Codigo"]
        )

        st.dataframe(df_crisp, width="stretch")

        lambda_max, ci, cr, ri = calcular_cr(matriz_crisp)

        st.subheader("Validación de consistencia")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Lambda máx.", f"{lambda_max:.4f}")
        col2.metric("CI", f"{ci:.4f}")
        col3.metric("RI", f"{ri:.2f}")
        col4.metric("CR", f"{cr:.4f}")

        if cr <= 0.30:
            st.success("La matriz es consistente: CR ≤ 0.30")
        else:
            st.error("La matriz no es consistente: CR > 0.30. Se recomienda revisar los juicios.")

        pesos = calcular_pesos_crisp(matriz_crisp)

        df_pesos = pd.DataFrame({
            "Codigo": criterios["Codigo"],
            "Criterio": criterios["Criterio"],
            "Peso": pesos
        })

        df_pesos["Peso_normalizado"] = df_pesos["Peso"] / df_pesos["Peso"].sum()

        st.subheader("Pesos normalizados de criterios")
        st.dataframe(df_pesos, width="stretch")

        csv = df_pesos.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Descargar pesos FAHP",
            data=csv,
            file_name=f"pesos_fahp_{experto_seleccionado}.csv",
            mime="text/csv"
        )

# ---------------------------------------------------------
# ETAPA 6: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif menu == "6. Evaluación matricial riesgo-criterio":

    st.header("6. Evaluación matricial de riesgos frente a criterios")

    st.write(
        "En esta sección, el experto evalúa automáticamente los riesgos seleccionados por RII "
        "frente a los criterios ponderados mediante FAHP. No es necesario cargar archivos."
    )

    # ===============================
    # 1. Obtener riesgos seleccionados desde RII
    # ===============================

    respuestas_rii = leer_respuestas()

    if respuestas_rii.empty:
        st.warning("Todavía no hay respuestas RII registradas.")
        st.stop()

    resultado_rii = calcular_rii_desde_respuestas(respuestas_rii)

    umbral_rii = st.slider(
        "Umbral mínimo de RII para seleccionar riesgos",
        min_value=0.0,
        max_value=1.0,
        value=0.70,
        step=0.01
    )

    riesgos_seleccionados = resultado_rii[resultado_rii["RII"] >= umbral_rii].copy()

    if riesgos_seleccionados.empty:
        st.warning("No hay riesgos seleccionados con el umbral indicado.")
        st.stop()

    st.subheader("Riesgos seleccionados automáticamente por RII")
    st.dataframe(riesgos_seleccionados, width="stretch")

    # ===============================
    # 2. Obtener pesos FAHP automáticamente
    # ===============================

    df_pesos, cr, experto_fahp = obtener_pesos_fahp_automaticos()

    if df_pesos is None:
        st.warning("Todavía no hay respuestas FAHP registradas.")
        st.stop()

    st.subheader(f"Pesos FAHP usados: experto {experto_fahp}")
    st.dataframe(df_pesos, width="stretch")

    if cr <= 0.10:
        st.success(f"Matriz FAHP consistente: CR = {cr:.4f}")
    else:
        st.error(f"Matriz FAHP no consistente: CR = {cr:.4f}. Se recomienda revisar los juicios.")

    # ===============================
    # 3. Encuesta matricial riesgo-criterio
    # ===============================

    experto = st.text_input("Nombre o código del experto evaluador")

    escala = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]

    respuestas = []

    if experto:

        st.subheader("Matriz de evaluación riesgo-criterio")

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

                    respuestas.append({
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

        df_respuestas_eval = pd.DataFrame(respuestas)

        st.subheader("Resumen de evaluación")
        st.dataframe(df_respuestas_eval, width="stretch")

        if st.button("Enviar evaluación matricial"):
            guardar_respuestas_evaluacion(df_respuestas_eval)
            st.success("Evaluación matricial guardada correctamente.")

    else:
        st.warning("Ingrese el nombre o código del experto para iniciar la evaluación.")

# ---------------------------------------------------------
# ETAPA 7: SELECCIÓN DE RIESGOS PRINCIPALES
# ---------------------------------------------------------

elif menu == "7. Ranking final de riesgos críticos":

    st.header("7. Ranking final de riesgos críticos")

    respuestas_eval = leer_respuestas_evaluacion()

    if respuestas_eval.empty:
        st.warning("Todavía no hay evaluaciones matriciales registradas.")
        st.stop()

    st.subheader("Evaluaciones registradas")
    st.dataframe(respuestas_eval, width="stretch")

    # Obtener pesos FAHP automáticamente
    df_pesos, cr, experto_fahp = obtener_pesos_fahp_automaticos()

    if df_pesos is None:
        st.warning("Todavía no hay pesos FAHP disponibles.")
        st.stop()

    st.subheader(f"Pesos FAHP usados: experto {experto_fahp}")
    st.dataframe(df_pesos, width="stretch")

    if cr <= 0.10:
        st.success(f"Matriz FAHP consistente: CR = {cr:.4f}")
    else:
        st.error(f"Matriz FAHP no consistente: CR = {cr:.4f}. Se recomienda revisar los juicios.")

    ranking = calcular_criticidad(
        respuestas_evaluacion=respuestas_eval,
        pesos_criterios=df_pesos
    )

    st.subheader("Ranking de riesgos críticos")
    st.dataframe(ranking, width="stretch")

    st.bar_chart(
        ranking.set_index("riesgo")["puntaje_criticidad"]
    )

    csv = ranking.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar ranking final",
        data=csv,
        file_name="ranking_final_riesgos_criticos.csv",
        mime="text/csv"
    )
