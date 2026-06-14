import streamlit as st
import pandas as pd
from supabase import create_client


@st.cache_resource
def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def guardar_respuestas(df_respuestas: pd.DataFrame):
    supabase = conectar_supabase()

    columnas = ["experto", "codigo", "riesgo", "calificacion", "valor"]
    registros = df_respuestas[columnas].to_dict(orient="records")

    if registros:
        supabase.table("respuestas_rii").insert(registros).execute()


def leer_respuestas() -> pd.DataFrame:
    supabase = conectar_supabase()

    response = supabase.table("respuestas_rii").select("*").execute()

    if not response.data:
        return pd.DataFrame(
            columns=["experto", "codigo", "riesgo", "calificacion", "valor"]
        )

    return pd.DataFrame(response.data)

def guardar_respuestas_fahp(df_respuestas: pd.DataFrame):
    supabase = conectar_supabase()

    columnas = [
        "experto",
        "criterio_i",
        "criterio_j",
        "criterio_i_nombre",
        "criterio_j_nombre",
        "criterio_preferido",
        "intensidad",
        "l",
        "m",
        "u",
    ]

    registros = df_respuestas[columnas].to_dict(orient="records")

    if registros:
        supabase.table("respuestas_fahp").insert(registros).execute()


def leer_respuestas_fahp() -> pd.DataFrame:
    supabase = conectar_supabase()

    response = supabase.table("respuestas_fahp").select("*").execute()

    if not response.data:
        return pd.DataFrame(
            columns=[
                "experto",
                "criterio_i",
                "criterio_j",
                "criterio_i_nombre",
                "criterio_j_nombre",
                "criterio_preferido",
                "intensidad",
                "l",
                "m",
                "u",
            ]
        )

    return pd.DataFrame(response.data)


def guardar_respuestas_evaluacion(df_respuestas: pd.DataFrame):
    supabase = conectar_supabase()

    columnas = [
        "experto",
        "codigo_riesgo",
        "riesgo",
        "codigo_criterio",
        "criterio",
        "calificacion",
        "l",
        "m",
        "u",
        "defuzzificado",
    ]

    registros = df_respuestas[columnas].to_dict(orient="records")

    if registros:
        supabase.table("respuestas_evaluacion").insert(registros).execute()


def leer_respuestas_evaluacion() -> pd.DataFrame:
    supabase = conectar_supabase()

    response = supabase.table("respuestas_evaluacion").select("*").execute()

    if not response.data:
        return pd.DataFrame(
            columns=[
                "experto",
                "codigo_riesgo",
                "riesgo",
                "codigo_criterio",
                "criterio",
                "calificacion",
                "l",
                "m",
                "u",
                "defuzzificado",
            ]
        )

    return pd.DataFrame(response.data)
