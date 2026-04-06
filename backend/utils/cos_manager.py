import os
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from datetime import datetime
import uuid
import logging

try:
    import requests as requests_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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
    
    def upload_bytes(self, file_bytes: bytes, cos_path: str) -> str:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            logger.info(f'开始上传文件: {cos_path}')
            
            self.client.put_object(
                Bucket=self.bucket,
                Body=file_bytes,
                Key=cos_path,
                EnableMD5=False
            )
            
            signed_url = self.client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket,
                Key=cos_path,
                Expired=3600 * 24 * 7  # 7天有效期
            )
            
            logger.info(f'文件上传成功: {cos_path}')
            
            return signed_url
            
        except Exception as e:
            logger.error(f'文件上传失败: {str(e)}', exc_info=True)
            raise Exception(f'文件上传失败: {str(e)}')
    
    def get_preview_url(self, file_key: str) -> str:
        if not self.is_available():
            return f'https://{self.bucket}.cos.{self.region}.myqcloud.com/{file_key}'
        
        try:
            return self.client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket,
                Key=file_key,
                Expired=3600 * 24 * 7
            )
        except:
            return f'https://{self.bucket}.cos.{self.region}.myqcloud.com/{file_key}'
    
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
    
    def download_file(self, file_key: str) -> bytes:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            presigned_url = self.get_presigned_url(file_key, expires=3600)
            
            if REQUESTS_AVAILABLE:
                response = requests_lib.get(presigned_url, timeout=60)
                response.raise_for_status()
                content = response.content
            else:
                import urllib.request
                with urllib.request.urlopen(presigned_url, timeout=60) as resp:
                    content = resp.read()
            
            logger.info(f'文件下载成功: {file_key}, 大小: {len(content)} bytes')
            return content
            
        except Exception as e:
            logger.error(f'文件下载失败: {str(e)}', exc_info=True)
            raise Exception(f'文件下载失败: {str(e)}')
    
    def upload_file_from_bytes(self, event_id: int, file_bytes, filename: str, content_type: str = 'application/octet-stream') -> dict:
        if not self.is_available():
            raise Exception('COS服务不可用')
        
        try:
            file_key = self.generate_file_key(event_id, filename)
            
            logger.info(f'开始上传字节流文件: {filename} -> {file_key}')
            
            self.client.put_object(
                Bucket=self.bucket,
                Body=file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes,
                Key=file_key,
                ContentType=content_type,
                EnableMD5=False
            )
            
            file_url = f'https://{self.bucket}.cos.{self.region}.myqcloud.com/{file_key}'
            
            logger.info(f'字节流文件上传成功: {file_key}')
            
            return {
                'file_key': file_key,
                'file_url': file_url
            }
            
        except Exception as e:
            logger.error(f'字节流文件上传失败: {str(e)}', exc_info=True)
            raise Exception(f'字节流文件上传失败: {str(e)}')

cos_manager = COSManager()
