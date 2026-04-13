import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///easy_invoice_mgr.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    
    # 腾讯云COS配置
    COS_SECRET_ID = os.environ.get('COS_SECRET_ID')
    COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY')
    COS_REGION = os.environ.get('COS_REGION', 'ap-guangzhou')
    COS_BUCKET = os.environ.get('COS_BUCKET')
