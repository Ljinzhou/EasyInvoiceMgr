import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'easy-invoice-mgr-secret-key'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'easy-invoice-mgr-jwt-secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:root@localhost:5432/easy_invoice_mgr')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = 3600

    # 文件存储后端: 'local' | 'cos'
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')

    # 腾讯云COS配置（仅 STORAGE_BACKEND=cos 时需要）
    COS_SECRET_ID = os.environ.get('COS_SECRET_ID')
    COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY')
    COS_REGION = os.environ.get('COS_REGION', 'ap-guangzhou')
    COS_BUCKET = os.environ.get('COS_BUCKET')

    # 智谱AI GLM视觉模型配置
    GLM_API_KEY = os.environ.get('GLM_API_KEY')
    GLM_MODEL = os.environ.get('GLM_MODEL', 'glm-4.6v-flash')
