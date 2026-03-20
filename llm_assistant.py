"""
llm_assistant.py
Panel de asistente LLM para BA³ — Motor de Reglas YAML

Usa Ollama (local, gratuito) para generar archivos YAML de reglas
a partir de descripciones en lenguaje natural del músico.

Instalación de Ollama:
  https://ollama.com  →  descargar e instalar
  ollama pull phi3     →  descargar modelo (~2.3 GB, una sola vez)

Si Ollama no está disponible, el panel muestra un mensaje de
instalación amigable en lugar de un error técnico.
"""

import threading
import tkinter as tk
import customtkinter as ctk
import json
import re

# Colores — deben coincidir con app_gui.py
C_BG      = "#0f1117"
C_PANEL   = "#1a1d27"
C_SURFACE = "#232738"
C_ACCENT  = "#4f8ef7"
C_ACCENT2 = "#7c5cbf"
C_SUCCESS = "#3ddc97"
C_WARN    = "#f7c948"
C_ERROR   = "#f7564a"
C_TEXT    = "#e8eaf0"
C_MUTED   = "#7a7f94"
C_BORDER  = "#2e3347"

# ── Modelos soportados (en orden de preferencia) ──────────────────
MODELOS_PREFERIDOS = [
    "phi3",           # Microsoft Phi-3 Mini — mejor para YAML estructurado
    "phi3:mini",
    "phi3:medium",
    "gemma3:4b",      # Google Gemma 3 4B
    "gemma3:1b",
    "gemma3",
    "mistral",
    "llama3.2",
    "qwen2.5:3b",
    "gemma2:2b",
    "gemma2",
]

# ── System prompt — contexto musical para el LLM ─────────────────
SYSTEM_PROMPT = """You are BA³, a music arrangement assistant. You output ONLY valid YAML — no text, no explanation, no markdown fences.

EXACT OUTPUT FORMAT — copy this structure exactly, replacing values:

meta:
  instrumento: "Instrument Name"
  descripcion: "One line description"
  autor: ""
  version: "1.0"
  genero: "clasico"

voces:
  Voice1:
    rango_midi: [67, 84]
    nombre_rango: "G4 - C6"
    duracion_minima: 0.25
  Voice2:
    rango_midi: [55, 72]
    nombre_rango: "G3 - C5"
    duracion_minima: 0.25
  Voice3:
    rango_midi: [31, 48]
    nombre_rango: "G1 - C3"
    duracion_minima: 1.0
    extender_duracion: true

armonizacion:
  notas_simultaneas_1:
    Voice1: original
    Voice2: Voice1 - 4
    Voice3: Voice1 - 12
  notas_simultaneas_2:
    Voice1: voz_aguda
    Voice2: Voice1 - 4
    Voice3: voz_grave
  notas_simultaneas_3:
    Voice1: voz_1
    Voice2: voz_2
    Voice3: voz_3

restricciones:
  bajo_sostenido: true
  notas_de_paso_en_saltos_grandes: true
  umbral_salto_nota_de_paso: 12

procesamiento:
  snap_grid: 0.25
  duracion_minima_nota: 0.25
  tolerancia_simultaneidad: 0.05

RULES:
- Output starts with "meta:" — nothing before it
- extender_duracion: true ONLY on the last (lowest) voice
- Classical snap_grid: 0.25 | Jazz/Pop snap_grid: 0.5
- Voice names: no spaces, use underscore

MIDI RANGES:
Violin: 55-95 | Viola: 48-81 | Cello: 36-74
Flute: 60-96 | Clarinet: 50-94 | Alto Sax: 49-80
Trumpet: 54-86 | Guitar: 40-83 | Piano: 33-96
Marimba GT: Soprano 67-84 / Alto 55-72 / Tenor 43-60 / Bass 31-48
"""


