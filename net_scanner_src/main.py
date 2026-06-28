import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui import NetScannerWindow

def find_icon():
    """Busca o ícone SVG em múltiplos locais de instalação."""
    import sys
    candidates = [
        # PyInstaller bundle
        os.path.join(getattr(sys, "_MEIPASS", ""), "net-scanner.svg"),
        # Instalação do sistema (makepkg / deb)
        "/usr/share/icons/hicolor/scalable/apps/net-scanner.svg",
        # Ícone local do usuário
        os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/net-scanner.svg"),
        # Pasta resources do projeto (desenvolvimento)
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "net-scanner.svg"),
        # Mesmo diretório do script
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "net-scanner.svg"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None

def main():
    app = QApplication(sys.argv)
    
    # Define o nome da aplicação para o sistema
    app.setApplicationName("NetScanner")
    app.setApplicationDisplayName("NetScanner - Monitor de Rede Local")
    
    # Define o ícone globalmente para a aplicação (barra de título + taskbar)
    icon_path = find_icon()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    window = NetScannerWindow()
    # Garante que a janela também use o mesmo ícone
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
