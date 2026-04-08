# Marimba Arranger — YAML Rule Engine

*Languages:*
- *[English](README.md)*
- *[Spanish](README-ES.md)*
---

An Open Source Software Desktop Application to generate musical arrangements based on configurable rules in YAML. This engine is completely generic: the musical knowegde comes from the `.yaml` archives, not from the code.

## Instalation Commands

After download and extract this project, you need to execute this commands in the folder you extract it:

```bash
pip install -r requirements.txt
python app_gui.py
```

## Files

| File | Description |
|---|---|
| `app_gui.py` | Principal Graphical Interface (CustomTkinter) |
| `rule_engine.py` | Generic engine that applies the YAML rules  |
| `plantilla_generica.yaml` | Template base to make new profiles |
| `reglas_marimba_guatemalteca.yaml` | Profile for a Guatemalan Concert Marimba |
| `midi_parser.py` | Lecture and parsing of MIDI files |
| `voice_separator.py` | Voices Separator (Legacy Module) |
| `marimba_range.py` | Voice Ranges for Marimba (Legacy) |
| `exporter.py` | Exportation to MusicXML y MIDI |
| `metrics.py` | Calculation of arrangement metrics |
| `utils.py` | Auxiliar Functions |

## Workflow

1. Load an input MIDI file 
2. Load or edite the `.yaml` rules file in the built-in editor
3. Select output folder
4. Press **PROCESAR ARREGLO**
5. Review metrics in the right panel
6. Listen the preview with the player

---

## YAML Rules Format

The YAML file is the heart of the system. Defines **all of the musical knowledge**
in the arragement: how many voices, what is the range or each one, how we generate the missing voices and what restictions apply. The code engine knows nothing about the target instrument—that information resides exclusively in this file.

This makes the system extensible by anyone, without programming: simply create a new `.yaml` file to support a different instrument or genre.

### Complete Structure

A rules file has five sections:

```yaml
meta:          # Profile Metadata (name, author, version)
voces:         # Definition of each voice: range, duration, behavior
armonizacion:  # How to generate missing voices based on the number of notes
restricciones: # voice leading and post-processing rules
procesamiento: # Technical parameters (quantization, tolerance)
```

---

### `meta` — Profile Metadata

Descriptive information. It does not affect processing, but it is important
for identifying the profile in the community repository.

```yaml
meta:
  instrumento: "Marimba Guatemalteca"   # Name visible in app
  descripcion: "Arreglo estándar para marimba guatemalteca de concierto"
  autor: "Nombre del arreglista"
  version: "1.0"
  genero: "general"                     # general | clasic | jazz | popular | folclor
```

---

### `voces` — Voices Definition

Define the number of voices in the arrangement and the properties of each voice.
Order matters: **first voice = highest pitch, last voice = lowest pitch**.
You can have between 2 and 8 voices. The engine adjusts automatically.

```yaml
voces:
  Soprano:                      # The name is free — it will appear in the score
    rango_midi: [67, 84]        # [MIDI mínimo, MIDI máximo] — mandatory
    nombre_rango: "G4 - C6"     # Just informative, for documentation
    salto_maximo: 7             # Halftones — reference, not yet applied
    duracion_minima: 0.25       # In quarter notes: 0.25=sixteenth note, 0.5=eighth note, 1.0=quarter note

  Bajo:
    rango_midi: [31, 48]        # G1 - C3
    duracion_minima: 1.0
    extender_duracion: true     # true = the note lasts until the next one (bass sharp)
```

**Referencia de números MIDI:**

| Nota | MIDI | Nota | MIDI | Nota | MIDI |
|------|------|------|------|------|------|
| C2   | 36   | C4 (Do central) | 60 | C6 | 84 |
| G2   | 43   | G4   | 67   | G6  | 91 |
| C3   | 48   | C5   | 72   | C7  | 96 |
| G3   | 55   | G5   | 79   |     |    |

Formula: `MIDI = (octava + 1) × 12 + clase_de_nota`
where C=0, D=2, E=4, F=5, G=7, A=9, B=11.

---

### `armonizacion` — Missing Voices Generator

This section defines what to do when the MIDI has **fewer simultaneous notes than voices**. For example, if the MIDI has 2 notes but the arrangement has 4 voices,
the engine needs to know how to generate the 2 missing voices.

