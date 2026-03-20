"""
app_gui.py
Aplicación de escritorio para arreglos automáticos con reglas YAML.
Framework: CustomTkinter

Módulos:
  - Panel izquierdo:  Cargar MIDI + seleccionar reglas + botón procesar
  - Panel central:    Editor YAML con syntax highlighting
  - Panel derecho:    Log de proceso + métricas
  - Barra inferior:   Reproductor MIDI (preview)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
try:
    from llm_assistant import LLMAssistantPanel
    LLM_DISPONIBLE = True
except ImportError:
    LLM_DISPONIBLE = False

# ── Tema ────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta personalizada
C_BG       = "#0f1117"
C_PANEL    = "#1a1d27"
C_SURFACE  = "#232738"
C_ACCENT   = "#4f8ef7"
C_ACCENT2  = "#7c5cbf"
C_SUCCESS  = "#3ddc97"
C_WARN     = "#f7c948"
C_ERROR    = "#f7564a"
C_TEXT     = "#e8eaf0"
C_MUTED    = "#7a7f94"
C_BORDER   = "#2e3347"


class ArrangerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Marimba Arranger  ·  Motor de Reglas YAML")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=C_BG)

        # Estado interno
        self.midi_path   = tk.StringVar(value="")
        self.rules_path  = tk.StringVar(value="")
        self.output_dir  = tk.StringVar(value="")
        self.midi_player = None   # instancia de MidiPlayer cuando exista

        self._build_ui()
        self._cargar_reglas_default()

    # ════════════════════════════════════════════════════════════════
    # Construcción de la UI
    # ════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Título superior
        header = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=0, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="⬡  Marimba Arranger",
            font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
            text_color=C_ACCENT,
        ).pack(side="left", padx=24, pady=12)

        ctk.CTkLabel(
            header,
            text="Motor de Reglas YAML para Arreglos Musicales",
            font=ctk.CTkFont(size=12),
            text_color=C_MUTED,
        ).pack(side="left", padx=4, pady=12)

        # Separador
        ctk.CTkFrame(self, fg_color=C_BORDER, height=1, corner_radius=0).pack(fill="x")

        # Cuerpo principal
        body = ctk.CTkFrame(self, fg_color=C_BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        body.columnconfigure(0, weight=0, minsize=280)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=0, minsize=300)
        body.columnconfigure(3, weight=0, minsize=280)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_center_panel(body)
        self._build_right_panel(body)
        self._build_assistant_panel(body)

        # Barra inferior: reproductor
        self._build_player_bar()

    # ── Panel Izquierdo ─────────────────────────────────────────────
    def _build_left_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 1))

        ctk.CTkLabel(frame, text="ARCHIVO & CONFIGURACIÓN",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C_MUTED).pack(anchor="w", padx=20, pady=(20, 8))

        # MIDI
        self._section_label(frame, "Archivo MIDI")
        midi_row = ctk.CTkFrame(frame, fg_color="transparent")
        midi_row.pack(fill="x", padx=16, pady=(4, 0))
        self.lbl_midi = ctk.CTkLabel(midi_row, textvariable=self.midi_path,
                                      text_color=C_MUTED,
                                      font=ctk.CTkFont(size=11),
                                      wraplength=200, justify="left")
        self.lbl_midi.pack(fill="x")
        ctk.CTkButton(frame, text="📂  Seleccionar MIDI",
                      command=self._seleccionar_midi,
                      fg_color=C_SURFACE, hover_color=C_ACCENT,
                      text_color=C_TEXT, corner_radius=6,
                      font=ctk.CTkFont(size=12)).pack(fill="x", padx=16, pady=(6, 16))

        ctk.CTkFrame(frame, fg_color=C_BORDER, height=1).pack(fill="x", padx=16)

        # Reglas
        self._section_label(frame, "Archivo de Reglas")
        self.lbl_rules = ctk.CTkLabel(frame, textvariable=self.rules_path,
                                       text_color=C_MUTED,
                                       font=ctk.CTkFont(size=11),
                                       wraplength=240, justify="left")
        self.lbl_rules.pack(anchor="w", padx=20, pady=(4, 0))

        rules_btns = ctk.CTkFrame(frame, fg_color="transparent")
        rules_btns.pack(fill="x", padx=16, pady=(6, 0))
        ctk.CTkButton(rules_btns, text="📂  Cargar",
                      command=self._seleccionar_reglas,
                      fg_color=C_SURFACE, hover_color=C_ACCENT,
                      text_color=C_TEXT, corner_radius=6,
                      font=ctk.CTkFont(size=12), width=110).pack(side="left", padx=(0, 6))
        ctk.CTkButton(rules_btns, text="💾  Guardar",
                      command=self._guardar_reglas,
                      fg_color=C_SURFACE, hover_color=C_SUCCESS,
                      text_color=C_TEXT, corner_radius=6,
                      font=ctk.CTkFont(size=12), width=110).pack(side="left")

        ctk.CTkFrame(frame, fg_color=C_BORDER, height=1).pack(fill="x", padx=16, pady=16)

        # Carpeta de salida
        self._section_label(frame, "Carpeta de salida")
        self.lbl_output = ctk.CTkLabel(frame, textvariable=self.output_dir,
                                        text_color=C_MUTED,
                                        font=ctk.CTkFont(size=11),
                                        wraplength=240, justify="left")
        self.lbl_output.pack(anchor="w", padx=20, pady=(4, 0))
        ctk.CTkButton(frame, text="📁  Seleccionar carpeta",
                      command=self._seleccionar_output,
                      fg_color=C_SURFACE, hover_color=C_ACCENT,
                      text_color=C_TEXT, corner_radius=6,
                      font=ctk.CTkFont(size=12)).pack(fill="x", padx=16, pady=(6, 16))

        ctk.CTkFrame(frame, fg_color=C_BORDER, height=1).pack(fill="x", padx=16)

        # Botón PROCESAR
        self.btn_procesar = ctk.CTkButton(
            frame,
            text="▶  PROCESAR ARREGLO",
            command=self._procesar,
            fg_color=C_ACCENT, hover_color="#3a6fd4",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8, height=44,
        )
        self.btn_procesar.pack(fill="x", padx=16, pady=20)

        # Progress bar
        self.progress = ctk.CTkProgressBar(frame, fg_color=C_SURFACE,
                                            progress_color=C_ACCENT)
        self.progress.pack(fill="x", padx=16, pady=(0, 12))
        self.progress.set(0)

    # ── Panel Central: Editor YAML ───────────────────────────────────
    def _build_center_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_BG)
        frame.grid(row=0, column=1, sticky="nsew", padx=1)

        # Header del editor
        editor_header = ctk.CTkFrame(frame, fg_color=C_PANEL, height=40)
        editor_header.pack(fill="x")
        editor_header.pack_propagate(False)

        ctk.CTkLabel(editor_header, text="EDITOR DE REGLAS  (.yaml)",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C_MUTED).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(editor_header, text="✓ Validar",
                      command=self._validar_yaml,
                      fg_color=C_SURFACE, hover_color=C_SUCCESS,
                      text_color=C_TEXT, width=90, height=28,
                      corner_radius=6,
                      font=ctk.CTkFont(size=11)).pack(side="right", padx=8, pady=6)

        ctk.CTkButton(editor_header, text="↺ Reset",
                      command=self._reset_yaml,
                      fg_color=C_SURFACE, hover_color=C_WARN,
                      text_color=C_TEXT, width=80, height=28,
                      corner_radius=6,
                      font=ctk.CTkFont(size=11)).pack(side="right", padx=(0, 4), pady=6)

        # Área de texto
        self.yaml_editor = tk.Text(
            frame,
            bg=C_SURFACE, fg=C_TEXT,
            insertbackground=C_ACCENT,
            selectbackground=C_ACCENT2,
            font=("Courier New", 12),
            relief="flat", bd=0,
            padx=16, pady=12,
            undo=True,
            wrap="none",
        )
        self.yaml_editor.pack(fill="both", expand=True)

        # Scrollbars
        sb_y = ctk.CTkScrollbar(frame, command=self.yaml_editor.yview)
        sb_y.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.yaml_editor.configure(yscrollcommand=sb_y.set)

        # Syntax highlighting (básico: colores por tipo de línea)
        self.yaml_editor.tag_configure("comment", foreground="#6a9955")
        self.yaml_editor.tag_configure("key",     foreground="#9cdcfe")
        self.yaml_editor.tag_configure("value",   foreground="#ce9178")
        self.yaml_editor.tag_configure("section", foreground=C_WARN,
                                        font=("Courier New", 12, "bold"))
        self.yaml_editor.bind("<KeyRelease>", self._highlight_yaml)

    # ── Panel Derecho: Log + Métricas ────────────────────────────────
    def _build_right_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=0)
        frame.grid(row=0, column=2, sticky="nsew", padx=(1, 0))

        # Tabs: Log / Métricas
        self.tabs = ctk.CTkTabview(frame, fg_color=C_PANEL,
                                    segmented_button_fg_color=C_SURFACE,
                                    segmented_button_selected_color=C_ACCENT,
                                    segmented_button_selected_hover_color="#3a6fd4")
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabs.add("Log")
        self.tabs.add("Métricas")

        # Log
        self.log_text = tk.Text(
            self.tabs.tab("Log"),
            bg=C_BG, fg=C_TEXT,
            font=("Courier New", 11),
            relief="flat", bd=0,
            state="disabled", wrap="word",
            padx=8, pady=8,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("ok",    foreground=C_SUCCESS)
        self.log_text.tag_configure("warn",  foreground=C_WARN)
        self.log_text.tag_configure("error", foreground=C_ERROR)
        self.log_text.tag_configure("info",  foreground=C_ACCENT)

        ctk.CTkButton(self.tabs.tab("Log"), text="Limpiar",
                      command=self._limpiar_log,
                      fg_color=C_SURFACE, hover_color=C_BORDER,
                      text_color=C_MUTED, height=26,
                      font=ctk.CTkFont(size=10)).pack(pady=(4, 0))

        # Métricas
        self.metricas_frame = ctk.CTkScrollableFrame(
            self.tabs.tab("Métricas"), fg_color=C_BG)
        self.metricas_frame.pack(fill="both", expand=True)
        self.lbl_metricas_placeholder = ctk.CTkLabel(
            self.metricas_frame,
            text="Procesa un archivo MIDI\npara ver las métricas.",
            text_color=C_MUTED,
            font=ctk.CTkFont(size=12),
        )
        self.lbl_metricas_placeholder.pack(pady=40)

    # ── Barra inferior: Reproductor ──────────────────────────────────
    def _build_player_bar(self):
        bar = ctk.CTkFrame(self, fg_color=C_PANEL, height=64, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        ctk.CTkFrame(self, fg_color=C_BORDER, height=1, corner_radius=0).pack(
            fill="x", side="bottom")

        ctk.CTkLabel(bar, text="PREVIEW",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C_MUTED).pack(side="left", padx=16)

        self.btn_play = ctk.CTkButton(
            bar, text="▶", width=40, height=36,
            fg_color=C_ACCENT, hover_color="#3a6fd4",
            font=ctk.CTkFont(size=16),
            command=self._toggle_play,
        )
        self.btn_play.pack(side="left", padx=8, pady=12)

        self.btn_stop = ctk.CTkButton(
            bar, text="■", width=40, height=36,
            fg_color=C_SURFACE, hover_color=C_ERROR,
            font=ctk.CTkFont(size=14),
            command=self._stop_play,
        )
        self.btn_stop.pack(side="left", padx=(0, 16), pady=12)

        self.lbl_player_file = ctk.CTkLabel(
            bar, text="Sin archivo generado",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED,
        )
        self.lbl_player_file.pack(side="left", padx=8)

        # Archivos generados
        self.lbl_outputs = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=11),
            text_color=C_SUCCESS,
        )
        self.lbl_outputs.pack(side="right", padx=16)

    # ════════════════════════════════════════════════════════════════
    # Helpers de UI
    # ════════════════════════════════════════════════════════════════

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=20, pady=(12, 0))

    def _log(self, mensaje, tipo="normal"):
        """Agrega una línea al log con color según tipo."""
        self.log_text.configure(state="normal")
        tag = tipo if tipo in ("ok", "warn", "error", "info") else ""
        self.log_text.insert("end", mensaje + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _limpiar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ════════════════════════════════════════════════════════════════
    # Acciones de archivo
    # ════════════════════════════════════════════════════════════════

    def _seleccionar_midi(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo MIDI",
            filetypes=[("MIDI", "*.mid *.midi"), ("Todos", "*.*")],
        )
        if path:
            self.midi_path.set(os.path.basename(path))
            self._midi_full_path = path
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(path))
                self._output_full_path = os.path.dirname(path)
            self._log(f"MIDI cargado: {os.path.basename(path)}", "info")

    def _seleccionar_reglas(self):
        path = filedialog.askopenfilename(
            title="Cargar archivo de reglas",
            filetypes=[("YAML", "*.yaml *.yml"), ("Todos", "*.*")],
        )
        if path:
            self.rules_path.set(os.path.basename(path))
            self._rules_full_path = path
            with open(path, "r", encoding="utf-8") as f:
                contenido = f.read()
            self.yaml_editor.delete("1.0", "end")
            self.yaml_editor.insert("1.0", contenido)
            self._highlight_yaml()
            self._log(f"Reglas cargadas: {os.path.basename(path)}", "info")

    def _seleccionar_output(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.output_dir.set(path)
            self._output_full_path = path

    def _guardar_reglas(self):
        contenido = self.yaml_editor.get("1.0", "end-1c")
        if not contenido.strip():
            messagebox.showwarning("Vacío", "El editor está vacío.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar reglas",
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml *.yml")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(contenido)
            self.rules_path.set(os.path.basename(path))
            self._rules_full_path = path
            self._log(f"Reglas guardadas: {os.path.basename(path)}", "ok")

    # ════════════════════════════════════════════════════════════════
    # Validación YAML
    # ════════════════════════════════════════════════════════════════

    def _validar_yaml(self):
        import yaml
        contenido = self.yaml_editor.get("1.0", "end-1c")
        try:
            datos = yaml.safe_load(contenido)
            # Validar estructura mínima
            from rule_engine import _validar_reglas
            _validar_reglas(datos)
            self._log("✓ YAML válido — estructura correcta", "ok")
        except Exception as e:
            self._log(f"✗ Error en YAML: {e}", "error")

    def _reset_yaml(self):
        """Recarga las reglas default desde archivo."""
        self._cargar_reglas_default()
        self._log("Reglas restauradas al default.", "warn")

    # ════════════════════════════════════════════════════════════════
    # Procesamiento principal
    # ════════════════════════════════════════════════════════════════

    def _procesar(self):
        if not hasattr(self, "_midi_full_path") or not self._midi_full_path:
            messagebox.showerror("Sin MIDI", "Seleccioná un archivo MIDI primero.")
            return

        # Guardar reglas del editor a un temp file
        import yaml, tempfile
        contenido = self.yaml_editor.get("1.0", "end-1c")
        try:
            yaml.safe_load(contenido)
        except Exception as e:
            messagebox.showerror("YAML inválido", str(e))
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False,
                                          mode="w", encoding="utf-8")
        tmp.write(contenido)
        tmp.close()
        self._temp_rules_path = tmp.name

        self.btn_procesar.configure(state="disabled", text="Procesando…")
        self.progress.set(0)
        self._limpiar_log()
        self._log("Iniciando pipeline…", "info")

        thread = threading.Thread(target=self._pipeline_thread, daemon=True)
        thread.start()

    def _pipeline_thread(self):
        """Corre el pipeline en un hilo para no bloquear la UI."""
        try:
            self._run_pipeline()
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._log(f"ERROR: {m}", "error"))
        finally:
            self.after(0, self._pipeline_done)

    def _run_pipeline(self):
        import importlib

        def log(msg, tipo="normal"):
            self.after(0, lambda m=msg, t=tipo: self._log(m, t))

        def prog(v):
            self.after(0, lambda: self.progress.set(v))

        # Redirigir stdout al log
        import io
        class LogCapture(io.StringIO):
            def __init__(self_, log_fn):
                super().__init__()
                self_._log_fn = log_fn
            def write(self_, s):
                if s.strip():
                    self_._log_fn(s.strip())
                return len(s)

        sys.stdout = LogCapture(log)

        try:
            from midi_parser  import leer_midi
            from rule_engine  import cargar_reglas, separar_voces_con_reglas
            from metrics      import calcular_metricas, exportar_csv
            from exporter     import construir_score, exportar

            # 1. Parsear MIDI
            log("── Parseando MIDI…", "info")
            todas_notas, drum_notas, tempo_bpm, info = leer_midi(self._midi_full_path)
            prog(0.25)

            if not todas_notas:
                log("ERROR: No se encontraron notas musicales.", "error")
                return

            # 2. Cargar reglas
            log("── Cargando reglas…", "info")
            reglas = cargar_reglas(self._temp_rules_path)
            prog(0.4)

            # 3. Separar voces
            log("── Separando voces…", "info")
            voces, nombres_voz, rangos = separar_voces_con_reglas(todas_notas, reglas)
            prog(0.6)

            # 4. Métricas
            log("── Calculando métricas…", "info")
            metricas = calcular_metricas(None, voces, nombres_voz)
            self.after(0, lambda m=metricas: self._mostrar_metricas(m))
            prog(0.75)

            # 5. Exportar
            log("── Exportando…", "info")
            score = construir_score(voces, drum_notas, tempo_bpm, info["time_signature"], nombres_voz, reglas)
            output_dir = getattr(self, "_output_full_path",
                                  os.path.dirname(self._midi_full_path))
            nombre_base = os.path.splitext(
                os.path.basename(self._midi_full_path))[0] + "_arreglo"
            xml_path, midi_path = exportar(score, output_dir, nombre_base)
            prog(0.9)

            # CSV métricas
            csv_path = os.path.join(output_dir, nombre_base + "_metricas.csv")
            exportar_csv(metricas, csv_path)
            prog(1.0)

            # Guardar MIDI generado para reproductor
            self._generated_midi = midi_path
            self.after(0, lambda: self.lbl_player_file.configure(
                text=os.path.basename(midi_path), text_color=C_SUCCESS))
            self.after(0, lambda: self.lbl_outputs.configure(
                text=f"✓ {os.path.basename(xml_path)}  |  ✓ {os.path.basename(midi_path)}"))

            log(f"✓ MusicXML → {xml_path}", "ok")
            log(f"✓ MIDI     → {midi_path}", "ok")
            log(f"✓ CSV      → {csv_path}", "ok")
            log("Pipeline completado exitosamente.", "ok")

        finally:
            sys.stdout = sys.__stdout__

    def _pipeline_done(self):
        self.btn_procesar.configure(state="normal", text="▶  PROCESAR ARREGLO")

    # ════════════════════════════════════════════════════════════════
    # Métricas
    # ════════════════════════════════════════════════════════════════

    def _mostrar_metricas(self, metricas):
        # Limpiar frame
        for w in self.metricas_frame.winfo_children():
            w.destroy()

        colores_voz = {
            "Soprano": "#f7c948",
            "Alto":    "#4f8ef7",
            "Tenor":   "#3ddc97",
            "Bajo":    "#c084fc",
        }

        for nombre, m in metricas.items():
            card = ctk.CTkFrame(self.metricas_frame, fg_color=C_SURFACE,
                                 corner_radius=8)
            card.pack(fill="x", padx=8, pady=6)

            ctk.CTkLabel(card, text=nombre,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=colores_voz.get(nombre, C_TEXT),
                         ).pack(anchor="w", padx=12, pady=(10, 4))

            datos = [
                ("Notas totales",   str(m["total_notas"])),
                ("En rango",        f"{m['pct_en_rango']:.1f}%"),
                ("Voice leading",   f"{m['vl_promedio']:.2f} st"),
                ("Colisiones",      str(m["colisiones"])),
            ]
            for llave, valor in datos:
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=1)
                ctk.CTkLabel(row, text=llave,
                             font=ctk.CTkFont(size=11),
                             text_color=C_MUTED, width=120, anchor="w",
                             ).pack(side="left")
                color = C_SUCCESS if llave == "En rango" and float(valor.replace("%","")) >= 95 \
                        else C_ERROR if llave == "Colisiones" and int(valor) > 0 \
                        else C_TEXT
                ctk.CTkLabel(row, text=valor,
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=color,
                             ).pack(side="right")
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

    # ════════════════════════════════════════════════════════════════
    # Reproductor MIDI
    # ════════════════════════════════════════════════════════════════

    def _toggle_play(self):
        if not hasattr(self, "_generated_midi") or not self._generated_midi:
            messagebox.showinfo("Sin audio", "Procesá un MIDI primero para generar el arreglo.")
            return
        if self.midi_player and self.midi_player.is_playing():
            self.midi_player.pause()
            self.btn_play.configure(text="▶")
        else:
            self._iniciar_player()
            self.btn_play.configure(text="⏸")

    def _stop_play(self):
        if self.midi_player:
            self.midi_player.stop()
            self.midi_player = None
        self.btn_play.configure(text="▶")

    def _iniciar_player(self):
        """Reproduce el MIDI generado usando pygame.mixer si está disponible."""
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(self._generated_midi)
            pygame.mixer.music.play()

            class _Player:
                def is_playing(self):
                    return pygame.mixer.music.get_busy()
                def pause(self):
                    pygame.mixer.music.pause()
                def stop(self):
                    pygame.mixer.music.stop()

            self.midi_player = _Player()
            self._log("▶ Reproduciendo arreglo…", "info")

        except ImportError:
            # Fallback: abrir con el programa default del sistema
            import subprocess, platform
            plat = platform.system()
            if plat == "Darwin":
                subprocess.Popen(["open", self._generated_midi])
            elif plat == "Windows":
                os.startfile(self._generated_midi)
            else:
                subprocess.Popen(["xdg-open", self._generated_midi])
            self._log("▶ Abriendo en reproductor del sistema…", "info")

    # ════════════════════════════════════════════════════════════════
    # Syntax Highlighting YAML (básico)
    # ════════════════════════════════════════════════════════════════

    def _highlight_yaml(self, event=None):
        editor = self.yaml_editor
        for tag in ("comment", "key", "value", "section"):
            editor.tag_remove(tag, "1.0", "end")

        content = editor.get("1.0", "end")
        lines = content.split("\n")
        for i, line in enumerate(lines):
            lineno = i + 1
            if line.strip().startswith("#"):
                editor.tag_add("comment", f"{lineno}.0", f"{lineno}.end")
            elif ":" in line and not line.strip().startswith("-"):
                col = line.index(":")
                # Clave
                editor.tag_add("key", f"{lineno}.0", f"{lineno}.{col}")
                # Valor
                if col + 1 < len(line):
                    editor.tag_add("value", f"{lineno}.{col+1}", f"{lineno}.end")
                # Sección sin valor = header
                if line.strip().endswith(":"):
                    editor.tag_add("section", f"{lineno}.0", f"{lineno}.end")

    # ════════════════════════════════════════════════════════════════
    # Carga de reglas default
    # ════════════════════════════════════════════════════════════════

    def _cargar_reglas_default(self):
        """Busca el YAML default junto al script."""
        default_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "reglas_marimba_guatemalteca.yaml"
        )
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                contenido = f.read()
            self.yaml_editor.delete("1.0", "end")
            self.yaml_editor.insert("1.0", contenido)
            self._highlight_yaml()
            self._rules_full_path = default_path
            self.rules_path.set("reglas_marimba_guatemalteca.yaml")


    # ════════════════════════════════════════════════════════════════
    # Panel Asistente IA
    # ════════════════════════════════════════════════════════════════

    def _build_assistant_panel(self, parent):
        """Panel lateral derecho con chat LLM para generar YAMLs."""
        frame = ctk.CTkFrame(parent, fg_color=C_PANEL, corner_radius=0)
        frame.grid(row=0, column=3, sticky="nsew", padx=(1, 0))

        if LLM_DISPONIBLE:
            self.llm_panel = LLMAssistantPanel(
                parent=frame,
                on_yaml_generado=self._yaml_desde_llm,
            )
        else:
            # Fallback si llm_assistant.py no está presente
            ctk.CTkLabel(
                frame,
                text="✦  ASISTENTE IA",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=C_MUTED,
            ).pack(anchor="w", padx=16, pady=(20, 8))
            ctk.CTkLabel(
                frame,
                text="llm_assistant.py no encontrado.\nAgregalo a la carpeta del proyecto.",
                font=ctk.CTkFont(size=11),
                text_color=C_MUTED,
                wraplength=240,
                justify="left",
            ).pack(padx=16, pady=8)

    def _yaml_desde_llm(self, yaml_str):
        """
        Callback del asistente LLM.
        Carga el YAML generado en el editor central.
        """
        self.yaml_editor.delete("1.0", "end")
        self.yaml_editor.insert("1.0", yaml_str)
        self._highlight_yaml()
        self.rules_path.set("generado por asistente IA")
        self._log("✦ YAML generado por asistente IA cargado en el editor.", "info")
        # Cambiar a tab Log para que el usuario vea la confirmación
        try:
            self.tabs.set("Log")
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = ArrangerApp()
    app.mainloop()