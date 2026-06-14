import pandas as pd


ESCALA_DIFUSA_RIESGOS = {
    "Muy bajo": (0.00, 0.10, 0.25),
    "Bajo": (0.10, 0.25, 0.40),
    "Medio": (0.30, 0.50, 0.70),
    "Alto": (0.60, 0.75, 0.90),
    "Muy alto": (0.80, 0.90, 1.00),
}


def obtener_tfn_calificacion(calificacion: str):
    return ESCALA_DIFUSA_RIESGOS[calificacion]


def defuzzificar_tfn(l: float, m: float, u: float) -> float:
    return (l + m + u) / 3


def calcular_criticidad(
    respuestas_evaluacion: pd.DataFrame,
    pesos_criterios: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula el puntaje de criticidad de cada riesgo.

    Si hay varios expertos, primero promedia la calificación defuzzificada
    por cada combinación riesgo-criterio.
    """

    df = respuestas_evaluacion.copy()
    pesos = pesos_criterios.copy()

    # Promedio por riesgo y criterio
    df_prom = (
        df.groupby(
            ["codigo_riesgo", "riesgo", "codigo_criterio", "criterio"],
            as_index=False
        )
        .agg(
            defuzzificado_promedio=("defuzzificado", "mean"),
            n_respuestas=("experto", "nunique")
        )
    )

    pesos = pesos.rename(columns={
        "Codigo": "codigo_criterio",
        "Peso_normalizado": "peso_criterio"
    })

    df_prom = df_prom.merge(
        pesos[["codigo_criterio", "peso_criterio"]],
        on="codigo_criterio",
        how="left"
    )

    df_prom["aporte"] = df_prom["defuzzificado_promedio"] * df_prom["peso_criterio"]

    ranking = (
        df_prom.groupby(["codigo_riesgo", "riesgo"], as_index=False)
        .agg(
            puntaje_criticidad=("aporte", "sum")
        )
    )

    ranking = ranking.sort_values("puntaje_criticidad", ascending=False)

    return ranking

    return ranking
