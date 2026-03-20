"""
metrics.py
Métricas para evaluar la calidad del arreglo generado.
Compatible con cualquier número de voces y nombres dinámicos.
"""

from marimba_range import RANGOS, NOMBRES_VOCES, esta_en_rango


def calcular_metricas(voces_antes, voces_despues, nombres_voz=None):
    """
    Calcula métricas por voz.
    nombres_voz: lista de strings. Si es None, usa NOMBRES_VOCES legacy.
    """
    if nombres_voz is None:
        nombres_voz = NOMBRES_VOCES[:len(voces_despues)]

    resultados = {}
    for i, nombre in enumerate(nombres_voz):
        if i >= len(voces_despues):
            break
        notas = voces_despues[i]

        # Rango: usar RANGOS legacy si el índice existe, sino usar toda la escala
        if i < len(RANGOS):
            en_rango = sum(1 for n in notas if esta_en_rango(n["pitch"], i))
        else:
            en_rango = len(notas)   # sin restricción de rango conocido
        pct_rango = (en_rango / len(notas) * 100) if notas else 0

        # Voice leading
        saltos = []
        notas_ord = sorted(notas, key=lambda x: x["offset"])
        for j in range(1, len(notas_ord)):
            salto = abs(notas_ord[j]["pitch"] - notas_ord[j-1]["pitch"])
            saltos.append(salto)
        vl_promedio = sum(saltos) / len(saltos) if saltos else 0

        # Colisiones
        offsets = [n["offset"] for n in notas]
        colisiones = len(offsets) - len(set(offsets))

        resultados[nombre] = {
            "total_notas":    len(notas),
            "notas_en_rango": en_rango,
            "pct_en_rango":   round(pct_rango, 2),
            "vl_promedio":    round(vl_promedio, 2),
            "colisiones":     colisiones,
        }

    return resultados


def imprimir_metricas(resultados, titulo="Métricas del arreglo"):
    print(f"\n{'='*55}")
    print(f"  {titulo}")
    print(f"{'='*55}")
    print(f"{'Voz':<12} {'Notas':>6} {'En rango':>10} {'VL prom':>9} {'Colisiones':>11}")
    print(f"{'-'*55}")
    for nombre, m in resultados.items():
        print(
            f"{nombre:<12} "
            f"{m['total_notas']:>6} "
            f"{m['pct_en_rango']:>9.1f}% "
            f"{m['vl_promedio']:>9.2f} "
            f"{m['colisiones']:>11}"
        )
    print(f"{'='*55}\n")


def exportar_csv(resultados, path):
    import csv
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "voz", "total_notas", "notas_en_rango",
            "pct_en_rango", "vl_promedio", "colisiones"
        ])
        writer.writeheader()
        for nombre, m in resultados.items():
            writer.writerow({"voz": nombre, **m})
    print(f"[metrics] CSV guardado en: {path}")