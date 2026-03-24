"""
midi_analyzer.py
Análisis previo del contenido MIDI antes de aplicar reglas YAML.

Posición en el pipeline:
    midi_parser.leer_midi()
        → midi_analyzer.analizar()      ← NUEVO
            → rule_engine.separar_voces_con_reglas()
                → exporter / metrics

Qué aporta:
  - Rango real de pitches del MIDI (global y por capa de registro)
  - Distribución de polifonía: qué % del tiempo hay 1, 2, 3... voces
  - Verificación de compatibilidad entre el MIDI y los rangos del YAML
  - Número y tipo de pistas/instrumentos detectados
  - Aviso de conflictos antes de procesar (rangos imposibles, etc.)
"""

from collections import Counter
from utils import snap


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_name(n):
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


# ═══════════════════════════════════════════════════════════════════
# Análisis principal
# ═══════════════════════════════════════════════════════════════════

def analizar(todas_notas, drum_notas, tempo_bpm, info, reglas=None):
    """
    Analiza el contenido del MIDI y, si se proporciona el YAML de reglas,
    verifica la compatibilidad entre el MIDI y los rangos definidos.

    Parámetros:
        todas_notas : lista de dicts con pitch, offset, duration, velocity
        drum_notas  : ídem para batería
        tempo_bpm   : tempo del archivo
        info        : dict de metadata de midi_parser
        reglas      : dict cargado con rule_engine.cargar_reglas() (opcional)

    Retorna:
        dict con:
            pitches          : lista de todos los pitches
            rango_global     : (min, max)
            capas            : dict con rango por cuartil de registro
            polifonia        : Counter {n_voces: cantidad_de_momentos}
            polifonia_pct    : {n_voces: porcentaje}
            instrumentos     : lista de strings
            compatibilidad   : lista de dicts (solo si se pasa reglas)
            advertencias     : lista de strings con problemas detectados
    """
    pitches = [n["pitch"] for n in todas_notas]
    if not pitches:
        return {"advertencias": ["El MIDI no contiene notas musicales."]}

    resultado = {}
    resultado["pitches"]      = pitches
    resultado["rango_global"] = (min(pitches), max(pitches))
    resultado["capas"]        = _calcular_capas(pitches)
    resultado["polifonia"], resultado["polifonia_pct"] = _calcular_polifonia(todas_notas)
    resultado["instrumentos"] = info.get("instrumentos", [])
    resultado["tempo_bpm"]    = tempo_bpm
    resultado["compas"]       = info.get("time_signature", "4/4")
    resultado["advertencias"] = []

    if reglas:
        resultado["compatibilidad"] = _verificar_compatibilidad(pitches, reglas)
        resultado["advertencias"]   = _generar_advertencias(resultado, reglas)

    return resultado


# ═══════════════════════════════════════════════════════════════════
# Cálculo de capas de registro
# ═══════════════════════════════════════════════════════════════════

