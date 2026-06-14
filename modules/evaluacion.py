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

    respuestas_evaluacion debe tener:
    codigo_riesgo, riesgo, codigo_criterio, defuzzificado

    pesos_criterios debe tener:
    Codigo, Peso_normalizado
    """

    df = respuestas_evaluacion.copy()
    pesos = pesos_criterios.copy()

    pesos = pesos.rename(columns={
        "Codigo": "codigo_criterio",
        "Peso_normalizado": "peso_criterio"
    })

    df = df.merge(
        pesos[["codigo_criterio", "peso_criterio"]],
        on="codigo_criterio",
        how="left"
    )

    df["aporte"] = df["defuzzificado"] * df["peso_criterio"]

    ranking = (
        df.groupby(["codigo_riesgo", "riesgo"], as_index=False)
        .agg(
            puntaje_criticidad=("aporte", "sum")
        )
    )

    ranking = ranking.sort_values("puntaje_criticidad", ascending=False)

    return ranking
