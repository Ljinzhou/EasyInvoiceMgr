import os
import logging

logger = logging.getLogger(__name__)

_storage_backend = os.environ.get('STORAGE_BACKEND', 'local')
storage_manager = None


def _init_storage():
    global storage_manager
    if _storage_backend == 'cos':
        from utils.cos_manager import cos_manager as cm
        storage_manager = cm
        logger.info('存储后端: 腾讯云COS')
    else:
        from utils.local_storage import LocalStorageManager
        storage_manager = LocalStorageManager()
        logger.info('存储后端: 本地文件系统')
    return storage_manager


_init_storage()
