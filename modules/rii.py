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
    resumen = (
        df.groupby(["codigo", "riesgo"], as_index=False)
        .agg(
            suma_respuestas=("valor", "sum"),
            n_expertos=("experto", "nunique"),
            promedio=("valor", "mean"),
        )
    )

    resumen["RII"] = resumen["suma_respuestas"] / (
        escala_maxima * resumen["n_expertos"]
    )

    return resumen.sort_values("RII", ascending=False)
