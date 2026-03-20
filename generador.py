"""
generar_midis_prueba.py
Genera archivos MIDI de prueba para testear el pipeline de arreglos.

Casos incluidos:
  1. melodia_simple       — melodía monofónica en Do mayor (1 nota a la vez)
  2. acordes_piano        — progresión I-IV-V-I con acordes de 3 notas (piano)
  3. melodia_con_bajo     — melodía + línea de bajo simultáneos (2 notas)
  4. textura_cuatro_voces — 4 voces simultáneas tipo coral
  5. tusa_simulada        — patrón rítmico pop estilo Tusa (Ab mayor, 4/4)
  6. saltos_grandes       — melodía con saltos de octava (prueba notas de paso)
  7. notas_mixtas         — mezcla de 1, 2, 3 y 4 notas (prueba todos los casos)

Uso:
  python generar_midis_prueba.py
  → genera carpeta midis_prueba/ con todos los archivos
"""

import os
import pretty_midi

OUTPUT_DIR = "midis_prueba"
TEMPO      = 120.0   # BPM para todos los casos


def guardar(midi, nombre):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{nombre}.mid")
    midi.write(path)
    print(f"  ✓ {path}")
    return path


def nota(pitch, start, end, velocity=80):
    """Crea una pretty_midi.Note."""
    return pretty_midi.Note(
        velocity=velocity,
        pitch=pitch,
        start=start,
        end=end,
    )


def beat(n, tempo=TEMPO):
    """Convierte N beats a segundos."""
    return n * (60.0 / tempo)


# ═══════════════════════════════════════════════════════════════════
# 1. Melodía simple — Do mayor ascendente y descendente
#    Prueba: caso de 1 nota — el motor genera las 4 voces
# ═══════════════════════════════════════════════════════════════════
def generar_melodia_simple():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")  # Piano acústico

    # Escala de Do mayor: C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4
    escala = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]
    for i, pitch in enumerate(escala):
        t = beat(i)
        inst.notes.append(nota(pitch, t, t + beat(0.9)))

    midi.instruments.append(inst)
    guardar(midi, "1_melodia_simple")


# ═══════════════════════════════════════════════════════════════════
# 2. Acordes de piano — progresión I-IV-V-I en Do mayor
#    Prueba: caso de 3 notas simultáneas
# ═══════════════════════════════════════════════════════════════════
def generar_acordes_piano():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")

    # I=C maj, IV=F maj, V=G maj, I=C maj — 2 compases cada uno
    acordes = [
        [60, 64, 67],   # C mayor (Do-Mi-Sol)
        [65, 69, 72],   # F mayor (Fa-La-Do)
        [67, 71, 74],   # G mayor (Sol-Si-Re)
        [60, 64, 67],   # C mayor (vuelta)
    ]
    for i, acorde in enumerate(acordes):
        t = beat(i * 2)
        for p in acorde:
            inst.notes.append(nota(p, t, t + beat(1.9)))

    midi.instruments.append(inst)
    guardar(midi, "2_acordes_piano")


# ═══════════════════════════════════════════════════════════════════
# 3. Melodía con bajo — 2 notas simultáneas
#    Prueba: caso de 2 notas — motor genera Alto y Tenor
# ═══════════════════════════════════════════════════════════════════
def generar_melodia_con_bajo():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")

    # Melodía en soprano + bajo armónico
    pares = [
        (72, 48),  # C5 + C3
        (71, 47),  # B4 + B2
        (69, 45),  # A4 + A2
        (67, 43),  # G4 + G2
        (65, 41),  # F4 + F2
        (64, 40),  # E4 + E2
        (62, 38),  # D4 + D2
        (60, 36),  # C4 + C2
    ]
    for i, (mel, bas) in enumerate(pares):
        t = beat(i)
        inst.notes.append(nota(mel, t, t + beat(0.9), velocity=85))
        inst.notes.append(nota(bas, t, t + beat(0.9), velocity=70))

    midi.instruments.append(inst)
    guardar(midi, "3_melodia_con_bajo")


