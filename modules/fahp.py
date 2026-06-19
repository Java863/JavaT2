import itertools
import numpy as np
import pandas as pd


ESCALA_FAHP = {
    "Igual importancia": (1.0, 1.0, 1.0),
    "Moderada": (2.0, 3.0, 4.0),
    "Fuerte": (4.0, 5.0, 6.0),
    "Muy fuerte": (6.0, 7.0, 8.0),
    "Extrema": (8.0, 9.0, 10.0),
}


def generar_pares_criterios(criterios: pd.DataFrame):
    """
    Genera todas las comparaciones por pares entre criterios.
    """
    registros = criterios.to_dict(orient="records")
    return list(itertools.combinations(registros, 2))


def obtener_tfn(intensidad: str):
    """
    Devuelve el número difuso triangular asociado a una intensidad lingüística.
    """
    return ESCALA_FAHP[intensidad]


def invertir_tfn(tfn):
    """
    Calcula el recíproco de un número difuso triangular.
    Si A = (l, m, u), entonces A^-1 = (1/u, 1/m, 1/l)
    """
    l, m, u = tfn
    return (1 / u, 1 / m, 1 / l)


def construir_matriz_difusa(criterios: pd.DataFrame, respuestas: pd.DataFrame):
    """
    Construye la matriz difusa recíproca de comparación por pares.

    Retorna:
    - matriz_l
    - matriz_m
    - matriz_u
    - matriz_texto
    """
    codigos = criterios["Codigo"].tolist()
    n = len(codigos)

    idx = {codigo: i for i, codigo in enumerate(codigos)}

    matriz_l = np.ones((n, n))
    matriz_m = np.ones((n, n))
    matriz_u = np.ones((n, n))

    matriz_texto = pd.DataFrame("", index=codigos, columns=codigos)

    for c in codigos:
        matriz_texto.loc[c, c] = "(1, 1, 1)"

    for _, row in respuestas.iterrows():
        ci = row["criterio_i"]
        cj = row["criterio_j"]
        preferido = row["criterio_preferido"]
        intensidad = row["intensidad"]

        tfn = obtener_tfn(intensidad)

        i = idx[ci]
        j = idx[cj]

        if preferido == ci:
            valor_ij = tfn
            valor_ji = invertir_tfn(tfn)
        elif preferido == cj:
            valor_ij = invertir_tfn(tfn)
            valor_ji = tfn
        else:
            valor_ij = (1.0, 1.0, 1.0)
            valor_ji = (1.0, 1.0, 1.0)

        matriz_l[i, j], matriz_m[i, j], matriz_u[i, j] = valor_ij
        matriz_l[j, i], matriz_m[j, i], matriz_u[j, i] = valor_ji

        matriz_texto.loc[ci, cj] = f"({valor_ij[0]:.4f}, {valor_ij[1]:.4f}, {valor_ij[2]:.4f})"
        matriz_texto.loc[cj, ci] = f"({valor_ji[0]:.4f}, {valor_ji[1]:.4f}, {valor_ji[2]:.4f})"

    return matriz_l, matriz_m, matriz_u, matriz_texto


def matriz_central_para_cr(matriz_m):
    """
    Devuelve la matriz crisp usando los valores centrales m.
    """
    return matriz_m


def calcular_pesos_crisp(matriz):
    """
    Calcula pesos aproximados mediante normalización por columnas.
    """
    matriz = np.array(matriz, dtype=float)
    matriz_norm = matriz / matriz.sum(axis=0)
    pesos = matriz_norm.mean(axis=1)
    return pesos


def calcular_cr(matriz):
    """
    Calcula CI y CR para una matriz crisp.
    """
    matriz = np.array(matriz, dtype=float)
    n = matriz.shape[0]

    valores_propios, _ = np.linalg.eig(matriz)
    lambda_max = np.max(np.real(valores_propios))

    ci = (lambda_max - n) / (n - 1)

    ri_tabla = {
        1: 0.00,
        2: 0.00,
        3: 0.58,
        4: 0.90,
        5: 1.12,
        6: 1.24,
        7: 1.32,
        8: 1.41,
        9: 1.45,
        10: 1.49,
    }

    ri = ri_tabla.get(n, 1.49)

    if ri == 0:
        cr = 0
    else:
        cr = ci / ri

    return lambda_max, ci, cr, ri


