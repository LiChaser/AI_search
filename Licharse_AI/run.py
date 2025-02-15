import sys
from PyQt5 import QtWidgets
from ui.main_window import CyberScanner

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = CyberScanner()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 