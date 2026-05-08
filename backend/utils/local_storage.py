import os
import uuid
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalStorageManager:
    """Local filesystem storage backend with the same interface as COSManager."""

    def __init__(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.uploads_dir = os.path.join(base, 'uploads')
        os.makedirs(self.uploads_dir, exist_ok=True)
        logger.info(f'本地存储初始化完成: {self.uploads_dir}')

    def is_available(self):
        return True

    def _resolve_path(self, file_key):
        """Resolve a file key to an absolute local path."""
        # Normalize: strip leading /uploads/ if present
        key = file_key.lstrip('/')
        if key.startswith('uploads/'):
            key = key[8:]
        return os.path.join(self.uploads_dir, key)

    def _ensure_dir(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def generate_file_key(self, event_id, original_filename):
        ext = os.path.splitext(original_filename)[1]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f'invoices/{event_id}/{timestamp}_{unique_id}{ext}'

    def generate_avatar_key(self, user_id, ext):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f'avatars/{user_id}/{timestamp}_{unique_id}{ext}'

    def upload_file(self, event_id, file_obj, filename):
        file_key = self.generate_file_key(event_id, filename)
        local_path = self._resolve_path(file_key)
        self._ensure_dir(local_path)

        file_obj.seek(0)
        with open(local_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)

        logger.info(f'本地文件保存成功: {file_key}')
        return {'file_key': file_key, 'file_url': f'/uploads/{file_key}'}

    def upload_file_from_bytes(self, event_id, file_bytes, filename, content_type='application/octet-stream'):
        file_key = self.generate_file_key(event_id, filename)
        local_path = self._resolve_path(file_key)
        self._ensure_dir(local_path)

        data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes
        with open(local_path, 'wb') as f:
            f.write(data)

        logger.info(f'本地字节文件保存成功: {file_key}')
        return {'file_key': file_key, 'file_url': f'/uploads/{file_key}'}

    def upload_bytes(self, file_bytes, cos_path):
        """Upload bytes directly to a given path (used by parse.py)."""
        local_path = self._resolve_path(cos_path)
        self._ensure_dir(local_path)

        with open(local_path, 'wb') as f:
            f.write(file_bytes)

        logger.info(f'本地字节保存成功: {cos_path}')
        return f'/uploads/{cos_path}'

    def upload_avatar(self, user_id, file_bytes, content_type='image/jpeg'):
        ext_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp'
        }
        ext = ext_map.get(content_type, '.jpg')
        file_key = self.generate_avatar_key(user_id, ext)
        local_path = self._resolve_path(file_key)
        self._ensure_dir(local_path)

        with open(local_path, 'wb') as f:
            f.write(file_bytes)

        logger.info(f'头像保存成功: {file_key}')
        return {'file_key': file_key, 'avatar_url': f'/uploads/{file_key}'}

    def download_file(self, file_key):
        local_path = self._resolve_path(file_key)
        if not os.path.exists(local_path):
            logger.warning(f'本地文件不存在: {local_path}')
            raise Exception(f'文件不存在: {file_key}')
        with open(local_path, 'rb') as f:
            return f.read()

    def get_presigned_url(self, file_key, expires=3600):
        """Local storage returns the direct file URL."""
        return f'/uploads/{file_key}'

    def delete_file(self, file_key):
        local_path = self._resolve_path(file_key)
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f'本地文件删除成功: {file_key}')
            return True
        except Exception as e:
            logger.error(f'本地文件删除失败: {file_key}, {str(e)}')
            return False

    def check_file_exists(self, file_key):
        return os.path.exists(self._resolve_path(file_key))
