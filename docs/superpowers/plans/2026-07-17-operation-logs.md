# 操作日志功能实现计划

> **目标：** 为管理员添加操作日志追踪功能，记录所有用户操作行为，并支持日志查看和删除

**架构概述：**
- 后端：新增 `operation_logs` 数据表，记录操作类型、操作人、操作时间、关联项目和详情
- 后端：新增 `backend/routes/operation_logs.py` API 路由
- 前端：侧边栏添加"操作日志"菜单（仅admin可见）
- 前端：新增 `/pages/operation-logs.vue` 日志查看页面
- 前端：修改 `layouts/default.vue` 添加菜单入口

**技术栈：** Python FastAPI + Vue 3 + PostgreSQL

---

## 任务1：数据库表设计

**文件：**
- 修改：`backend/sql/base.sql`

- [ ] **步骤1：添加操作日志表定义**

在 `backend/sql/base.sql` 末尾（索引之前）添加：

```sql
-- ============================================
-- 2.12 操作日志表 (operation_logs)
-- 记录所有用户的操作行为，便于追溯和审计
-- ============================================
CREATE TABLE operation_logs (
    log_id BIGSERIAL PRIMARY KEY,
    
    -- 操作人信息
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    username VARCHAR(50) NOT NULL, -- 冗余存储，方便查询
    
    -- 操作类型枚举
    action_type VARCHAR(50) NOT NULL, -- 见下方 action_type 释义
    action_description TEXT NOT NULL, -- 操作描述中文名
    
    -- 关联实体信息
    target_type VARCHAR(50), -- 目标实体类型: event/invoice/voucher/purchase_record/user/invitation_code/system_config/backup
    target_id BIGINT, -- 目标实体ID
    target_name VARCHAR(200), -- 目标名称冗余（如项目名称、发票号码等）
    
    -- 项目关联（如果操作与项目相关）
    event_id BIGINT REFERENCES events(event_id),
    event_name VARCHAR(200),
    
    -- 操作详情（JSON格式存储额外信息）
    detail JSONB,
    
    -- 元数据
    ip_address VARCHAR(45), -- 操作者IP地址
    user_agent TEXT, -- 浏览器UA
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- action_type 释义：
-- events: create_event, update_event, delete_event, add_member, remove_member, update_member_role
-- invoices: create_invoice, delete_invoice, update_invoice, approve_invoice, reject_invoice, reimburse_invoice, batch_reimburse_invoices
-- vouchers: create_voucher, delete_voucher, update_voucher, reimburse_voucher, batch_reimburse_vouchers
-- purchase_records: create_record, update_record, delete_record, transfer_record, reimburse_record
-- users: create_user, update_user, delete_user, change_password, upload_avatar, delete_avatar
-- invitation_codes: create_code, toggle_code, delete_code
-- system: update_config, backup, restore_backup, delete_backup, test_model, ai_summary
-- export: start_export
```

- [ ] **步骤2：添加索引**

在索引区域添加：

```sql
-- 操作日志索引
CREATE INDEX idx_operation_logs_user ON operation_logs(user_id);
CREATE INDEX idx_operation_logs_action ON operation_logs(action_type);
CREATE INDEX idx_operation_logs_target ON operation_logs(target_type, target_id);
CREATE INDEX idx_operation_logs_event ON operation_logs(event_id);
CREATE INDEX idx_operation_logs_time ON operation_logs(created_at DESC);
```

- [ ] **步骤3：执行数据库迁移**

```bash
cd E:/AAACodeProjectMy/EasyInvoiceMgr
# 先备份当前数据库
pg_dump -U postgres -d invoice_db > backup_before_log.sql

# 执行新增表和索引（追加到现有表）
psql -U postgres -d invoice_db -c "CREATE TABLE IF NOT EXISTS operation_logs (...);"
```

---

## 任务2：后端日志记录服务

**文件：**
- 创建：`backend/services/log_service.py`
- 修改：`backend/routes/events.py`
- 修改：`backend/routes/invoices.py`
- 修改：`backend/routes/vouchers.py`
- 修改：`backend/routes/purchase_records.py`
- 修改：`backend/routes/auth.py`
- 修改：`backend/routes/invitation_codes.py`
- 修改：`backend/routes/system.py`
- 修改：`backend/routes/export.py`

