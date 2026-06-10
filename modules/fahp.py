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
