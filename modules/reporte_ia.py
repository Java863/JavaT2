import streamlit as st
from google import genai


def generar_reporte_decisiones_gemini(
    ranking_global,
    pesos_criterios,
    resumen_sensibilidad,
    modelo="gemini-2.5-flash"
):
    """
    Genera un reporte ejecutivo usando Gemini.

    La IA no calcula el ranking.
    La IA no modifica pesos.
    La IA no inventa riesgos.
    Solo redacta una interpretación ejecutiva con base en datos estructurados.
    """

    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        return (
            "No se encontró GEMINI_API_KEY en Streamlit Secrets. "
            "Agrega la clave antes de generar el reporte con IA."
        )

    client = genai.Client(api_key=api_key)

    ranking_texto = ranking_global.to_string(index=False)
    pesos_texto = pesos_criterios.to_string(index=False)

    if resumen_sensibilidad is None:
        sensibilidad_texto = "No se proporcionó resumen de análisis de sensibilidad."
    else:
        sensibilidad_texto = str(resumen_sensibilidad)

    prompt = f"""
Eres un asistente técnico de apoyo a la toma de decisiones en gestión de riesgos
para proyectos de diseño de cierre de mina.

Tu tarea es redactar un REPORTE EJECUTIVO FINAL a partir de los resultados de un
modelo multicriterio basado en RII, Fuzzy AHP, lógica difusa y análisis de sensibilidad.

REGLAS OBLIGATORIAS:
1. No inventes riesgos nuevos.
2. No cambies el ranking.
3. No modifiques los puntajes.
4. No inventes pesos ni criterios.
5. No afirmes que la decisión es obligatoria.
6. No reemplaces el juicio del Project Manager.
7. No propongas acciones excesivamente específicas que no se deriven del ranking.
8. Usa lenguaje profesional, claro y ejecutivo.
9. Explica que el resultado sirve como apoyo a la toma de decisiones.
10. Si mencionas acciones, que sean generales: priorizar, monitorear, revisar, escalar, asignar seguimiento o validar información.

DATOS DEL RANKING GLOBAL:
{ranking_texto}

PESOS GLOBALES DE CRITERIOS:
{pesos_texto}

RESUMEN DEL ANÁLISIS DE SENSIBILIDAD:
{sensibilidad_texto}

ESTRUCTURA DEL REPORTE:
1. Resumen ejecutivo.
2. Interpretación del ranking global de riesgos críticos.
3. Riesgos que requieren atención prioritaria.
4. Implicancias para la toma de decisiones del Project Manager.
5. Interpretación del análisis de sensibilidad.
6. Recomendaciones generales de seguimiento.
7. Nota de alcance: indicar que el reporte no reemplaza el juicio profesional del PM ni del equipo técnico.

Redacta el reporte en español.
"""

    try:
        respuesta = client.models.generate_content(
            model=modelo,
            contents=prompt
        )

        return respuesta.text

    except Exception as e:
        return f"Error al generar el reporte con Gemini: {e}"
