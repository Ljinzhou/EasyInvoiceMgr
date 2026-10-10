"""赛事(Event)统计字段的统一重算。

背景：赛事上的统计字段（invoice_count / invoice_total_amount /
purchase_record_count / voucher_count / voucher_total_amount / reimbursed_amount /
remaining_budget）此前由各路由用**增量式**（`+= amount`、`-= old + new`）分散维护，
共散落 16 处；同时 events.py 的列表/详情接口又用**统计式**（SQL SUM）动态计算，
两套算法口径还不一致：

- 增量式按 `status == 'approved'` 累加 reimbursed_amount，
  统计式按 `is_reimbursed == True` 累加 —— 审批通过 ≠ 已报销，两者本就不同，
  导致写入值与读取值长期漂移。
- 增量式用 `invoice.amount`，统计式用 `Invoice.total_amount`（含税总额）。
- 增量式对 PurchaseRecord 用 `record.total_amount or record.amount`。

本模块以「统计式」为唯一权威口径（与 events.py 读取侧一致），所有写路径改为
调用 `recalc_event_stats()` 全量重算，彻底消除漂移。

重算是纯查询+赋值，不额外 commit，由调用方决定事务边界。
"""

import logging

from models import db

logger = logging.getLogger(__name__)


def _to_float(value) -> float:
    """Numeric/None 安全转 float。"""
    if value is None:
        return 0.0
    return float(value)


def compute_event_stats(event_id: int) -> dict:
    """按明细表实时统计赛事的汇总数值（不写库）。

    返回键与 Event 上的统计字段一一对应。
    """
    from models import Invoice, Voucher, PurchaseRecord

    invoice_count = Invoice.query.filter_by(event_id=event_id, is_deleted=False).count()
    purchase_count = PurchaseRecord.query.filter_by(
        event_id=event_id, is_deleted=False
    ).count()
    voucher_agg = db.session.query(
        db.func.count(Voucher.voucher_id),
        db.func.coalesce(db.func.sum(Voucher.amount), 0),
    ).filter(Voucher.event_id == event_id, Voucher.is_deleted == False).first()

    # 发票总额：Invoice 表金额 + PurchaseRecord 中已开票记录的发票总额
    # （与 routes/events.py 读取侧口径一致）
    invoice_table_total = db.session.query(
        db.func.coalesce(db.func.sum(Invoice.amount), 0)
    ).filter(
        Invoice.event_id == event_id, Invoice.is_deleted == False
    ).scalar()
    purchase_invoice_total = db.session.query(
        db.func.coalesce(db.func.sum(PurchaseRecord.total_amount), 0)
    ).filter(
        PurchaseRecord.event_id == event_id,
        PurchaseRecord.is_deleted == False,
        PurchaseRecord.has_invoice == True,
    ).scalar()

    # 已报销金额：发票按 is_reimbursed，购买记录要求已开票且已报销
    # （与 routes/events.py 列表/详情接口的统计口径保持一致）
    invoice_reimbursed = db.session.query(
        db.func.coalesce(db.func.sum(Invoice.total_amount), 0)
    ).filter(
        Invoice.event_id == event_id,
        Invoice.is_deleted == False,
        Invoice.is_reimbursed == True,
    ).scalar()

    purchase_reimbursed = db.session.query(
        db.func.coalesce(db.func.sum(PurchaseRecord.total_amount), 0)
    ).filter(
        PurchaseRecord.event_id == event_id,
        PurchaseRecord.is_deleted == False,
        PurchaseRecord.has_invoice == True,
        PurchaseRecord.is_reimbursed == True,
    ).scalar()

    return {
        'invoice_count': int(invoice_count or 0),
        'invoice_total_amount': _to_float(invoice_table_total) + _to_float(purchase_invoice_total),
        'voucher_count': int(voucher_agg[0] or 0),
        'voucher_total_amount': _to_float(voucher_agg[1]),
        'purchase_record_count': int(purchase_count or 0),
        'reimbursed_amount': _to_float(invoice_reimbursed) + _to_float(purchase_reimbursed),
    }


def recalc_event_stats(event_id: int, commit: bool = False) -> dict:
    """重算并写回赛事的全部统计字段。

    应在**任何**影响明细的操作（发票/凭证/购买记录的增删改、审核、报销、
    项目间转移）之后调用，替换原先的增量式维护。

    Args:
        event_id: 赛事 ID
        commit: 是否在此处提交。默认 False，由调用方在同一个事务里一起提交。
    Returns:
        写入的统计值字典
    """
    from models import Event

    event = db.session.get(Event, event_id)
    if not event:
        logger.warning(f'recalc_event_stats: 赛事不存在 event_id={event_id}')
        return {}

    stats = compute_event_stats(event_id)
    stats['remaining_budget'] = _to_float(event.total_budget) - stats['reimbursed_amount']

    event.invoice_count = stats['invoice_count']
    event.invoice_total_amount = stats['invoice_total_amount']
    event.voucher_count = stats['voucher_count']
    event.voucher_total_amount = stats['voucher_total_amount']
    event.purchase_record_count = stats['purchase_record_count']
    event.reimbursed_amount = stats['reimbursed_amount']
    event.remaining_budget = stats['remaining_budget']

    if commit:
        db.session.commit()

    return stats