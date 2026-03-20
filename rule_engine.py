"""
rule_engine.py
Motor genérico de reglas YAML para arreglos musicales.

Soporta cualquier instrumento, cualquier número de voces (2-8),
y cualquier configuración de armonización. El perfil de instrumento
es un dato externo, no está hardcodeado.

Conceptos clave:
  - "perfil"  : define las voces, rangos y nombre del instrumento destino
  - "reglas"  : define cómo armonizar, qué restricciones aplicar
  Un archivo YAML puede contener ambos, o separarse en dos archivos.
"""

import yaml
from utils import snap, agrupar_por_tiempo, eliminar_duplicados


# ═══════════════════════════════════════════════════════════════════
# Carga y validación
# ═══════════════════════════════════════════════════════════════════

def cargar_reglas(path):
    """Carga y valida un archivo YAML de reglas/perfil."""
    with open(path, "r", encoding="utf-8") as f:
        reglas = yaml.safe_load(f)
    _validar_reglas(reglas)
    return reglas


def _validar_reglas(reglas):
    """Valida estructura mínima. Lanza ValueError con mensaje claro."""
    if "voces" not in reglas:
        raise ValueError("El archivo de reglas debe tener una sección 'voces'.")
    if not isinstance(reglas["voces"], dict) or len(reglas["voces"]) < 2:
        raise ValueError("Se necesitan al menos 2 voces definidas en 'voces'.")
    for nombre, cfg in reglas["voces"].items():
        if "rango_midi" not in cfg:
            raise ValueError(f"La voz '{nombre}' no tiene 'rango_midi'.")
        if len(cfg["rango_midi"]) != 2:
            raise ValueError(f"'rango_midi' de '{nombre}' debe ser [min, max].")
    if "armonizacion" not in reglas:
        raise ValueError("El archivo de reglas debe tener una sección 'armonizacion'.")


# ═══════════════════════════════════════════════════════════════════
# Motor principal
# ═══════════════════════════════════════════════════════════════════

def separar_voces_con_reglas(todas_notas, reglas):
    """
    Distribuye las notas del MIDI en las voces definidas por las reglas.

    Retorna:
        voces       : lista de listas, una por voz (en orden del YAML)
        nombres_voz : lista de strings con los nombres de cada voz
        rangos      : dict {idx: (lo, hi)} con rangos MIDI
    """
    proc      = reglas.get("procesamiento", {})
    tolerance = proc.get("tolerancia_simultaneidad", 0.05)
    grid      = proc.get("snap_grid", 0.25)

    nombres_voz = list(reglas["voces"].keys())
    n_voces     = len(nombres_voz)
    rangos      = {}
    min_durs    = {}
    for i, nombre in enumerate(nombres_voz):
        cfg = reglas["voces"][nombre]
        rangos[i]   = tuple(cfg["rango_midi"])
        min_durs[i] = cfg.get("duracion_minima", 0.25)

    voces  = [[] for _ in range(n_voces)]
    arm    = reglas["armonizacion"]
    grupos = agrupar_por_tiempo(todas_notas, tolerance=tolerance)

    for offset, grupo in grupos:
        unicos  = eliminar_duplicados(grupo)
        n_notas = len(unicos)
        dur     = unicos[0]["duration"]

        if n_notas >= n_voces:
            _asignar_directo(voces, unicos, offset, rangos, n_voces)
        else:
            _asignar_con_reglas(voces, unicos, offset, dur,
                                rangos, arm, nombres_voz, n_notas)

    # Post-procesamiento por voz
    restricciones = reglas.get("restricciones", {})
    for i, nombre in enumerate(nombres_voz):
        cfg_voz = reglas["voces"][nombre]
        min_dur = min_durs[i]

        # Extender duración si la voz lo pide o si es el bajo y bajo_sostenido=true
        es_bajo = (i == n_voces - 1)
        if cfg_voz.get("extender_duracion", False) or \
           (restricciones.get("bajo_sostenido", False) and es_bajo):
            voces[i] = _extender_duraciones(voces[i], min_dur, grid)

        if restricciones.get("notas_de_paso_en_saltos_grandes", False):
            umbral = restricciones.get("umbral_salto_nota_de_paso", 12)
            voces[i] = _notas_de_paso(voces[i], umbral, rangos[i], min_dur, grid)

    for i, nombre in enumerate(nombres_voz):
        print(f"[rule_engine] {nombre}: {len(voces[i])} notas")

    return voces, nombres_voz, rangos


# ═══════════════════════════════════════════════════════════════════
# Estrategias de asignación
# ═══════════════════════════════════════════════════════════════════

def _asignar_directo(voces, unicos, offset, rangos, n_voces):
    """Hay tantas notas como voces o más: asignación directa agudo→grave."""
    for i in range(n_voces):
        voces[i].append({
            "pitch":    _clampar(unicos[i]["pitch"], i, rangos),
            "offset":   offset,
            "duration": unicos[i]["duration"],
        })


