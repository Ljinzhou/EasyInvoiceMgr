"""AI 视觉模型配置：服务商预设、参数解析与旧配置迁移。

支持的视觉服务商（均为 OpenAI 兼容的 chat/completions 协议）：

- ``deepseek``：DeepSeek 官方，``deepseek-flash``（原生支持图像理解）
- ``siliconflow``：硅基流动，``zai-org/GLM-5.3-Flash``（原生多模态）

智谱 GLM 官方接口（``open.bigmodel.cn``）已下线不再支持，启动时会自动把
指向智谱的旧配置迁移到默认服务商，并清除仅为智谱准备的密钥。

配置优先级：数据库 ``system_configs`` > 环境变量 > 服务商默认值。
每个服务商可单独保存 API Key（``ai_api_key_<provider>``），
未单独保存时回退到通用 ``ai_api_key``，便于在两个平台之间切换。
"""

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_AI_PROVIDER = 'deepseek'

AI_PROVIDER_PRESETS = {
    'deepseek': {
        'label': 'DeepSeek 官方',
        'api_url': 'https://api.deepseek.com/chat/completions',
        'default_model': 'deepseek-flash',
        'models': ['deepseek-flash'],
        'api_key_env': ('DEEPSEEK_API_KEY',),
        'console_url': 'https://platform.deepseek.com/api_keys',
    },
    'siliconflow': {
        'label': '硅基流动 SiliconFlow',
        'api_url': 'https://api.siliconflow.cn/v1/chat/completions',
        'default_model': 'zai-org/GLM-5.3-Flash',
        'models': ['zai-org/GLM-5.3-Flash'],
        'api_key_env': ('SILICONFLOW_API_KEY', 'SILICONFLOW_APIKEY'),
        'console_url': 'https://cloud.siliconflow.cn/account/ak',
    },
}

# 已废弃的智谱 GLM 官方接口配置键：启动时直接清除，避免继续被读取
LEGACY_GLM_CONFIG_KEYS = ('ai_api_key_glm',)


def provider_preset(provider: str | None) -> dict:
    """返回服务商预设，未知服务商回退到默认服务商。"""
    return AI_PROVIDER_PRESETS.get(provider or '', AI_PROVIDER_PRESETS[DEFAULT_AI_PROVIDER])


def available_providers() -> list:
    """返回服务商列表（供设置页渲染下拉框）。"""
    return [
        {
            'value': name,
            'label': preset['label'],
            'api_url': preset['api_url'],
            'default_model': preset['default_model'],
            'models': list(preset['models']),
            'console_url': preset.get('console_url', ''),
        }
        for name, preset in AI_PROVIDER_PRESETS.items()
    ]


def _db_value(key: str) -> str | None:
    """从数据库读取配置值（加密项自动解密）。不在应用上下文时返回 None。"""
    try:
        from models import SystemConfig
        from utils.crypto_utils import decrypt_value

        record = SystemConfig.query.filter_by(config_key=key).first()
        if not record or not record.config_value:
            return None
        if record.is_encrypted:
            return decrypt_value(record.config_value)
        return record.config_value
    except Exception as exc:  # 应用尚未初始化 / 表不存在
        logger.debug('读取配置 %s 失败: %s', key, exc)
        return None


def is_legacy_glm_config(api_url: str = '', model: str = '') -> bool:
    """判断一组配置是否指向已下线的智谱 GLM 官方接口。"""
    url = (api_url or '').lower()
    name = (model or '').strip()
    if 'bigmodel.cn' in url or 'zhipu' in url:
        return True
    # 硅基流动的模型形如 zai-org/GLM-5.3-Flash，不能误判为智谱官方模型
    return name.upper().startswith('GLM')


def infer_provider(api_url: str = '', model: str = '') -> str:
    """根据已知的 URL / 模型名推断服务商。"""
    url = (api_url or '').lower()
    model_name = (model or '').strip()
    if 'siliconflow' in url or model_name.startswith('zai-org/'):
        return 'siliconflow'
    return DEFAULT_AI_PROVIDER


def resolve_ai_provider() -> str:
    """解析当前 AI 服务商。已废弃的 glm 值回退到默认服务商。"""
    explicit = _db_value('ai_provider') or os.environ.get('AI_PROVIDER')
    if explicit in AI_PROVIDER_PRESETS:
        return explicit
    return infer_provider(
        _db_value('ai_api_url') or os.environ.get('AI_API_URL', ''),
        _db_value('ai_model') or os.environ.get('AI_MODEL', ''),
    )


def resolve_ai_model(provider: str | None = None) -> str:
    """解析视觉模型名。残留的智谱模型名会被忽略。"""
    provider = provider or resolve_ai_provider()
    model = _db_value('ai_model') or os.environ.get('AI_MODEL')
    if model and not (provider != 'siliconflow' and is_legacy_glm_config('', model)):
        return model
    return provider_preset(provider)['default_model']


