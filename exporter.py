"""
exporter.py
Exporta las voces generadas a MusicXML y MIDI usando music21.
Compatible con cualquier número de voces, nombres dinámicos
e instrumento definido en el YAML.
"""

from music21 import stream, note, meter, tempo, instrument
from utils import snap


# ── Mapa por nombre de voz (clave = lowercase sin espacios) ─────────
# Prioridad 1: coincidencia exacta por nombre de voz
VOZ_MAP = {
    # Cuarteto de cuerdas
    "violin_i":       instrument.Violin,
    "violin_ii":      instrument.Violin,
    "violin":         instrument.Violin,
    "violín_i":       instrument.Violin,
    "violín_ii":      instrument.Violin,
    "viola":          instrument.Viola,
    "cello":          instrument.Violoncello,
    "celo":           instrument.Violoncello,
    # Guitarra
    "melodia":        instrument.AcousticGuitar,
    "armonica":       instrument.AcousticGuitar,
    "bajo_jazz":      instrument.ElectricGuitar,
    "voz_media_1":    instrument.ElectricGuitar,
    "voz_media_2":    instrument.ElectricGuitar,
    # Saxofones
    "alto":           instrument.AltoSaxophone,
    "tenor":          instrument.TenorSaxophone,
    "baritono":       instrument.BaritoneSaxophone,
    "barítono":       instrument.BaritoneSaxophone,
    "soprano_sax":    instrument.SopranoSaxophone,
    # Combo pop/funk
    "lead":           instrument.ElectricPiano,
    "keys":           instrument.ElectricPiano,
    "bajo_electrico": instrument.ElectricBass,
    "bajo_eléctrico": instrument.ElectricBass,
    # Voces genéricas de marimba/teclado
    "soprano":        instrument.Marimba,
    "bajo":           instrument.Marimba,
    "tenor_voz":      instrument.Marimba,
    "alto_voz":       instrument.Marimba,
}

# ── Mapa por meta.instrumento del YAML (keywords en lowercase) ──────
# Prioridad 2: coincidencia por instrumento del perfil
INSTRUMENT_MAP = [
    # Percusión melódica
    (["marimba"],                                 instrument.Marimba),
    (["xilofon", "xylophone", "xilófono"],        instrument.Xylophone),
    (["vibrafono", "vibraphone", "vibráfono"],    instrument.Vibraphone),
    # Cuerdas
    (["cuarteto", "quartet", "string quartet"],   instrument.Violin),
    (["violin", "violín"],                        instrument.Violin),
    (["viola"],                                   instrument.Viola),
    (["cello", "celo", "violoncello"],            instrument.Violoncello),
    (["contrabajo", "double bass", "contrabass"], instrument.Contrabass),
    # Guitarra
    (["guitarra jazz", "guitar jazz",
      "jazz guitar"],                             instrument.ElectricGuitar),
    (["guitarra eléctrica", "electric guitar"],   instrument.ElectricGuitar),
    (["guitarra", "guitar"],                      instrument.AcousticGuitar),
    # Saxofón
    (["saxofon alto", "alto sax",
      "alto saxophone"],                          instrument.AltoSaxophone),
    (["saxofon tenor", "tenor sax"],              instrument.TenorSaxophone),
    (["saxofon", "saxophone", "saxofón"],         instrument.AltoSaxophone),
    # Viento madera
    (["flauta", "flute"],                         instrument.Flute),
    (["clarinete", "clarinet"],                   instrument.Clarinet),
    (["oboe"],                                    instrument.Oboe),
    (["fagot", "bassoon"],                        instrument.Bassoon),
    # Viento metal
    (["trompeta", "trumpet"],                     instrument.Trumpet),
    (["trombon", "trombone", "trombón"],          instrument.Trombone),
    (["tuba"],                                    instrument.Tuba),
    # Teclado / combo
    (["electric piano", "rhodes",
      "teclado", "keys", "combo"],                instrument.ElectricPiano),
    (["bajo electrico", "electric bass",
      "bajo eléctrico"],                          instrument.ElectricBass),
    (["piano"],                                   instrument.Piano),
    (["organo", "organ", "órgano"],               instrument.Organ),
]


