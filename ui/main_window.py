# ui/main_window.py
import os
import re
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
    QRadioButton, QPlainTextEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QHBoxLayout, QVBoxLayout,
    QMessageBox, QApplication, QFileDialog
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

        # Zona superior
        top = QHBoxLayout()
        api_g = QGroupBox()
        api_l = QHBoxLayout(api_g)
        api_l.addWidget(QLabel("Clave de API:"))
        self.api_line = QLineEdit()
        self.api_line.setEchoMode(QLineEdit.Password)
        api_l.addWidget(self.api_line)
        self.btn_save = QPushButton("Guardar")
        api_l.addWidget(self.btn_save)
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
        self.txt_code = QPlainTextEdit()
        # Detectar cambios para activar paste_mode
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
        btns = QHBoxLayout()
        self.btn_copy = QPushButton("Copiar")
        self.btn_diff = QPushButton("Mostrar diff")
        self.btn_diff.setEnabled(False)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_diff)
        res_l.addLayout(btns)
        center.addWidget(res_g, stretch=3)

        main_layout.addLayout(center)

        # Inicializar estados
        self.btn_execute.setEnabled(False)
        self.btn_copy.setEnabled(False)

        # Conectar señales
        self.btn_save.clicked.connect(self.on_save_api)
        self.btn_open_file.clicked.connect(self.on_open_file)
        self.btn_open_dir.clicked.connect(self.on_open_dir)
        self.btn_prev_file.clicked.connect(self.on_prev_file)
        self.btn_next_file.clicked.connect(self.on_next_file)
        self.btn_prev_res.clicked.connect(self.on_prev_result)
        self.btn_next_res.clicked.connect(self.on_next_result)
        self.btn_execute.clicked.connect(self.on_execute)
        self.btn_copy.clicked.connect(self.on_copy)
        self.btn_diff.clicked.connect(self.on_show_diff)

    def on_code_changed(self):
        """El usuario ha editado el texto: volvemos a paste_mode."""
        self.paste_mode = True
        self.dir_files.clear()
        self.current_file_index = -1
        self._update_file_nav()
        # No tocamos RESULTADO para mantener lo anterior si ya existía

    def on_save_api(self):
        key = self.api_line.text().strip()
        if not self.controller.validate_api_key(key):
            QMessageBox.warning(self, "Clave inválida", "Clave de API ≥ 20 caracteres.")
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
            self, "Seleccionar fichero", "", "Código (*.py *.cpp *.c *.java);;Todos (*.*)"
        )
        if not path:
            return
        # Modo archivos
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
        exts = {".py", ".cpp", ".c", ".h", ".java"}
        files = []
        for root, _, fnames in os.walk(dirpath):
            for f in fnames:
                if os.path.splitext(f)[1] in exts:
                    files.append(os.path.join(root, f))
        if not files:
            QMessageBox.information(self, "Sin ficheros", "No se encontraron archivos de código.")
            return
        # Modo archivos
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
        """Carga el archivo en txt_code y limpia resultados."""
        try:
            text = open(path, "r", encoding="utf-8").read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer {path}:\n{e}")
            return
        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(text)
        self.txt_code.blockSignals(False)
        # Limpiar resultados solo aquí
        self.page_code.clear()
        self.page_diff.clear()
        self.stack.setCurrentIndex(0)
        self.btn_diff.setEnabled(False)
        self.btn_copy.setEnabled(False)

    def _load_code_file(self, path):
        """Carga el archivo solo en el panel de CÓDIGO, sin tocar RESULTADO."""
        try:
            text = open(path, "r", encoding="utf-8").read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer {path}:\n{e}")
            return
        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(text)
        self.txt_code.blockSignals(False)

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

    def on_prev_file(self):
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self._update_file_nav()
            self._load_code_file(self.dir_files[self.current_file_index])

    def on_next_file(self):
        if self.current_file_index < len(self.dir_files) - 1:
            self.current_file_index += 1
            self._update_file_nav()
            self._load_code_file(self.dir_files[self.current_file_index])

    def on_execute(self):
        code = self.txt_code.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Sin entrada", "Pega o carga un fragmento primero.")
            return

        # Determinar modo según el radio seleccionado
        mode = "optimization" if self.radio_opt.isChecked() else "correction"

        # Desactivamos botón y mostramos spinner
        self.btn_execute.setEnabled(False)
        if not self.paste_mode and len(self.dir_files) > 1:
            self.lbl_spinner.setText("Procesando todos…")
        else:
            self.lbl_spinner.setText("Procesando…")
        QApplication.processEvents()

        try:
            if self.paste_mode:
                # Modo pegado único
                prompt = self.controller.build_prompt(code, mode)
                raw = self.controller.send_to_openai(prompt)
                clean = self.controller.extract_code(raw)
                self.paste_clean = clean
                self.paste_diff = self.controller.generar_diff(code, clean)
                self.current_result_index = 0
            else:
                # Modo multi-archivo
                for path in self.dir_files:
                    orig = open(path, "r", encoding="utf-8").read()
                    prompt = self.controller.build_prompt(orig, mode)
                    raw = self.controller.send_to_openai(prompt)
                    clean = self.controller.extract_code(raw)
                    self.corrected_map[path] = clean
                    self.diff_map[path] = self.controller.generar_diff(orig, clean)
                self.current_result_index = 0

            # Reset de diff_mode y mostrar primer resultado
            self.diff_mode = False
            self.btn_diff.setText("Mostrar diff")
            self._show_current_result()
            self._update_result_nav()

        except Exception as e:
            QMessageBox.critical(self, "Error en la petición", str(e))
        finally:
            # Restaurar estado de la interfaz
            self.lbl_spinner.setText("")
            self.btn_execute.setEnabled(True)
            self.btn_diff.setEnabled(True)
            self.btn_copy.setEnabled(True)

    def on_prev_result(self):
        if self.current_result_index > 0:
            self.current_result_index -= 1
            self._show_current_result()
            self._update_result_nav()
        self.stack.currentWidget().setFocus()

    def on_next_result(self):
        max_idx = len(self.dir_files) - 1 if not self.paste_mode else 0
        if self.current_result_index < max_idx:
            self.current_result_index += 1
            self._show_current_result()
            self._update_result_nav()
        self.stack.currentWidget().setFocus()

    def _show_current_result(self):
        idx = self.current_result_index
        if idx < 0:
            return
        if self.diff_mode:
            # Mostrar diff
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
            # Mostrar código corregido
            if self.paste_mode:
                text = self.paste_clean
            else:
                text = self.corrected_map.get(self.dir_files[idx], "")
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
