# Marimba Arranger — Motor de Reglas YAML

Aplicación de escritorio de software libre para generar arreglos musicales
automáticos basados en reglas configurables en YAML. El motor es completamente
genérico: el conocimiento musical vive en los archivos `.yaml`, no en el código.

## Instalación

```bash
pip install -r requirements.txt
python app_gui.py
```

## Archivos

| Archivo | Descripción |
|---|---|
| `app_gui.py` | Interfaz gráfica principal (CustomTkinter) |
| `rule_engine.py` | Motor genérico que aplica las reglas YAML |
| `plantilla_generica.yaml` | Plantilla base para crear nuevos perfiles |
| `reglas_marimba_guatemalteca.yaml` | Perfil para marimba guatemalteca de concierto |
| `midi_parser.py` | Lectura y parsing de archivos MIDI |
| `voice_separator.py` | Separación de voces (módulo legacy) |
| `marimba_range.py` | Rangos de voces para marimba (legacy) |
| `exporter.py` | Exportación a MusicXML y MIDI |
| `metrics.py` | Cálculo de métricas del arreglo |
| `utils.py` | Funciones auxiliares |

## Flujo de trabajo

1. Cargar un archivo MIDI de entrada
2. Cargar o editar el archivo de reglas `.yaml` en el editor integrado
3. Seleccionar carpeta de salida
4. Presionar **PROCESAR ARREGLO**
5. Revisar métricas en el panel derecho
6. Escuchar el preview con el reproductor

---

## Formato de reglas YAML

El archivo YAML es el corazón del sistema. Define **todo el conocimiento musical**
del arreglo: cuántas voces hay, qué rango tiene cada una, cómo se generan las
voces faltantes y qué restricciones se aplican. El motor de código no sabe nada
del instrumento destino — esa información vive exclusivamente en este archivo.

Esto hace que el sistema sea extensible por cualquier persona, sin programar:
basta con crear un nuevo `.yaml` para soportar un instrumento o género distinto.

### Estructura completa

Un archivo de reglas tiene cinco secciones:

```yaml
meta:          # Metadatos del perfil (nombre, autor, versión)
voces:         # Definición de cada voz: rango, duración, comportamiento
armonizacion:  # Cómo generar voces faltantes según cuántas notas hay
restricciones: # Reglas de voice leading y post-procesamiento
procesamiento: # Parámetros técnicos (cuantización, tolerancia)
```

---

### `meta` — Metadatos del perfil

Información descriptiva. No afecta el procesamiento, pero es importante
para identificar el perfil en el repositorio comunitario.

```yaml
meta:
  instrumento: "Marimba Guatemalteca"   # Nombre visible en la app
  descripcion: "Arreglo estándar para marimba guatemalteca de concierto"
  autor: "Nombre del arreglista"
  version: "1.0"
  genero: "general"                     # general | clasico | jazz | popular | folclor
```

---

### `voces` — Definición de voces

Define cuántas voces tiene el arreglo y las propiedades de cada una.
El orden importa: **primera voz = más aguda, última = más grave**.
Podés tener entre 2 y 8 voces. El motor se adapta automáticamente.

```yaml
voces:
  Soprano:                      # El nombre es libre — aparecerá en la partitura
    rango_midi: [67, 84]        # [MIDI mínimo, MIDI máximo] — obligatorio
    nombre_rango: "G4 - C6"     # Solo informativo, para documentación
    salto_maximo: 7             # Semitonos — referencia, no aplicado aún
    duracion_minima: 0.25       # En quarter notes: 0.25=semicorchea, 0.5=corchea, 1.0=negra

  Bajo:
    rango_midi: [31, 48]        # G1 - C3
    duracion_minima: 1.0
    extender_duracion: true     # true = la nota dura hasta la siguiente (bajo sostenido)
```

**Referencia de números MIDI:**

