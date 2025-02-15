from PyQt5 import QtWidgets, QtGui, QtCore
from ui.components import CyberTextEdit
from core.github_scanner import GitHubScanner
from core.workers import HackerWorker, WebshellWorker
from ui.styles import *
from config.settings import OLLAMA_API_URL, OLLAMA_MODEL
import tempfile
import shutil
import os
import re
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from ui.github_dialog import GitHubSearchDialog
import queue
from git import Repo
from PyQt5.QtWidgets import QMessageBox
import time
from urllib.parse import urlparse, urljoin

class OllamaWorker(QThread):
    output_received = pyqtSignal(str)
    thinking_started = pyqtSignal()
    thinking_finished = pyqtSignal()
    
    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
        self.running = True
        self.history = []  # 对话历史
        self.message_queue = queue.Queue()  # 消息队列
        self._is_processing = False  # 添加处理状态标志
        
    def run(self):
        """初始化测试"""
        try:
            # 发送初始测试请求
            self._send_request("你好，请用中文回复。")
            
            # 启动消息处理循环
            while self.running:
                try:
                    # 非阻塞方式获取消息
                    message = self.message_queue.get_nowait()
                    if message:
                        self._send_request(message)
                except queue.Empty:
                    # 队列为空时休眠
                    QtCore.QThread.msleep(100)
                    
        except Exception as e:
            print(f"Error in worker: {e}")
            self.output_received.emit(f"❌ 连接失败: {str(e)}")
            
    def _send_request(self, message):
        """发送请求到 Ollama API"""
        if self._is_processing:
            return
            
        try:
            self._is_processing = True
            self.thinking_started.emit()
            
            # 构建带历史的提示
            if self.history:
                context = "\n".join(self.history[-3:])
                full_prompt = f"{context}\n{message}"
            else:
                full_prompt = message
                
            response = requests.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=70
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
                if ai_response:
                    # 保存到历史
                    self.history.append(f"Human: {message}")
                    self.history.append(f"Assistant: {ai_response}")
                    # 保持历史在合理范围
                    if len(self.history) > 6:
                        self.history = self.history[-6:]
                    self.output_received.emit(ai_response)
                else:
                    self.output_received.emit("❌ 未收到有效回复")
            else:
                self.output_received.emit(f"❌ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending request: {e}")
            self.output_received.emit(f"❌ 发送失败: {str(e)}")
        finally:
            self._is_processing = False
            self.thinking_finished.emit()
            
    def send_message(self, message):
        """将消息加入队列"""
        if not self._is_processing:
            self.message_queue.put(message)
            
    def stop(self):
        """停止工作线程"""
        self.running = False
        # 清空消息队列
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        # 等待当前处理完成
        if self._is_processing:
            QtCore.QThread.msleep(100)

class LoadingIndicator(QtWidgets.QLabel):
    """动态加载指示器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dots = 0
        self.max_dots = 3
        self.base_text = "🤔 AI思考中"
        self.wait_time = 0  # 等待时间（秒）
        self.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-size: 12pt;
                padding: 5px;
            }
        """)
        
        # 创建动画定时器
        self.dot_timer = QtCore.QTimer(self)
        self.dot_timer.timeout.connect(self.update_dots)
        self.dot_timer.setInterval(500)  # 每500ms更新一次点
        
        # 创建时间定时器
        self.time_timer = QtCore.QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.setInterval(1000)  # 每秒更新一次
        
    def start(self):
        """开始动画"""
        self.dots = 0
        self.wait_time = 0
        self.update_display()
        self.dot_timer.start()
        self.time_timer.start()
        self.show()
        
    def stop(self):
        """停止动画"""
        self.dot_timer.stop()
        self.time_timer.stop()
        self.hide()
        
    def update_dots(self):
        """更新点的数量"""
        self.dots = (self.dots + 1) % (self.max_dots + 1)
        self.update_display()
        
    def update_time(self):
        """更新等待时间"""
        self.wait_time += 1
        self.update_display()
        
    def update_display(self):
        """更新显示内容"""
        dots = '.' * self.dots
        time_str = f"({self.wait_time}s)" if self.wait_time > 0 else ""
        self.setText(f"{self.base_text}{dots} {time_str}")

class GitHubDownloader(QThread):
    """GitHub项目下载线程"""
    progress_update = pyqtSignal(str, str, float)
    download_complete = pyqtSignal(str, str, bool)
    
    def __init__(self, repo_name, repo_url, target_dir):
        super().__init__()
        self.repo_name = repo_name
        self.repo_url = repo_url
        self.target_dir = target_dir
        
    def run(self):
        try:
            # 清理目标目录
            if os.path.exists(self.target_dir):
                try:
                    # 修改文件权限
                    import stat
                    def remove_readonly(func, path, _):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    
                    # 使用 shutil.rmtree 的 onerror 参数处理只读文件
                    shutil.rmtree(self.target_dir, onerror=remove_readonly)
                except Exception as e:
                    print(f"Error cleaning directory: {e}")
                    # 如果清理失败，使用系统命令强制删除
                    import subprocess
                    subprocess.run(['rd', '/s', '/q', self.target_dir], shell=True)
            
            # 发出开始下载信号
            self.progress_update.emit(
                self.repo_name,
                "开始下载...",
                0
            )
            
            # 执行git clone
            import subprocess
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', self.repo_url, self.target_dir],
                capture_output=True,
                text=True
            )
            
            # 检查克隆结果
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            # 发出完成信号
            self.download_complete.emit(self.repo_name, self.target_dir, True)
            
        except Exception as e:
            print(f"Error downloading {self.repo_name}: {e}")
            # 清理失败的下载
            if os.path.exists(self.target_dir):
                try:
                    shutil.rmtree(self.target_dir, onerror=lambda func, path, _: os.chmod(path, stat.S_IWRITE))
                except:
                    subprocess.run(['rd', '/s', '/q', self.target_dir], shell=True)
            self.download_complete.emit(self.repo_name, "", False)

