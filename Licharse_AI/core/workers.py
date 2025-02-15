from PyQt5.QtCore import QThread, pyqtSignal
import requests
import json
import re
import os
import sys

# 导入配置
from config import OLLAMA_API_URL, OLLAMA_MODEL  # 直接从config.py导入

class HackerWorker(QThread):
    analysis_complete = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, files_content):
        super().__init__()
        self.files_content = files_content

    def run(self):
        full_report = []
        for filepath, content in self.files_content.items():
            self.progress_update.emit(f"🔍 分析中 {os.path.basename(filepath)}...")
            
            try:
                # 检查文件内容是否为空或无法读取
                if not content or content == "无法读取文件内容":
                    full_report.append(f"⚠️ 警告：文件 {filepath} 内容为空或无法读取")
                    continue

                # 发送请求到 Ollama
                OLLAMA_HOST = OLLAMA_API_URL.split('/api')[0]  # 获取基础URL
                api_url = f"{OLLAMA_HOST}/api/generate"
                
                response = requests.post(
                    api_url,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": self._generate_prompt(content),
                        "stream": False
                    },
                    timeout=300
                )

                # 检查响应状态
                response.raise_for_status()

                try:
                    result = response.json()
                    if "response" in result:
                        analysis_result = result["response"]
                        # 清理结果中的思考过程
                        analysis_result = re.sub(r'<think>.*?</think>', '', analysis_result, flags=re.DOTALL)
                        
                        # 只有当发现漏洞时才添加到报告
                        if '[高危]' in analysis_result or '[中危]' in analysis_result:
                            full_report.append(f"📄 文件：{filepath}\n{analysis_result}\n{'━'*50}")
                    else:
                        full_report.append(f"⚠️ 警告：文件 {filepath} 分析结果格式异常")
                except json.JSONDecodeError:
                    full_report.append(f"⚠️ 警告：文件 {filepath} 响应解析失败")

            except requests.RequestException as e:
                full_report.append(f"❌ 错误：处理文件 {filepath} 时网络请求失败\n{str(e)}")
            except Exception as e:
                full_report.append(f"❌ 错误：处理文件 {filepath} 时发生未知错误\n{str(e)}")

        # 如果没有发现任何漏洞
        if not any('[高危]' in report or '[中危]' in report for report in full_report):
            full_report.append("✅ 未发现高危或中危漏洞")

        self.analysis_complete.emit("\n".join(full_report))

    def _generate_prompt(self, content):
        """生成审计提示"""
        return f"""【强制指令】你是一个专业的安全审计AI，请按以下要求分析代码：
        
1. 漏洞分析流程：
   1.1 识别潜在风险点（SQL操作、文件操作、用户输入点、文件上传漏洞、CSRF、SSRF、XSS、RCE、OWASP top10等漏洞）
   1.2 验证漏洞可利用性
   1.3 按CVSS评分标准评估风险等级

2. 输出规则：
   - 仅输出确认存在的高危/中危漏洞
   - 使用严格格式：[风险等级] 类型 - 位置:行号 - 50字内描述
   - 禁止解释漏洞原理
   - 禁止给出修复建议
   - 如果有可能，给出POC（HTTP请求数据包）

3. 输出示例（除此外不要有任何输出）：
   [高危] SQL注入 - user_login.php:32 - 未过滤的$_GET参数直接拼接SQL查询
   [POC]POST /login.php HTTP/1.1
   Host: example.com
   Content-Type: application/x-www-form-urlencoded

4. 当前代码（仅限分析）：
{content[:3000]}"""

class WebshellWorker(QThread):
    detection_complete = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, files_content):
        super().__init__()
        self.files_content = files_content

    def run(self):
        detection_results = []
        for filepath, content in self.files_content.items():
            self.progress_update.emit(f"🕵️ 扫描 {os.path.basename(filepath)}...")
            
            try:
                # 检查文件内容
                if not content or content == "无法读取文件内容":
                    detection_results.append(f"⚠️ 警告：文件 {filepath} 内容为空或无法读取")
                    continue

                # 发送请求到 Ollama
                api_url = f"{OLLAMA_API_URL}/api/generate"  # 确保URL正确
                
                response = requests.post(
                    api_url,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": self._generate_prompt(content),
                        "stream": False
                    },
                    timeout=30
                )

                response.raise_for_status()
                result = response.json()
                
                if "response" in result:
                    detection_result = result["response"]
                    detection_result = re.sub(r'<think>.*?</think>', '', detection_result, flags=re.DOTALL)
                    
                    # 只有检测到 Webshell 时才添加到报告
                    if '🔴 [高危] Webshell' in detection_result:
                        detection_results.append(f"📁 {filepath}\n{detection_result}\n{'━'*50}")

            except (requests.RequestException, json.JSONDecodeError) as e:
                detection_results.append(f"❌ 错误：{filepath}\n{str(e)}")

        if not detection_results:
            detection_results.append("✅ 未发现 Webshell")

        self.detection_complete.emit("\n".join(detection_results))

    def _generate_prompt(self, content):
        """生成 Webshell 检测提示"""
        return f"""【Webshell检测指令】请严格按以下步骤分析代码：

1. 检测要求：         
    请分析以下文件内容是否为WebShell或内存马。要求：
    1. 检查PHP/JSP/ASP等WebShell特征（如加密函数、执行系统命令、文件操作）
    2. 识别内存马特征（如无文件落地、进程注入、异常网络连接）
    3. 分析代码中的可疑功能（如命令执行、文件上传、信息收集）
    4. 检查混淆编码、加密手段等规避技术

2. 判断规则：
   - 仅当确认恶意性时报告
   - 输出格式：🔴 [高危] Webshell - 文件名:行号 - 检测到[特征1+特征2+...]

3. 输出示例（严格按照此格式输出，不要有任何的补充，如果未检测到危险，则不输出）：
   🔴 [高危] Webshell - malicious.php:8 - 检测到[system执行+base64解码+错误抑制]

4. 待分析代码：
{content[:3000]}""" 