| Nota | MIDI | Nota | MIDI | Nota | MIDI |
|------|------|------|------|------|------|
| C2   | 36   | C4 (Do central) | 60 | C6 | 84 |
| G2   | 43   | G4   | 67   | G6  | 91 |
| C3   | 48   | C5   | 72   | C7  | 96 |
| G3   | 55   | G5   | 79   |     |    |

Fórmula: `MIDI = (octava + 1) × 12 + clase_de_nota`
donde C=0, D=2, E=4, F=5, G=7, A=9, B=11.

---

### `armonizacion` — Generación de voces faltantes

Esta sección define qué hacer cuando el MIDI tiene **menos notas simultáneas
que voces**. Por ejemplo, si el MIDI tiene 2 notas pero el arreglo tiene 4 voces,
el motor necesita saber cómo generar las 2 voces faltantes.

Se define una clave por cada caso posible:

```yaml
armonizacion:
  notas_simultaneas_1:    # Cuando hay exactamente 1 nota en ese momento
    ...
  notas_simultaneas_2:    # Cuando hay 2 notas simultáneas
    ...
  notas_simultaneas_3:    # Cuando hay 3 notas simultáneas
    ...
  notas_simultaneas_default:  # Fallback para cualquier caso no definido
    ...
```

Cuando hay **tantas notas como voces o más**, el motor asigna directamente
de agudo a grave sin consultar estas reglas.

#### Expresiones de intervalo

Cada voz dentro de un caso de armonización se define con una expresión:

| Expresión | Significado |
|-----------|-------------|
| `original` | El pitch exacto de la nota más aguda del grupo |
| `soprano` | Alias de `original` — la voz más aguda |
| `voz_aguda` | La nota más aguda del grupo MIDI |
| `voz_grave` | La nota más grave del grupo MIDI |
| `voz_1` | La primera nota del grupo (más aguda) |
| `voz_2` | La segunda nota del grupo |
| `voz_3` | La tercera nota del grupo |
| `<nombre> - N` | N semitonos abajo de `<nombre>` |
| `<nombre> + N` | N semitonos arriba de `<nombre>` |
| `<nombre_de_voz>` | Referencia a una voz ya calculada en este grupo |

La última opción es poderosa: permite que una voz tome como referencia
a otra voz **ya asignada** en el mismo grupo, no solo a las notas del MIDI.

```yaml
# Ejemplo: el Tenor se calcula a partir del Alto ya asignado
notas_simultaneas_2:
  Soprano: voz_aguda
  Alto:    Soprano - 3     # 3 semitonos abajo del Soprano
  Tenor:   Alto - 5        # 5 semitonos abajo del Alto (ya calculado)
  Bajo:    voz_grave
```

#### Intervalos musicales de referencia

| Semitonos | Intervalo |
|-----------|-----------|
| -1  | 2da menor |
| -2  | 2da mayor (tono) |
| -3  | 3ra menor |
| -4  | 3ra mayor |
| -5  | 4ta justa |
| -6  | tritono |
| -7  | 5ta justa |
| -8  | 6ta menor |
| -9  | 6ta mayor |
| -10 | 7ma menor |
| -11 | 7ma mayor |
| -12 | octava |

> **Nota sobre transposición automática:** después de calcular el pitch con
> la expresión, el motor lo transpone por octavas automáticamente hasta que
> quede dentro del `rango_midi` definido para esa voz. No necesitás preocuparte
> por en qué octava está el resultado.

---

### `restricciones` — Voice leading y post-procesamiento

```yaml
restricciones:
  bajo_sostenido: true
  # La última voz extiende su duración hasta la siguiente nota,
  # llenando los silencios. Produce un bajo más melódico y continuo.

  notas_de_paso_en_saltos_grandes: true
  # Cuando hay un salto mayor al umbral entre dos notas consecutivas
  # de cualquier voz, se interpola una nota de paso a la mitad del espacio.

  umbral_salto_nota_de_paso: 12
  # Semitonos mínimos para activar la nota de paso. 12 = octava.
  # Bajarlo a 7 interviene también en saltos de quinta.
```

---

### `procesamiento` — Parámetros técnicos

