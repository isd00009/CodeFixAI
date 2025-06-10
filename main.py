import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CodeFixAI – Versión Inicial")
        self.setGeometry(100, 100, 600, 400)
        lbl = QLabel("¡Ventana de prueba!", self)
        lbl.move(200, 180)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
