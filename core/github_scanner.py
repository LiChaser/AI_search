import requests
import os
from git import Repo
from config.settings import GITHUB_TOKEN
import shutil

class GitHubScanner:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
        self.api_base = "https://api.github.com"

    def search_repos(self, query, sort="stars", order="desc"):
        """搜索GitHub仓库"""
        try:
            # 添加调试信息
            print(f"Searching GitHub with query: {query}")
            
            # 构建API URL
            api_url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": 100  # 获取更多结果
            }
            
            # 发送请求
            response = requests.get(api_url, params=params)
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"GitHub API error: {response.status_code}")
                print(f"Response: {response.text}")
                raise Exception(f"GitHub API返回错误: {response.status_code}")
                
            data = response.json()
            
            # 检查返回数据
            if "items" not in data:
                print(f"Unexpected API response: {data}")
                raise Exception("API返回数据格式错误")
                
            return data["items"]
            
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            print(f"Error in search_repos: {e}")
            raise

    def _format_date(self, date_str):
        """格式化日期显示"""
        from datetime import datetime
        try:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return date.strftime("%Y-%m-%d")
        except:
            return date_str

    def clone_repo(self, repo_url, target_dir):
        """克隆仓库"""
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # 直接使用git clone命令
            import subprocess
            subprocess.run(['git', 'clone', repo_url, target_dir], 
                          check=True,
                          capture_output=True)
            return True
        except Exception as e:
            print(f"Error cloning repo: {e}")
            return False

    def search_vulnerable_repos(self, min_stars=100):
        """搜索可能包含漏洞的仓库"""
        query = f"stars:>={min_stars} language:python language:php language:java"
        repos = self.g.search_repositories(query)
        return [repo for repo in repos if self._has_website(repo)]
    
    def _has_website(self, repo):
        """检查仓库是否有官网"""
        try:
            return bool(repo.homepage) or bool(getattr(repo, 'html_url', None))
        except:
            return False
    
    def get_repo_info(self, repo):
        """获取仓库信息"""
        return {
            'name': repo.full_name,
            'url': repo.html_url,
            'website': repo.homepage or repo.html_url,
            'stars': repo.stargazers_count,
            'description': repo.description
        } 