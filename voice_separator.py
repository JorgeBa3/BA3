"""
voice_separator.py
Algoritmo de separación armónica en 4 voces.
Este es el aporte central del paper.

Estrategia por número de notas simultáneas:
  4+ notas → asignar directo agudo→grave
  3 notas  → Soprano, Alto, Bajo + Tenor generado (cuarta abajo del Alto)
  2 notas  → Soprano y Bajo fijos + Alto (3ra menor) y Tenor (5ta) generados
  1 nota   → generar las 4 voces: original, -3, -7, -12

Post-procesamiento del Bajo:
  - Las duraciones se extienden para llenar el silencio hasta la siguiente nota
    (bajo sostenido, sin negras sueltas).
  - Si hay un salto ≥ octava entre dos notas consecutivas y hay espacio libre,
    se interpola una nota de paso cromática/diatónica para suavizar el movimiento.
"""

from utils import agrupar_por_tiempo, eliminar_duplicados
from marimba_range import clampar, NOMBRES_VOCES


# Duración mínima de una nota del bajo (negra = 1.0 quarter)
MIN_DUR_BAJO = 1.0
# Umbral de salto (en semitonos) a partir del cual se genera nota de paso
UMBRAL_SALTO_BAJO = 12


def separar_voces(todas_notas, tolerance=0.05):
    """
    Recibe lista de notas y retorna lista de 4 listas (una por voz).
    Cada nota es un dict con pitch, offset, duration.
    """
    grupos = agrupar_por_tiempo(todas_notas, tolerance=tolerance)

    voces = [[], [], [], []]  # Soprano, Alto, Tenor, Bajo

    for offset, grupo in grupos:
        unicos = eliminar_duplicados(grupo)  # ordenados agudo→grave
        n = len(unicos)
        dur = unicos[0]["duration"]

        if n >= 4:
            _asignar_4_o_mas(voces, unicos, offset)

        elif n == 3:
            _asignar_3(voces, unicos, offset, dur)

        elif n == 2:
            _asignar_2(voces, unicos, offset, dur)

        elif n == 1:
            _asignar_1(voces, unicos, offset, dur)

    # Post-procesamiento del bajo: extender duraciones + notas de paso
    voces[3] = _mejorar_bajo(voces[3])

    # Log distribución
    for i, voz in enumerate(voces):
        print(f"[voice_separator] {NOMBRES_VOCES[i]}: {len(voz)} notas")

    return voces


# -------------------------
# Estrategias de asignación
# -------------------------

def _asignar_4_o_mas(voces, unicos, offset):
    """4+ notas: asignar las 4 más extremas por registro."""
    for i in range(4):
        voces[i].append({
            "pitch":    clampar(unicos[i]["pitch"], i),
            "offset":   offset,
            "duration": unicos[i]["duration"],
        })


def _asignar_3(voces, unicos, offset, dur):
    """
    3 notas: Soprano, Alto, Bajo directos.
    Tenor generado como cuarta justa abajo del Alto.
    """
    voces[0].append({"pitch": clampar(unicos[0]["pitch"],     0), "offset": offset, "duration": dur})
    voces[1].append({"pitch": clampar(unicos[1]["pitch"],     1), "offset": offset, "duration": dur})
    voces[2].append({"pitch": clampar(unicos[1]["pitch"] - 5, 2), "offset": offset, "duration": dur})
    voces[3].append({"pitch": clampar(unicos[2]["pitch"],     3), "offset": offset, "duration": dur})


def _asignar_2(voces, unicos, offset, dur):
    """
    2 notas: Soprano y Bajo fijos.
    Alto = tercera menor abajo del Soprano.
    Tenor = quinta justa abajo del Soprano.
    """
    voces[0].append({"pitch": clampar(unicos[0]["pitch"],     0), "offset": offset, "duration": dur})
    voces[1].append({"pitch": clampar(unicos[0]["pitch"] - 3, 1), "offset": offset, "duration": dur})
    voces[2].append({"pitch": clampar(unicos[0]["pitch"] - 7, 2), "offset": offset, "duration": dur})
    voces[3].append({"pitch": clampar(unicos[1]["pitch"],     3), "offset": offset, "duration": dur})


def _asignar_1(voces, unicos, offset, dur):
    """
    1 nota: generar armonía completa.
    Soprano: original
    Alto:    tercera menor abajo  (-3)
    Tenor:   quinta justa abajo   (-7)
    Bajo:    octava abajo         (-12)
    """
    p = unicos[0]["pitch"]
    voces[0].append({"pitch": clampar(p,      0), "offset": offset, "duration": dur})
    voces[1].append({"pitch": clampar(p - 3,  1), "offset": offset, "duration": dur})
    voces[2].append({"pitch": clampar(p - 7,  2), "offset": offset, "duration": dur})
    voces[3].append({"pitch": clampar(p - 12, 3), "offset": offset, "duration": dur})


# -------------------------
# Post-procesamiento del Bajo
# -------------------------

def _mejorar_bajo(notas_bajo):
    """
    Mejora la línea del bajo en dos pasos:

    1. Extender duración de cada nota para cubrir el silencio hasta
       la siguiente (bajo sostenido, más cantábile).
    2. Interpolar notas de paso cuando el salto entre dos notas
       consecutivas es >= UMBRAL_SALTO_BAJO semitonos y hay espacio
       suficiente entre ellas (>= 2 quarter notes libres).

    Retorna la lista de notas del bajo mejorada, ordenada por offset.
    """
    from utils import snap

    if not notas_bajo:
        return notas_bajo

    # Ordenar por offset
    notas = sorted(notas_bajo, key=lambda x: x["offset"])

    # ── Paso 1: extender duraciones ──────────────────────────────────
    for i in range(len(notas) - 1):
        gap = notas[i + 1]["offset"] - notas[i]["offset"]
        # Llenar el gap completo, respetando duración mínima
        nueva_dur = max(gap, MIN_DUR_BAJO)
        notas[i]["duration"] = snap(nueva_dur)

    # Última nota: garantizar duración mínima
    notas[-1]["duration"] = max(notas[-1]["duration"], MIN_DUR_BAJO)

    # ── Paso 2: notas de paso en saltos grandes ──────────────────────
    resultado = []
    for i, nota_actual in enumerate(notas):
        resultado.append(nota_actual)

        if i >= len(notas) - 1:
            break

        nota_sig = notas[i + 1]
        salto    = nota_sig["pitch"] - nota_actual["pitch"]   # con signo
        abs_salto = abs(salto)

        # Solo intervenir si el salto es grande y hay espacio >= 2 quarters
        espacio = nota_sig["offset"] - nota_actual["offset"]
        if abs_salto < UMBRAL_SALTO_BAJO or espacio < 2.0:
            continue

        # Calcular pitch de nota de paso: mitad del camino (redondeado)
        paso_pitch = nota_actual["pitch"] + salto // 2
        paso_pitch = clampar(paso_pitch, 3)

        # Colocar la nota de paso a la mitad del espacio disponible
        paso_offset   = snap(nota_actual["offset"] + espacio / 2)
        paso_duration = snap(espacio / 2)
        paso_duration = max(paso_duration, MIN_DUR_BAJO)

        # Ajustar duración de la nota anterior para no solapar
        resultado[-1]["duration"] = snap(espacio / 2)

        resultado.append({
            "pitch":    paso_pitch,
            "offset":   paso_offset,
            "duration": paso_duration,
        })

    return sorted(resultado, key=lambda x: x["offset"])