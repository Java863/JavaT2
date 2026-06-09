import pandas as pd


def convertir_likert(valor: str) -> int:
    escala = {
        "Muy baja": 1,
        "Baja": 2,
        "Media": 3,
        "Alta": 4,
        "Muy alta": 5,
    }
    return escala[valor]


def calcular_rii_desde_respuestas(df: pd.DataFrame, escala_maxima: int = 5) -> pd.DataFrame:
    """
    Calcula RII desde respuestas en formato largo.

    Formato esperado:
    Experto | Codigo | Riesgo | Calificacion | Valor
    """
    resumen = (
        df.groupby(["Codigo", "Riesgo"], as_index=False)
        .agg(
            Suma_respuestas=("Valor", "sum"),
            N_expertos=("Experto", "nunique"),
            Promedio=("Valor", "mean"),
        )
    )

    resumen["RII"] = resumen["Suma_respuestas"] / (
        escala_maxima * resumen["N_expertos"]
    )

    return resumen.sort_values("RII", ascending=False)