def _asignar_con_reglas(voces, unicos, offset, dur, rangos, arm, nombres_voz, n_notas):
    """
    Hay menos notas que voces.
    Busca la clave correcta en armonizacion y aplica las expresiones.
    """
    clave = f"notas_simultaneas_{n_notas}"
    conf  = arm.get(clave) or arm.get("notas_simultaneas_default") or {}

    # Referencias disponibles para las expresiones YAML
    refs = {
        "original":  unicos[0]["pitch"],
        "voz_aguda": unicos[0]["pitch"],
        "voz_grave": unicos[-1]["pitch"],
        "soprano":   unicos[0]["pitch"],
    }
    for j, u in enumerate(unicos):
        refs[f"voz_{j+1}"] = u["pitch"]
        refs[f"voz_{j}"]   = u["pitch"]

    for i, nombre in enumerate(nombres_voz):
        expr  = conf.get(nombre, _intervalo_default(i))
        pitch = _parse_intervalo(expr, refs)
        pitch = _clampar(pitch, i, rangos)
        refs[nombre] = pitch   # disponible para voces siguientes
        voces[i].append({"pitch": pitch, "offset": offset, "duration": dur})


def _intervalo_default(voz_idx):
    """Fallback cuando no hay regla definida para la combinación."""
    intervalos = [0, -3, -7, -12, -15, -19, -24, -27]
    v = min(voz_idx, len(intervalos) - 1)
    return f"soprano - {abs(intervalos[v])}" if v > 0 else "original"


# ═══════════════════════════════════════════════════════════════════
# Post-procesamiento
# ═══════════════════════════════════════════════════════════════════

def _extender_duraciones(notas, min_dur, grid):
    """Extiende cada nota hasta la siguiente (bajo sostenido)."""
    if not notas:
        return notas
    notas = sorted(notas, key=lambda x: x["offset"])
    for i in range(len(notas) - 1):
        gap = notas[i + 1]["offset"] - notas[i]["offset"]
        notas[i]["duration"] = snap(max(gap, min_dur), grid)
    notas[-1]["duration"] = max(notas[-1]["duration"], min_dur)
    return notas


def _notas_de_paso(notas, umbral, rango, min_dur, grid):
    """Interpola una nota de paso en saltos mayores al umbral."""
    if not notas:
        return notas
    notas = sorted(notas, key=lambda x: x["offset"])
    resultado = []
    for i, nota_actual in enumerate(notas):
        resultado.append(nota_actual)
        if i >= len(notas) - 1:
            break
        nota_sig = notas[i + 1]
        salto    = nota_sig["pitch"] - nota_actual["pitch"]
        espacio  = nota_sig["offset"] - nota_actual["offset"]
        if abs(salto) < umbral or espacio < 2.0:
            continue
        paso_pitch  = _clampar(nota_actual["pitch"] + salto // 2, 0, {0: rango})
        paso_offset = snap(nota_actual["offset"] + espacio / 2, grid)
        paso_dur    = max(snap(espacio / 2, grid), min_dur)
        resultado[-1]["duration"] = snap(espacio / 2, grid)
        resultado.append({"pitch": paso_pitch, "offset": paso_offset, "duration": paso_dur})
    return sorted(resultado, key=lambda x: x["offset"])


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _clampar(pitch, voz_idx, rangos):
    lo, hi = rangos[voz_idx]
    while pitch < lo:
        pitch += 12
    while pitch > hi:
        pitch -= 12
    return pitch


def _parse_intervalo(expr, refs):
    """
    Evalúa expresiones de intervalo del YAML.
    Soporta: "original", "soprano - 7", "alto + 4", "voz_grave - 12", 60
    """
    if isinstance(expr, int):
        return expr
    expr = str(expr).strip()
    for op in ("-", "+"):
        if op in expr:
            partes = expr.split(op, 1)
            ref_nombre = partes[0].strip()
            try:
                intervalo = int(partes[1].strip())
                base = refs.get(ref_nombre, refs.get("soprano", 60))
                return base - intervalo if op == "-" else base + intervalo
            except ValueError:
                pass
    return refs.get(expr, refs.get("soprano", 60))


# ═══════════════════════════════════════════════════════════════════
# Utilidad: listar perfiles disponibles en un directorio
# ═══════════════════════════════════════════════════════════════════

def listar_perfiles(directorio):
    """Escanea un directorio y retorna metadata de cada perfil .yaml."""
    import os
    perfiles = []
    for nombre in os.listdir(directorio):
        if nombre.endswith((".yaml", ".yml")):
            path = os.path.join(directorio, nombre)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    datos = yaml.safe_load(f)
                meta = datos.get("meta", {})
                perfiles.append({
                    "archivo":     nombre,
                    "path":        path,
                    "instrumento": meta.get("instrumento", nombre),
                    "descripcion": meta.get("descripcion", ""),
                    "autor":       meta.get("autor", ""),
                    "n_voces":     len(datos.get("voces", {})),
                })
            except Exception:
                pass
    return sorted(perfiles, key=lambda x: x["instrumento"])