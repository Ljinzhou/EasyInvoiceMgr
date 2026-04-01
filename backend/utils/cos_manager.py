import os
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class COSManager:
    def __init__(self):
        self.secret_id = os.getenv('COS_SECRET_ID')
        self.secret_key = os.getenv('COS_SECRET_KEY')
        self.region = os.getenv('COS_REGION', 'ap-shanghai')
        self.bucket = os.getenv('COS_BUCKET')
        
        if not all([self.secret_id, self.secret_key, self.bucket]):
            logger.warning('腾讯云COS配置不完整，文件上传功能将不可用')
            self.client = None
            return
        
        try:
            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key
            )
            self.client = CosS3Client(config)
            logger.info(f'腾讯云COS初始化成功: bucket={self.bucket}, region={self.region}')
        except Exception as e:
            logger.error(f'腾讯云COS初始化失败: {str(e)}', exc_info=True)
            self.client = None
    
    def is_available(self):
        return self.client is not None
    
    def generate_file_key(self, event_id: int, original_filename: str) -> str:
        ext = os.path.splitext(original_filename)[1]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f'invoices/{event_id}/{timestamp}_{unique_id}{ext}'
    
    def upload_file(self, event_id: int, file_obj, filename: str) -> dict:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            file_key = self.generate_file_key(event_id, filename)
            
            logger.info(f'开始上传文件: {filename} -> {file_key}')
            
            self.client.put_object(
                Bucket=self.bucket,
                Body=file_obj.read(),
                Key=file_key,
                EnableMD5=False
            )
            
            file_url = f'https://{self.bucket}.cos.{self.region}.myqcloud.com/{file_key}'
            
            logger.info(f'文件上传成功: {file_key}')
            
            return {
                'file_key': file_key,
                'file_url': file_url
            }
            
        except Exception as e:
            logger.error(f'文件上传失败: {str(e)}', exc_info=True)
            raise Exception(f'文件上传失败: {str(e)}')
    
    def get_presigned_url(self, file_key: str, expires: int = 3600) -> str:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            url = self.client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket,
                Key=file_key,
                Expired=expires
            )
            
            logger.info(f'生成临时URL成功: {file_key}, 有效期: {expires}秒')
            return url
            
        except Exception as e:
            logger.error(f'生成临时URL失败: {str(e)}', exc_info=True)
            raise Exception(f'生成临时URL失败: {str(e)}')
    
    def delete_file(self, file_key: str) -> bool:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=file_key
            )
            
            logger.info(f'文件删除成功: {file_key}')
            return True
            
        except Exception as e:
            logger.error(f'文件删除失败: {str(e)}', exc_info=True)
            return False
    
    def check_file_exists(self, file_key: str) -> bool:
        if not self.is_available():
            return False
        
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=file_key
            )
            return True
        except:
            return False

cos_manager = COSManager()