def resolve_ai_api_url(provider: str | None = None) -> str:
    """解析 chat/completions 接口地址。残留的智谱地址会被忽略。"""
    provider = provider or resolve_ai_provider()
    url = _db_value('ai_api_url') or os.environ.get('AI_API_URL')
    if url and not (provider != 'siliconflow' and is_legacy_glm_config(url, '')):
        return url
    return provider_preset(provider)['api_url']


def resolve_ai_api_key(provider: str | None = None) -> str | None:
    """解析 API Key：provider 专属 Key > 通用 Key > 环境变量。"""
    provider = provider or resolve_ai_provider()
    key = _db_value(f'ai_api_key_{provider}') or _db_value('ai_api_key')
    if key:
        return key
    for env_name in provider_preset(provider)['api_key_env']:
        value = os.environ.get(env_name)
        if value:
            return value
    return None


def _json_safe(value: str) -> str:
    return value.strip() if isinstance(value, str) else ''


def migrate_legacy_ai_config() -> None:
    """启动时清理已下线的智谱 GLM 配置，并补齐 ``ai_provider`` 字段。

    - 删除 ``ai_api_key_glm``（智谱官方 Key，已无用途）；
    - 若 URL / 模型名仍指向智谱官方接口，重写为默认服务商的地址与模型；
    - 同时清掉明显只对智谱有效的通用 Key，避免把旧 Key 发给新服务商。

    幂等：配置已迁移过则不会重复改写，也不会覆盖用户在设置页里的选择。
    """
    try:
        from models import db, SystemConfig
        from utils.crypto_utils import decrypt_value
    except Exception as exc:  # pragma: no cover - 极端导入失败
        logger.debug('跳过 AI 配置迁移: %s', exc)
        return

    try:
        rows = {row.config_key: row for row in SystemConfig.query.all()}
        changed = []

        # 1) 彻底移除智谱官方 Key
        for key in LEGACY_GLM_CONFIG_KEYS:
            row = rows.pop(key, None)
            if row is not None:
                db.session.delete(row)
                changed.append(f'删除 {key}')

        url_row = rows.get('ai_api_url')
        model_row = rows.get('ai_model')
        provider_row = rows.get('ai_provider')

        url = _json_safe(url_row.config_value) if url_row else ''
        model = _json_safe(model_row.config_value) if model_row else ''
        explicit = _json_safe(provider_row.config_value) if provider_row else ''

        target = explicit if explicit in AI_PROVIDER_PRESETS else infer_provider(url, model)
        migrated_from_glm = False

        if target != 'siliconflow' and is_legacy_glm_config(url, model):
            target = DEFAULT_AI_PROVIDER
            migrated_from_glm = True

        preset = provider_preset(target)

        # 2) 重写指向智谱的地址与模型
        if migrated_from_glm:
            if model_row:
                if model_row.config_value != preset['default_model']:
                    model_row.config_value = preset['default_model']
                    changed.append('ai_model')
            else:
                db.session.add(SystemConfig(
                    config_key='ai_model', config_value=preset['default_model'],
                    is_encrypted=False, description='AI 视觉模型',
                ))
                changed.append('ai_model')

            if url_row:
                if url_row.config_value != preset['api_url']:
                    url_row.config_value = preset['api_url']
                    changed.append('ai_api_url')
            else:
                db.session.add(SystemConfig(
                    config_key='ai_api_url', config_value=preset['api_url'],
                    is_encrypted=False, description='AI 接口地址',
                ))
                changed.append('ai_api_url')

            # 3) 智谱的 Key 形如 `id.secret`，DeepSeek / 硅基流动都是 `sk-` 开头
            key_row = rows.get('ai_api_key')
            if key_row and key_row.config_value:
                plain = key_row.config_value
                if key_row.is_encrypted:
                    try:
                        plain = decrypt_value(key_row.config_value)
                    except Exception:
                        plain = ''
                if not plain.startswith('sk-'):
                    key_row.config_value = ''
                    key_row.is_encrypted = False
                    changed.append('清空 ai_api_key')
                    logger.warning('旧的智谱 API Key 已清除，请在设置页重新填写 %s 的密钥', preset['label'])

        # 4) 补齐 provider 字段
        if provider_row:
            if provider_row.config_value != target:
                provider_row.config_value = target
                changed.append('ai_provider')
        else:
            db.session.add(SystemConfig(
                config_key='ai_provider', config_value=target,
                is_encrypted=False, description='AI 服务商（deepseek / siliconflow）',
            ))
            changed.append('ai_provider')

        db.session.commit()
        if changed:
            logger.info('AI 配置已迁移: provider=%s, 变更=%s', target, ','.join(changed))
    except Exception as exc:
        db.session.rollback()
        logger.warning('AI 配置迁移失败（不影响启动）: %s', exc)
