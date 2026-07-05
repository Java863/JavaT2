import pandas as pd


def preparar_base_sensibilidad(
    respuestas_evaluacion: pd.DataFrame,
    pesos_criterios: pd.DataFrame,
    top_n: int = 5
):
    """
    Prepara la base del análisis de sensibilidad usando información ya leída
    desde Supabase.

    No carga archivos.
    No pide inputs al usuario.
    Solo procesa las respuestas existentes en la base de datos.
    """

    if respuestas_evaluacion.empty:
        return None, None, None, "No hay respuestas de evaluación riesgo-criterio registradas."

    if pesos_criterios.empty:
        return None, None, None, "No hay pesos de criterios disponibles."

    # 1. Promedio global de evaluación riesgo-criterio
    df_eval = (
        respuestas_evaluacion
        .groupby(
            ["codigo_riesgo", "riesgo", "codigo_criterio", "criterio"],
            as_index=False
        )
        .agg(
            defuzzificado_promedio=("defuzzificado", "mean"),
            n_expertos=("experto", "nunique")
        )
    )

    # 2. Preparar pesos globales
    pesos_base = pesos_criterios[["Codigo", "Criterio", "Peso_normalizado"]].copy()

    pesos_base = pesos_base.rename(
        columns={
            "Codigo": "codigo_criterio",
            "Criterio": "criterio",
            "Peso_normalizado": "peso"
        }
    )

    # 3. Unir evaluación promedio con pesos globales
    df_merge = df_eval.merge(
        pesos_base,
        on=["codigo_criterio", "criterio"],
        how="left"
    )

    if df_merge["peso"].isna().any():
        return None, None, None, "Hay criterios evaluados que no tienen peso FAHP asociado."

    # 4. Calcular puntaje base de criticidad
    df_merge["aporte"] = df_merge["defuzzificado_promedio"] * df_merge["peso"]

    ranking = (
        df_merge
        .groupby(["codigo_riesgo", "riesgo"], as_index=False)
        .agg(
            puntaje_criticidad=("aporte", "sum"),
            n_expertos=("n_expertos", "max")
        )
        .sort_values("puntaje_criticidad", ascending=False)
        .reset_index(drop=True)
    )

    ranking.insert(0, "Ranking", range(1, len(ranking) + 1))

    # 5. Seleccionar Top N riesgos
    top_riesgos = ranking.head(top_n).copy()

    codigos_top = top_riesgos["codigo_riesgo"].tolist()

    # 6. Matriz riesgo-criterio solo para Top N
    df_top = df_eval[df_eval["codigo_riesgo"].isin(codigos_top)].copy()

    matriz_riesgo_criterio = df_top.pivot_table(
        index=["codigo_riesgo", "riesgo"],
        columns="codigo_criterio",
        values="defuzzificado_promedio",
        aggfunc="mean"
    ).reset_index()

    # 7. Ordenar matriz según ranking
    orden = {codigo: i for i, codigo in enumerate(codigos_top)}

    matriz_riesgo_criterio["orden"] = matriz_riesgo_criterio["codigo_riesgo"].map(orden)

    matriz_riesgo_criterio = (
        matriz_riesgo_criterio
        .sort_values("orden")
        .drop(columns=["orden"])
        .reset_index(drop=True)
    )

    return top_riesgos, matriz_riesgo_criterio, pesos_base, None