```yaml
procesamiento:
  snap_grid: 0.25
  # Cuantización rítmica en quarter notes.
  # 0.25 = semicorchea (más preciso)
  # 0.5  = corchea
  # 1.0  = negra (más "cuadrado")

  duracion_minima_nota: 0.25
  # Ninguna nota puede ser más corta que esto.

  tolerancia_simultaneidad: 0.05
  # Segundos de margen para considerar que dos notas suenan "al mismo tiempo".
  # Útil para MIDIs con timing humanizado.
```

---

### Ejemplo completo — Marimba Guatemalteca

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

### Crear un perfil para otro instrumento

1. Copiá `plantilla_generica.yaml`
2. Cambiá los valores de `rango_midi` en cada voz
3. Ajustá los intervalos en `armonizacion` según la escritura idiomática del instrumento
4. Guardá con nombre descriptivo: `reglas_vibrafono.yaml`, `reglas_cuarteto.yaml`, etc.
5. Cargalo en la app con el botón **Cargar**

Los perfiles son archivos de texto plano portables. Pueden compartirse entre
arreglistas, versionarse en Git, y en el futuro generarse automáticamente
a partir de descripciones en lenguaje natural.

---

## Asistente IA (opcional)

El panel derecho de la app incluye un asistente que genera perfiles YAML
desde descripciones en lenguaje natural. Requiere [Ollama](https://ollama.com)
instalado localmente.

```bash
# Instalar el modelo recomendado (una sola vez, ~2.3 GB)
ollama pull phi3
```

El asistente corre completamente **offline** — ningún dato sale de tu máquina.
Si Ollama no está instalado, el resto de la app funciona normalmente.

> **Nota:** Los perfiles generados por el asistente IA son un punto de partida.
> Se recomienda revisarlos en el editor antes de procesar, especialmente los
> rangos MIDI y los intervalos de armonización.

---

## Perfiles incluidos

| Archivo | Instrumento | Voces | Género |
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

## Contribuir perfiles

¿Trabajás con un instrumento que no está en la lista? Podés contribuir:

1. Creá tu perfil basándote en `plantilla_generica.yaml`
2. Probalo con al menos un MIDI de prueba (`python generar_midis_prueba.py`)
3. Abrí un Pull Request en el repositorio

Los perfiles contribuidos se validan automáticamente con:
```bash
python rule_engine.py --validate tu_perfil.yaml
```

---

## Limitaciones conocidas

Estas limitaciones son conocidas y están documentadas para trabajo futuro:

- **Asistente IA:** Los perfiles generados automáticamente pueden tener
  errores en rangos o referencias de voces. Siempre revisar antes de usar.
- **MIDI con tempo variable:** El parser usa el primer tempo del archivo.
  Piezas con múltiples cambios de tempo pueden tener desincronización.
- **Cuantización rítmica:** El snap al grid puede afectar piezas con
  ritmos muy sincopados. Ajustar `snap_grid: 0.125` para más precisión.
- **Exportación MIDI con batería:** En algunos casos music21 falla al
  exportar MIDI con percusión. El sistema re-exporta automáticamente
  sin batería como fallback.

---

## Trabajo futuro

- Inferencia automática de reglas desde corpus de arreglos existentes
- Perfil para marimba orquesta guatemalteca (instrumento completo)
- Evaluación controlada del asistente IA con músicos no técnicos
- Instalador de un solo clic (.exe Windows, .dmg macOS)
- Repositorio comunitario de perfiles con validación automatizada

---

## Citar este trabajo

Si lo usas en tu investigación:

```
De León Batres, J.A. & Serrano, M.P. (2026). A Rule-Based Adaptive
Arrangement Architecture for Acoustic Instruments — Case Study on the
Guatemalan Marimba.
```

---

## Licencia

Software Libre — MIT License

Copyright (c) 2026 Jorge Alejandro De León Batres, María Patricia Serrano
Universidad de San Carlos de Guatemala, Facultad de Ingeniería