"""
utils.py
Funciones auxiliares: snap al grid y agrupación temporal.
"""

def snap(offset, grid=0.25):
    """Redondea un offset al grid musical más cercano (default: semicorchea)."""
    return round(offset / grid) * grid


def agrupar_por_tiempo(notas, tolerance=0.05):
    """
    Agrupa notas que suenan al mismo tiempo (±tolerance segundos).
    Retorna lista de (offset_snapped, [notas]).
    """
    if not notas:
        return []

    grupos = []
    usadas = [False] * len(notas)

    for i, n in enumerate(notas):
        if usadas[i]:
            continue
        grupo = [n]
        usadas[i] = True
        for j, m in enumerate(notas):
            if not usadas[j] and abs(n["offset"] - m["offset"]) <= tolerance:
                grupo.append(m)
                usadas[j] = True
        grupos.append((snap(n["offset"]), grupo))

    return grupos


def eliminar_duplicados(grupo):
    """Elimina notas con el mismo pitch dentro de un grupo, dejando la más larga."""
    vistos = {}
    for n in grupo:
        p = n["pitch"]
        if p not in vistos or n["duration"] > vistos[p]["duration"]:
            vistos[p] = n
    return sorted(vistos.values(), key=lambda x: -x["pitch"])