- [ ] **步骤1：创建日志记录服务**

创建 `backend/services/log_service.py`：

```python
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text
from database import get_db_connection

class LogService:
    """操作日志服务"""
    
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
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO operation_logs 
                    (user_id, username, action_type, action_description, 
                     target_type, target_id, target_name, event_id, event_name,
                     detail, ip_address, user_agent, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, username, action_type, action_description,
                    target_type, target_id, target_name, event_id, event_name,
                    json.dumps(detail) if detail else None,
                    ip_address, user_agent, datetime.now()
                ))
            conn.commit()
        finally:
            conn.close()
    
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
    ):
        """查询操作日志"""
        conn = get_db_connection()
        try:
            conditions = []
            params = []
            
            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)
            if action_type:
                conditions.append("action_type = %s")
                params.append(action_type)
            if target_type:
                conditions.append("target_type = %s")
                params.append(target_type)
            if event_id:
                conditions.append("event_id = %s")
                params.append(event_id)
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            with conn.cursor() as cur:
                # 获取总数
                cur.execute(f"SELECT COUNT(*) FROM operation_logs WHERE {where_clause}", params)
                total = cur.fetchone()[0]
                
                # 获取分页数据
                offset = (page - 1) * page_size
                cur.execute(f"""
                    SELECT log_id, user_id, username, action_type, action_description,
                           target_type, target_id, target_name, event_id, event_name,
                           detail, ip_address, created_at
                    FROM operation_logs
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                
                logs = []
                for row in cur.fetchall():
                    logs.append({
                        "log_id": row[0],
                        "user_id": row[1],
                        "username": row[2],
                        "action_type": row[3],
                        "action_description": row[4],
                        "target_type": row[5],
                        "target_id": row[6],
                        "target_name": row[7],
                        "event_id": row[8],
                        "event_name": row[9],
                        "detail": row[10],
                        "ip_address": row[11],
                        "created_at": row[12].isoformat() if row[12] else None
                    })
                
                return {"logs": logs, "total": total, "page": page, "page_size": page_size}
        finally:
            conn.close()
    
    @staticmethod
    def delete_log(log_id: int) -> bool:
        """删除单条日志"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM operation_logs WHERE log_id = %s", (log_id,))
                affected = cur.rowcount
            conn.commit()
            return affected > 0
        finally:
            conn.close()
    
    @staticmethod
    def delete_logs(log_ids: list) -> int:
        """批量删除日志"""
        if not log_ids:
            return 0
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                placeholders = ','.join(['%s'] * len(log_ids))
                cur.execute(f"DELETE FROM operation_logs WHERE log_id IN ({placeholders})", log_ids)
                affected = cur.rowcount
            conn.commit()
            return affected
        finally:
            conn.close()
    
    @staticmethod
    def get_action_types():
        """获取所有操作类型（用于筛选）"""
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
```

- [ ] **步骤2：在各个路由中集成日志记录**

需要修改的文件和添加的日志调用位置：

**backend/routes/events.py:**
```python
from services.log_service import LogService

# create_event 函数末尾添加:
LogService.log(
    user_id=current_user['user_id'],
    username=current_user['username'],
    action_type='create_event',
    action_description=f'创建项目「{event_name}」',
    target_type='event',
    target_id=event_id,
    target_name=event_name,
    detail={'budget': total_budget, 'description': description}
)

# update_event 函数添加类似日志
# delete_event 函数添加类似日志
# add_event_member 函数添加类似日志
# remove_event_member 函数添加类似日志
# update_event_member 函数添加类似日志
```

**backend/routes/invoices.py:**
- create_invoice: `create_invoice`
- delete_invoice: `delete_invoice`
- update_invoice: `update_invoice`
- approve_invoice: `approve_invoice` 或 `reject_invoice`
- reimburse_invoice: `reimburse_invoice`
- batch_reimburse_invoices: `batch_reimburse_invoices`

**backend/routes/vouchers.py:**
- create_voucher: `create_voucher`
- delete_voucher: `delete_voucher`
- update_voucher: `update_voucher`
- batch_reimburse_vouchers: `batch_reimburse_vouchers`

