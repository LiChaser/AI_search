import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'db': 'log_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}