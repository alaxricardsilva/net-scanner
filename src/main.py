import sys
from PySide6.QtWidgets import QApplication
from ui import NetScannerWindow

def main():
    app = QApplication(sys.argv)
    
    # Define o nome da aplicação para o sistema
    app.setApplicationName("NetScanner")
    app.setApplicationDisplayName("NetScanner - Monitor de Rede Local")
    
    window = NetScannerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
