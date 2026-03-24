"""
metrics.py
Métricas para evaluar la calidad del arreglo generado.
Compatible con cualquier número de voces y nombres dinámicos.
"""

from marimba_range import RANGOS, NOMBRES_VOCES


def calcular_metricas(voces_antes, voces_despues, nombres_voz=None, rangos_yaml=None):
    """
    Calcula métricas por voz.

    Parámetros:
        voces_antes  : voces originales (no se usan aún, reservado)
        voces_despues: voces procesadas — lista de listas de notas
        nombres_voz  : lista de strings. Si es None, usa NOMBRES_VOCES legacy.
        rangos_yaml  : dict {idx: (lo, hi)} — retornado por rule_engine.
                       Si se pasa, se usa para validar rango en lugar de
                       los rangos hardcodeados de marimba_range.
                       Permite métricas correctas con cualquier perfil YAML.
    """
    if nombres_voz is None:
        nombres_voz = NOMBRES_VOCES[:len(voces_despues)]

    # Construir tabla de rangos efectivos para esta sesión:
    # Prioridad 1 → rangos_yaml (del YAML cargado)
    # Prioridad 2 → RANGOS legacy de marimba_range (compatibilidad)
    # Prioridad 3 → None (sin restricción de rango)
    rangos_efectivos = {}
    for i in range(len(voces_despues)):
        if rangos_yaml and i in rangos_yaml:
            rangos_efectivos[i] = rangos_yaml[i]
        elif i in RANGOS:
            rangos_efectivos[i] = RANGOS[i]
        else:
            rangos_efectivos[i] = None

    resultados = {}
    for i, nombre in enumerate(nombres_voz):
        if i >= len(voces_despues):
            break
        notas = voces_despues[i]

        # Notas en rango
        rango = rangos_efectivos.get(i)
        if rango is not None:
            lo, hi = rango
            en_rango = sum(1 for n in notas if lo <= n["pitch"] <= hi)
        else:
            en_rango = len(notas)   # sin restricción conocida
        pct_rango = (en_rango / len(notas) * 100) if notas else 0

        # Voice leading: promedio de salto entre notas consecutivas
        saltos = []
        notas_ord = sorted(notas, key=lambda x: x["offset"])
        for j in range(1, len(notas_ord)):
            salto = abs(notas_ord[j]["pitch"] - notas_ord[j-1]["pitch"])
            saltos.append(salto)
        vl_promedio = sum(saltos) / len(saltos) if saltos else 0

        # Colisiones: dos notas de la misma voz en el mismo offset
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