"""
midi_parser.py
Lectura robusta de MIDI usando pretty_midi.
Separa automáticamente batería de instrumentos musicales.
"""

import pretty_midi
from utils import snap


# Rango máximo en segundos a procesar (None = todo)
MAX_SECONDS = None


def segundos_a_quarters(seconds, tempo_bpm):
    """Convierte tiempo en segundos a quarter lengths dado un tempo."""
    beats_per_second = tempo_bpm / 60.0
    return seconds * beats_per_second


def leer_midi(archivo, max_seconds=MAX_SECONDS):
    """
    Parsea un archivo MIDI y retorna:
      - todas_notas: lista de dicts con pitch, offset, duration, velocity
      - drum_notas:  mismo formato pero para batería
      - tempo_bpm:   tempo estimado
      - info:        dict con metadata del archivo
    """
    try:
        midi = pretty_midi.PrettyMIDI(archivo)
    except Exception as e:
        raise ValueError(f"No se pudo leer el MIDI: {e}")

    # Estimar tempo
    tempos = midi.get_tempo_changes()
    if len(tempos[1]) > 0:
        tempo_bpm = float(tempos[1][0])
    else:
        tempo_bpm = 120.0

    todas_notas = []
    drum_notas  = []

    for instrumento in midi.instruments:
        for n in instrumento.notes:

            # Filtrar por tiempo máximo
            if max_seconds and n.start > max_seconds:
                continue

            offset_q   = segundos_a_quarters(n.start, tempo_bpm)
            duration_q = segundos_a_quarters(n.end - n.start, tempo_bpm)
            duration_q = max(duration_q, 0.25)  # mínimo semicorchea

            nota = {
                "pitch":      n.pitch,
                "offset":     snap(offset_q),
                "duration":   snap(duration_q),
                "velocity":   n.velocity,
                "instrument": instrumento.name or "Unknown",
            }

            if instrumento.is_drum:
                drum_notas.append(nota)
            else:
                todas_notas.append(nota)

    # Ordenar por offset, luego pitch descendente
    todas_notas.sort(key=lambda x: (x["offset"], -x["pitch"]))
    drum_notas.sort(key=lambda x: x["offset"])

    # Metadata
    info = {
        "tempo_bpm":     tempo_bpm,
        "duracion_seg":  midi.get_end_time(),
        "instrumentos":  [i.name for i in midi.instruments if not i.is_drum],
        "n_notas":       len(todas_notas),
        "n_drum_notas":  len(drum_notas),
        "time_signature": _get_time_signature(midi),
    }

    print(f"[midi_parser] Tempo: {tempo_bpm:.1f} BPM")
    print(f"[midi_parser] Compás: {info['time_signature']}")
    print(f"[midi_parser] Notas musicales: {len(todas_notas)}")
    print(f"[midi_parser] Notas de batería: {len(drum_notas)}")
    print(f"[midi_parser] Instrumentos: {info['instrumentos']}")

    return todas_notas, drum_notas, tempo_bpm, info


def _get_time_signature(midi):
    """Extrae el time signature del MIDI, default 4/4."""
    if midi.time_signature_changes:
        ts = midi.time_signature_changes[0]
        return f"{ts.numerator}/{ts.denominator}"
    return "4/4"