class ProjectWatcher(QThread):
    """项目目录监控线程"""
    projects_changed = pyqtSignal()  # 项目变化信号
    
    def __init__(self, projects_dir):
        super().__init__()
        self.projects_dir = projects_dir
        self.running = True
        self.last_projects = set()
        
    def run(self):
        while self.running:
            try:
                # 获取当前项目列表
                current_projects = set(
                    name for name in os.listdir(self.projects_dir)
                    if os.path.isdir(os.path.join(self.projects_dir, name))
                )
                
                # 检查是否有变化
                if current_projects != self.last_projects:
                    self.last_projects = current_projects
                    self.projects_changed.emit()
                    
                # 休眠1秒
                QtCore.QThread.sleep(1)
                
            except Exception as e:
                print(f"Error watching projects: {e}")
                QtCore.QThread.sleep(5)  # 出错时等待更长时间
                
    def stop(self):
        self.running = False

class JSFinder:
    """JS接口提取器"""
    def __init__(self):
        # URL正则模式 - 优化匹配规则
        self.url_pattern = re.compile(
            r'''(?:https?:)?//(?:[\w\-_]+[.])+[\w\-_]+(?:/[\w\-.,@?^=%&:/~+#]*[\w\-@?^=%&/~+#])?''',
            re.VERBOSE
        )
        # API端点正则模式 - 优化匹配规则
        self.api_pattern = re.compile(
            r'''(?:["'])((?:/[a-zA-Z0-9\-._~!$&'()*+,;=:@%]+)+)(?:["'])''',
            re.VERBOSE
        )
        
    def clean_url(self, url):
        """清理URL"""
        # 去除无效的URL
        if url.endswith(('"}', '"', "'", '"}}')):
            url = url.rstrip('"}\'}}')
        # 去除JavaScript代码片段
        if '.js' in url and ('"+' in url or '",' in url):
            return None
        # 去除明显的代码模板
        if '${' in url or '{' in url or '}' in url:
            return None
        return url
        
    def clean_api(self, api):
        """清理API端点"""
        # 去除无效的API端点
        if api.endswith(('"}', '"', "'", '"}}')):
            api = api.rstrip('"}\'}}')
        # 去除文件扩展名结尾的路径
        if api.endswith(('.js', '.css', '.html', '.png', '.jpg', '.gif')):
            return None
        # 去除明显的代码模板
        if '${' in api or '{' in api or '}' in api:
            return None
        # 去除过短的路径
        if len(api.split('/')) < 2:
            return None
        return api
        
    def extract_from_js(self, content, base_url=None):
        """从JS内容中提取URL和API端点"""
        results = {
            'urls': set(),
            'apis': set()
        }
        
        # 提取完整URL
        urls = self.url_pattern.findall(content)
        for url in urls:
            cleaned_url = self.clean_url(url)
            if cleaned_url:
                if not cleaned_url.startswith('http'):
                    cleaned_url = 'http:' + cleaned_url
                results['urls'].add(cleaned_url)
        
        # 提取API端点
        apis = self.api_pattern.findall(content)
        for api in apis:
            cleaned_api = self.clean_api(api)
            if cleaned_api:
                if base_url and not cleaned_api.startswith('http'):
                    cleaned_api = urljoin(base_url, cleaned_api)
                results['apis'].add(cleaned_api)
            
        return results

