# 主题颜色定义
COLORS = {
    'bg_dark': '#1a0000',
    'bg_medium': '#330000',
    'bg_light': '#4d0000',
    'text_primary': '#ff0000',
    'text_secondary': '#ff3333',
    'accent': '#ff1a1a',
    'border': '#800000',
    'highlight': '#ff4d4d'
}

# 主窗口样式
MAIN_WINDOW_STYLE = f"""
    QMainWindow {{
        background-color: {COLORS['bg_dark']};
    }}
"""

# 文本编辑器样式
CYBER_TEXT_STYLE = f"""
    QTextEdit {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 5px;
        padding: 10px;
        font-family: 'Consolas';
        font-size: 12pt;
        selection-background-color: {COLORS['bg_light']};
        selection-color: {COLORS['text_secondary']};
    }}
    QScrollBar:vertical {{
        border: 1px solid {COLORS['border']};
        background: {COLORS['bg_dark']};
        width: 15px;
        margin: 15px 0 15px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['bg_light']};
        min-height: 20px;
    }}
"""

# 按钮样式
BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_medium']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        padding: 12px;
        font-size: 14pt;
        font-weight: bold;
        border-radius: 5px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_light']};
        border-color: {COLORS['accent']};
        color: {COLORS['text_secondary']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['accent']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['border']};
        border-color: {COLORS['bg_medium']};
    }}
"""

# 左侧面板样式
LEFT_PANEL_STYLE = f"""
    QFrame {{
        background-color: {COLORS['bg_medium']};
        border-right: 2px solid {COLORS['border']};
        border-radius: 5px;
    }}
"""

# 文件树样式
FILE_TREE_STYLE = f"""
    QTreeView {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        font-family: 'Consolas';
        font-size: 11pt;
    }}
    QTreeView::item {{
        padding: 5px;
    }}
    QTreeView::item:hover {{
        background-color: {COLORS['bg_medium']};
    }}
    QTreeView::item:selected {{
        background-color: {COLORS['bg_light']};
        color: {COLORS['text_secondary']};
    }}
"""

# 分组框样式
GROUP_BOX_STYLE = f"""
    QGroupBox {{
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 5px;
        margin-top: 10px;
        font-size: 12pt;
        padding: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }}
"""

# 单选按钮样式
RADIO_BUTTON_STYLE = f"""
    QRadioButton {{
        color: {COLORS['text_primary']};
        padding: 8px;
        font-size: 11pt;
    }}
    QRadioButton::indicator {{
        width: 15px;
        height: 15px;
    }}
    QRadioButton::indicator:unchecked {{
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        background-color: {COLORS['bg_dark']};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {COLORS['accent']};
        border-radius: 8px;
        background-color: {COLORS['accent']};
    }}
"""

# 复选框样式
CHECKBOX_STYLE = f"""
    QCheckBox {{
        color: {COLORS['text_primary']};
        padding: 8px;
        font-size: 11pt;
    }}
    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
    }}
    QCheckBox::indicator:unchecked {{
        border: 2px solid {COLORS['border']};
        background-color: {COLORS['bg_dark']};
    }}
    QCheckBox::indicator:checked {{
        border: 2px solid {COLORS['accent']};
        background-color: {COLORS['accent']};
    }}
"""

# 状态栏样式
STATUS_BAR_STYLE = f"""
    QStatusBar {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text_primary']};
        border-top: 1px solid {COLORS['border']};
    }}
    QStatusBar::item {{
        border: none;
    }}
"""

# 标签样式
LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: 11pt;
        padding: 5px;
    }}
"""

# 数字输入框样式
SPIN_BOX_STYLE = f"""
    QSpinBox {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        padding: 5px;
        font-size: 11pt;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {COLORS['bg_medium']};
        border: 1px solid {COLORS['border']};
        width: 20px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {COLORS['bg_light']};
    }}
"""

# 其他样式定义... 