def _resolver_instrumento(nombre_voz, meta_instrumento):
    """
    Determina el instrumento music21 para una voz.
    Prioridad:
      1. Nombre exacto de la voz (VOZ_MAP)
      2. meta.instrumento del YAML (INSTRUMENT_MAP)
      3. Marimba como fallback
    """
    # 1. Por nombre de voz
    clave = nombre_voz.lower().replace(" ", "_")
    if clave in VOZ_MAP:
        return VOZ_MAP[clave]()

    # 2. Por meta.instrumento
    if meta_instrumento:
        meta_lower = meta_instrumento.lower()
        for keywords, inst_class in INSTRUMENT_MAP:
            if any(kw in meta_lower for kw in keywords):
                return inst_class()

    # 3. Fallback
    return instrument.Marimba()


def construir_score(voces, drum_notas, tempo_bpm,
                    time_signature="4/4", nombres_voz=None, reglas=None):
    """
    Construye un Score de music21 con N partes + batería opcional.
    """
    from marimba_range import NOMBRES_VOCES as NOMBRES_LEGACY

    if nombres_voz is None:
        nombres_voz = NOMBRES_LEGACY[:len(voces)]
        while len(nombres_voz) < len(voces):
            nombres_voz.append(f"Voz {len(nombres_voz)+1}")

    meta_instrumento = ""
    if reglas and "meta" in reglas:
        meta_instrumento = reglas["meta"].get("instrumento", "")

    score = stream.Score()

    for i, voz_notas in enumerate(voces):
        nombre = nombres_voz[i] if i < len(nombres_voz) else f"Voz {i+1}"
        inst   = _resolver_instrumento(nombre, meta_instrumento)

        part = stream.Part()
        part.partName = nombre
        part.id       = nombre
        part.insert(0, inst)
        part.insert(0, meter.TimeSignature(time_signature))
        part.insert(0, tempo.MetronomeMark(number=int(tempo_bpm)))

        for n in voz_notas:
            nueva = note.Note(n["pitch"])
            nueva.quarterLength = n["duration"]
            part.insert(snap(n["offset"]), nueva)

        score.append(part)
        print(f"[exporter] '{nombre}' → {inst.__class__.__name__}: {len(voz_notas)} notas")

    if drum_notas:
        drum_part = _construir_bateria(drum_notas, tempo_bpm, time_signature)
        score.append(drum_part)
        print(f"[exporter] Batería añadida: {len(drum_notas)} notas")

    return score


def exportar(score, output_dir, nombre_base):
    import os
    xml_path  = os.path.join(output_dir, f"{nombre_base}.musicxml")
    midi_path = os.path.join(output_dir, f"{nombre_base}.mid")

    score.write("musicxml", xml_path)
    print(f"[exporter] MusicXML → {xml_path}")

    try:
        score.write("midi", midi_path)
        print(f"[exporter] MIDI → {midi_path}")
    except Exception as e:
        print(f"[exporter] MIDI con batería falló: {e}")
        score_sin_drums = stream.Score()
        for part in score.parts:
            if part.partName != "Drums":
                score_sin_drums.append(part)
        score_sin_drums.write("midi", midi_path)
        print(f"[exporter] MIDI sin batería → {midi_path}")

    return xml_path, midi_path


def _construir_bateria(drum_notas, tempo_bpm, time_signature):
    dp = stream.Part()
    dp.partName = "Drums"
    dp.id       = "Drums"
    dp.insert(0, instrument.Percussion())
    dp.insert(0, meter.TimeSignature(time_signature))
    dp.insert(0, tempo.MetronomeMark(number=int(tempo_bpm)))
    for n in drum_notas:
        nueva = note.Note(n["pitch"])
        nueva.quarterLength = n["duration"]
        dp.insert(snap(n["offset"]), nueva)
    return dp