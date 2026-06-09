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

    st.write(
        "En esta sección, cada experto califica los riesgos filtrados según su importancia "
        "para generar riesgos críticos e impacto presupuestal en un proyecto de diseño de cierre de mina."
    )

    try:
        riesgos = pd.read_csv("data/riesgos_filtrados.csv")

        st.success("Lista de riesgos filtrados cargada automáticamente.")
        st.dataframe(riesgos, use_container_width=True)

        experto = st.text_input("Nombre o código del experto")

        st.subheader("Calificación de riesgos")

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
                    "¿Qué tan importante considera este riesgo para generar criticidad e impacto presupuestal?",
                    escala,
                    key=f"{experto}_{codigo}"
                )

                respuestas.append({
                    "Experto": experto,
                    "Codigo": codigo,
                    "Riesgo": riesgo,
                    "Calificacion": calificacion,
                    "Valor": convertir_likert(calificacion)
                })

            df_respuestas = pd.DataFrame(respuestas)

            st.subheader("Resumen de respuestas del experto")
            st.dataframe(df_respuestas, use_container_width=True)

            csv = df_respuestas.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Descargar respuestas del experto en CSV",
                data=csv,
                file_name=f"respuestas_{experto}.csv",
                mime="text/csv"
            )

        else:
            st.warning("Ingrese el nombre o código del experto para iniciar la encuesta.")

    except FileNotFoundError:
        st.error(
            "No se encontró el archivo data/riesgos_filtrados.csv. "
            "Verifica que exista dentro del repositorio de GitHub."
        )
# ---------------------------------------------------------
# ETAPA 2: CÁLCULO RII
# ---------------------------------------------------------

elif menu == "2. Cálculo RII":

    st.header("2. Cálculo del Índice de Importancia Relativa")

    st.write(
        "Cargue uno o varios archivos CSV descargados desde la encuesta. "
        "La aplicación consolidará las respuestas y calculará el RII de cada riesgo."
    )

    archivos_respuestas = st.file_uploader(
        "Cargue las respuestas de los expertos",
        type=["csv"],
        accept_multiple_files=True
    )

    if archivos_respuestas:

        lista_df = []

        for archivo in archivos_respuestas:
            df = pd.read_csv(archivo)
            lista_df.append(df)

        respuestas_totales = pd.concat(lista_df, ignore_index=True)

        st.subheader("Respuestas consolidadas")
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