def detectar_inconsistencias_fuertes(matriz_crisp, criterios: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:

    codigos = criterios["Codigo"].tolist()
    nombres = dict(zip(criterios["Codigo"], criterios["Criterio"]))

    registros = []

    for i, j, k in itertools.combinations(range(len(codigos)), 3):
        ci, cj, ck = codigos[i], codigos[j], codigos[k]

        aij = matriz_crisp[i, j]
        ajk = matriz_crisp[j, k]
        aik = matriz_crisp[i, k]

        if aij <= 0 or ajk <= 0 or aik <= 0:
            continue

        desviacion = abs(np.log(aij) + np.log(ajk) - np.log(aik))

        registros.append({
            "Triada": f"{ci} - {cj} - {ck}",
            "Criterios involucrados": f"{nombres[ci]} | {nombres[cj]} | {nombres[ck]}",
            "Comparación 1": f"{ci} vs {cj}",
            "Comparación 2": f"{cj} vs {ck}",
            "Comparación 3": f"{ci} vs {ck}",
            "Desviación": desviacion
        })

    df = pd.DataFrame(registros)

    if df.empty:
        return df

    return df.sort_values("Desviación", ascending=False).head(top_n)

def agregar_matrices_fahp_global(criterios: pd.DataFrame, respuestas_fahp: pd.DataFrame):
    """
    Construye una matriz FAHP global agregando las matrices individuales
    mediante media geométrica difusa.

    Solo considera los expertos presentes en respuestas_fahp.
    """

    codigos = criterios["Codigo"].tolist()
    n = len(codigos)

    expertos = respuestas_fahp["experto"].unique().tolist()

    matrices_l = []
    matrices_m = []
    matrices_u = []

    for experto in expertos:
        respuestas_experto = respuestas_fahp[
            respuestas_fahp["experto"] == experto
        ]

        matriz_l, matriz_m, matriz_u, _ = construir_matriz_difusa(
            criterios,
            respuestas_experto
        )

        matrices_l.append(matriz_l)
        matrices_m.append(matriz_m)
        matrices_u.append(matriz_u)

    matrices_l = np.array(matrices_l)
    matrices_m = np.array(matrices_m)
    matrices_u = np.array(matrices_u)

    # Media geométrica por celda
    matriz_l_global = np.prod(matrices_l, axis=0) ** (1 / len(expertos))
    matriz_m_global = np.prod(matrices_m, axis=0) ** (1 / len(expertos))
    matriz_u_global = np.prod(matrices_u, axis=0) ** (1 / len(expertos))

    matriz_texto = pd.DataFrame("", index=codigos, columns=codigos)

    for i in range(n):
        for j in range(n):
            matriz_texto.iloc[i, j] = (
                f"({matriz_l_global[i, j]:.4f}, "
                f"{matriz_m_global[i, j]:.4f}, "
                f"{matriz_u_global[i, j]:.4f})"
            )

    return matriz_l_global, matriz_m_global, matriz_u_global, matriz_texto


def calcular_pesos_globales_fahp(criterios: pd.DataFrame, respuestas_fahp: pd.DataFrame):
    """
    Calcula los pesos globales FAHP a partir de todas las respuestas de expertos.
    """

    matriz_l_g, matriz_m_g, matriz_u_g, matriz_texto_g = agregar_matrices_fahp_global(
        criterios,
        respuestas_fahp
    )

    matriz_crisp_global = matriz_central_para_cr(matriz_m_g)

    lambda_max, ci, cr, ri = calcular_cr(matriz_crisp_global)

    pesos = calcular_pesos_crisp(matriz_crisp_global)

    df_pesos_globales = pd.DataFrame({
        "Codigo": criterios["Codigo"],
        "Criterio": criterios["Criterio"],
        "Peso": pesos
    })

    df_pesos_globales["Peso_normalizado"] = (
        df_pesos_globales["Peso"] / df_pesos_globales["Peso"].sum()
    )

    df_pesos_globales = df_pesos_globales.sort_values(
        "Peso_normalizado",
        ascending=False
    )

    return df_pesos_globales, matriz_texto_g, matriz_crisp_global, lambda_max, ci, cr, ri


