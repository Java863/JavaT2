import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Modelo de riesgos de cierre de mina",
    layout="wide"
)

st.title("Modelo multicriterio para riesgos críticos")
st.subheader("Proyecto de diseño de cierre de mina")

st.write(
    "Esta aplicación implementará una metodología basada en juicio experto, "
    "RII, FAHP y estimación presupuestal."
)

st.info("Versión inicial del prototipo.")
