"""
marimba_range.py
Define los rangos de cada voz para marimba y transpone por octavas.
"""

# Rangos MIDI por voz (lo, hi) — rango real de marimba de concierto
RANGOS = {
    0: (67, 84),   # Soprano: G4 - C6
    1: (55, 72),   # Alto:    G3 - C5
    2: (43, 60),   # Tenor:   G2 - C4
    3: (31, 48),   # Bajo:    G1 - C3
}

NOMBRES_VOCES = ["Soprano", "Alto", "Tenor", "Bajo"]


def clampar(pitch, voz):
    """
    Transpone un pitch por octavas hasta que quede dentro
    del rango correcto de la voz indicada.
    """
    lo, hi = RANGOS[voz]
    while pitch < lo:
        pitch += 12
    while pitch > hi:
        pitch -= 12
    return pitch


def esta_en_rango(pitch, voz):
    """Verifica si un pitch ya está dentro del rango de la voz."""
    lo, hi = RANGOS[voz]
    return lo <= pitch <= hi


def rango_como_string(voz):
    """Retorna el rango de una voz como string legible."""
    from music21 import note as m21note
    lo, hi = RANGOS[voz]
    lo_str = m21note.Note(lo).nameWithOctave
    hi_str = m21note.Note(hi).nameWithOctave
    return f"{lo_str} - {hi_str}"
