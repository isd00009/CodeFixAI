# ui/main_window.py
import os
import re
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
    QRadioButton, QPlainTextEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QHBoxLayout, QVBoxLayout,
    QMessageBox, QApplication, QFileDialog, QDialog
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from logic.controller import Controller

# Colores suaves para el diff
COLOR_ADD = QColor("#e6f4e6")
COLOR_REM = QColor("#f4e6e6")
COLOR_CTX = QColor("#e6edf4")
COLOR_HDR = QColor("#f0f0f0")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = Controller()

        # Navegación de archivos originales
        self.dir_files = []
        self.current_file_index = -1

        # Para guardar los originales históricos
        self.orig_map = {}

        # Resultados multi-archivo
        self.corrected_map = {}
        self.diff_map = {}
        self.current_result_index = -1

        # Resultado de paste único
        self.paste_clean = ""
        self.paste_diff = []

        # Modos
        self.diff_mode = False
        self.paste_mode = True

        # Historial de ejecuciones
        self.history = []  # cada entry guarda orig_map, corrected_map, diff_map, etc.

        self.setWindowTitle("CodeFixAI")
        self.resize(1280, 720)
        self._setup_ui()

        saved = self.controller.load_api_key()
        if saved:
            self.api_line.setText(saved)
            self.btn_execute.setEnabled(True)

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Zona superior: API key, guardar, historial, modo
        top = QHBoxLayout()
        api_g = QGroupBox()
        api_l = QHBoxLayout(api_g)
        api_l.addWidget(QLabel("Clave de API:"))
        self.api_line = QLineEdit()
        self.api_line.setEchoMode(QLineEdit.Password)
        api_l.addWidget(self.api_line)
        self.btn_save = QPushButton("Guardar")
        api_l.addWidget(self.btn_save)
        self.btn_history = QPushButton("Historial")
        api_l.addWidget(self.btn_history)
        top.addWidget(api_g)

        mode_g = QGroupBox()
        mode_l = QHBoxLayout(mode_g)
        mode_l.addWidget(QLabel("Modo:"))
        self.radio_correct = QRadioButton("Corrección")
        self.radio_correct.setChecked(True)
        self.radio_opt = QRadioButton("Optimización")
        mode_l.addWidget(self.radio_correct)
        mode_l.addWidget(self.radio_opt)
        top.addWidget(mode_g)

        main_layout.addLayout(top)

        # Zona central
        center = QHBoxLayout()

        # Panel CÓDIGO
        code_g = QGroupBox("CÓDIGO")
        code_l = QVBoxLayout(code_g)
        self.lbl_code_filename = QLabel("")
        self.lbl_code_filename.setAlignment(Qt.AlignCenter)
        code_l.addWidget(self.lbl_code_filename)
        self.txt_code = QPlainTextEdit()
        self.txt_code.textChanged.connect(self.on_code_changed)
        code_l.addWidget(self.txt_code)
        self.btn_open_file = QPushButton("Abrir fichero…")
        self.btn_open_dir = QPushButton("Abrir directorio…")
        code_l.addWidget(self.btn_open_file)
        code_l.addWidget(self.btn_open_dir)
        nav_code = QHBoxLayout()
        self.btn_prev_file = QPushButton("←")
        self.btn_next_file = QPushButton("→")
        for b in (self.btn_prev_file, self.btn_next_file):
            b.setEnabled(False)
            nav_code.addWidget(b)
        code_l.addLayout(nav_code)
        center.addWidget(code_g, stretch=3)

        # Controles centrales
        mid = QVBoxLayout()
        self.btn_execute = QPushButton("Ejecutar")
        mid.addWidget(self.btn_execute, alignment=Qt.AlignCenter)
        self.lbl_spinner = QLabel("")
        mid.addWidget(self.lbl_spinner, alignment=Qt.AlignCenter)
        center.addLayout(mid, stretch=1)

        # Panel RESULTADO
        res_g = QGroupBox("RESULTADO")
        res_l = QVBoxLayout(res_g)
        self.lbl_result_filename = QLabel("")
        self.lbl_result_filename.setAlignment(Qt.AlignCenter)
        res_l.addWidget(self.lbl_result_filename)
        self.stack = QStackedWidget()
        self.page_code = QPlainTextEdit()
        self.page_code.setReadOnly(True)
        self.page_diff = QListWidget()
        font = QFont("Consolas", 11)
        self.txt_code.setFont(font)
        self.page_code.setFont(font)
        self.page_diff.setFont(font)
        self.stack.addWidget(self.page_code)
        self.stack.addWidget(self.page_diff)
        res_l.addWidget(self.stack)
        nav_res = QHBoxLayout()
        self.btn_prev_res = QPushButton("←")
        self.btn_next_res = QPushButton("→")
        for b in (self.btn_prev_res, self.btn_next_res):
            b.setEnabled(False)
            nav_res.addWidget(b)
        res_l.addLayout(nav_res)
        # Botones Copiar / Mostrar diff / Guardar
        btns = QHBoxLayout()
        self.btn_copy = QPushButton("Copiar")
        self.btn_diff = QPushButton("Mostrar diff")
        self.btn_diff.setEnabled(False)
        self.btn_save_file = QPushButton("Guardar resultado")
        self.btn_save_file.setEnabled(False)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_diff)
        btns.addWidget(self.btn_save_file)
        res_l.addLayout(btns)
        center.addWidget(res_g, stretch=3)

        main_layout.addLayout(center)

        # Estados iniciales
        self.btn_execute.setEnabled(False)
        self.btn_copy.setEnabled(False)

        # Conectar señales
        self.btn_save.clicked.connect(self.on_save_api)
        self.btn_history.clicked.connect(self.on_show_history)
        self.btn_open_file.clicked.connect(self.on_open_file)
        self.btn_open_dir.clicked.connect(self.on_open_dir)
        self.btn_prev_file.clicked.connect(self.on_prev_file)
        self.btn_next_file.clicked.connect(self.on_next_file)
        self.btn_prev_res.clicked.connect(self.on_prev_result)
        self.btn_next_res.clicked.connect(self.on_next_result)
        self.btn_execute.clicked.connect(self.on_execute)
        self.btn_copy.clicked.connect(self.on_copy)
        self.btn_diff.clicked.connect(self.on_show_diff)
        self.btn_save_file.clicked.connect(self.on_save_file_result)

    def on_code_changed(self):
        """El usuario editó texto: volvemos a paste_mode."""
        self.paste_mode = True
        self.dir_files.clear()
        self.current_file_index = -1
        self._update_file_nav()
        self._update_code_filename()
        self._update_result_filename()

    def on_save_api(self):
        key = self.api_line.text().strip()
        if not self.controller.validate_api_key(key):
            QMessageBox.warning(self, "Clave inválida", "Clave ≥ 20 caracteres.")
            return
        try:
            self.controller.save_api_key(key)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        QMessageBox.information(self, "Clave guardada", "Clave de API almacenada.")
        self.btn_execute.setEnabled(True)

    def on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar fichero", "", "Código (*.py *.cpp *.c *.java *.js);;Todos (*.*)"
        )
        if not path:
            return
        self.paste_mode = False
        self.dir_files = [path]
        self.current_file_index = 0
        self.corrected_map.clear()
        self.diff_map.clear()
        self.current_result_index = -1
        self.paste_clean = ""
        self.paste_diff.clear()
        self.diff_mode = False
        self.btn_diff.setText("Mostrar diff")
        self._update_file_nav()
        self._update_result_nav()
        self._display_initial_file(path)
        self.btn_execute.setEnabled(True)

    def on_open_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Seleccionar directorio", "")
        if not dirpath:
            return
        exts = {".py", ".cpp", ".c", ".h", ".java", ".js"}
        files = []
        for root, _, fnames in os.walk(dirpath):
            for f in fnames:
                if os.path.splitext(f)[1] in exts:
                    files.append(os.path.join(root, f))
        if not files:
            QMessageBox.information(self, "Sin ficheros", "No se encontraron archivos de código.")
            return
        self.paste_mode = False
        self.dir_files = sorted(files)
        self.current_file_index = 0
        self.corrected_map.clear()
        self.diff_map.clear()
        self.current_result_index = -1
        self.paste_clean = ""
        self.paste_diff.clear()
        self.diff_mode = False
        self.btn_diff.setText("Mostrar diff")
        self._update_file_nav()
        self._update_result_nav()
        self._display_initial_file(self.dir_files[0])
        self.btn_execute.setEnabled(True)

    def _display_initial_file(self, path):
        """Carga archivo en txt_code y limpia resultados."""
        try:
            text = open(path, "r", encoding="utf-8").read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer {path}:\n{e}")
            return
        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(text)
        self.txt_code.blockSignals(False)
        self.page_code.clear()
        self.page_diff.clear()
        self.stack.setCurrentIndex(0)
        self.btn_diff.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self._update_code_filename()

    def _load_code_file(self, path):
        """
        Navegación en CÓDIGO: si hay orig_map,
        carga ese texto; si no, lee desde disco.
        """
        if not self.paste_mode and path in self.orig_map:
            text = self.orig_map[path]
        else:
            try:
                text = open(path, "r", encoding="utf-8").read()
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                     f"No se pudo leer {path}:\n{e}")
                return
        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(text)
        self.txt_code.blockSignals(False)
        self._update_code_filename()

    def _update_file_nav(self):
        n, idx = len(self.dir_files), self.current_file_index
        ok = n > 1
        self.btn_prev_file.setEnabled(ok and idx > 0)
        self.btn_next_file.setEnabled(ok and idx < n - 1)

    def _update_result_nav(self):
        n, idx = len(self.dir_files), self.current_result_index
        ok = n > 1 and idx >= 0
        self.btn_prev_res.setEnabled(ok and idx > 0)
        self.btn_next_res.setEnabled(ok and idx < n - 1)

    def _update_code_filename(self):
        """Actualiza la etiqueta con el nombre del fichero en el panel CÓDIGO."""
        if not self.paste_mode and self.dir_files:
            name = os.path.basename(self.dir_files[self.current_file_index])
            self.lbl_code_filename.setText(name)
        else:
            self.lbl_code_filename.setText("Editor de código")

    def _update_result_filename(self):
        """Actualiza la etiqueta con el nombre del fichero en el panel RESULTADO."""
        if not self.paste_mode and self.dir_files and self.current_result_index >= 0:
            name = os.path.basename(self.dir_files[self.current_result_index])
            self.lbl_result_filename.setText(name)
        else:
            self.lbl_result_filename.setText("Salida de IA")

    def on_prev_file(self):
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self._update_file_nav()
            self._load_code_file(self.dir_files[self.current_file_index])
            self._update_code_filename()

    def on_next_file(self):
        if self.current_file_index < len(self.dir_files) - 1:
            self.current_file_index += 1
            self._update_file_nav()
            self._load_code_file(self.dir_files[self.current_file_index])
            self._update_code_filename()

    def on_execute(self):
        import datetime

        code = self.txt_code.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Sin entrada",
                                "Pega o carga un fragmento de código primero.")
            return

        mode = "optimization" if self.radio_opt.isChecked() else "correction"
        self.btn_execute.setEnabled(False)
        self.lbl_spinner.setText(
            "Procesando todos…" if (not self.paste_mode and len(self.dir_files) > 1)
            else "Procesando…"
        )
        QApplication.processEvents()

        # Preparamos orig_map para esta ejecución
        self.orig_map = {}

        try:
            if self.paste_mode:
                prompt = self.controller.build_prompt(code, mode)
                raw = self.controller.send_to_openai(prompt)
                clean = self.controller.extract_code(raw)
                self.paste_clean = clean
                self.paste_diff = self.controller.generar_diff(code, clean)
                self.current_result_index = 0
            else:
                for path in self.dir_files:
                    orig = open(path, "r", encoding="utf-8").read()
                    self.orig_map[path] = orig
                    prompt = self.controller.build_prompt(orig, mode)
                    raw = self.controller.send_to_openai(prompt)
                    clean = self.controller.extract_code(raw)
                    self.corrected_map[path] = clean
                    self.diff_map[path] = self.controller.generar_diff(orig, clean)
                self.current_result_index = 0

            # Guardar en historial
            entry = {
                "timestamp": datetime.datetime.now(),
                "mode": mode,
                "paste_mode": self.paste_mode,
                "dir_files": list(self.dir_files),
                "orig_map": dict(self.orig_map),
                "corrected_map": dict(self.corrected_map),
                "diff_map": dict(self.diff_map),
                "paste_original": code,
                "paste_clean": self.paste_clean,
                "paste_diff": list(self.paste_diff),
            }
            self.history.append(entry)

            # reset de diff y mostrar primer resultado
            self.diff_mode = False
            self.btn_diff.setText("Mostrar diff")
            self._show_current_result()
            self._update_result_nav()

        except Exception as e:
            QMessageBox.critical(self, "Error en la petición", str(e))
        finally:
            self.lbl_spinner.setText("")
            self.btn_execute.setEnabled(True)
            self.btn_diff.setEnabled(True)
            self.btn_copy.setEnabled(True)
            self.btn_save_file.setEnabled(True)

    def on_prev_result(self):
        if self.current_result_index > 0:
            self.current_result_index -= 1
            self._show_current_result()
            self._update_result_nav()
        self.stack.currentWidget().setFocus()
        self._update_result_filename()

    def on_next_result(self):
        max_idx = len(self.dir_files) - 1 if not self.paste_mode else 0
        if self.current_result_index < max_idx:
            self.current_result_index += 1
            self._show_current_result()
            self._update_result_nav()
        self.stack.currentWidget().setFocus()
        self._update_result_filename()

    def _show_current_result(self):
        idx = self.current_result_index
        if idx < 0:
            return
        self._update_result_filename()
        if self.diff_mode:
            self.page_diff.clear()
            lines = (
                self.diff_map.get(self.dir_files[idx], [])
                if not self.paste_mode else self.paste_diff
            )
            for line in lines:
                item = QListWidgetItem(line.rstrip("\n"))
                if line.startswith("+") and not line.startswith("+++"):
                    item.setBackground(COLOR_ADD);
                    item.setForeground(QColor("black"))
                elif line.startswith("-") and not line.startswith("---"):
                    item.setBackground(COLOR_REM);
                    item.setForeground(QColor("black"))
                elif line.startswith("@@"):
                    item.setBackground(COLOR_CTX);
                    item.setForeground(QColor("black"))
                elif line.startswith("---") or line.startswith("+++"):
                    item.setBackground(COLOR_HDR);
                    item.setForeground(QColor("black"))
                self.page_diff.addItem(item)
            self.stack.setCurrentIndex(1)
        else:
            text = self.paste_clean if self.paste_mode else self.corrected_map.get(self.dir_files[idx], "")
            self.page_code.setPlainText(text)
            self.stack.setCurrentIndex(0)

    def on_copy(self):
        if self.diff_mode:
            return
        if self.paste_mode:
            QApplication.clipboard().setText(self.paste_clean)
        else:
            path = self.dir_files[self.current_result_index]
            QApplication.clipboard().setText(self.corrected_map.get(path, ""))
        QMessageBox.information(self, "Copiado", "Código copiado al portapapeles.")

    def on_show_diff(self):
        self.diff_mode = not self.diff_mode
        self.btn_diff.setText("Mostrar código" if self.diff_mode else "Mostrar diff")
        self._show_current_result()

    def on_save_file_result(self):
        """Guardar el código corregido/optimizado actual a un fichero, sugiriendo la extensión correcta."""
        if self.diff_mode:
            QMessageBox.warning(self, "Guardar", "Desactiva el diff para guardar el código.")
            return

        text = self.paste_clean if self.paste_mode else self.corrected_map.get(
            self.dir_files[self.current_result_index], ""
        )
        if not text:
            QMessageBox.warning(self, "Guardar", "No hay código para guardar.")
            return

        lang = self.controller.detect_language(text)
        if lang == "Python":
            filter_str = "Python (*.py);;Todos (*.*)"
        elif lang == "C++":
            filter_str = "C++ (*.cpp *.h);;Todos (*.*)"
        elif lang == "Java":
            filter_str = "Java (*.java);;Todos (*.*)"
        else:
            filter_str = "Todos (*.*)"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar resultado", "", filter_str
        )
        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))
        else:
            QMessageBox.information(self, "Guardado", f"Resultado guardado en:\n{save_path}")

    def on_show_history(self):
        from PyQt5.QtWidgets import QDialog

        dialog = QDialog(self)
        dialog.setWindowTitle("Historial de ejecuciones")
        layout = QVBoxLayout(dialog)

        # Lista de entradas de historial
        list_w = QListWidget()
        for entry in self.history:
            ts = entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            if entry["paste_mode"]:
                label = f"{ts} — Paste ({entry['mode']})"
            else:
                cnt = len(entry["dir_files"])
                label = f"{ts} — {cnt} archivos ({entry['mode']})"
            list_w.addItem(label)
        layout.addWidget(list_w)

        # Botones Cargar / Eliminar / Cerrar
        btns = QHBoxLayout()
        btn_load = QPushButton("Cargar")
        btn_del = QPushButton("Eliminar")
        btn_close = QPushButton("Cerrar")
        btns.addWidget(btn_load)
        btns.addWidget(btn_del)
        btns.addWidget(btn_close)
        layout.addLayout(btns)

        def load_selected():
            idx = list_w.currentRow()
            if idx < 0:
                return
            entry = self.history[idx]

            # Restaurar flags y mapas
            self.paste_mode = entry["paste_mode"]
            self.dir_files = list(entry["dir_files"])
            self.orig_map = dict(entry["orig_map"])
            self.corrected_map = dict(entry["corrected_map"])
            self.diff_map = dict(entry["diff_map"])
            self.paste_clean = entry["paste_clean"]
            self.paste_diff = list(entry["paste_diff"])
            self.current_file_index = 0
            self.current_result_index = 0
            self.diff_mode = False
            self.btn_diff.setText("Mostrar diff")

            # Actualizar navegación
            self._update_file_nav()
            self._update_result_nav()

            # Mostrar el original correcto en el panel CÓDIGO
            if self.paste_mode:
                self.txt_code.setPlainText(entry["paste_original"])
            else:
                # navegamos con nuestro método que respeta orig_map
                self._load_code_file(self.dir_files[0])

            # Mostrar el resultado histórico (código corregido)
            self._show_current_result()

            dialog.accept()

        def del_selected():
            idx = list_w.currentRow()
            if idx < 0:
                return
            self.history.pop(idx)
            list_w.takeItem(idx)

        btn_load.clicked.connect(load_selected)
        btn_del.clicked.connect(del_selected)
        btn_close.clicked.connect(dialog.reject)

        dialog.exec_()
