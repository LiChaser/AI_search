from PyQt5 import QtWidgets, QtCore, QtGui
from core.github_scanner import GitHubScanner
from ui.styles import *  # 导入样式
import os
from PyQt5.QtCore import Qt

class GitHubSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub项目搜索")
        self.setMinimumSize(600, 400)  # 设置最小尺寸
        self.setup_ui()
        self.github_scanner = GitHubScanner()
        self.repos = []

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 搜索区域
        search_frame = QtWidgets.QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #0a0a0a;
                border: 2px solid #008000;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        search_layout = QtWidgets.QHBoxLayout(search_frame)
        
        # 搜索图标
        search_icon = QtWidgets.QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-size: 20px;
                padding: 5px;
            }
        """)
        search_layout.addWidget(search_icon)
        
        # 搜索输入框
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索GitHub项目...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #001a00;
                color: #00ff00;
                border: 2px solid #008000;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                min-height: 30px;
            }
            QLineEdit:focus {
                border-color: #00ff00;
                background-color: #002200;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        
        # 搜索按钮
        search_btn = QtWidgets.QPushButton("搜索")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #004400;
                color: #00ff00;
                border: 2px solid #008000;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 14px;
                min-width: 80px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #006600;
                border-color: #00ff00;
            }
            QPushButton:pressed {
                background-color: #008800;
            }
        """)
        search_btn.clicked.connect(self.search_repos)
        search_layout.addWidget(search_btn)
        
        layout.addWidget(search_frame)

        # 过滤选项
        filter_frame = QtWidgets.QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #0a0a0a;
                border: 1px solid #008000;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        filter_layout = QtWidgets.QVBoxLayout(filter_frame)  # 改为垂直布局
        
        # 第一行过滤选项
        filter_row1 = QtWidgets.QHBoxLayout()
        
        # 语言过滤
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems([
            "全部", 
            "Python", 
            "Java", 
            "JavaScript",
            "Vue",  # 添加Vue
            "C++", 
            "PHP"
        ])
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #001a00;
                color: #00ff00;
                border: 1px solid #008000;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(resources/icons/down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #001a00;
                color: #00ff00;
                selection-background-color: #004400;
                selection-color: #00ff00;
                border: 1px solid #008000;
            }
        """)
        filter_row1.addWidget(QtWidgets.QLabel("语言:"))
        filter_row1.addWidget(self.lang_combo)
        
        # 排序选项
        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItems([
            "Star数递增"  # 只保留一个排序选项
        ])
        self.sort_combo.setStyleSheet(self.lang_combo.styleSheet())
        filter_row1.addWidget(QtWidgets.QLabel("排序:"))
        filter_row1.addWidget(self.sort_combo)
        
        filter_row1.addStretch()
        filter_layout.addLayout(filter_row1)
        
        # 第二行过滤选项
        filter_row2 = QtWidgets.QHBoxLayout()
        
        # 最小Star数
        filter_row2.addWidget(QtWidgets.QLabel("最小Star数:"))
        self.min_stars = QtWidgets.QSpinBox()
        self.min_stars.setRange(0, 1000000)
        self.min_stars.setValue(100)  # 默认值
        self.min_stars.setStyleSheet("""
            QSpinBox {
                background-color: #001a00;
                color: #00ff00;
                border: 1px solid #008000;
                border-radius: 4px;
                padding: 5px;
                min-width: 80px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #002200;
                border: 1px solid #008000;
                border-radius: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #003300;
            }
        """)
        filter_row2.addWidget(self.min_stars)
        
        # 最长未更新时间（天）
        filter_row2.addWidget(QtWidgets.QLabel("最长未更新天数:"))
        self.max_days = QtWidgets.QSpinBox()
        self.max_days.setRange(0, 3650)  # 0-10年
        self.max_days.setValue(365)  # 默认一年
        self.max_days.setStyleSheet(self.min_stars.styleSheet())
        filter_row2.addWidget(self.max_days)
        
        filter_row2.addStretch()
        filter_layout.addLayout(filter_row2)
        
        layout.addWidget(filter_frame)

        # 搜索结果列表
        self.result_list = QtWidgets.QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                background-color: #0a0a0a;
                border: 2px solid #008000;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                color: #00ff00;
                padding: 10px;
                border-bottom: 1px solid #004400;
            }
            QListWidget::item:hover {
                background-color: #001a00;
            }
            QListWidget::item:selected {
                background-color: #002200;
                border: none;
            }
        """)
        self.result_list.setSelectionMode(QtWidgets.QListWidget.MultiSelection)
        layout.addWidget(self.result_list)

        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.select_btn = QtWidgets.QPushButton("确定")
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #004400;
                color: #00ff00;
                border: 2px solid #008000;
                border-radius: 5px;
                padding: 8px 30px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #006600;
                border-color: #00ff00;
            }
            QPushButton:pressed {
                background-color: #008800;
            }
        """)
        self.select_btn.clicked.connect(self.accept)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setStyleSheet(self.select_btn.styleSheet())
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def on_search_changed(self, text):
        """搜索框文本变化时的处理"""
        # 可以添加实时搜索功能
        pass

    def search_repos(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QtWidgets.QMessageBox.warning(self, "警告", "请输入搜索关键词！")
            return
            
        # 显示加载提示
        self.result_list.clear()
        self.result_list.addItem("正在搜索...")
        QtWidgets.QApplication.processEvents()
        
        # 获取搜索参数
        language = None if self.lang_combo.currentText() == "全部" else self.lang_combo.currentText()
        min_stars = self.min_stars.value()
        max_days_since_update = self.max_days.value()
        
        try:
            # 构建基础查询
            if language == "Vue":
                query = f"{keyword} topic:vue-component stars:>={min_stars}"
            else:
                query = f"{keyword} stars:>={min_stars}"
                if language != "全部":
                    query += f" language:{language}"
            
            if max_days_since_update > 0:
                from datetime import datetime, timedelta
                date_limit = (datetime.now() - timedelta(days=max_days_since_update)).strftime("%Y-%m-%d")
                query += f" pushed:>{date_limit}"
            
            # 显示实际的搜索查询
            self.result_list.clear()
            self.result_list.addItem(f"执行搜索查询: {query}")
            self.result_list.addItem("─" * 50)
            QtWidgets.QApplication.processEvents()
            
            # 执行搜索
            try:
                self.repos = self.github_scanner.search_repos(
                    query, sort="stars", order="asc"
                )
            except Exception as api_error:
                self.result_list.addItem(f"API错误: {str(api_error)}")
                self.result_list.addItem("请检查GitHub API配置和网络连接")
                return
            
            if not self.repos:
                self.result_list.addItem("API返回为空，可能原因：")
                self.result_list.addItem("1. 搜索条件过于严格")
                self.result_list.addItem("2. API访问限制")
                self.result_list.addItem("3. 网络连接问题")
                return
            
            # 过滤并排序结果
            filtered_repos = [
                repo for repo in self.repos 
                if repo['stargazers_count'] >= min_stars
            ]
            
            # 显示结果
            self.result_list.clear()
            if not filtered_repos:
                self.result_list.addItem(f"未找到符合条件的仓库")
                self.result_list.addItem(f"搜索条件:")
                self.result_list.addItem(f"- 关键词: {keyword}")
                self.result_list.addItem(f"- 最小Star数: {min_stars}")
                if language != "全部":
                    self.result_list.addItem(f"- 语言: {language}")
                if max_days_since_update > 0:
                    self.result_list.addItem(f"- 最近更新: {max_days_since_update}天内")
                return
            
            # 按star数升序排序
            filtered_repos.sort(key=lambda x: x['stargazers_count'])
            
            for repo in filtered_repos:
                star_count = repo['stargazers_count']
                if star_count >= 1000:
                    star_display = f"{star_count/1000:.1f}k"
                else:
                    star_display = str(star_count)
                
                from datetime import datetime
                last_update = datetime.strptime(repo['updated_at'][:10], "%Y-%m-%d")
                days_ago = (datetime.now() - last_update).days
                
                # 使用HTML格式来显示，而不是制表符
                item_text = (f"{repo['full_name']} "  # 仓库名称
                            f"<span style='color: #888888;'>"
                            f"⭐{star_display} • "  # star数
                            f"{days_ago}天前更新"    # 更新时间
                            f"</span>")
                item = QtWidgets.QListWidgetItem(item_text)
                self.result_list.addItem(item)
            
            # 显示搜索统计
            self.result_list.insertItem(0, f"找到 {len(filtered_repos)} 个仓库")
            self.result_list.insertItem(1, "─" * 50)
                
        except Exception as e:
            self.result_list.clear()
            self.result_list.addItem(f"搜索过程出错:")
            self.result_list.addItem(f"- 错误信息: {str(e)}")
            self.result_list.addItem(f"- 查询语句: {query}")
            self.result_list.addItem("\n请检查:")
            self.result_list.addItem("1. 网络连接")
            self.result_list.addItem("2. GitHub API配置")
            self.result_list.addItem("3. 搜索参数是否合理")

    def get_selected_repos(self):
        """获取选中的仓库"""
        selected = []
        for i in range(self.result_list.count()):
            if self.result_list.item(i).isSelected():
                # 从显示文本中提取仓库名称
                full_text = self.result_list.item(i).text()
                # 提取仓库全名（在第一个空格之前的部分）
                repo_name = full_text.split(' ')[0].strip()
                # 跳过统计信息和分隔线
                if repo_name.startswith('找到 ') or repo_name.startswith('─') or repo_name.startswith('执行'):
                    continue
                selected.append(repo_name)
        return selected 