One key is defined for each possible case:

```yaml
armonizacion:
  notas_simultaneas_1:    # When there is exactly 1 note at that moment
    ...
  notas_simultaneas_2:    # When there are 2 simultaneous notes
    ...
  notas_simultaneas_3:    # When there are 3 simultaneous notes
    ...
  notas_simultaneas_default:  # Fallback for any undefined case
    ...
```

When there are **as many notes as voices or more**, the engine directly assigns notes from high to low without consulting these rules.

#### Interval expressions

Each voice within a harmonization case is defined by an expression:

| Expression | Meaning |
|-----------|-------------|
| `original` | The exact pitch of the highest note in the group |
| `soprano` | Alias ​​of `original` — the highest voice |
| `voz_aguda` | The highest note in the MIDI group |
| `voz_grave` | The lowest note in the MIDI group |
| `voz_1` | The first note of the group (highest) |
| `voz_2` | The second note from the group |
| `voz_3` | The third note from the group |
| `<nombre> - N` | N halftones below `<nombre>` |
| `<nombre> + N` | N halftones above `<nombre>` |
| `<nombre_de_voz>` | Reference to a voice already calculated in this group |

The last option is powerful: it allows a voice to reference
another voice **already assigned** in the same group, not just the MIDI notes.

```yaml
# Example: The Tenor is calculated from the already assigned Alto
notas_simultaneas_2:
  Soprano: voz_aguda
  Alto:    Soprano - 3     # 3 halftones below Soprano
  Tenor:   Alto - 5        # 5 halftones below Alto (already calculated)
  Bajo:    voz_grave
```

#### Reference Musical Intervals

| Halftones | Interval |
|-----------|-----------|
| -1  | Minor 2nd (m2) |
| -2  | Major 2nd (M3) |
| -3  | Minor 3rd (m3) |
| -4  | Major 3rd (M4) |
| -5  | Perfect 4th (P4) |
| -6  | Tritone (TT) |
| -7  | Perfect 5th (P5) |
| -8  | Minor 6th (m6) |
| -9  | Major 6th (M6) |
| -10 | Minor 7th (m7) |
| -11 | Major 7th (M7) |
| -12 | Perfect Octave (P8) |

> **Note on automatic transposition:** After calculating the pitch with the expression, the engine automatically transposes it by octaves until it falls within the MIDI range defined for that voice. You don't need to worry about which octave the result is in.

---

### `restricciones` — Voice leading y post-processing

```yaml
restricciones:
  bajo_sostenido: true
  # The last voice extends its duration into the next note,
  # filling the silences. It produces a more melodic and continuous bass.

  notas_de_paso_en_saltos_grandes: true
  # When there is a leap greater than the threshold between two consecutive notes
  # of any voice, a passing note is interpolated halfway across the space.

  umbral_salto_nota_de_paso: 12
  # Minimum semitones to activate the passing note. 12 = octave.
  # Lowering it to 7 also affects leaps of a fifth.
```

---

### `procesamiento` — Technical Parameters

```yaml
procesamiento:
  snap_grid: 0.25
  # Rhythmic quantization in quarter notes.
  # 0.25 = sixteenth note (more precise)
  # 0.5 = eighth note
  # 1.0 = quarter note (more "square")

  duracion_minima_nota: 0.25
  # No note can be shorter than this.

  tolerancia_simultaneidad: 0.05
  # Seconds of margin to consider two notes as sounding "at the same time".
  # Useful for MIDI with humanized timing.
```

---

### Complete Example — Marimba Guatemalteca

```yaml
meta:
  instrumento: "Marimba Guatemalteca"
  descripcion: "Arreglo estándar, 4 voces"
  autor: ""
  version: "1.0"

voces:
  Soprano:
    rango_midi: [67, 84]
    duracion_minima: 0.25
  Alto:
    rango_midi: [55, 72]
    duracion_minima: 0.25
  Tenor:
    rango_midi: [43, 60]
    duracion_minima: 0.25
  Bajo:
    rango_midi: [31, 48]
    duracion_minima: 1.0
    extender_duracion: true

armonizacion:
  notas_simultaneas_1:
    Soprano: original
    Alto:    Soprano - 3
    Tenor:   Soprano - 7
    Bajo:    Soprano - 12
  notas_simultaneas_2:
    Soprano: voz_aguda
    Alto:    Soprano - 3
    Tenor:   Soprano - 7
    Bajo:    voz_grave
  notas_simultaneas_3:
    Soprano: voz_1
    Alto:    voz_2
    Tenor:   Alto - 5
    Bajo:    voz_3

restricciones:
  bajo_sostenido: true
  notas_de_paso_en_saltos_grandes: true
  umbral_salto_nota_de_paso: 12

procesamiento:
  snap_grid: 0.25
  tolerancia_simultaneidad: 0.05
```

