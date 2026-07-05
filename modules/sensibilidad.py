import pandas as pd
import numpy as np
import plotly.express as px
import textwrap


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



def generar_escenarios_sensibilidad(
    matriz_riesgo_criterio: pd.DataFrame,
    pesos_base: pd.DataFrame,
    pasos: int = 11
):
    """
    Genera escenarios de sensibilidad para cada criterio.
    El peso del criterio focal varía de 0% a 100%,
    y el peso restante se redistribuye proporcionalmente
    entre los demás criterios según los pesos base.
    """

    df = matriz_riesgo_criterio.copy()

    criterios = pesos_base["codigo_criterio"].tolist()
    nombres_criterios = dict(zip(pesos_base["codigo_criterio"], pesos_base["criterio"]))
    pesos_dict = dict(zip(pesos_base["codigo_criterio"], pesos_base["peso"]))

    escenarios = {}

    for criterio_focal in criterios:
        otros = [c for c in criterios if c != criterio_focal]
        suma_otros_base = sum(pesos_dict[c] for c in otros)

        filas = []

        for peso_focal in np.linspace(0, 1, pasos):
            pesos_nuevos = {}

            # Peso del criterio que se analiza
            pesos_nuevos[criterio_focal] = peso_focal

            # Redistribuir el resto
            restante = 1 - peso_focal

            if len(otros) > 0:
                if suma_otros_base > 0:
                    for c in otros:
                        pesos_nuevos[c] = restante * (pesos_dict[c] / suma_otros_base)
                else:
                    for c in otros:
                        pesos_nuevos[c] = restante / len(otros)

            for _, row in df.iterrows():
                puntaje = 0
                for c in criterios:
                    puntaje += row[c] * pesos_nuevos[c]

                filas.append({
                    "criterio_focal": criterio_focal,
                    "criterio_nombre": nombres_criterios[criterio_focal],
                    "peso_pct": round(peso_focal * 100, 0),
                    "peso_base_pct": pesos_dict[criterio_focal] * 100,
                    "codigo_riesgo": row["codigo_riesgo"],
                    "riesgo": row["riesgo"],
                    "puntaje": puntaje
                })

        df_esc = pd.DataFrame(filas)

        # Normalización tipo porcentaje para graficar similar al paper
        df_esc["score_pct"] = (
            df_esc.groupby("peso_pct")["puntaje"]
            .transform(lambda s: (s / s.max()) * 100 if s.max() != 0 else 0)
        )

        escenarios[criterio_focal] = df_esc

    return escenarios


def graficar_sensibilidad_por_criterio(df_escenario: pd.DataFrame):
    """
    Genera una gráfica de sensibilidad para un criterio.
    """

    df = df_escenario.copy()

    def envolver_texto(texto, ancho=38):
        texto = str(texto)
        return "<br>".join(textwrap.wrap(texto, width=ancho))

    criterio_nombre = df["criterio_nombre"].iloc[0]
    peso_base = df["peso_base_pct"].iloc[0]

    # Etiquetas completas, pero partidas en varias líneas
    df["etiqueta_riesgo"] = df.apply(
        lambda x: f"{x['codigo_riesgo']} - {envolver_texto(x['riesgo'], ancho=42)}",
        axis=1
    )

    # -------- Ajuste dinámico del eje Y --------
    y_min_real = df["score_pct"].min()
    y_max_real = df["score_pct"].max()

    # Redondear hacia abajo y arriba en bloques de 10
    y_min = max(0, np.floor((y_min_real - 5) / 10) * 10)
    y_max = min(100, np.ceil((y_max_real + 2) / 10) * 10)

    # Evitar que el rango salga demasiado corto
    if (y_max - y_min) < 20:
        y_min = max(0, y_min - 10)

    # Ticks del eje Y cada 10
    y_ticks = list(np.arange(y_min, y_max + 1, 10))

    titulo = f"Peso de {criterio_nombre}"

    fig = px.line(
        df,
        x="peso_pct",
        y="score_pct",
        color="etiqueta_riesgo",
        markers=True,
        title=titulo
    )

    # Línea vertical del escenario base
    fig.add_vline(
        x=peso_base,
        line_width=2,
        line_dash="dash",
        line_color="black"
    )

    # Texto vertical de escenario base
    fig.add_annotation(
        x=peso_base,
        y=y_min,
        text="Escenario base",
        showarrow=False,
        textangle=-90,
        xanchor="right",
        yanchor="bottom",
        font=dict(size=11, color="black"),
        bgcolor="rgba(255,255,255,0.6)"
    )

    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=7),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            f"Peso de {criterio_nombre}: " + "%{x}%<br>"
            "Puntaje del riesgo: %{y:.2f}%<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(
            text=titulo,
            x=0.02
        ),
        xaxis_title=f"Peso de {criterio_nombre} (%)",
        yaxis_title="Puntaje del riesgo (%)",
        height=500,
        margin=dict(l=70, r=280, t=70, b=70),
        legend=dict(
            title="Riesgos",
            orientation="v",
            x=1.02,
            y=1.0,
            xanchor="left",
            yanchor="top",
            font=dict(size=11)
        ),
        xaxis=dict(
            range=[0, 100],
            tickmode="array",
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0%", "20%", "40%", "60%", "80%", "100%"]
        ),
        yaxis=dict(
            range=[y_min, y_max],
            tickmode="array",
            tickvals=y_ticks,
            ticktext=[f"{int(v)}%" for v in y_ticks]
        )
    )

    return fig