**backend/routes/purchase_records.py:**
- create_purchase_record: `create_record`
- update_purchase_record: `update_record`
- delete_purchase_record: `delete_record`
- transfer_purchase_record: `transfer_record`
- reimburse_purchase_record: `reimburse_record`

**backend/routes/auth.py:**
- register: `create_user`
- update_user: `update_user`
- delete_user: `delete_user`
- change_password: `change_password`
- upload_avatar: `upload_avatar`
- delete_avatar: `delete_avatar`

**backend/routes/invitation_codes.py:**
- create_invitation_code: `create_code`
- toggle_invitation_code: `toggle_code`
- delete_invitation_code: `delete_code`

**backend/routes/system.py:**
- update_system_config: `update_config`
- manual_backup: `backup`
- delete_backup: `delete_backup`
- restore_backup: `restore_backup`
- ai_summary: `ai_summary`
- test_model: `test_model`
- test_summary_model: `test_model`

**backend/routes/export.py:**
- start_export: `start_export`

---

## 任务3：后端API路由

**文件：**
- 创建：`backend/routes/operation_logs.py`

- [ ] **步骤1：创建操作日志API路由**

创建 `backend/routes/operation_logs.py`：

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from auth import get_current_admin_user

router = APIRouter(prefix="/operation-logs", tags=["操作日志"])

class LogDeleteRequest(BaseModel):
    log_ids: List[int]

@router.get("")
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    event_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """获取操作日志列表（仅管理员）"""
    from services.log_service import LogService
    result = LogService.get_logs(
        page=page,
        page_size=page_size,
        user_id=user_id,
        action_type=action_type,
        target_type=target_type,
        event_id=event_id,
        start_date=start_date,
        end_date=end_date
    )
    return {"code": 200, "message": "success", "data": result}

@router.get("/action-types")
async def get_action_types(current_user: dict = Depends(get_current_admin_user)):
    """获取所有操作类型"""
    from services.log_service import LogService
    return {"code": 200, "message": "success", "data": LogService.get_action_types()}

