import os
import time
import re
import threading
import mysql.connector
from config import DB_CONFIG

LOG_DIR = 'logs/'
LOG_FILE = 'audit_tool.log'
INTERVAL = 1
def get_db_connection():
    return mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['db']
    )

def parse_log_line(line):
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)] ([^-\n]*) - (.+)', line)
    if match:
        return match.groups()
    return None

def collect_logs_loop():
    processed_lines = set()
    while True:
        filepath = os.path.join(LOG_DIR, LOG_FILE)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            conn = get_db_connection()
            cursor = conn.cursor()

            for line in lines:
                if line in processed_lines:
                    continue
                parsed = parse_log_line(line)
                if parsed:
                    timestamp, level, source, message = parsed
                    sql = "INSERT INTO logs (timestamp, level, source, message) VALUES (%s, %s, %s, %s)"
                    try:
                        cursor.execute(sql, (timestamp, level, source.strip(), message.strip()))
                        processed_lines.add(line)
                    except Exception as e:
                        print(f"插入失败：{e}")

            conn.commit()
            cursor.close()
            conn.close()

        time.sleep(INTERVAL)

# 用于从 Flask 启动
def start_log_collector():
    thread = threading.Thread(target=collect_logs_loop, daemon=True)
    thread.start()
