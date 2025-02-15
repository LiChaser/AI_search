# API配置
# API_TYPE = "deepseek"  # 可选值: "deepseek" 或 "ollama"
#
# # DeepSeek API配置
# DEEPSEEK_API_URL = ""  # API地址
# DEEPSEEK_API_KEY = ""  # API密钥
# DEEPSEEK_MODEL = ""    # 模型名称

# Ollama API配置
OLLAMA_API_URL = "http://localhost:11434"  # Ollama API基础地址
OLLAMA_MODEL = "codegeex4:latest"  # Ollama模型名称

# GitHub配置
GITHUB_TOKEN = "*****"  # 可选，不设置则使用未认证模式

# 支持的文件类型
SUPPORTED_EXTENSIONS = ['.php', '.jsp', '.asp', '.js', '.html', '.py', '.java']

# UI主题配置
THEMES = {
    "深色主题": {
        "main_bg": "#1e1e1e",
        "secondary_bg": "#2d2d2d",
        "text_color": "#ffffff",
        "accent_color": "#007acc",
        "border_color": "#404040",
        "button_hover": "#005999",
        "button_pressed": "#004c80"
    },
    "浅色主题": {
        "main_bg": "#f5f5f5",
        "secondary_bg": "#ffffff",
        "text_color": "#333333",
        "accent_color": "#2196f3",
        "border_color": "#e0e0e0",
        "button_hover": "#1976d2",
        "button_pressed": "#1565c0"
    }
} 