class CyberScanner(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI安全审计系统 - AI_Search Pro")
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        
        # 初始化属性
        self.ollama_worker = None
        self.chat_input = None
        self.chat_input_widget = None
        
        # 添加项目管理相关属性
        self.projects_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'projects')
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir)
        self.project_list = []
        
        # 启动项目监控
        self.project_watcher = ProjectWatcher(self.projects_dir)
        self.project_watcher.projects_changed.connect(self.refresh_project_list)
        self.project_watcher.start()
        
        # 设置UI
        self.setup_ui()
        self.init_scanner()

    def init_scanner(self):
        self.files_content = {}
        self.scan_thread = None
        self.github_scanner = GitHubScanner()
        self.temp_dir = None

    def setup_ui(self):
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        layout = QtWidgets.QHBoxLayout(main_widget)

        # 左侧面板
        left_panel = QtWidgets.QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #0a0a0a;
                border: 2px solid #800000;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Logo或标题
        logo_label = QtWidgets.QLabel("🔒 AI_Search Pro")
        logo_label.setStyleSheet("""
            QLabel {
                color: #ff0000;
                font-size: 24pt;
                font-weight: bold;
                padding: 20px;
            }
        """)
        left_layout.addWidget(logo_label)

        # 模式选择
        mode_group = QtWidgets.QGroupBox("🔧 审计模式")
        mode_group.setStyleSheet(GROUP_BOX_STYLE)
        mode_layout = QtWidgets.QVBoxLayout()
        
        # 本地审计按钮
        self.btn_local_scan = QtWidgets.QPushButton("📁 本地项目审计")
        self.btn_local_scan.setStyleSheet(BUTTON_STYLE)
        self.btn_local_scan.clicked.connect(self.start_local_scan)
        mode_layout.addWidget(self.btn_local_scan)
        
        # GitHub项目审计按钮
        self.btn_github_scan = QtWidgets.QPushButton("🌐 GitHub项目审计")
        self.btn_github_scan.setStyleSheet(BUTTON_STYLE)
        self.btn_github_scan.clicked.connect(self.start_github_scan)
        mode_layout.addWidget(self.btn_github_scan)
        
        # 新增：JS接口提取按钮
        self.btn_js_extract = QtWidgets.QPushButton("🔍 JS接口提取")
        self.btn_js_extract.setStyleSheet(BUTTON_STYLE)
        self.btn_js_extract.clicked.connect(self.start_js_extract)
        mode_layout.addWidget(self.btn_js_extract)
        
        # 模式选择组之后，添加测试连接按钮
        self.btn_test_ollama = QtWidgets.QPushButton("🔌 测试 Ollama 连接")
        self.btn_test_ollama.setStyleSheet("""
            QPushButton {
                background-color: #002b2b;
                color: #ff0000;
                border: 2px solid #800000;
                padding: 10px;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #004d4d;
                border-color: #ff0000;
            }
        """)
        self.btn_test_ollama.clicked.connect(self.test_ollama_connection)
        mode_layout.addWidget(self.btn_test_ollama)
        
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)

        # 审计配置
        config_group = QtWidgets.QGroupBox("⚙️ 审计配置")
        config_group.setStyleSheet(GROUP_BOX_STYLE)
        config_layout = QtWidgets.QVBoxLayout()
        
        # 修改项目列表组
        projects_group = QtWidgets.QGroupBox("📁 任务项目")
        projects_group.setStyleSheet("""
            QGroupBox {
                color: #00ff00;
                border: 2px solid #008000;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                font-weight: bold;
                background-color: #0a0a0a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: #0a0a0a;
                font-size: 13pt;
            }
        """)
        
        # 使用 QVBoxLayout 并设置伸缩因子
        projects_layout = QtWidgets.QVBoxLayout()
        projects_layout.setSpacing(10)
        projects_layout.setContentsMargins(5, 15, 5, 5)
        
        # 添加滚动区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0a0a0a;
                margin: 0px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #0a0a0a;
            }
            QScrollBar:vertical {
                background-color: #0a0a0a;
                width: 8px;
                border: 1px solid #00ff00;
            }
            QScrollBar::handle:vertical {
                background-color: #008000;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00ff00;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 项目列表容器
        self.projects_widget = QtWidgets.QWidget()
        self.projects_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self.projects_widget.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
            }
            QCheckBox {
                color: #00ff00;
                font-size: 12pt;
                padding: 10px 15px;
                border: 1.5px solid #008000;
                border-radius: 6px;
                margin: 3px;
                background-color: #0a0a0a;
            }
            QCheckBox:hover {
                background-color: #001a00;
                border-color: #00ff00;
            }
            QCheckBox:checked {
                background-color: #002200;
                border-color: #00ff00;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #008000;
                border-radius: 4px;
                background-color: #0a0a0a;
                margin-right: 10px;
            }
            QCheckBox::indicator:hover {
                border-color: #00ff00;
                background-color: #001a00;
            }
            QCheckBox::indicator:checked {
                background-color: #008000;
                image: url(resources/icons/check.png);
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00aa00;
            }
        """)
        
        self.projects_layout = QtWidgets.QVBoxLayout(self.projects_widget)
        self.projects_layout.setSpacing(5)
        self.projects_layout.setContentsMargins(2, 2, 2, 2)
        self.projects_layout.addStretch()
        
        scroll_area.setWidget(self.projects_widget)
        projects_layout.addWidget(scroll_area, 1)  # 添加伸缩因子
        
        # 添加扫描按钮
        scan_btn = QtWidgets.QPushButton("🔍 开始扫描")
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a0000;
                color: #ff0000;
                border: 2px solid #800000;
                border-radius: 8px;
                padding: 12px;
                font-size: 13pt;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #330000;
                border-color: #ff0000;
                color: #ff3333;
            }
            QPushButton:pressed {
                background-color: #400000;
                padding: 14px 10px 10px 14px;
            }
        """)
        scan_btn.clicked.connect(self.scan_selected_projects)
        projects_layout.addWidget(scan_btn)
        
        projects_group.setLayout(projects_layout)
        config_layout.addWidget(projects_group, 1)  # 添加伸缩因子
        
        # 设置配置组布局
        config_group.setLayout(config_layout)
        
        # 添加到左侧面板
        left_layout.addWidget(config_group)
        
        # 添加状态组
        status_group = QtWidgets.QGroupBox("📊 审计状态")
        status_group.setStyleSheet(GROUP_BOX_STYLE)
        status_layout = QtWidgets.QVBoxLayout()

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #800000;
                border-radius: 5px;
                text-align: center;
                background-color: #1a0000;
                color: #ff0000;
            }
            QProgressBar::chunk {
                background-color: #ff0000;
            }
        """)
        status_layout.addWidget(self.progress_bar)

        # 当前状态标签
        self.status_label = QtWidgets.QLabel("等待开始审计...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ff0000;
                font-size: 11pt;
                padding: 5px;
            }
        """)
        status_layout.addWidget(self.status_label)

        # 统计信息
        self.stats_label = QtWidgets.QLabel("""
        已扫描文件: 0
        发现高危漏洞: 0
        发现中危漏洞: 0
        """)
        self.stats_label.setStyleSheet(LABEL_STYLE)
        status_layout.addWidget(self.stats_label)

        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)

        # 右侧显示区
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QHBoxLayout(right_panel)  # 改为水平布局
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 右侧的结果显示区域
        result_panel = QtWidgets.QWidget()
        result_layout = QtWidgets.QVBoxLayout(result_panel)
        result_layout.setSpacing(0)
        result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_display = QtWidgets.QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 2px solid #008000;
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12pt;
                line-height: 1.5;
            }
        """)
        
        # 添加欢迎信息
        welcome_message = """
🎉 欢迎使用 AI_Search Pro 安全审计系统！

📌 主要功能:
  • 本地项目审计 - 分析本地代码项目的安全问题
  • GitHub项目审计 - 自动下载并分析GitHub仓库
  • JS接口提取 - 从JavaScript文件中提取URL和API端点

🔧 使用方法:
1. 选择左侧的审计模式
2. 根据提示选择项目或输入搜索条件
3. 等待分析完成，查看审计结果

✨ 支持的文件类型:
  • JavaScript/Vue/React
  • HTML/CSS
  • Python/Java/PHP
  • C/C++
  • 配置文件

