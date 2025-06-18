from datetime import datetime
from flask import Flask, jsonify, request, render_template
import re
from config import DB_CONFIG
from flask_mysqldb import MySQL
from flask_cors import CORS
from log_collector import start_log_collector
app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = DB_CONFIG['host']
app.config['MYSQL_USER'] = DB_CONFIG['user']
app.config['MYSQL_PASSWORD'] = DB_CONFIG['password']
app.config['MYSQL_DB'] = DB_CONFIG['db']
app.config['MYSQL_CHARSET'] = DB_CONFIG['charset']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

start_log_collector()
@app.route('/')
def logs_page():
    return render_template('logs.html')

@app.route('/api/logs')
def get_logs():
    level = request.args.get('level')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    keyword = request.args.get('keyword')

    query = "SELECT * FROM logs WHERE 1=1"  # 1=1 是一个技巧，方便后续添加 AND 条件
    params = []  # 用于存储查询参数，防止 SQL 注入
    if level:
        query += " AND level = %s"
        params.append(level)
    if start_time:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        query += " AND timestamp >= %s"
        params.append(start_time)
    if end_time:
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        query += " AND timestamp <= %s"
        params.append(end_time)
    if keyword:
        keyword = keyword.strip()
        if ' and ' in keyword.lower():
            # AND 逻辑
            terms = re.split(r'\s+and\s+', keyword, flags=re.IGNORECASE)
            for term in terms:
                query += " AND message LIKE %s"
                params.append(f"%{term.strip()}%")
        elif ' or ' in keyword.lower():
            # OR 逻辑（需要用括号包裹）
            terms = re.split(r'\s+or\s+', keyword, flags=re.IGNORECASE)
            query += " AND (" + " OR ".join(["message LIKE %s"] * len(terms)) + ")"
            params.extend([f"%{term.strip()}%" for term in terms])
        else:
            # 单个关键词默认 AND
            query += " AND message LIKE %s"
            params.append(f"%{keyword}%")

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(query, params)  # 执行查询，传入参数
        logs = cursor.fetchall()  # 获取所有查询结果
        cursor.close()
        return jsonify({'logs':logs})

    except Exception as e:
        return jsonify({'error':str(e)}),500



if __name__ == '__main__':
    app.run()
