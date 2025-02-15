import sys
from PyQt5 import QtWidgets, QtGui
from ui.main_window import CyberScanner
from config.settings import OLLAMA_API_URL

def main():
    OLLAMA_HOST = OLLAMA_API_URL.split('/api')[0]

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QtGui.QFont("Consolas", 10)
    app.setFont(font)
    
    window = CyberScanner()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 