💡 开始使用:
  • 点击左侧按钮选择审计模式
  • 在右侧可以查看支持的文件类型
  • 审计结果将在此区域显示

祝您使用愉快！🚀
"""
        self.result_display.setText(welcome_message)
        
        result_layout.addWidget(self.result_display, stretch=1)

        # 聊天输入区域（默认隐藏）
        self.chat_input_widget = QtWidgets.QWidget()
        self.chat_input_widget.setVisible(False)  # 默认隐藏
        self.chat_input_widget.setStyleSheet("""
            QWidget {
                background-color: #001a1a;
                border-top: 2px solid #00ffff;
            }
        """)
        chat_input_layout = QtWidgets.QHBoxLayout(self.chat_input_widget)
        chat_input_layout.setContentsMargins(10, 10, 10, 10)
        chat_input_layout.setSpacing(10)

        # 聊天输入框
        self.chat_input = QtWidgets.QLineEdit()
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #002b2b;
                color: #00ff00;
                border: 2px solid #00ffff;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
                min-height: 40px;
            }
        """)
        self.chat_input.setPlaceholderText("在此输入消息...")
        self.chat_input.returnPressed.connect(self.send_message)

        # 发送按钮
        send_btn = QtWidgets.QPushButton("发送")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #002b2b;
                color: #00ff00;
                border: 2px solid #00ffff;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 80px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #004d4d;
            }
        """)
        send_btn.clicked.connect(self.send_message)

        # 替换原来的 thinking_label
        self.loading_indicator = LoadingIndicator()
        chat_input_layout.addWidget(self.loading_indicator)
        self.loading_indicator.hide()

        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(send_btn)
        result_layout.addWidget(self.chat_input_widget)

        # 新增：右侧的文件类型选择面板
        file_type_panel = QtWidgets.QFrame()
        file_type_panel.setStyleSheet("""
            QFrame {
                background-color: #0a0a0a;
                border: 2px solid #ff0000;
                border-radius: 5px;
                margin: 0px;
            }
            QWidget {
                background-color: #0a0a0a;
            }
        """)
        file_type_layout = QtWidgets.QVBoxLayout(file_type_panel)

        # 修改标题样式
        title_label = QtWidgets.QLabel("支持的文件类型")
        title_label.setStyleSheet("""
            QLabel {
                color: #ff0000;
                font-size: 16pt;
                font-weight: bold;
                padding: 10px;
                background-color: #0a0a0a;
            }
        """)
        file_type_layout.addWidget(title_label)

        # 修改文件类型组样式
        default_group = QtWidgets.QGroupBox("默认文件类型")
        default_group.setStyleSheet("""
            QGroupBox {
                color: #ff0000;
                border: 2px solid #800000;
                border-radius: 5px;
                margin: 0px;
                padding: 5px;
                background-color: #0a0a0a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 5px;
                background-color: #0a0a0a;
            }
        """)
        default_layout = QtWidgets.QVBoxLayout(default_group)

        # 创建滚动区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0a0a0a;
                margin: 0px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #0a0a0a;
            }
            QScrollBar:vertical {
                background-color: #0a0a0a;
                width: 8px;
                border: 1px solid #ff0000;
            }
            QScrollBar::handle:vertical {
                background-color: #800000;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #ff0000;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # 创建滚动区域的内容容器
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距

        # 添加文件类型选项
        self.file_type_vars = {}
        default_types = {
            "JavaScript": [".js", ".jsx", ".vue", ".ts", ".tsx"],
            "HTML": [".html", ".htm", ".shtml"],
            "Python": [".py", ".pyw"],
            "Java": [".java"],
            "CSS": [".css"],
            "PHP": [".php"],
            "C/C++": [".c", ".cpp", ".h", ".hpp"],
            "SQL": [".sql"],
            "XML": [".xml"],
            "配置文件": [".conf", ".config", ".ini"]
        }

        for ft_name, extensions in default_types.items():
            checkbox = QtWidgets.QCheckBox(f"{ft_name}")
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ff0000;
                    font-size: 12pt;
                    padding: 8px;
                    border-radius: 4px;
                    background-color: #0a0a0a;
                }
                QCheckBox:hover {
                    background-color: #1a0000;
                    border: 1px solid #ff0000;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #ff0000;
                    border-radius: 3px;
                    background-color: #0a0a0a;
                }
                QCheckBox::indicator:checked {
                    background-color: #ff0000;
                    image: url(resources/icons/check.png);
                }
                QCheckBox::indicator:checked:hover {
                    background-color: #cc0000;
                }
                QCheckBox::indicator:hover {
                    border-color: #ff0000;
                    background-color: #1a0000;
                }
            """)
            checkbox.setToolTip(f"支持的扩展名: {', '.join(extensions)}")
            self.file_type_vars[ft_name] = {
                'checkbox': checkbox,
                'extensions': extensions
            }
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)  # 修复：设置正确的内容widget
        default_layout.addWidget(scroll_area)
        file_type_layout.addWidget(default_group)

        # 将面板添加到右侧布局
        right_layout.addWidget(result_panel, stretch=2)  # 结果显示区占2/3
        right_layout.addWidget(file_type_panel, stretch=1)  # 文件类型选择区占1/3

        # 布局设置
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 2)

        # 状态栏
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(STATUS_BAR_STYLE)
        self.status_bar.showMessage("⚡ 系统就绪")

    def create_file_type_selection(self):
        """创建文件类型选择框"""
        file_type_group = QtWidgets.QGroupBox("选择审计文件类型")
        layout = QtWidgets.QVBoxLayout()

        self.file_type_vars = {}
        file_types = {
            "Python": [".py", ".pyw"],
            "Java": [".java"],
            "JavaScript": [".js", ".jsx"],
            "HTML": [".html", ".htm"],
            "CSS": [".css"],
            "PHP": [".php"],
            "C/C++": [".c", ".cpp", ".h", ".hpp"],
            "SQL": [".sql"],
            "XML": [".xml"],
            "配置文件": [".conf", ".config", ".ini"]
        }

        for ft_name, extensions in file_types.items():
            checkbox = QtWidgets.QCheckBox(f"{ft_name} ({', '.join(extensions)})")
            checkbox.stateChanged.connect(self.update_selected_types)
            self.file_type_vars[ft_name] = {
                'checkbox': checkbox,
                'extensions': extensions
            }
            layout.addWidget(checkbox)

        file_type_group.setLayout(layout)
        
        # 将文件类型选择组添加到主布局中
        # 假设主布局是vertical_layout
        self.vertical_layout.addWidget(file_type_group)

    def update_selected_types(self):
        """更新选中的文件类型列表"""
        self.selected_file_types = []
        for data in self.file_type_vars.values():
            if data['checkbox'].isChecked():
                self.selected_file_types.extend(data['extensions'])

    def start_audit(self):
        """开始审计"""
        if not hasattr(self, 'selected_file_types') or not self.selected_file_types:
            QMessageBox.warning(self, "警告", "请至少选择一种文件类型")
            return

        # 获取项目路径
        project_path = self.get_project_path()  # 假设有这个方法
        if not project_path:
            return

        # 使用选中的文件类型进行扫描
        files_to_scan = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.selected_file_types):
                    files_to_scan.append(os.path.join(root, file))

        # 继续执行现有的审计逻辑
        # ... existing audit code ...

    def scan_code_files(self, directory):
        """扫描代码文件"""
        code_files = {}
        
        # 获取选中的文件类型
        selected_types = []
        for ft_name, data in self.file_type_vars.items():
            if data['checkbox'].isChecked():
                selected_types.extend(data['extensions'])
        
        if not selected_types:
            QtWidgets.QMessageBox.warning(self, "警告", "请至少选择一种文件类型！")
            return code_files

        # 首先统计文件总数
        total_files = 0
        matched_files = 0
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in selected_types):
                    matched_files += 1
                total_files += 1

        self.result_display.append(f"""
📊 文件统计:
- 总文件数: {total_files}
- 匹配文件数: {matched_files}
""")

        # 扫描匹配的文件
        current_file = 0
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in selected_types):
                    current_file += 1
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            code_files[path] = content
                            
                            # 显示进度
                            progress = (current_file / matched_files) * 100
                            self.result_display.append(f"\r🔍 正在审计: [{current_file}/{matched_files}] {progress:.1f}% - {file}")
                            
                            # 处理界面事件
                            QtWidgets.QApplication.processEvents()
                            time.sleep(0.05)  # 稍微减慢显示速度
                            
                    except Exception as e:
                        self.result_display.append(f"❌ 无法读取: {path} ({str(e)})")

        return code_files

    def update_status(self, message):
        """更新状态信息"""
        self.status_bar.showMessage(message)
        self.status_label.setText(message)
        self.result_display.append(f"⚡ {message}")
        
        # 更新进度条
        if "分析中" in message:
            current_file = len(self.files_content)
            self.progress_bar.setValue(int((current_file / max(len(self.files_content), 1)) * 100))
        
        # 更新统计信息
        high_risk = len([line for line in self.result_display.toPlainText().split('\n') if '[高危]' in line])
        medium_risk = len([line for line in self.result_display.toPlainText().split('\n') if '[中危]' in line])
        
        self.stats_label.setText(f"""
        已扫描文件: {len(self.files_content)}
        发现高危漏洞: {high_risk}
        发现中危漏洞: {medium_risk}
        """)

    def show_results(self, report):
        """显示扫描结果"""
        self.result_display.append("\n 代码审计完成！发现以下安全漏洞：\n")
        report = re.sub(r'\[高危\]', '[高危]', report)
        report = re.sub(r'\[中危\]', '[中危]', report)
        
        self.result_display.append(report)
        self.status_bar.showMessage("✅ 扫描完成")

    def start_local_scan(self):
        """开始本地项目审计"""
        # 退出 AI 交互模式
        self.exit_ai_mode()
        
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "选择项目目录",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly
        )
        if directory:
            self.status_bar.showMessage("✅ 开始审计本地项目")
            self.result_display.append(f"📂 正在审计目录: {directory}")
            self.files_content = self.scan_code_files(directory)
            self.start_scan()

    def start_github_scan(self):
        """开始GitHub项目审计"""
        self.exit_ai_mode()
        
        dialog = GitHubSearchDialog(self)
        # 设置对话框样式
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                border: 2px solid #00ff00;
            }
            QLabel {
                color: #00ff00;
            }
            QLineEdit {
                background-color: #001a00;
                color: #00ff00;
                border: 1px solid #008000;
                padding: 5px;
            }
            QListWidget {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 1px solid #008000;
            }
            QListWidget::item:hover {
                background-color: #001a00;
            }
            QListWidget::item:selected {
                background-color: #002200;
            }
            QPushButton {
                background-color: #001a00;
                color: #00ff00;
                border: 1px solid #008000;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #002200;
                border-color: #00ff00;
            }
        """)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            repo_names = dialog.get_selected_repos()
            if repo_names:
                # 先清理已存在的项目
                for repo_name in repo_names:
                    dir_name = repo_name.split('/')[-1]
                    repo_dir = os.path.join(self.projects_dir, dir_name)
                    if os.path.exists(repo_dir):
                        try:
                            # 修改文件权限并删除
                            def remove_readonly(func, path, _):
                                import stat
                                os.chmod(path, stat.S_IWRITE)
                                func(path)
                            import shutil
                            shutil.rmtree(repo_dir, onerror=remove_readonly)
                        except Exception as e:
                            # 如果上面的方法失败，使用系统命令强制删除
                            try:
                                import subprocess
                                if os.name == 'nt':  # Windows
                                    subprocess.run(['rd', '/s', '/q', repo_dir], shell=True, check=True)
                                else:  # Linux/Mac
                                    subprocess.run(['rm', '-rf', repo_dir], shell=True, check=True)
                            except Exception as e2:
                                self.result_display.append(f"❌ 无法删除目录 {repo_dir}: {str(e2)}")
                                continue

                self.result_display.clear()
                self.result_display.append("🔍 开始批量拉取 GitHub 项目...\n")
                
                # 启动下载线程
                self.downloaders = []
                for repo_name in repo_names:
                    dir_name = repo_name.split('/')[-1]
                    repo_dir = os.path.join(self.projects_dir, dir_name)
                    
                    downloader = GitHubDownloader(
                        repo_name,
                        f"https://github.com/{repo_name}.git",
                        repo_dir
                    )
                    downloader.progress_update.connect(self.update_download_progress)
                    downloader.download_complete.connect(self.handle_download_complete)
                    self.downloaders.append(downloader)
                    downloader.start()

    def update_download_progress(self, repo_name, message, progress):
        """更新下载进度"""
        # 直接添加新的进度信息，而不是尝试修改现有行
        self.result_display.append(f"📦 {repo_name} - {message} ({progress:.1f}%)")
        QtWidgets.QApplication.processEvents()

    def handle_download_complete(self, repo_name, repo_dir, success):
        """处理下载完成事件"""
        if success:
            try:
                # 添加到项目列表
                project_name = repo_name.split('/')[-1]
                # self.add_project_to_list(project_name, repo_dir)
                # 更新显示
                self.result_display.append(f"✅ 项目 {repo_name} 下载完成！\n")
            except Exception as e:
                self.result_display.append(f"❌ 添加项目到列表失败: {str(e)}\n")
        else:
            self.result_display.append(f"❌ 项目 {repo_name} 下载失败！")
            self.result_display.append("尝试重新下载...\n")
            try:
                # 使用系统命令克隆
                import subprocess
                # 只使用仓库名作为目录名
                dir_name = repo_name.split('/')[-1]
                repo_dir = os.path.join(self.projects_dir, dir_name)
                
                # 确保目标目录不存在
                if os.path.exists(repo_dir):
                    import shutil
                    shutil.rmtree(repo_dir)
                
                # 执行克隆命令
                subprocess.run(
                    f'git clone --depth 1 https://github.com/{repo_name}.git "{repo_dir}"',
                    shell=True,
                    check=True
                )
                self.add_project_to_list(dir_name, repo_dir)
                self.result_display.append(f"✅ 项目 {repo_name} 重试下载成功！\n")
            except Exception as e:
                self.result_display.append(f"❌ 重试下载也失败了: {str(e)}\n")

    def add_project_to_list(self, project_name, project_path):
        """添加项目到列表"""
        checkbox = QtWidgets.QCheckBox(project_name)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #00ff00;
                font-size: 12pt;
                padding: 10px 15px;
                border: 1.5px solid #004400;
                border-radius: 6px;
                margin: 3px;
                background-color: rgba(0, 20, 0, 0.2);
            }
            QCheckBox:hover {
                background-color: rgba(0, 40, 0, 0.3);
                border-color: #008800;
            }
            QCheckBox:checked {
                background-color: rgba(0, 60, 0, 0.4);
                border-color: #00ff00;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #008000;
                border-radius: 4px;
                background-color: rgba(0, 0, 0, 0.5);
                margin-right: 10px;
            }
            QCheckBox::indicator:hover {
                border-color: #00aa00;
                background-color: rgba(0, 40, 0, 0.3);
            }
            QCheckBox::indicator:checked {
                background-color: #008000;
                image: url(resources/icons/check.png);
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00aa00;
            }
        """)
        checkbox.setToolTip(project_path)
        
        # 添加到布局，确保在 stretch 之前
        self.projects_layout.insertWidget(self.projects_layout.count() - 1, checkbox)
        self.project_list.append({
            'name': project_name,
            'path': project_path,
            'checkbox': checkbox
        })

    def start_scan(self, auto_mode=False):
        """开始扫描"""
        if not self.files_content:
            QtWidgets.QMessageBox.warning(self, "警告", "没有可审计的文件！")
            return

        # 重置进度条
        self.progress_bar.setValue(0)
        
        # 默认使用代码审计模式
        worker = HackerWorker(self.files_content)
        init_msg = "🚀 启动深度代码分析协议..."
        
        self.scan_thread = worker
        self.scan_thread.progress_update.connect(self.update_status)
        self.scan_thread.analysis_complete.connect(self.show_results)
        self.scan_thread.start()
        
        self.result_display.setText(f"{init_msg}\n" + "▮"*50 + "\n")

    def test_ollama_connection(self):
        """启动 Ollama 交互对话"""
        # 如果已经有worker在运行，先停止它
        if self.ollama_worker is not None:
            try:
                self.ollama_worker.stop()
                self.ollama_worker.wait()
            except:
                pass
            self.ollama_worker = None
        
        self.result_display.clear()
        self.result_display.append(f"""
🔌 Ollama AI 助手
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 基本信息：
   当前模型: {OLLAMA_MODEL}

2️⃣ 正在启动对话模式...
""")
        
        try:
            # 显示聊天输入区域
            self.chat_input_widget.setVisible(True)
            
            # 启动 Ollama worker
            self.start_ollama_process()
            
            # 禁用测试按钮，改为显示状态
            self.btn_test_ollama.setEnabled(False)
            self.btn_test_ollama.setText("💬 AI 助手已启动")
            
            # 显示就绪信息
            self.result_display.append("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ AI 助手已就绪！

💡 使用说明：
1. 在下方输入框中输入您的问题
2. 按回车键或点击发送按钮
3. 等待 AI 回复

现在开始对话吧！
""")
            
            # 聚焦到输入框
            self.chat_input.setFocus()
            
        except Exception as e:
            self.result_display.append(f"❌ 错误: {str(e)}")
            # 恢复按钮状态
            self.btn_test_ollama.setEnabled(True)
            self.btn_test_ollama.setText("🔌 测试 Ollama 连接")

    def start_ollama_process(self):
        """启动 Ollama 进程"""
        try:
            # 创建并启动 worker
            self.ollama_worker = OllamaWorker(OLLAMA_MODEL)
            self.ollama_worker.output_received.connect(self.handle_ollama_output)
            self.ollama_worker.thinking_started.connect(self.on_thinking_started)
            self.ollama_worker.thinking_finished.connect(self.on_thinking_finished)
            self.ollama_worker.start()
            
        except Exception as e:
            self.result_display.append(f"❌ 启动失败: {str(e)}")

    def handle_ollama_output(self, text):
        """处理 Ollama 输出"""
        if text.strip():
            if text.startswith("❌"):  # 错误消息
                self.result_display.append(text)
                # 恢复按钮状态
                self.btn_test_ollama.setEnabled(True)
                self.btn_test_ollama.setText("🔌 测试 Ollama 连接")
            else:
                # 移除之前的"正在思考"提示
                current_text = self.result_display.toPlainText()
                if current_text.endswith("💭 AI正在思考...\n\n"):
                    new_text = current_text[:-len("💭 AI正在思考...\n\n")]
                    self.result_display.setText(new_text)
                
                # 显示AI回复
                self.result_display.append(f"🤖 AI: {text}")
                
                # 添加分隔线
                self.result_display.append("─" * 50 + "\n")
        
            # 滚动到底部
            self.result_display.verticalScrollBar().setValue(
                self.result_display.verticalScrollBar().maximum()
            )

    def send_message(self):
        """发送消息到 Ollama"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # 清空输入框
        self.chat_input.clear()
        
        # 显示用户消息
        self.result_display.append(f"\n You: {message}\n")
        
        try:
            # 发送消息
            self.ollama_worker.send_message(message)
        except Exception as e:
            self.result_display.append(f"❌ 错误: {str(e)}\n")
        
        # 滚动到底部
        self.result_display.verticalScrollBar().setValue(
            self.result_display.verticalScrollBar().maximum()
        )

    def exit_ai_mode(self):
        """退出 AI 交互模式"""
        if self.ollama_worker is not None:
            try:
                # 停止 worker
                self.ollama_worker.stop()
                self.ollama_worker.wait()
                self.ollama_worker = None
                
                # 隐藏聊天界面
                self.chat_input_widget.setVisible(False)
                
                # 恢复按钮状态
                self.btn_test_ollama.setEnabled(True)
                self.btn_test_ollama.setText("🔌 测试 Ollama 连接")
                
                # 清理加载动画
                if hasattr(self, 'loading_indicator'):
                    self.loading_indicator.stop()
                
                # 添加提示信息
                self.result_display.append("\n💡 已退出 AI 交互模式\n")
                
            except Exception as e:
                print(f"Error exiting AI mode: {e}")

    def closeEvent(self, event):
        """关闭窗口时清理"""
        self.exit_ai_mode()
        if hasattr(self, 'project_watcher'):
            self.project_watcher.stop()
            self.project_watcher.wait()
        event.accept()

    def on_thinking_started(self):
        """AI开始思考时的处理"""
        self.loading_indicator.start()
        self.chat_input.setEnabled(False)
        self.chat_input.setPlaceholderText("AI正在思考...")
        # 添加思考中的提示到结果显示区
        self.result_display.append("\n AI正在思考...\n")

    def on_thinking_finished(self):
        """AI结束思考时的处理"""
        self.loading_indicator.stop()
        self.chat_input.setEnabled(True)
        self.chat_input.setPlaceholderText("在此输入消息...")
        self.chat_input.setFocus()

    def import_project(self):
        """导入本地项目"""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly
        )
        
        if directory:
            project_name = os.path.basename(directory)
            target_dir = os.path.join(self.projects_dir, project_name)
            
            try:
                # 如果目标目录已存在，先删除
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                
                # 复制项目到指定目录
                shutil.copytree(directory, target_dir)
                
                # 添加到项目列表
                self.add_project_to_list(project_name, target_dir)
                
                self.result_display.append(f"✅ 项目 {project_name} 导入成功！\n")
                
            except Exception as e:
                self.result_display.append(f"❌ 项目导入失败: {str(e)}\n")

    def scan_selected_projects(self):
        """扫描选中的项目"""
        selected_projects = [
            project for project in self.project_list 
            if project['checkbox'].isChecked()
        ]
        
        if not selected_projects:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "请选择要扫描的项目！"
            )
            return
        
        # 检查是否选择了文件类型
        selected_types = []
        for ft_name, data in self.file_type_vars.items():
            if data['checkbox'].isChecked():
                selected_types.extend(data['extensions'])
        
        if not selected_types:
            QtWidgets.QMessageBox.warning(
                self,
                "警告",
                "请至少选择一种文件类型！"
            )
            return
        
        # 清空之前的结果
        self.result_display.clear()
        self.files_content = {}
        
        # 显示开始扫描信息
        self.result_display.append("🚀 开始项目扫描")
        self.result_display.append(f"📁 选中项目: {', '.join(p['name'] for p in selected_projects)}")
        self.result_display.append(f"🔍 文件类型: {', '.join(selected_types)}\n")
        
        # 扫描选中的项目
        for project in selected_projects:
            self.result_display.append(f"\n📂 扫描项目: {project['name']}")
            try:
                # 扫描项目文件
                project_files = self.scan_code_files(project['path'])
                self.files_content.update(project_files)
                
            except Exception as e:
                self.result_display.append(f"❌ 扫描失败: {str(e)}\n")
        
        if self.files_content:
            # 开始扫描
            self.start_scan()
        else:
            self.result_display.append("❌ 未找到匹配的代码文件！")

    def refresh_project_list(self):
        """刷新项目列表"""
        # 清理旧的项目列表
        for project in self.project_list:
            project['checkbox'].deleteLater()
        self.project_list.clear()
        
        # 获取并显示当前项目
        try:
            for name in sorted(os.listdir(self.projects_dir)):
                path = os.path.join(self.projects_dir, name)
                if os.path.isdir(path):
                    self.add_project_to_list(name, path)
        except Exception as e:
            print(f"Error refreshing project list: {e}")

    def add_custom_file_type(self):
        """添加自定义文件类型"""
        type_name = self.custom_type_input.text().strip()
        extension = self.custom_ext_input.text().strip()
        
        if not type_name or not extension:
            QtWidgets.QMessageBox.warning(self, "警告", "请输入类型名称和扩展名！")
            return
        
        if not extension.startswith('.'):
            extension = '.' + extension
        
        # 添加新的文件类型
        checkbox = QtWidgets.QCheckBox(f"{type_name}")
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #ff0000;
                font-size: 12pt;
                padding: 5px;
            }
        """)
        checkbox.setToolTip(f"支持的扩展名: {extension}")
        self.file_type_vars[type_name] = {
            'checkbox': checkbox,
            'extensions': [extension]
        }
        
        # 清空输入框
        self.custom_type_input.clear()
        self.custom_ext_input.clear()
        
        # 刷新界面
        self.update_file_type_list()

    def update_file_type_list(self):
        """刷新文件类型列表"""
        # 清理旧的文件类型列表
        for checkbox in self.file_type_vars.values():
            checkbox['checkbox'].deleteLater()
        self.file_type_vars.clear()
        
        # 获取并显示当前文件类型
        for type_name, data in self.file_type_vars.items():
            checkbox = QtWidgets.QCheckBox(f"{type_name}")
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ff0000;
                    font-size: 12pt;
                    padding: 5px;
                }
            """)
            checkbox.setToolTip(f"支持的扩展名: {', '.join(data['extensions'])}")
            self.file_type_vars[type_name] = {
                'checkbox': checkbox,
                'extensions': data['extensions']
            }
            
            # 添加到布局，确保在 stretch 之前
            self.file_type_layout.insertWidget(self.file_type_layout.count() - 1, checkbox)

    def start_js_extract(self):
        """开始JS接口提取"""
        # 退出 AI 交互模式
        self.exit_ai_mode()
        
        # 确保只选中JS相关文件类型
        for ft_name, data in self.file_type_vars.items():
            if ft_name in ["JavaScript", "HTML"]:
                data['checkbox'].setChecked(True)
            else:
                data['checkbox'].setChecked(False)
        
        # 清空之前的结果
        self.result_display.clear()
        self.result_display.append("🔍 开始JS接口提取分析...\n")
        
        # 获取选中的项目
        selected_projects = [
            project for project in self.project_list 
            if project['checkbox'].isChecked()
        ]
        
        if not selected_projects:
            # 如果没有选中的项目，打开目录选择对话框
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self, 
                "选择要分析的目录",
                "",
                QtWidgets.QFileDialog.ShowDirsOnly
            )
            if directory:
                self.result_display.append(f"📂 分析目录: {directory}")
                self.scan_js_files(directory)
        else:
            # 分析选中的项目
            for project in selected_projects:
                self.result_display.append(f"\n📂 分析项目: {project['name']}")
                self.scan_js_files(project['path'])

    def scan_js_files(self, directory):
        """专门用于JS文件扫描和接口提取"""
        js_finder = JSFinder()
        js_results = {
            'urls': set(),
            'apis': set(),
            'files_scanned': 0,
            'errors': []
        }
        
        self.result_display.append("🔍 开始扫描JS文件...\n")
        
        # 首先统计文件总数
        total_files = 0
        for root, _, files in os.walk(directory):
            total_files += len([f for f in files if f.endswith(('.js', '.jsx', '.vue', '.ts', '.tsx', '.html', '.htm'))])
        
        self.result_display.append(f"找到 {total_files} 个待分析文件\n")
        
        # 扫描JS和HTML文件
        current_file = 0
        for root, _, files in os.walk(directory):
            js_files = [f for f in files if f.endswith(('.js', '.jsx', '.vue', '.ts', '.tsx', '.html', '.htm'))]
            
            for file in js_files:
                current_file += 1
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        js_results['files_scanned'] += 1
                        
                        # 显示进度
                        progress = (current_file / total_files) * 100
                        self.result_display.append(f"\r📍 正在分析: [{current_file}/{total_files}] {progress:.1f}% - {file}")
                        QtWidgets.QApplication.processEvents()
                        
                        # 提取URL和API
                        results = js_finder.extract_from_js(content)
                        js_results['urls'].update(results['urls'])
                        js_results['apis'].update(results['apis'])
                        
                except Exception as e:
                    js_results['errors'].append((path, str(e)))
        
        # 显示汇总结果
        self.result_display.append(f"""
\n📊 扫描统计:
- 扫描文件数: {js_results['files_scanned']}
- 发现URL数: {len(js_results['urls'])}
- 发现API数: {len(js_results['apis'])}
""")
        
        # 显示发现的URL和API
        if js_results['urls']:
            self.result_display.append("\n📡 发现的URL:")
            for url in sorted(js_results['urls']):
                if url.strip() and not url.endswith(('.js', '.css', '.jpg', '.png', '.gif')):
                    self.result_display.append(f"  • {url}")
            
        if js_results['apis']:
            self.result_display.append("\n🔌 发现的API端点:")
            for api in sorted(js_results['apis']):
                if api.strip():
                    self.result_display.append(f"  • {api}")
        
        # 如果有错误，在最后显示错误信息
        if js_results['errors']:
            self.result_display.append("\n❌ 扫描错误:")
            for path, error in js_results['errors']:
                self.result_display.append(f"  • {os.path.basename(path)}: {error}")
        
        self.result_display.append("\n✅ JS接口提取完成！")

    # 其他方法... 