class LLMAssistantPanel:
    """
    Panel lateral con chat para generar YAMLs desde lenguaje natural.
    Se integra en app_gui.py pasando el frame padre y un callback
    que recibe el YAML generado.
    """

    def __init__(self, parent, on_yaml_generado):
        """
        parent           : frame de CustomTkinter donde se construye el panel
        on_yaml_generado : función callback(yaml_str) que recibe el YAML generado
        """
        self.parent           = parent
        self.on_yaml_generado = on_yaml_generado
        self.ollama_ok        = False
        self.modelo_activo    = None
        self.historial        = []   # para contexto multi-turno

        self._build(parent)
        self._verificar_ollama()

    # ════════════════════════════════════════════════════════════════
    # Construcción del panel
    # ════════════════════════════════════════════════════════════════

    def _build(self, parent):
        # Header
        header = ctk.CTkFrame(parent, fg_color=C_PANEL, height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="✦  ASISTENTE IA",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_ACCENT2,
        ).pack(side="left", padx=16, pady=8)

        self.lbl_modelo = ctk.CTkLabel(
            header, text="verificando…",
            font=ctk.CTkFont(size=9),
            text_color=C_MUTED,
        )
        self.lbl_modelo.pack(side="right", padx=12, pady=8)

        # Chat — historial de mensajes
        self.chat_frame = ctk.CTkScrollableFrame(
            parent, fg_color=C_BG, corner_radius=0)
        self.chat_frame.pack(fill="both", expand=True)

        # Mensaje de bienvenida
        self._burbuja_sistema(
            "Hola 👋 Describime el instrumento o el arreglo que querés "
            "y genero las reglas YAML automáticamente.\n\n"
            "Ejemplos:\n"
            "• «Quiero arreglar para cuarteto de cuerdas clásico»\n"
            "• «Necesito un perfil para saxofón alto en estilo jazz»\n"
            "• «Hacé un arreglo de 3 voces para guitarra fingerstyle»"
        )

        # Área de input
        input_frame = ctk.CTkFrame(parent, fg_color=C_SURFACE, corner_radius=0)
        input_frame.pack(fill="x", padx=0, pady=0)

        self.input_text = ctk.CTkTextbox(
            input_frame,
            height=72,
            fg_color=C_SURFACE,
            text_color=C_TEXT,
            font=ctk.CTkFont(size=12),
            wrap="word",
        )
        self.input_text.pack(fill="x", padx=8, pady=(8, 4))
        self.input_text.bind("<Return>",    self._on_enter)
        self.input_text.bind("<Shift-Return>", lambda e: None)  # salto de línea

        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(0, 8))

        self.btn_enviar = ctk.CTkButton(
            btn_row, text="Enviar  ↵",
            command=self._enviar,
            fg_color=C_ACCENT2, hover_color="#5e3d9e",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32, corner_radius=6,
        )
        self.btn_enviar.pack(side="right")

        ctk.CTkButton(
            btn_row, text="Limpiar",
            command=self._limpiar_chat,
            fg_color=C_SURFACE, hover_color=C_BORDER,
            text_color=C_MUTED,
            height=32, width=70, corner_radius=6,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(0, 6))

    # ════════════════════════════════════════════════════════════════
    # Burbujas de chat
    # ════════════════════════════════════════════════════════════════

    def _burbuja_sistema(self, texto):
        """Mensaje del sistema / asistente."""
        frame = ctk.CTkFrame(self.chat_frame, fg_color=C_SURFACE,
                              corner_radius=8)
        frame.pack(fill="x", padx=8, pady=4, anchor="w")
        ctk.CTkLabel(
            frame, text=texto,
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT,
            wraplength=240, justify="left",
            anchor="w",
        ).pack(padx=10, pady=8, anchor="w")

    def _burbuja_usuario(self, texto):
        """Mensaje del usuario."""
        frame = ctk.CTkFrame(self.chat_frame, fg_color=C_ACCENT2,
                              corner_radius=8)
        frame.pack(fill="x", padx=8, pady=4, anchor="e")
        ctk.CTkLabel(
            frame, text=texto,
            font=ctk.CTkFont(size=11),
            text_color="white",
            wraplength=240, justify="right",
            anchor="e",
        ).pack(padx=10, pady=8, anchor="e")

    def _burbuja_yaml(self, yaml_str):
        """Burbuja especial con botón para cargar el YAML generado."""
        frame = ctk.CTkFrame(self.chat_frame, fg_color="#1e3a2f",
                              corner_radius=8)
        frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(
            frame, text="✓ YAML generado",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_SUCCESS,
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Preview del YAML (primeras 6 líneas)
        preview = "\n".join(yaml_str.strip().split("\n")[:6]) + "\n…"
        ctk.CTkLabel(
            frame, text=preview,
            font=ctk.CTkFont(family="Courier New", size=10),
            text_color=C_MUTED,
            justify="left", anchor="w",
            wraplength=240,
        ).pack(anchor="w", padx=10, pady=(0, 4))

        ctk.CTkButton(
            frame,
            text="⬆  Cargar en editor",
            command=lambda y=yaml_str: self._cargar_yaml(y),
            fg_color=C_SUCCESS, hover_color="#2ab87a",
            text_color="#0a1a0f",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30, corner_radius=6,
        ).pack(fill="x", padx=10, pady=(0, 8))

    def _burbuja_error(self, texto):
        frame = ctk.CTkFrame(self.chat_frame, fg_color="#2a1a1a",
                              corner_radius=8)
        frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            frame, text=texto,
            font=ctk.CTkFont(size=11),
            text_color=C_ERROR,
            wraplength=240, justify="left",
        ).pack(padx=10, pady=8)

    def _burbuja_pensando(self):
        """Indicador de carga mientras el LLM responde."""
        frame = ctk.CTkFrame(self.chat_frame, fg_color=C_SURFACE,
                              corner_radius=8)
        frame.pack(fill="x", padx=8, pady=4, anchor="w")
        lbl = ctk.CTkLabel(
            frame, text="⏳ Generando YAML…",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED,
        )
        lbl.pack(padx=10, pady=8)
        return frame   # lo guardamos para poder destruirlo después

    def _scroll_abajo(self):
        """Scroll automático al último mensaje."""
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    # ════════════════════════════════════════════════════════════════
    # Lógica de envío y generación
    # ════════════════════════════════════════════════════════════════

    def _on_enter(self, event):
        """Enter envía, Shift+Enter hace salto de línea."""
        if not event.state & 0x1:   # sin Shift
            self._enviar()
            return "break"

    def _enviar(self):
        texto = self.input_text.get("1.0", "end-1c").strip()
        if not texto:
            return
        if not self.ollama_ok:
            self._burbuja_error(
                "Ollama no está disponible.\n"
                "Instalá Ollama desde https://ollama.com\n"
                "y ejecutá: ollama pull phi3"
            )
            self._scroll_abajo()
            return

        self.input_text.delete("1.0", "end")
        self._burbuja_usuario(texto)
        burbuja_carga = self._burbuja_pensando()
        self._scroll_abajo()
        self.btn_enviar.configure(state="disabled")

        self.historial.append({"role": "user", "content": texto})

        thread = threading.Thread(
            target=self._generar,
            args=(texto, burbuja_carga),
            daemon=True,
        )
        thread.start()

    def _generar(self, prompt, burbuja_carga):
        """Llama a Ollama en un hilo para no bloquear la UI."""
        try:
            yaml_str = self._llamar_ollama(prompt)
            yaml_limpio = self._limpiar_yaml(yaml_str)

            self.historial.append({
                "role": "assistant",
                "content": yaml_limpio,
            })

            self.parent.after(0, lambda: burbuja_carga.destroy())
            self.parent.after(0, lambda: self._burbuja_yaml(yaml_limpio))

        except Exception as e:
            msg = str(e)
            self.parent.after(0, lambda: burbuja_carga.destroy())
            self.parent.after(0, lambda m=msg: self._burbuja_error(
                f"Error al generar:\n{m}"
            ))
        finally:
            self.parent.after(0, lambda: self.btn_enviar.configure(state="normal"))
            self.parent.after(0, self._scroll_abajo)

    def _llamar_ollama(self, prompt):
        """Llama a la API REST de Ollama usando /api/generate."""
        import urllib.request

        # Construir el prompt completo con el schema como ejemplo directo
        prompt_completo = f"""{SYSTEM_PROMPT}

USER REQUEST: {prompt}

OUTPUT (start with meta:):"""

        payload = {
            "model":  self.modelo_activo,
            "prompt": prompt_completo,
            "stream": False,
            "options": {
                "temperature": 0.1,   # muy bajo — queremos output determinístico
                "top_p": 0.9,
                "num_predict": 800,
                "stop": ["\n\n\n"],   # parar si genera demasiado texto extra
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=300) as resp:
            resultado = json.loads(resp.read().decode("utf-8"))
            return resultado["response"]

    def _limpiar_yaml(self, texto):
        """
        Limpia el output del LLM:
        - Elimina bloques ```yaml ... ``` o ``` ... ```
        - Elimina cualquier texto antes de la primera línea con "meta:"
        - Verifica que el resultado sea YAML válido con estructura BA³
        """
        # Extraer bloque entre backticks si existe
        match = re.search(r"```(?:yaml)?\s*([\s\S]+?)```", texto)
        if match:
            texto = match.group(1).strip()
        else:
            # Buscar la primera línea que empiece con "meta:"
            lineas = texto.strip().split("\n")
            inicio = None
            for i, l in enumerate(lineas):
                if l.strip().startswith("meta:"):
                    inicio = i
                    break
            if inicio is not None:
                texto = "\n".join(lineas[inicio:])
            else:
                # Último intento: buscar "voces:" si no hay "meta:"
                for i, l in enumerate(lineas):
                    if l.strip().startswith("voces:"):
                        texto = "\n".join(lineas[i:])
                        break

        # Validar YAML parseabe
        import yaml
        try:
            datos = yaml.safe_load(texto)
            if not isinstance(datos, dict):
                raise ValueError("El modelo no generó un YAML válido. Intentá de nuevo con una descripción más específica.")
            if "voces" not in datos:
                raise ValueError("El YAML no tiene la sección 'voces'. Intentá pedirlo de nuevo.")
            if "armonizacion" not in datos:
                raise ValueError("El YAML no tiene la sección 'armonizacion'. Intentá pedirlo de nuevo.")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML con error de sintaxis: {e}\n\nIntentá de nuevo con una descripción más simple.")

        return texto

    def _cargar_yaml(self, yaml_str):
        """Envía el YAML al editor principal vía callback."""
        self.on_yaml_generado(yaml_str)
        self._burbuja_sistema(
            "✓ YAML cargado en el editor.\n"
            "Podés editarlo antes de procesar, o presionar "
            "PROCESAR ARREGLO directamente."
        )
        self._scroll_abajo()

    # ════════════════════════════════════════════════════════════════
    # Verificación de Ollama
    # ════════════════════════════════════════════════════════════════

    def _verificar_ollama(self):
        """Verifica que Ollama esté corriendo y elige el mejor modelo."""
        thread = threading.Thread(target=self._check_ollama, daemon=True)
        thread.start()

    def _check_ollama(self):
        import urllib.request
        import urllib.error

        try:
            with urllib.request.urlopen(
                "http://localhost:11434/api/tags", timeout=3
            ) as resp:
                datos = json.loads(resp.read().decode("utf-8"))
                modelos_instalados = [m["name"] for m in datos.get("models", [])]

            # Elegir el mejor modelo disponible
            modelo_elegido = None
            for preferido in MODELOS_PREFERIDOS:
                for instalado in modelos_instalados:
                    if preferido in instalado.lower():
                        modelo_elegido = instalado
                        break
                if modelo_elegido:
                    break

            if modelo_elegido:
                self.modelo_activo = modelo_elegido
                self.ollama_ok     = True
                nombre_corto = modelo_elegido.split(":")[0]
                self.parent.after(0, lambda: self.lbl_modelo.configure(
                    text=f"● {nombre_corto}",
                    text_color=C_SUCCESS,
                ))
            else:
                # Ollama corre pero no hay modelos instalados
                self.ollama_ok = False
                self.parent.after(0, lambda: self.lbl_modelo.configure(
                    text="sin modelo",
                    text_color=C_WARN,
                ))
                self.parent.after(0, lambda: self._burbuja_error(
                    "Ollama está instalado pero no hay modelos.\n\n"
                    "Ejecutá en la terminal:\n"
                    "  ollama pull phi3\n\n"
                    "Luego reiniciá la aplicación."
                ))

        except (urllib.error.URLError, OSError):
            self.ollama_ok = False
            self.parent.after(0, lambda: self.lbl_modelo.configure(
                text="● sin conexión",
                text_color=C_ERROR,
            ))
            self.parent.after(0, lambda: self._burbuja_error(
                "Ollama no está corriendo.\n\n"
                "Para activar el asistente IA:\n\n"
                "1. Descargá Ollama:\n"
                "   https://ollama.com\n\n"
                "2. Instalalo y ejecutá:\n"
                "   ollama pull phi3\n\n"
                "3. Reiniciá la aplicación.\n\n"
                "El resto del programa funciona\n"
                "normalmente sin el asistente."
            ))

    # ════════════════════════════════════════════════════════════════
    # Utilidades
    # ════════════════════════════════════════════════════════════════

    def _limpiar_chat(self):
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.historial = []
        self._burbuja_sistema(
            "Chat limpiado. ¿Qué instrumento o arreglo necesitás?"
        )