@router.delete("/{log_id}")
async def delete_log(
    log_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """删除单条日志"""
    from services.log_service import LogService
    success = LogService.delete_log(log_id)
    if success:
        return {"code": 200, "message": "日志已删除"}
    return {"code": 404, "message": "日志不存在"}

@router.delete("")
async def delete_logs(
    request: LogDeleteRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """批量删除日志"""
    from services.log_service import LogService
    count = LogService.delete_logs(request.log_ids)
    return {"code": 200, "message": f"已删除 {count} 条日志", "data": {"deleted": count}}
```

- [ ] **步骤2：在 app.py 中注册路由**

在 `backend/app.py` 中添加：

```python
from routes.operation_logs import router as operation_logs_router

app.include_router(operation_logs_router)
```

---

## 任务4：前端界面

**文件：**
- 修改：`frontend/layouts/default.vue`
- 创建：`frontend/pages/operation-logs.vue`

- [ ] **步骤1：在侧边栏添管理员菜单**

在 `frontend/layouts/default.vue` 的 nav-item 列表中添加：

```vue
<NuxtLink v-if="isMounted && isAdmin" to="/operation-logs" class="nav-item" :class="{ active: $route.path.startsWith('/operation-logs') }" @click="mobileMenuOpen = false">
  <span class="nav-icon">📋</span>
  <span class="nav-text">操作日志</span>
</NuxtLink>
```

放置位置：在"系统设置"菜单项之后。

- [ ] **步骤2：创建操作日志页面**

创建 `frontend/pages/operation-logs.vue`：

```vue
<template>
  <div class="operation-logs-page">
    <div class="page-header">
      <h1>操作日志</h1>
      <p class="subtitle">追踪所有用户操作行为</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>操作类型</label>
        <select v-model="filters.action_type" @change="fetchLogs">
          <option value="">全部操作</option>
          <option v-for="type in actionTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>目标类型</label>
        <select v-model="filters.target_type" @change="fetchLogs">
          <option value="">全部类型</option>
          <option value="event">项目</option>
          <option value="invoice">发票</option>
          <option value="voucher">凭证</option>
          <option value="purchase_record">购买记录</option>
          <option value="user">用户</option>
          <option value="invitation_code">邀请码</option>
          <option value="system">系统</option>
        </select>
      </div>
      <div class="filter-group">
        <label>开始日期</label>
        <input type="date" v-model="filters.start_date" @change="fetchLogs" />
      </div>
      <div class="filter-group">
        <label>结束日期</label>
        <input type="date" v-model="filters.end_date" @change="fetchLogs" />
      </div>
      <button class="reset-btn" @click="resetFilters">重置筛选</button>
    </div>

    <!-- 批量操作栏 -->
    <div class="batch-actions" v-if="selectedLogs.length > 0">
      <span>已选择 {{ selectedLogs.length }} 条</span>
      <button class="delete-btn" @click="batchDelete">删除选中</button>
      <button class="cancel-btn" @click="selectedLogs = []">取消选择</button>
    </div>

    <!-- 日志列表 -->
    <div class="logs-table">
      <table>
        <thead>
          <tr>
            <th class="checkbox-col">
              <input type="checkbox" @change="toggleSelectAll" :checked="isAllSelected" />
            </th>
            <th>时间</th>
            <th>操作人</th>
            <th>操作类型</th>
            <th>操作描述</th>
            <th>关联项目</th>
            <th>目标详情</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.log_id">
            <td class="checkbox-col">
              <input type="checkbox" :value="log.log_id" v-model="selectedLogs" />
            </td>
            <td class="time-col">{{ formatTime(log.created_at) }}</td>
            <td>{{ log.username }}</td>
            <td>
              <span class="action-tag" :class="getActionClass(log.action_type)">
                {{ getActionLabel(log.action_type) }}
              </span>
            </td>
            <td class="desc-col">{{ log.action_description }}</td>
            <td>{{ log.event_name || '-' }}</td>
            <td class="target-col">
              <template v-if="log.target_name">
                {{ log.target_type }} #{{ log.target_id }}: {{ log.target_name }}
              </template>
              <template v-else-if="log.target_id">
                {{ log.target_type }} #{{ log.target_id }}
              </template>
              <template v-else>-</template>
            </td>
            <td class="action-col">
              <button class="delete-single-btn" @click="deleteLog(log.log_id)" title="删除">
                🗑️
              </button>
            </td>
          </tr>
          <tr v-if="logs.length === 0">
            <td colspan="8" class="empty-row">暂无操作日志</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button @click="page--" :disabled="page === 1">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button @click="page++" :disabled="page >= totalPages">下一页</button>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="confirm-modal">
        <h3>确认删除</h3>
        <p>确定要删除选中的 {{ deleteCount }} 条日志吗？此操作不可恢复。</p>
        <div class="modal-actions">
          <button @click="showDeleteConfirm = false">取消</button>
          <button class="delete-btn" @click="confirmDelete">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

const { $api } = useNuxtApp()

const logs = ref<any[]>([])
const actionTypes = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const selectedLogs = ref<number[]>([])

const filters = ref({
  action_type: '',
  target_type: '',
  start_date: '',
  end_date: ''
})

const showDeleteConfirm = ref(false)
const deleteCount = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const isAllSelected = computed(() => logs.value.length > 0 && selectedLogs.value.length === logs.value.length)

onMounted(async () => {
  await fetchActionTypes()
  await fetchLogs()
})

watch(page, () => fetchLogs())

async function fetchActionTypes() {
  try {
    const resp = await $api.get('/operation-logs/action-types')
    if (resp.data.code === 200) {
      actionTypes.value = resp.data.data
    }
  } catch (e) {
    console.error('获取操作类型失败', e)
  }
}

async function fetchLogs() {
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.value.action_type) params.action_type = filters.value.action_type
    if (filters.value.target_type) params.target_type = filters.value.target_type
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    
    const resp = await $api.get('/operation-logs', { params })
    if (resp.data.code === 200) {
      logs.value = resp.data.data.logs
      total.value = resp.data.data.total
    }
  } catch (e) {
    console.error('获取日志失败', e)
  }
}

function resetFilters() {
  filters.value = { action_type: '', target_type: '', start_date: '', end_date: '' }
  page.value = 1
  fetchLogs()
}