---

### Create a New Profile for Another Instrument 

1. Make a copy of `plantilla_generica.yaml`
2. Change the `rango_midi` values ​​in each voice
3. Adjust the intervals in `armonizacion` according to the idiomatic writing of the instrument
4. Save it with a descriptive name like: `reglas_vibrafono.yaml`, `reglas_cuarteto.yaml`, etc.
5. Load it in the app with the button **Cargar**

Profiles are portable plain text files. They can be shared among arrangers, versioned in Git, and in the future, automatically generated from natural language descriptions.

---

## Asistente IA (opcional)

The app's right panel includes a wizard that generates YAML profiles from natural language descriptions. It requires [Ollama](https://ollama.com) to be installed locally.

```bash
# Install the recommended model (only once, ~2.3 GB)
ollama pull phi3
```

The assistant runs completely offline—no data leaves your machine.

If Ollama is not installed, the rest of the app functions normally.

> **Note:** The profiles generated by the AI ​​assistant are a starting point.
> It is recommended to review them in the editor before processing, especially the MIDI ranges and harmonization intervals.

---

## Included Profiles

| File | Instrument | Voices | Musical Genre |
|---|---|---|---|
| `reglas_marimba_guatemalteca.yaml` | Marimba Guatemalteca | 4 | General |
| `reglas_tusa_pop.yaml` | Marimba Guatemalteca | 4 | Pop latino |
| `reglas_cuarteto_clasico.yaml` | Cuarteto de Cuerdas | 4 | Clásico |
| `reglas_guitarra_clasica.yaml` | Guitarra Clásica | 3 | Clásico |
| `reglas_guitarra_jazz.yaml` | Guitarra Jazz | 4 | Jazz |
| `reglas_piano_clasico.yaml` | Piano | 4 | Clásico |
| `reglas_saxofon_alto.yaml` | Sección de Saxofones | 3 | Jazz |
| `reglas_combo_pop_funk.yaml` | Combo Pop/Funk | 3 | Pop/Funk |
| `plantilla_generica.yaml` | (plantilla base) | 4 | — |

---

## Contribute Profiles

Do you work with an instrument that's not on the list? You can contribute:

1. Create your profile based on `plantilla_generica.yaml`
2. Try it with at least one test MIDI file. (`python generar_midis_prueba.py`)
3. Open a Pull Request in the repository

Contributed profiles are automatically validated with:
```bash
python rule_engine.py --validate tu_perfil.yaml
```

---

## Known Limitations

These limitations are known and documented for future work:

- **AI Assistant:** Automatically generated profiles may have errors in voice ranges or references. Always check before use.
- **MIDI with Variable Tempo:** The parser uses the first tempo in the file. Pieces with multiple tempo changes may experience desynchronization.
- **Rhythmic Quantization:** Snapping to the grid can affect pieces with highly syncopated rhythms. Adjust `snap_grid: 0.125` for greater accuracy.
- **MIDI Export with Drums:** In some cases, music21 fails to export MIDI with percussion. The system automatically re-exports without drums as a fallback.

---

## Future Work

- Automatic rule inference from existing arrangement corpora
- Profile for Guatemalan marimba orchestra (complete instrument)
- Controlled evaluation of the AI ​​assistant with non-technical musicians
- One-click installer (.exe Windows, .dmg macOS)
- Community repository of profiles with automated validation

---

## Cite this work

If you use it in your research:

```
De León Batres, J.A. & Serrano, M.P. (2026). A Rule-Based Adaptive
Arrangement Architecture for Acoustic Instruments — Case Study on the
Guatemalan Marimba.
```

---

## License

Software Libre — MIT License

Copyright (c) 2026 Jorge Alejandro De León Batres, María Patricia Serrano
Universidad de San Carlos de Guatemala, Facultad de Ingeniería