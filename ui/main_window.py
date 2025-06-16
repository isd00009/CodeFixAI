# ui/main_window.py
import re
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
    QRadioButton, QPlainTextEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QHBoxLayout, QVBoxLayout,
    QMessageBox, QApplication
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
        self.last_original = ""
        self.last_corrected = ""

        self.setWindowTitle("CodeFixAI")
        self.resize(1280, 720)
        self._setup_ui()

        # Cargar clave si existe
        saved = self.controller.load_api_key()
        if saved:
            self.api_line.setText(saved)
            self.btn_execute.setEnabled(True)

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ─── Zona superior ───
        top_layout = QHBoxLayout()
        api_group = QGroupBox()
        api_layout = QHBoxLayout(api_group)
        api_layout.addWidget(QLabel("Clave de API:"))
        self.api_line = QLineEdit()
        self.api_line.setEchoMode(QLineEdit.Password)
        api_layout.addWidget(self.api_line)
        self.btn_save = QPushButton("Guardar")
        api_layout.addWidget(self.btn_save)
        top_layout.addWidget(api_group)

        mode_group = QGroupBox()
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("Modo:"))
        self.radio_correct = QRadioButton("Corrección")
        self.radio_correct.setChecked(True)
        mode_layout.addWidget(self.radio_correct)
        self.radio_opt = QRadioButton("Optimización")
        self.radio_opt.setEnabled(False)
        mode_layout.addWidget(self.radio_opt)
        top_layout.addWidget(mode_group)

        main_layout.addLayout(top_layout)

        # ─── Zona central ───
        center_layout = QHBoxLayout()

        # Panel de entrada de código
        code_group = QGroupBox("CÓDIGO")
        code_layout = QVBoxLayout(code_group)
        self.txt_code = QPlainTextEdit()
        code_layout.addWidget(self.txt_code)
        center_layout.addWidget(code_group, stretch=3)

        # Controles centrales
        mid = QVBoxLayout()
        self.btn_execute = QPushButton("Ejecutar")
        mid.addWidget(self.btn_execute, alignment=Qt.AlignCenter)
        for arrow in ("→", "←"):
            lbl = QLabel(arrow)
            lbl.setAlignment(Qt.AlignCenter)
            mid.addWidget(lbl)
        self.lbl_spinner = QLabel("")
        mid.addWidget(self.lbl_spinner, alignment=Qt.AlignCenter)
        center_layout.addLayout(mid, stretch=1)

        # Panel RESULTADO / diff
        result_group = QGroupBox("RESULTADO")
        result_layout = QVBoxLayout(result_group)

        # QStackedWidget para alternar entre código limpio y diff
        self.stack = QStackedWidget()
        self.page_code = QPlainTextEdit()
        self.page_code.setReadOnly(True)
        self.page_diff = QListWidget()

        # Misma fuente en todas las áreas de texto
        font = QFont("Consolas", 11)
        self.txt_code.setFont(font)     # <–– Aplicar fuente a la izquierda también
        self.page_code.setFont(font)
        self.page_diff.setFont(font)

        self.stack.addWidget(self.page_code)
        self.stack.addWidget(self.page_diff)
        result_layout.addWidget(self.stack)

        # Botones Copiar / Mostrar diff
        btns = QHBoxLayout()
        self.btn_copy = QPushButton("Copiar")
        self.btn_diff = QPushButton("Mostrar diff")
        self.btn_diff.setEnabled(False)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_diff)
        result_layout.addLayout(btns)

        center_layout.addWidget(result_group, stretch=3)
        main_layout.addLayout(center_layout)

        # Estados iniciales
        self.btn_execute.setEnabled(False)
        self.btn_copy.setEnabled(False)

        # Conexiones
        self.btn_save.clicked.connect(self.on_save_api)
        self.btn_execute.clicked.connect(self.on_execute)
        self.btn_copy.clicked.connect(self.on_copy)
        self.btn_diff.clicked.connect(self.on_show_diff)

    def on_save_api(self):
        key = self.api_line.text().strip()
        if not self.controller.validate_api_key(key):
            QMessageBox.warning(self, "Clave inválida",
                                "La clave de API debe tener al menos 20 caracteres.")
            return
        try:
            self.controller.save_api_key(key)
        except Exception as e:
            QMessageBox.critical(self, "Error guardando clave", str(e))
            return
        QMessageBox.information(self, "Clave guardada",
                                "Clave de API almacenada correctamente.")
        self.btn_execute.setEnabled(True)

    def on_execute(self):
        code = self.txt_code.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Código vacío",
                                "Pega o escribe un fragmento de código.")
            return

        self.last_original = code
        self.btn_execute.setEnabled(False)
        self.lbl_spinner.setText("Enviando…")
        QApplication.processEvents()

        try:
            prompt = self.controller.build_prompt(code)
            raw = self.controller.send_to_openai(prompt)
            clean = self.controller.extract_code(raw)
            self.last_corrected = clean

            # Mostrar código limpio
            self.page_code.setPlainText(clean)
            self.stack.setCurrentIndex(0)
            self.btn_copy.setEnabled(True)
            self.btn_diff.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error IA", str(e))
        finally:
            self.lbl_spinner.setText("")
            self.btn_execute.setEnabled(True)

    def on_copy(self):
        if not self.last_corrected:
            return
        QApplication.clipboard().setText(self.last_corrected)
        QMessageBox.information(self, "Copiado",
                                "Código corregido copiado al portapapeles.")

    def on_show_diff(self):
        # Toggle entre código y diff
        if self.stack.currentIndex() == 0:
            diff = self.controller.generar_diff(
                self.last_original, self.last_corrected
            )
            self.page_diff.clear()
            for line in diff:
                item = QListWidgetItem(line.rstrip("\n"))
                if line.startswith("+") and not line.startswith("+++"):
                    item.setBackground(COLOR_ADD)
                    item.setForeground(QColor("black"))
                elif line.startswith("-") and not line.startswith("---"):
                    item.setBackground(COLOR_REM)
                    item.setForeground(QColor("black"))
                elif line.startswith("@@"):
                    item.setBackground(COLOR_CTX)
                    item.setForeground(QColor("black"))
                elif line.startswith("---") or line.startswith("+++"):
                    item.setBackground(COLOR_HDR)
                    item.setForeground(QColor("black"))
                self.page_diff.addItem(item)

            self.stack.setCurrentIndex(1)
            self.btn_diff.setText("Mostrar código")
        else:
            self.stack.setCurrentIndex(0)
            self.btn_diff.setText("Mostrar diff")
