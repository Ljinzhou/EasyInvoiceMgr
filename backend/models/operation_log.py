from flask import request
from datetime import datetime
from typing import Optional, Dict, Any, List
from models import db
import json


class OperationLog(db.Model):
    """操作日志模型"""
    __tablename__ = 'operation_logs'

    log_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    action_description = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.BigInteger)
    target_name = db.Column(db.String(200))
    event_id = db.Column(db.BigInteger, db.ForeignKey('events.event_id'))
    event_name = db.Column(db.String(200))
    detail = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now())

    user = db.relationship('User', foreign_keys=[user_id], backref='operation_logs')
    event = db.relationship('Event', foreign_keys=[event_id], backref='operation_logs')


class LogService:
    """操作日志服务"""

    @staticmethod
    def _get_client_info():
        """获取客户端信息"""
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        user_agent = request.headers.get('User-Agent', '')
        return ip_address, user_agent

    @staticmethod
    def log(
        user_id: int,
        username: str,
        action_type: str,
        action_description: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        event_id: Optional[int] = None,
        event_name: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录操作日志"""
        if ip_address is None or user_agent is None:
            client_ip, client_ua = LogService._get_client_info()
            ip_address = ip_address or client_ip
            user_agent = user_agent or client_ua

        log_entry = OperationLog(
            user_id=user_id,
            username=username,
            action_type=action_type,
            action_description=action_description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            event_id=event_id,
            event_name=event_name,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log_entry)
        db.session.commit()

    @staticmethod
    def get_logs(
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        event_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询操作日志"""
        query = OperationLog.query

        if user_id:
            query = query.filter(OperationLog.user_id == user_id)
        if action_type:
            query = query.filter(OperationLog.action_type == action_type)
        if target_type:
            query = query.filter(OperationLog.target_type == target_type)
        if event_id:
            query = query.filter(OperationLog.event_id == event_id)
        if start_date:
            query = query.filter(OperationLog.created_at >= start_date)
        if end_date:
            query = query.filter(OperationLog.created_at <= end_date)

        total = query.count()
        logs = query.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return {
            'logs': [log.to_dict() for log in logs],
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def delete_log(log_id: int) -> bool:
        """删除单条日志"""
        log = OperationLog.query.get(log_id)
        if log:
            db.session.delete(log)
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete_logs(log_ids: List[int]) -> int:
        """批量删除日志"""
        if not log_ids:
            return 0
        count = OperationLog.query.filter(OperationLog.log_id.in_(log_ids)).delete(synchronize_session=False)
        db.session.commit()
        return count

    @staticmethod
    def get_action_types() -> List[Dict[str, str]]:
        """获取所有操作类型"""
        return [
            {"value": "create_event", "label": "创建项目"},
            {"value": "update_event", "label": "修改项目"},
            {"value": "delete_event", "label": "删除项目"},
            {"value": "add_member", "label": "添加成员"},
            {"value": "remove_member", "label": "移除成员"},
            {"value": "update_member_role", "label": "修改成员角色"},
            {"value": "create_invoice", "label": "上传发票"},
            {"value": "delete_invoice", "label": "删除发票"},
            {"value": "update_invoice", "label": "修改发票"},
            {"value": "approve_invoice", "label": "审批通过发票"},
            {"value": "reject_invoice", "label": "拒绝发票"},
            {"value": "reimburse_invoice", "label": "报销发票"},
            {"value": "batch_reimburse_invoices", "label": "批量报销发票"},
            {"value": "create_voucher", "label": "上传凭证"},
            {"value": "delete_voucher", "label": "删除凭证"},
            {"value": "update_voucher", "label": "修改凭证"},
            {"value": "reimburse_voucher", "label": "报销凭证"},
            {"value": "batch_reimburse_vouchers", "label": "批量报销凭证"},
            {"value": "create_record", "label": "创建购买记录"},
            {"value": "update_record", "label": "修改购买记录"},
            {"value": "delete_record", "label": "删除购买记录"},
            {"value": "transfer_record", "label": "转移购买记录"},
            {"value": "reimburse_record", "label": "报销购买记录"},
            {"value": "create_user", "label": "创建用户"},
            {"value": "update_user", "label": "修改用户"},
            {"value": "delete_user", "label": "删除用户"},
            {"value": "change_password", "label": "修改密码"},
            {"value": "upload_avatar", "label": "上传头像"},
            {"value": "delete_avatar", "label": "删除头像"},
            {"value": "create_code", "label": "创建邀请码"},
            {"value": "toggle_code", "label": "切换邀请码状态"},
            {"value": "delete_code", "label": "删除邀请码"},
            {"value": "update_config", "label": "修改系统配置"},
            {"value": "backup", "label": "执行备份"},
            {"value": "restore_backup", "label": "恢复备份"},
            {"value": "delete_backup", "label": "删除备份"},
            {"value": "test_model", "label": "测试模型"},
            {"value": "ai_summary", "label": "AI财务总结"},
            {"value": "start_export", "label": "发起导出"},
        ]


# Extension of OperationLog model with to_dict method
def _operation_log_to_dict(self):
    return {
        'log_id': self.log_id,
        'user_id': self.user_id,
        'username': self.username,
        'action_type': self.action_type,
        'action_description': self.action_description,
        'target_type': self.target_type,
        'target_id': self.target_id,
        'target_name': self.target_name,
        'event_id': self.event_id,
        'event_name': self.event_name,
        'detail': self.detail,
        'ip_address': self.ip_address,
        'created_at': self.created_at.isoformat() if self.created_at else None
    }


OperationLog.to_dict = _operation_log_to_dict
