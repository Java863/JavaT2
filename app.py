from modules.db import guardar_respuestas, leer_respuestas
from modules.rii import convertir_likert, calcular_rii_desde_respuestas
import streamlit as st
import pandas as pd
from modules.rii import convertir_likert, calcular_rii_desde_respuestas

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
        "3. Selección de riesgos principales"
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