# ═══════════════════════════════════════════════════════════════════
# 4. Textura de 4 voces — tipo coral (SATB)
#    Prueba: caso de 4+ notas — asignación directa
# ═══════════════════════════════════════════════════════════════════
def generar_cuatro_voces():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")

    # Progresión coral simple: 4 voces por acorde
    # [Soprano, Alto, Tenor, Bajo]
    coral = [
        [72, 67, 64, 48],   # C5, G4, E4, C3  — C mayor
        [71, 67, 62, 47],   # B4, G4, D4, B2  — G mayor
        [69, 65, 60, 45],   # A4, F4, C4, A2  — F mayor
        [67, 64, 59, 43],   # G4, E4, B3, G2  — G mayor 2da inv
        [72, 67, 64, 48],   # C mayor — vuelta
    ]
    for i, voces in enumerate(coral):
        t = beat(i * 2)
        for p in voces:
            inst.notes.append(nota(p, t, t + beat(1.9)))

    midi.instruments.append(inst)
    guardar(midi, "4_cuatro_voces_coral")


# ═══════════════════════════════════════════════════════════════════
# 5. Tusa simulada — estilo pop latino en Ab mayor
#    Prueba: perfil reglas_tusa_pop.yaml
#    Progresión: vi-IV-I-V (Am-F-C-G en relativa Do mayor)
# ═══════════════════════════════════════════════════════════════════
def generar_tusa_simulada():
    midi = pretty_midi.PrettyMIDI(initial_tempo=130)  # pop es más rápido
    inst = pretty_midi.Instrument(program=0, name="Piano")

    # Progresión vi-IV-I-V en Ab mayor = Fm-Db-Ab-Eb
    # Simplificado a Do mayor relativa: Am-F-C-G
    beat_s = 60.0 / 130.0

    # Patrón rítmico: acordes en tiempos 1 y 3, bajo en 1
    progresion = [
        # (bajo, acorde_3_notas) — 1 compás = 4 beats
        (45, [69, 72, 76]),   # Am: A2, A4, C5, E5
        (41, [65, 69, 72]),   # F:  F2, F4, A4, C5
        (36, [60, 64, 67]),   # C:  C2, C4, E4, G4
        (43, [67, 71, 74]),   # G:  G2, G4, B4, D5
    ]

    t = 0.0
    for bajo_p, acorde in progresion:
        dur = beat_s * 4  # 1 compás

        # Bajo en tiempo 1 y 3
        inst.notes.append(nota(bajo_p, t,              t + beat_s * 0.9, velocity=90))
        inst.notes.append(nota(bajo_p, t + beat_s * 2, t + beat_s * 2.9, velocity=80))

        # Acorde en tiempo 1
        for p in acorde:
            inst.notes.append(nota(p, t, t + beat_s * 1.9, velocity=75))

        # Acorde en tiempo 3 (syncopado — empieza un poco antes)
        for p in acorde:
            inst.notes.append(nota(p, t + beat_s * 1.75, t + beat_s * 3.9, velocity=70))

        t += dur

    midi.instruments.append(inst)
    guardar(midi, "5_tusa_pop_simulada")


# ═══════════════════════════════════════════════════════════════════
# 6. Saltos grandes — prueba de notas de paso en el bajo
#    Melodía con saltos de octava y más
# ═══════════════════════════════════════════════════════════════════
def generar_saltos_grandes():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")

    # Melodía con saltos grandes — prueba el suavizado del bajo
    melodia = [
        (72, 1.0),   # C5
        (48, 1.0),   # C3  — salto de 2 octavas
        (71, 1.0),   # B4
        (47, 1.0),   # B2  — salto de 2 octavas
        (67, 2.0),   # G4
        (43, 2.0),   # G2  — salto de 2 octavas
        (72, 2.0),   # C5
    ]
    t = 0.0
    for pitch, dur in melodia:
        inst.notes.append(nota(pitch, t, t + dur * (60.0/TEMPO) * 0.9))
        t += dur * (60.0/TEMPO)

    midi.instruments.append(inst)
    guardar(midi, "6_saltos_grandes")


