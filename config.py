"""配置文件"""
import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    JWT_EXPIRATION_HOURS = 24
    DB_PATH = os.environ.get('DB_PATH', 'education.db')