def _calcular_capas(pitches):
    """
    Divide el rango en capas por cuartiles.
    Útil para comparar con los rangos de las voces del YAML.
    """
    s = sorted(pitches)
    n = len(s)
    return {
        "alta":  (s[n * 3 // 4], s[-1]),
        "media": (s[n // 4],     s[n * 3 // 4]),
        "baja":  (s[0],          s[n // 4]),
    }


# ═══════════════════════════════════════════════════════════════════
# Distribución de polifonía
# ═══════════════════════════════════════════════════════════════════

def _calcular_polifonia(todas_notas):
    """
    Reconstruye el estado de notas activas a lo largo del tiempo
    y cuenta cuántos momentos hay con 1, 2, 3... voces simultáneas.

    Usa los offsets snapeados de las notas como puntos de muestreo.
    """
    if not todas_notas:
        return Counter(), {}

    # Construir eventos (inicio y fin de cada nota)
    eventos = []
    for n in todas_notas:
        eventos.append((n["offset"],              +1, n["pitch"]))
        eventos.append((n["offset"] + n["duration"], -1, n["pitch"]))

    eventos.sort(key=lambda x: (x[0], x[1]))

    conteo = Counter()
    activas = 0
    prev_tiempo = None

    for tiempo, delta, _ in eventos:
        if prev_tiempo is not None and tiempo != prev_tiempo:
            conteo[activas] += 1
        activas += delta
        activas = max(0, activas)
        prev_tiempo = tiempo

    total = sum(conteo.values()) or 1
    polifonia_pct = {k: round(v / total * 100, 1) for k, v in conteo.items()}
    return conteo, polifonia_pct


# ═══════════════════════════════════════════════════════════════════
# Compatibilidad MIDI ↔ YAML
# ═══════════════════════════════════════════════════════════════════

def _transpone_al_rango(pitch, rango_min, rango_max):
    """Replica la lógica de _clampar del rule_engine."""
    p = pitch
    while p < rango_min:
        p += 12
    while p > rango_max:
        p -= 12
    return p, rango_min <= p <= rango_max


def _verificar_compatibilidad(pitches, reglas):
    """
    Para cada voz del YAML, calcula qué % de las notas del MIDI
    puede entrar en ese rango mediante transposición por octavas.

    Retorna lista de dicts con la información por voz.
    """
    voces_cfg = reglas.get("voces", {})
    resultado = []

    for nombre, cfg in voces_cfg.items():
        rmin, rmax = cfg["rango_midi"]
        ancho = rmax - rmin

        ok = sum(1 for p in pitches if _transpone_al_rango(p, rmin, rmax)[1])
        pct = ok / len(pitches) * 100

        # Ejemplos de pitches que no entran
        ejemplos_fuera = [
            midi_to_name(p)
            for p in pitches
            if not _transpone_al_rango(p, rmin, rmax)[1]
        ]
        # Deduplicar y limitar
        ejemplos_fuera = list(dict.fromkeys(ejemplos_fuera))[:5]

        resultado.append({
            "voz":             nombre,
            "rango_midi":      (rmin, rmax),
            "rango_str":       f"{midi_to_name(rmin)}–{midi_to_name(rmax)}",
            "ancho_st":        ancho,
            "rango_menor_octava": ancho < 12,
            "pct_transportable":  round(pct, 1),
            "ejemplos_fuera":  ejemplos_fuera,
        })

    return resultado


# ═══════════════════════════════════════════════════════════════════
# Advertencias automáticas
# ═══════════════════════════════════════════════════════════════════

def _generar_advertencias(resultado, reglas):
    advertencias = []
    voces_cfg = reglas.get("voces", {})
    n_voces = len(voces_cfg)

    # 1. Polifonía máxima del MIDI vs. número de voces del YAML
    max_voces_midi = max(resultado["polifonia"].keys(), default=0)
    if max_voces_midi > n_voces:
        advertencias.append(
            f"El MIDI tiene momentos con {max_voces_midi} voces simultáneas, "
            f"pero el YAML define solo {n_voces} voces. "
            f"Las notas extra se descartarán."
        )

    # 2. Rangos menores a una octava
    for item in resultado.get("compatibilidad", []):
        if item["rango_menor_octava"]:
            advertencias.append(
                f"Rango de '{item['voz']}' ({item['ancho_st']} st) "
                f"es menor a una octava — la transposición puede fallar "
                f"para algunos pitches. Considera ampliar el rango."
            )

    # 3. Voces con baja transportabilidad
    for item in resultado.get("compatibilidad", []):
        pct = item["pct_transportable"]
        if pct < 95:
            nivel = "⚠" if pct >= 70 else "✗"
            ej = ", ".join(item["ejemplos_fuera"]) if item["ejemplos_fuera"] else "—"
            advertencias.append(
                f"{nivel} '{item['voz']}': solo {pct}% de las notas del MIDI "
                f"caben en [{item['rango_midi'][0]}, {item['rango_midi'][1]}]. "
                f"Notas problemáticas: {ej}."
            )

    return advertencias


# ═══════════════════════════════════════════════════════════════════
# Presentación (para la GUI y para logs)
# ═══════════════════════════════════════════════════════════════════

def imprimir_analisis(resultado):
    """Imprime el análisis en consola. La GUI puede leer resultado directamente."""
    rg = resultado["rango_global"]
    print(f"\n{'═'*55}")
    print(f"  ANÁLISIS DEL MIDI")
    print(f"{'═'*55}")
    print(f"  Tempo      : {resultado['tempo_bpm']:.1f} BPM  |  Compás: {resultado['compas']}")
    print(f"  Rango total: {midi_to_name(rg[0])} – {midi_to_name(rg[1])}  "
          f"[{rg[0]}, {rg[1]}]")

    capas = resultado["capas"]
    print(f"  Capa alta  : {midi_to_name(capas['alta'][0])} – {midi_to_name(capas['alta'][1])}")
    print(f"  Capa media : {midi_to_name(capas['media'][0])} – {midi_to_name(capas['media'][1])}")
    print(f"  Capa baja  : {midi_to_name(capas['baja'][0])} – {midi_to_name(capas['baja'][1])}")

    print(f"\n  Distribución de polifonía:")
    for k in sorted(resultado["polifonia_pct"]):
        if k == 0:
            continue
        pct = resultado["polifonia_pct"][k]
        bar = "█" * int(pct / 3)
        print(f"    {k} voz{'es' if k > 1 else '  '}: {pct:5.1f}%  {bar}")

    if resultado.get("compatibilidad"):
        print(f"\n  Compatibilidad con rangos YAML:")
        for item in resultado["compatibilidad"]:
            pct = item["pct_transportable"]
            estado = "✓" if pct >= 95 else ("△" if pct >= 70 else "✗")
            print(f"    {estado}  {item['voz']:10s}  {item['rango_str']:12s}  "
                  f"{pct:5.1f}% transportable")

    if resultado.get("advertencias"):
        print(f"\n  Advertencias:")
        for adv in resultado["advertencias"]:
            print(f"    • {adv}")

    print(f"{'═'*55}\n")