# ═══════════════════════════════════════════════════════════════════
# 7. Notas mixtas — ejercicio completo que prueba TODOS los casos
#    Combina: 1 nota, 2 notas, 3 notas y 4 notas en secuencia
# ═══════════════════════════════════════════════════════════════════
def generar_notas_mixtas():
    midi = pretty_midi.PrettyMIDI(initial_tempo=TEMPO)
    inst = pretty_midi.Instrument(program=0, name="Piano")

    b = 60.0 / TEMPO
    t = 0.0

    # Compás 1: 1 nota sola
    inst.notes.append(nota(67, t, t + b * 0.9))          # G4
    t += b

    # Compás 2: 2 notas simultáneas
    inst.notes.append(nota(72, t, t + b * 0.9))          # C5
    inst.notes.append(nota(48, t, t + b * 0.9))          # C3
    t += b

    # Compás 3: 3 notas simultáneas
    inst.notes.append(nota(72, t, t + b * 0.9))          # C5
    inst.notes.append(nota(67, t, t + b * 0.9))          # G4
    inst.notes.append(nota(48, t, t + b * 0.9))          # C3
    t += b

    # Compás 4: 4 notas simultáneas
    inst.notes.append(nota(72, t, t + b * 0.9))          # C5
    inst.notes.append(nota(67, t, t + b * 0.9))          # G4
    inst.notes.append(nota(64, t, t + b * 0.9))          # E4
    inst.notes.append(nota(48, t, t + b * 0.9))          # C3
    t += b

    # Compás 5-8: repetir con otra tonalidad (Sol mayor)
    t += b  # silencio

    inst.notes.append(nota(71, t, t + b * 0.9))          # B4 — 1 nota
    t += b

    inst.notes.append(nota(74, t, t + b * 0.9))          # D5
    inst.notes.append(nota(43, t, t + b * 0.9))          # G2
    t += b

    inst.notes.append(nota(74, t, t + b * 0.9))          # D5
    inst.notes.append(nota(71, t, t + b * 0.9))          # B4
    inst.notes.append(nota(43, t, t + b * 0.9))          # G2
    t += b

    inst.notes.append(nota(74, t, t + b * 0.9))          # D5
    inst.notes.append(nota(71, t, t + b * 0.9))          # B4
    inst.notes.append(nota(67, t, t + b * 0.9))          # G4
    inst.notes.append(nota(43, t, t + b * 0.9))          # G2
    t += b

    midi.instruments.append(inst)
    guardar(midi, "7_notas_mixtas")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n Generando MIDIs de prueba...\n")

    generar_melodia_simple()
    generar_acordes_piano()
    generar_melodia_con_bajo()
    generar_cuatro_voces()
    generar_tusa_simulada()
    generar_saltos_grandes()
    generar_notas_mixtas()

    print(f"\n Listo. Archivos en carpeta: {OUTPUT_DIR}/")
    print("""
Guía de uso con el Marimba Arranger:
─────────────────────────────────────────────────────────────
MIDI                       Reglas recomendadas         Qué prueba
─────────────────────────────────────────────────────────────
1_melodia_simple           marimba_guatemalteca        Generación de 4 voces desde 1 nota
2_acordes_piano            marimba_guatemalteca        Distribución de acordes de 3 notas
3_melodia_con_bajo         marimba_guatemalteca        Completar Alto y Tenor en 2 notas
4_cuatro_voces_coral       marimba_guatemalteca        Asignación directa (4+ notas)
5_tusa_pop_simulada        tusa_pop                    Perfil pop: 3ra mayor, snap corchea
6_saltos_grandes           marimba_guatemalteca        Notas de paso en saltos de octava
7_notas_mixtas             marimba_guatemalteca        Todos los casos en un solo archivo
─────────────────────────────────────────────────────────────
""")