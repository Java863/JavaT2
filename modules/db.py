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
