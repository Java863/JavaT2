import pandas as pd

def calcular_rii(df: pd.DataFrame, factor_col: str, respuesta_cols: list, escala_maxima: int = 5) -> pd.DataFrame:
    """
    Calcula el Relative Importance Index (RII).

    Parámetros:
    df: DataFrame con factores y respuestas.
    factor_col: nombre de la columna donde están los factores/riesgos.
    respuesta_cols: columnas con respuestas Likert de expertos.
    escala_maxima: valor máximo de la escala Likert.

    Retorna:
    DataFrame ordenado de mayor a menor RII.
    """
    resultado = df.copy()
    n_expertos = len(respuesta_cols)

    resultado["Suma_respuestas"] = resultado[respuesta_cols].sum(axis=1)
    resultado["RII"] = resultado["Suma_respuestas"] / (escala_maxima * n_expertos)

    return resultado.sort_values("RII", ascending=False)
