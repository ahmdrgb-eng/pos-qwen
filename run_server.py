# run_server.py
from waitress import serve
from app import app

if __name__ == '__main__':
    print("🚀 تشغيل النظام على جميع الشبكات...")
    serve(app, host='192.168.159.117', port=5000)