from PyQt5 import QtWidgets
from .styles import CYBER_TEXT_STYLE

class CyberTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CYBER_TEXT_STYLE)

# 其他UI组件... 