function formatTime(isoString: string) {
  if (!isoString) return '-'
  const d = new Date(isoString)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function getActionLabel(actionType: string) {
  const type = actionTypes.value.find(t => t.value === actionType)
  return type ? type.label : actionType
}

function getActionClass(actionType: string) {
  if (actionType.includes('create')) return 'create'
  if (actionType.includes('delete')) return 'delete'
  if (actionType.includes('update') || actionType.includes('edit')) return 'update'
  if (actionType.includes('reimburse') || actionType.includes('approve')) return 'approve'
  return 'default'
}

function toggleSelectAll(e: Event) {
  if ((e.target as HTMLInputElement).checked) {
    selectedLogs.value = logs.value.map(l => l.log_id)
  } else {
    selectedLogs.value = []
  }
}

function batchDelete() {
  deleteCount.value = selectedLogs.value.length
  showDeleteConfirm.value = true
}

function deleteLog(logId: number) {
  selectedLogs.value = [logId]
  deleteCount.value = 1
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  try {
    const resp = await $api.delete('/operation-logs', { data: { log_ids: selectedLogs.value } })
    if (resp.data.code === 200) {
      alert(`成功删除 ${resp.data.data.deleted} 条日志`)
      selectedLogs.value = []
      showDeleteConfirm.value = false
      await fetchLogs()
    } else {
      alert(resp.data.message || '删除失败')
    }
  } catch (e) {
    alert('删除失败')
  }
}
</script>

<style scoped>
.operation-logs-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  font-size: 0.9rem;
}

.filter-bar {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  background: white;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.filter-group label {
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
}

.filter-group select,
.filter-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-height: 36px;
}

.reset-btn {
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-end;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #fff3cd;
  padding: 0.8rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.delete-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.cancel-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.logs-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.8rem;
  text-align: left;
  border-bottom: 1px solid #eee;
  font-size: 0.9rem;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.time-col {
  white-space: nowrap;
  color: #666;
  font-size: 0.85rem;
}

.desc-col {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.target-col {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #666;
  font-size: 0.85rem;
}

.action-tag {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.action-tag.create { background: #d4edda; color: #155724; }
.action-tag.delete { background: #f8d7da; color: #721c24; }
.action-tag.update { background: #cce5ff; color: #004085; }
.action-tag.approve { background: #fff3cd; color: #856404; }
.action-tag.default { background: #e2e3e5; color: #383d41; }

.delete-single-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.3rem;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.delete-single-btn:hover {
  opacity: 1;
}

.empty-row {
  text-align: center;
  color: #999;
  padding: 2rem !important;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.confirm-modal {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 400px;
}

.confirm-modal h3 {
  margin: 0 0 1rem;
}

.confirm-modal p {
  color: #666;
  margin-bottom: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.8rem;
  justify-content: flex-end;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions button:first-child {
  background: #f0f0f0;
}

.modal-actions .delete-btn {
  background: #dc3545;
}
</style>
```

---

## 任务5：测试验证

- [ ] **步骤1：测试日志记录功能**

1. 使用 admin 账号登录
2. 创建一个项目 → 应记录 `create_event`
3. 上传一张发票 → 应记录 `create_invoice`
4. 审批发票 → 应记录 `approve_invoice`
5. 报销发票 → 应记录 `reimburse_invoice`

- [ ] **步骤2：测试日志查看功能**

1. 访问"操作日志"页面
2. 验证日志列表显示正确
3. 验证筛选功能正常
4. 验证分页功能正常

- [ ] **步骤3：测试日志删除功能**

1. 选择单条日志，点击删除
2. 批量选择日志，点击删除
3. 验证删除后日志确实被移除

- [ ] **步骤4：验证权限控制**

1. 使用非 admin 账号登录
2. 尝试访问 `/operation-logs` 页面 → 应被重定向或拒绝
3. 尝试直接调用 API → 应返回 403

---

## 自查清单

- [ ] 所有操作类型都已记录日志
- [ ] 日志包含完整的用户、时间和操作信息
- [ ] 前端页面样式与系统整体风格一致
- [ ] 批量删除功能正常工作
- [ ] 分页和筛选功能正常工作
- [ ] 非管理员无法访问日志页面和 API
- [ ] 数据库迁移保留了现有数据
