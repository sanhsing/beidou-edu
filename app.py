"""
北斗教育系統 - 主程式入口
XTF-DAO 模組化架構
"""
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from utils import init_db
from routes import register_blueprints

# 日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Config)
    
    # 初始化
    CORS(app)
    init_db(app)
    register_blueprints(app)
    
    # 錯誤處理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    logging.info("Starting Beidou Education System - XTF-DAO")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
