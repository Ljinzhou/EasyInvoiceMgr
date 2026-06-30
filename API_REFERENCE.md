# EasyInvoiceMgr — 完整 API 接口文档

> 本文档供后端重写时参考，涵盖所有 HTTP 接口的路径、方法、参数、请求体和响应格式。

---

## 通用约定

### 基础 URL
- 前端请求通过 `/api` 前缀访问后端
- 部分接口前缀为 `/api/auth`

### 认证方式
- 使用 JWT Bearer Token，登录后获取
- Header: `Authorization: Bearer <token>`
- 部分下载接口也支持 Query String: `?token=<token>`

### 统一响应格式
```json
{
  "code": 200,           // HTTP 状态码语义
  "message": "success",  // 描述信息
  "data": {}             // 业务数据，无数据时为 null
}
```

### 用户角色
| 角色 | 常量值 | 说明 |
|------|--------|------|
| 管理员 | `admin` | 最高权限 |
| 老师 | `teacher` | 可创建项目、审核、生成邀请码 |
| 学生管理员 | `student_admin` | 可审核、管理学生 |
| 学生 | `student` | 基础用户，上传发票/记录 |

### 发票状态
| 值 | 说明 |
|----|------|
| `pending` | 待审核 |
| `approved` | 已通过 |
| `rejected` | 已拒绝 |

### 赛事状态
| 值 | 说明 |
|----|------|
| `ongoing` | 进行中 |
| `completed` | 已结束 |

---

## 1. 认证模块 (Auth) — `/api/auth`

### 1.1 用户注册
```
POST /api/auth/register
```
**无需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名，唯一 |
| password | string | 是 | 密码（明文，后端哈希存储） |
| real_name | string | 是 | 真实姓名 |
| email | string | 否 | 邮箱，唯一 |
| phone | string | 否 | 手机号 |
| user_type | string | 否 | 角色，默认 `student` |
| student_or_staff_id | string | 否 | 学号/工号 |
| invitation_code | string | 否 | 邀请码（若有则校验） |

**响应** `201`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": 1,
    "username": "zhangsan",
    "real_name": "张三",
    "email": "zhangsan@example.com",
    "phone": null,
    "user_type": "student",
    "student_or_staff_id": "2021001",
    "account_status": "active"
  }
}
```

---

### 1.2 用户登录
```
POST /api/auth/login
```
**无需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOi...",
    "user": {
      "user_id": 1,
      "username": "admin",
      "real_name": "系统管理员",
      "email": "admin@example.com",
      "phone": null,
      "user_type": "admin",
      "student_or_staff_id": null,
      "avatar_url": "/uploads/avatars/1/xxx.png"
    }
  }
}
```

---

### 1.3 获取用户列表
```
GET /api/auth/users
```
**需认证**，权限: admin / teacher / student_admin

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| search | string | 否 | 模糊搜索（用户名/姓名/邮箱） |
| user_type | string | 否 | 按角色筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 10,
    "data": [
      {
        "user_id": 1,
        "username": "admin",
        "real_name": "系统管理员",
        "email": "admin@example.com",
        "phone": null,
        "user_type": "admin",
        "student_or_staff_id": null,
        "account_status": "active",
        "register_time": "2025-01-01T00:00:00+00:00",
        "avatar_url": null
      }
    ]
  }
}
```

---

### 1.4 获取单个用户信息
```
GET /api/auth/users/<user_id>
```
**需认证**，仅允许查看自己的信息（`current_user_id == user_id`）

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": 1,
    "username": "admin",
    "real_name": "系统管理员",
    "email": "admin@example.com",
    "phone": null,
    "user_type": "admin",
    "student_or_staff_id": null,
    "avatar_url": null,
    "account_status": "active",
    "register_time": "2025-01-01T00:00:00+00:00",
    "last_login_time": "2025-06-01T12:00:00+00:00"
  }
}
```

---

### 1.5 更新用户信息
```
PUT /api/auth/users/<user_id>
```
**需认证**

- **admin** 可修改任意用户的: `real_name`, `email`, `phone`, `student_or_staff_id`, `user_type`, `account_status`
- **本人** 只能修改自己的: `real_name`, `email`, `phone`, `student_or_staff_id`

请求体（JSON，所有字段可选）:
```json
{
  "real_name": "新名字",
  "email": "new@example.com",
  "phone": "13800138000",
  "student_or_staff_id": "2021002",
  "user_type": "teacher",
  "account_status": "active"
}
```

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": 1,
    "username": "admin",
    "real_name": "新名字",
    "email": "new@example.com",
    "phone": "13800138000",
    "user_type": "teacher",
    "student_or_staff_id": "2021002",
    "account_status": "active"
  }
}
```

---

### 1.6 修改密码
```
PUT /api/auth/users/<user_id>/password
```
**需认证**，仅可修改自己的密码

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| old_password | string | 是 | 旧密码 |
| new_password | string | 是 | 新密码（>=8位，含字母+数字，不能与旧密码相同） |

**响应** `200`:
```json
{ "code": 200, "message": "密码修改成功", "data": null }
```

---

### 1.7 删除用户（软删除）
```
DELETE /api/auth/users/<user_id>
```
**需认证**，仅 admin，不能删除 admin 自身

**响应** `200`:
```json
{ "code": 200, "message": "success", "data": null }
```

---

### 1.8 获取头像
```
GET /api/auth/avatar
```
**需认证**

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": { "avatar_url": "/uploads/avatars/1/xxx.png" }
}
```

---

### 1.9 上传头像
```
POST /api/auth/avatar/upload
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件，仅支持 jpg/jpeg/png/webp，最大 5MB |

**响应** `200`:
```json
{
  "code": 200,
  "message": "头像上传成功",
  "data": {
    "avatar_url": "/uploads/avatars/1/20250601120000_abc123.png",
    "file_md5": "d41d8cd98f00b204e9800998ecf8427e"
  }
}
```

---

### 1.10 删除头像
```
DELETE /api/auth/avatar
```
**需认证**

**响应** `200`:
```json
{ "code": 200, "message": "头像已删除", "data": null }
```

---

## 2. 赛事/项目管理 (Events) — `/api`

### 2.1 创建赛事
```
POST /api/events
```
**需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| event_name | string | 是 | 赛事名称 |
| event_start_time | string | 是 | 开始时间 ISO8601 |
| event_end_time | string | 是 | 结束时间 ISO8601 |
| description | string | 否 | 描述 |
| upload_start_time | string | 否 | 上传窗口开始时间 |
| upload_end_time | string | 否 | 上传窗口结束时间 |
| leader_id | int | 否 | 负责人用户ID |
| total_budget | number | 否 | 总预算，默认 0 |

> 创建者自动加入为成员；若指定了 leader_id，leader 也自动加入

**响应** `201`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "event_id": 1,
    "event_name": "机器人竞赛",
    "description": "...",
    "status": "ongoing",
    "event_start_time": "2025-06-01T00:00:00+00:00",
    "event_end_time": "2025-06-30T00:00:00+00:00",
    "upload_start_time": null,
    "upload_end_time": null,
    "creator_id": 1,
    "leader_id": 2,
    "total_budget": 10000.00,
    "reimbursed_amount": 0.00,
    "remaining_budget": 10000.00,
    "invoice_count": 0,
    "invoice_total_amount": 0.00
  }
}
```

---

### 2.2 获取赛事列表
```
GET /api/events
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 10 |
| status | string | 否 | 按状态筛选 (`ongoing` / `completed`) |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 10,
    "data": [
      {
        "event_id": 1,
        "event_name": "机器人竞赛",
        "description": "...",
        "status": "ongoing",
        "event_start_time": "2025-06-01T00:00:00+00:00",
        "event_end_time": "2025-06-30T00:00:00+00:00",
        "upload_start_time": null,
        "upload_end_time": null,
        "total_budget": 10000.00,
        "reimbursed_amount": 500.00,
        "remaining_budget": 9500.00,
        "spent_amount": 2000.00,
        "invoice_total_amount": 500.00,
        "purchase_total_amount": 1500.00,
        "invoice_count": 2,
        "purchase_record_count": 5,
        "voucher_count": 7,
        "creator_id": 1,
        "leader_id": 2,
        "leader_name": "李老师",
        "is_member": true
      }
    ]
  }
}
```

> `is_member`: 当前用户是否有权限操作此赛事（admin/teacher/student_admin 始终为 true）

---

### 2.3 获取单个赛事详情
```
GET /api/events/<event_id>
```
**需认证**

响应字段与列表项相同。

---

### 2.4 更新赛事
```
PUT /api/events/<event_id>
```
**需认证**，权限: admin / teacher / student_admin

请求体（JSON，所有字段可选）:
```json
{
  "event_name": "新名称",
  "description": "...",
  "event_start_time": "2025-07-01T00:00:00+00:00",
  "event_end_time": "2025-07-31T00:00:00+00:00",
  "upload_start_time": "2025-07-01T00:00:00+00:00",
  "upload_end_time": "2025-07-15T00:00:00+00:00",
  "leader_id": 3,
  "total_budget": 20000.00
}
```

> 更新 total_budget 时自动重算 remaining_budget = total_budget - reimbursed_amount

**响应** `200`，返回更新后的赛事对象。

---

### 2.5 删除赛事（软删除）
```
DELETE /api/events/<event_id>
```
**需认证**，仅当赛事下没有关联发票时才可删除。

**响应** `200`，或 `400`（还有发票未删除）。

---

### 2.6 获取赛事成员列表
```
GET /api/events/<event_id>/members
```
**需认证**

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "members": [
      {
        "user_id": 2,
        "username": "lisi",
        "real_name": "李四",
        "email": "lisi@example.com",
        "phone": null,
        "user_type": "student",
        "student_or_staff_id": "2021002",
        "avatar_url": null,
        "role_in_event": "student",
        "created_at": "2025-06-01T00:00:00+00:00"
      }
    ],
    "total_count": 1
  }
}
```

---

### 2.7 添加赛事成员
```
POST /api/events/<event_id>/members
```
**需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 是 | 要添加的用户ID |
| role_in_event | string | 否 | 赛事内角色: `student` / `student_admin` / `teacher`，默认 `student` |

**响应** `201`:
```json
{
  "code": 200,
  "message": "添加成员成功",
  "data": {
    "member_id": 1,
    "user_id": 2,
    "role_in_event": "student"
  }
}
```

---

### 2.8 更新赛事成员角色
```
PUT /api/events/<event_id>/members/<user_id>
```
**需认证**，权限: admin / teacher / student_admin

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_in_event | string | 是 | `student` / `student_admin` / `teacher` |

---

### 2.9 移除赛事成员（软删除）
```
DELETE /api/events/<event_id>/members/<user_id>
```
**需认证**

---

### 2.10 用户消费汇总排名
```
GET /api/events/stats/user-summary
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| event_id | int | 否 | 限定赛事，不传则汇总所有赛事 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "rankings": [
      {
        "user_id": 1,
        "real_name": "张三",
        "user_type": "student",
        "total_amount": 2500.50,
        "record_count": 7
      }
    ]
  }
}
```

> 按 total_amount 降序排列

---

## 3. 发票管理 (Invoices) — `/api`

### 3.1 获取发票列表
```
GET /api/invoices
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| event_id | int | 是 | 赛事ID |
| page | int | 否 | 默认 1 |
| page_size | int | 否 | 默认 20 |
| uploader_id | int | 否 | 按上传人筛选 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "data": [
      {
        "invoice_id": 1,
        "event_id": 1,
        "uploader_id": 1,
        "uploader_name": "张三",
        "file_name": "invoice.pdf",
        "invoice_type": "增值税电子普通发票",
        "invoice_number": "12345678",
        "project_name": "机器人配件",
        "amount": 500.00,
        "total_amount": 500.00,
        "invoice_date": "2025-05-01",
        "status": "approved",
        "reviewer_id": 2,
        "reviewer_name": "李老师",
        "review_time": "2025-05-02T10:00:00+00:00",
        "rejection_reason": null,
        "remarks": null,
        "is_reimbursed": false,
        "reimbursed_at": null,
        "created_at": "2025-05-01T12:00:00+00:00",
        "image_url": "https://cos.example.com/..."
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 3.2 上传发票
```
POST /api/invoices
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 发票文件（pdf/png/jpg/jpeg） |
| event_id | int | 是 | 所属赛事ID |
| invoice_type | string | 否 | 发票类型 |
| invoice_number | string | 否 | 发票号码 |
| project_name | string | 否 | 项目名称 |
| amount | number | 否 | 金额 |
| total_amount | number | 否 | 价税合计（默认等于 amount） |
| invoice_date | string | 否 | 开票日期 (YYYY-MM-DD) |
| remarks | string | 否 | 备注 |

> MD5 去重：相同 MD5 的发票不允许重复上传。

**响应** `200`:
```json
{
  "code": 200,
  "message": "发票上传成功",
  "data": {
    "invoice_id": 1,
    "file_name": "invoice.pdf",
    "image_url": "https://cos.example.com/..."
  }
}
```

---

### 3.3 更新发票信息
```
PUT /api/invoices/<invoice_id>
```
**需认证**

请求体（JSON，所有字段可选）:
```json
{
  "invoice_type": "增值税专用发票",
  "project_name": "新项目名",
  "amount": 600.00,
  "invoice_date": "2025-06-01",
  "invoice_number": "87654321",
  "remarks": "更新备注"
}
```

> 修改 amount 时会自动更新对应赛事的 `invoice_total_amount`，已 approved 的还会更新 `reimbursed_amount` 和 `remaining_budget`

---

### 3.4 删除发票（软删除）
```
DELETE /api/invoices/<invoice_id>
```
**需认证**，权限：admin/teacher 或上传者本人。学生需是项目成员。

> 删除后赛事 `invoice_count -= 1`，`invoice_total_amount -= amount`

---

### 3.5 审核发票
```
POST /api/invoices/<invoice_id>/approve
```
**需认证**，权限: admin / teacher / student_admin

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | `approved` 或 `rejected` |
| rejection_reason | string | 条件 | 拒绝时必填 |

> approved 时: `event.reimbursed_amount += invoice.amount`, `event.remaining_budget = event.total_budget - event.reimbursed_amount`

---

### 3.6 单张发票报销
```
POST /api/invoices/<invoice_id>/reimburse
```
**需认证**，权限: admin / teacher

> 只能报销 `status=approved` 且 `is_reimbursed=false` 的发票

---

### 3.7 批量报销发票
```
POST /api/invoices/batch-reimburse
```
**需认证**，权限: admin / teacher

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| invoice_ids | int[] | 是 | 发票ID列表 |

**响应** `200`:
```json
{ "code": 200, "message": "成功报销 3 张发票", "data": { "count": 3 } }
```

---

### 3.8 获取发票预览图
```
GET /api/invoices/<invoice_id>/preview
```
**需认证**

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "preview_url": "https://cos.example.com/...",
    "has_preview": true
  }
}
```

---

### 3.9 生成发票预览图
```
POST /api/invoices/<invoice_id>/generate-preview
```
**需认证**

> PDF 文件直接用原文件作为预览；图片格式直接使用原图。

---

### 3.10 下载发票文件
```
GET /api/invoices/<invoice_id>/download
```
**需认证**

> 直接返回文件流（Content-Disposition: attachment）

---

## 4. 购买记录 (Purchase Records) — `/api`

### 4.1 获取购买记录列表
```
GET /api/events/<event_id>/records
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| uploader_id | int | 否 | 按上传人筛选 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "record_id": 1,
        "event_id": 1,
        "item_name": "电机驱动模块",
        "purchase_platform": "淘宝",
        "purchase_date": "2025-05-01",
        "amount": 150.00,
        "receipt_image_url": "https://cos.example.com/...",
        "receipt_image_name": "receipt.jpg",
        "cannot_invoice": false,
        "has_invoice": true,
        "invoice_file_key": "invoices/abc123.pdf",
        "invoice_preview_key": "invoices/abc123_preview.jpg",
        "invoice_url": "https://cos.example.com/...",
        "invoice_preview_url": "https://cos.example.com/...",
        "invoice_original_filename": "invoice.pdf",
        "invoice_type": "增值税电子普通发票",
        "invoice_number": "12345678",
        "total_amount": 150.00,
        "invoice_date": "2025-05-02",
        "status": "approved",
        "is_reimbursed": false,
        "remarks": null,
        "uploader_id": 1,
        "uploader_name": "张三",
        "reviewer_name": "李老师",
        "created_at": "2025-05-01T12:00:00+00:00",
        "rejection_reason": null
      }
    ],
    "total_count": 5,
    "total_amount": "750.00",
    "invoice_total": "150.00",
    "pending_reimburse": "150.00"
  }
}
```

---

### 4.2 创建购买记录
```
POST /api/events/<event_id>/records
```
**需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| item_name | string | 是 | 物品名称 |
| purchase_platform | string | 是 | 购买平台（淘宝/京东/拼多多等） |
| purchase_date | string | 是 | 购买日期 (YYYY-MM-DD) |
| amount | number | 是 | 金额 |
| receipt_image_url | string | 是 | 购物凭证图片URL（需先通过 upload-file 上传获取） |
| receipt_image_name | string | 否 | 凭证文件名 |
| receipt_file_md5 | string | 否 | 凭证文件MD5 |
| cannot_invoice | bool | 否 | 是否无法开发票 |
| invoice_file_key | string | 否 | 发票文件key（有发票时） |
| invoice_preview_key | string | 否 | 发票预览key |
| invoice_original_filename | string | 否 | 发票原始文件名 |
| invoice_md5 | string | 否 | 发票MD5 |
| invoice_type | string | 否 | 发票类型 |
| invoice_number | string | 否 | 发票号码 |
| total_amount | number | 否 | 发票价税合计 |
| invoice_date | string | 否 | 开票日期 |
| remarks | string | 否 | 备注 |

> 若有发票且 total_amount > 0，则实际 amount 以 total_amount 为准（发票解析结果优先）

**响应** `201`:
```json
{
  "code": 200,
  "message": "购买记录创建成功",
  "data": {
    "record_id": 1,
    "item_name": "电机驱动模块",
    "has_invoice": true
  }
}
```

---

### 4.3 更新购买记录
```
PUT /api/records/<record_id>
```
**需认证**，权限：admin/teacher/student_admin 或上传者本人。学生需是项目成员。

请求体（JSON，所有字段可选，与创建参数相同）:
```json
{
  "item_name": "新物品名",
  "amount": 200.00,
  "remarks": "更新备注",
  "uploader_id": 3
}
```

> `uploader_id` 仅 admin/teacher/student_admin 可修改。
> 有发票时 amount 自动以 total_amount 为准。

---

### 4.4 删除购买记录（软删除）
```
DELETE /api/records/<record_id>
```
**需认证**，权限：admin/teacher/student_admin 或上传者本人。

---

### 4.5 报销购买记录
```
POST /api/records/<record_id>/reimburse
```
**需认证**，权限: admin / teacher / student_admin

> 仅限 `has_invoice=true` 且 `is_reimbursed=false` 的记录

---

### 4.6 下载购买记录关联的发票文件
```
GET /api/records/<record_id>/download-invoice
```
**需认证**，返回文件流

---

### 4.8 获取购买记录发票预览URL
```
GET /api/records/<record_id>/preview-invoice
```
**需认证**

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "preview_url": "https://cos.example.com/...",
    "is_pdf": true
  }
}
```

---

### 4.9 重新解析发票（AI）
```
POST /api/records/<record_id>/re-parse-invoice
```
**需认证**

> 对已上传的发票文件重新调用 AI 视觉模型解析，返回解析结果

**响应** `200`:
```json
{
  "code": 200,
  "message": "重新解析成功",
  "data": {
    "parsed_info": {
      "item_name": "机器人配件",
      "invoice_number": "12345678",
      "amount": 500.00,
      "date": "2025-05-01"
    },
    "extraction_method": "glm_vision"
  }
}
```

---

## 5. 凭证管理 (Vouchers) — `/api`

### 5.1 获取凭证列表
```
GET /api/vouchers
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| event_id | int | 是 | 赛事ID |
| page | int | 否 | 默认 1 |
| page_size | int | 否 | 默认 20 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "data": [
      {
        "voucher_id": 1,
        "event_id": 1,
        "uploader_id": 1,
        "uploader_name": "张三",
        "file_name": "receipt.jpg",
        "item_name": "餐饮费",
        "voucher_type": "餐饮",
        "purchase_channel": "美团",
        "purchase_date": "2025-05-01",
        "amount": 100.00,
        "is_reimbursed": false,
        "reimbursed_at": null,
        "remarks": null,
        "created_at": "2025-05-01T12:00:00+00:00",
        "record_type": "voucher",
        "file_url": "https://cos.example.com/..."
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 5.2 创建凭证
```
POST /api/vouchers
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 凭证文件（pdf/png/jpg/jpeg） |
| event_id | int | 是 | 赛事ID |
| item_name | string | 是 | 物品/服务名称 |
| voucher_type | string | 否 | 凭证类型 |
| purchase_channel | string | 否 | 购买渠道 |
| purchase_date | string | 否 | 购买日期 (YYYY-MM-DD) |
| amount | number | 否 | 金额，默认 0 |
| remarks | string | 否 | 备注 |

---

### 5.3 更新凭证
```
PUT /api/vouchers/<voucher_id>
```
**需认证**

请求体（JSON，所有字段可选）:
```json
{
  "item_name": "新名称",
  "voucher_type": "交通",
  "purchase_channel": "滴滴",
  "purchase_date": "2025-06-01",
  "amount": 50.00,
  "remarks": "更新备注"
}
```

> 修改 amount 时会自动更新对应赛事的 `voucher_total_amount`

---

### 5.4 删除凭证（软删除）
```
DELETE /api/vouchers/<voucher_id>
```
**需认证**，权限：admin/teacher 或上传者本人

---

### 5.5 下载凭证文件
```
GET /api/vouchers/<voucher_id>/download
```
**需认证**，返回文件流

---

### 5.6 批量报销凭证
```
POST /api/vouchers/batch-reimburse
```
**需认证**，权限: admin / teacher

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| voucher_ids | int[] | 是 | 凭证ID列表 |

---

### 5.7 检查文件MD5是否重复
```
GET /api/check-file-md5
```
**需认证**

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| md5 | string | 是 | 文件MD5值 |
| event_id | string | 否 | 赛事ID |

> 同时检查 PurchaseRecord 的 receipt_file_md5 和 Voucher 的 file_md5

**响应**:
```json
{
  "code": 200,
  "message": "找到重复文件",
  "data": {
    "exists": true,
    "uploader_name": "张三",
    "upload_time": "2025-05-01T12:00:00+00:00",
    "file_name": "receipt.jpg",
    "type": "receipt"
  }
}
```

---

## 6. 文件上传与AI解析 (Parse) — `/api`

### 6.1 通用文件上传（不解析）
```
POST /api/upload-file
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 文件（pdf/png/jpg/jpeg） |

**响应** `200`:
```json
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "image_url": "https://cos.example.com/...",
    "file_key": "invoices/uuid123.pdf",
    "preview_url": "https://cos.example.com/...",
    "file_md5": "d41d8cd98f00b204e9800998ecf8427e",
    "original_filename": "invoice.pdf",
    "file_type": "pdf"
  }
}
```

---

### 6.2 发票解析+上传（完整流程）
```
POST /api/parse-invoice
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 发票文件（pdf/png/jpg/jpeg） |
| preview_file | file | 否 | 客户端预生成的预览图（PDF场景） |

> 自动完成：
> 1. MD5 去重检查
> 2. PDF → JPG 转换（服务端 PyMuPDF 渲染）
> 3. 上传原始文件和预览图到 COS / 本地存储
> 4. 调用 AI 视觉模型解析发票信息

**响应** `200`:
```json
{
  "code": 200,
  "message": "解析完成",
  "data": {
    "file_key": "invoices/uuid123.pdf",
    "preview_key": "invoices/uuid123_preview.jpg",
    "file_url": "https://cos.example.com/...",
    "preview_url": "https://cos.example.com/...",
    "original_filename": "invoice.pdf",
    "file_type": "pdf",
    "is_pdf": true,
    "pdf_page_count": 1,
    "file_md5": "d41d8cd98f00b204e9800998ecf8427e",
    "parsed_info": {
      "item_name": "机器人配件",
      "invoice_number": "12345678",
      "amount": 500.00,
      "date": "2025-05-01"
    },
    "extraction_method": "glm_vision"
  }
}
```

---

### 6.3 仅解析图片（不上传）
```
POST /api/parse-image
```
**需认证**，multipart/form-data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件（不含PDF） |

> 仅调用 AI 解析，不上传存储。用于客户端已将 PDF 转图片后的场景。

**响应** `200`:
```json
{
  "code": 200,
  "message": "解析完成",
  "data": {
    "parsed_info": {
      "item_name": "...",
      "invoice_number": "...",
      "amount": 500.00,
      "date": "2025-05-01"
    },
    "filename": "invoice.jpg"
  }
}
```

---

### 6.4 获取发票预览URL（按文件key）
```
GET /api/invoices/<path:file_key>/preview
```
**需认证**

> `file_key` 为 URL 编码的路径，如 `invoices/uuid123_preview.jpg`

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": { "preview_url": "https://cos.example.com/..." }
}
```

---

### 6.5 下载发票文件（按文件key）
```
GET /api/invoices/<path:file_key>/download
```
**需认证**，返回文件流

---

## 7. 邀请码管理 (Invitation Codes) — `/api`

### 7.1 获取邀请码列表
```
GET /api/invitation-codes
```
**需认证**，权限: admin / teacher / student_admin

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| page | int | 否 | 默认 1 |
| page_size | int | 否 | 默认 20 |

> teacher 只能看到自己创建的邀请码

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "data": [
      {
        "id": 1,
        "code": "TCH-202506011200-ABCD1234",
        "target_user_type": "teacher",
        "target_user_type_text": "老师",
        "expires_at": "2025-07-01T12:00:00+00:00",
        "max_uses": 5,
        "used_count": 2,
        "created_by": 1,
        "creator_name": "系统管理员",
        "is_active": true,
        "status": "active",
        "created_at": "2025-06-01T12:00:00+00:00"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 7.2 创建邀请码
```
POST /api/invitation-codes
```
**需认证**，权限: admin / teacher / student_admin

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_user_type | string | 否 | 目标角色，默认 `student` |
| expires_days | int | 否 | 有效期天数，默认 30，范围 1-365 |
| max_uses | int | 否 | 最大使用次数，-1 表示不限，默认 -1 |
| quantity | int | 否 | 生成数量，默认 1，范围 1-20 |

**权限约束**:
- `student_admin` 只能生成 `student` / `student_admin` 类型
- `teacher` 不能生成 `admin` 类型

**响应** `200`:
```json
{
  "code": 200,
  "message": "成功生成 3 个邀请码",
  "data": {
    "codes": [
      {
        "code": "STU-202506011200-XYZ789",
        "target_user_type": "student",
        "expires_at": "2025-07-01T12:00:00+00:00"
      }
    ],
    "count": 3
  }
}
```

---

### 7.3 验证邀请码
```
POST /api/invitation-codes/verify
```
**无需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 邀请码 |

**响应** `200`:
```json
{
  "code": 200,
  "message": "邀请码有效",
  "data": {
    "valid": true,
    "target_user_type": "student"
  }
}
```

无效时:
```json
{ "code": 200, "message": "该邀请码已过期", "data": { "valid": false, "reason": "expired" } }
```

---

### 7.4 启用/禁用邀请码
```
POST /api/invitation-codes/<code_id>/toggle
```
**需认证**，权限: admin / teacher / student_admin

> teacher 只能操作自己创建的邀请码

**响应**:
```json
{ "code": 200, "message": "邀请码已启用", "data": { "is_active": true } }
```

---

### 7.5 删除邀请码（硬删除）
```
DELETE /api/invitation-codes/<code_id>
```
**需认证**，仅 admin

---

## 8. 数据导出 (Export) — `/api`

### 8.1 创建导出任务
```
POST /api/events/<event_id>/export
```
**需认证**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| columns | string[] | 是 | 要导出的列名列表 |
| options | object | 否 | 导出选项 |

**可选列名**:
| key | 中文名 |
|-----|--------|
| `item_name` | 名称 |
| `purchase_platform` | 购买平台 |
| `amount` | 金额 |
| `purchase_date` | 购物日期 |
| `invoice_date` | 开票日期 |
| `uploader` | 上传人 |
| `invoice_tax_number` | 发票税号 |
| `receipt_image` | 购物图片 |
| `invoice_image` | 发票图片 |

**options**:
```json
{
  "only_mine": false
}
```

> 导出为异步后台任务，创建后返回 task_id

**响应** `200`:
```json
{
  "code": 200,
  "message": "导出任务已创建",
  "data": {
    "task_id": 1,
    "status": "pending"
  }
}
```

---

### 8.2 查询导出任务状态
```
GET /api/events/<event_id>/export/status?task_id=<task_id>
```
**需认证**

**响应** `200`:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": 1,
    "status": "completed",
    "progress_percent": 100,
    "progress_message": "导出完成",
    "record_count": 50,
    "file_size": 1048576,
    "created_at": "2025-06-01 12:00:00",
    "completed_at": "2025-06-01 12:00:30",
    "error_message": null
  }
}
```

> status 枚举: `pending` → `processing` → `completed` / `failed`

---

### 8.3 下载导出文件
```
GET /api/events/<event_id>/export/download?task_id=<task_id>
```
**需认证**

> 仅 `status=completed` 且文件未过期时可下载。直接返回文件流（.xlsx 或 .zip）。

---

## 9. 系统管理 (System) — `/api`

### 9.1 获取系统配置
```
GET /api/system/config
```
**需认证**，仅 admin

> 敏感值（ai_api_key）会被脱敏显示（前4位+后4位，中间 `*`）

**响应** `200`:
```json
{
  "code": 200,
  "data": {
    "ai_model": { "value": "glm-4.6v-flash", "is_encrypted": false, "description": "", "updated_at": "...", "has_value": true },
    "ai_api_key": { "value": "sk-1****b2c3", "is_encrypted": true, "description": "", "updated_at": "...", "has_value": true },
    "ai_api_url": { "value": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "is_encrypted": false, "description": "", "updated_at": "...", "has_value": true },
    "_version": { "value": "1.0.0" }
  }
}
```

---

### 9.2 更新系统配置
```
PUT /api/system/config
```
**需认证**，仅 admin

**允许的 key**: `ai_model`, `ai_api_key`, `ai_api_url`

请求体:
```json
{
  "configs": {
    "ai_model": "glm-4-flash",
    "ai_api_key": "sk-new-key",
    "ai_api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
  }
}
```

> `ai_api_key` 自动加密存储

**响应**:
```json
{
  "code": 200,
  "message": "配置保存成功",
  "data": { "updated_keys": ["ai_model", "ai_api_key"] }
}
```

---

### 9.3 检查更新
```
GET /api/system/check-update
```
**需认证**，仅 admin

> 查询 GitHub Releases 获取最新版本号，与当前 VERSION 比较

**响应** `200`:
```json
{
  "code": 200,
  "data": {
    "current_version": "1.0.0",
    "latest_version": "1.1.0",
    "has_update": true,
    "update_info": {
      "version": "1.1.0",
      "release_name": "v1.1.0",
      "release_notes": "...",
      "download_url": "https://github.com/Ljinzhou/EasyInvoiceMgr/releases/tag/v1.1.0",
      "published_at": "2025-06-01T00:00:00Z"
    },
    "update_commands": { ... },
    "manual_steps": { ... }
  }
}
```

---

### 9.4 测试AI模型连通性
```
POST /api/system/test-model
```
**需认证**，仅 admin

> 用当前配置的模型和 API Key 发送一条简单测试消息

**响应** `200`:
```json
{
  "code": 200,
  "message": "模型连接测试成功",
  "data": {
    "model": "glm-4.6v-flash",
    "latency_ms": 1234,
    "reply": "连接测试成功"
  }
}
```

---

### 9.5 手动触发备份
```
POST /api/system/backup
```
**需认证**，仅 admin

> 异步执行全量备份任务

**响应** `200`:
```json
{
  "code": 200,
  "message": "备份任务已创建",
  "data": { "id": 1, "status": "pending" }
}
```

---

### 9.6 获取备份记录列表
```
GET /api/system/backups
```
**需认证**，仅 admin

| Query 参数 | 类型 | 必填 | 说明 |
|------------|------|------|------|
| page | int | 否 | 默认 1 |
| per_page | int | 否 | 默认 20，最大 100 |

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "backup_type": "manual",
        "backup_scope": "full",
        "status": "completed",
        "progress": 100,
        "progress_message": "备份完成",
        "file_size": 10485760,
        "file_count": 50,
        "error_message": null,
        "created_at": "2025-06-01T12:00:00+00:00",
        "completed_at": "2025-06-01T12:01:00+00:00",
        "created_by_name": "系统管理员"
      }
    ],
    "total": 5,
    "page": 1,
    "per_page": 20
  }
}
```

---

### 9.7 下载备份文件
```
GET /api/system/backup/<backup_id>/download
```
**需认证**，仅 admin，返回文件流

---

### 9.8 删除备份
```
DELETE /api/system/backup/<backup_id>
```
**需认证**，仅 admin

> 同时删除数据库记录和备份文件

---

### 9.9 从备份恢复
```
POST /api/system/backup/restore/<backup_id>
```
**需认证**，仅 admin

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| confirm | bool | 是 | 必须为 `true`，防止误操作 |

**响应**:
```json
{ "code": 200, "message": "恢复任务已启动", "data": { "backup_id": 1 } }
```

---

### 9.10 获取定时备份配置
```
GET /api/system/backup/config
```
**需认证**，仅 admin

**响应**:
```json
{
  "code": 200,
  "data": {
    "enabled": true,
    "frequency": "daily",
    "time": "03:00",
    "retention_count": 10
  }
}
```

---

### 9.11 更新定时备份配置
```
PUT /api/system/backup/config
```
**需认证**，仅 admin

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| enabled | bool | 是 | 是否启用 |
| frequency | string | 是 | `daily` / `weekly` / `monthly` |
| time | string | 是 | 执行时间 `HH:MM` |
| retention_count | int | 是 | 保留备份数量，1-100 |

**响应**:
```json
{ "code": 200, "message": "备份配置已保存" }
```

---

## 10. 数据模型速览

### User（用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | bigint (PK) | 自增 |
| username | varchar(50) | 唯一 |
| password_hash | varchar(255) | werkzeug hash |
| real_name | varchar(50) | |
| email | varchar(100) | 唯一 |
| phone | varchar(20) | |
| user_type | varchar(20) | admin/teacher/student_admin/student |
| organization | varchar(100) | |
| student_or_staff_id | varchar(50) | 学号/工号 |
| avatar_url | text | |
| account_status | varchar(20) | active/disabled |
| register_time | timestamptz | |
| last_login_time | timestamptz | |
| extra_fields | json | |
| is_deleted | bool | 软删除 |

### Event（赛事/项目）
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | bigint (PK) | |
| event_name | varchar(200) | |
| description | text | |
| status | varchar(20) | ongoing/completed |
| event_start_time | timestamptz | |
| event_end_time | timestamptz | |
| upload_start_time | timestamptz | 上传窗口开始 |
| upload_end_time | timestamptz | 上传窗口结束 |
| creator_id | bigint (FK→users) | |
| leader_id | bigint (FK→users) | 负责人 |
| total_budget | numeric(12,2) | |
| reimbursed_amount | numeric(12,2) | |
| remaining_budget | numeric(12,2) | |
| invoice_count | int | |
| invoice_total_amount | numeric(12,2) | |
| purchase_record_count | int | |
| voucher_count | int | |
| voucher_total_amount | numeric(12,2) | |
| extra_fields | json | |
| is_deleted | bool | |

### Invoice（发票）
| 字段 | 类型 | 说明 |
|------|------|------|
| invoice_id | bigint (PK) | |
| event_id | bigint (FK→events) | |
| uploader_id | bigint (FK→users) | |
| file_name | varchar(255) | |
| file_md5 | varchar(64) | 去重用 |
| image_url | text | 文件存储路径/key |
| preview_image_url | text | 预览图路径 |
| invoice_type | varchar(50) | |
| invoice_number | varchar(50) | |
| project_name | varchar(200) | |
| amount | numeric(12,2) | |
| total_amount | numeric(12,2) | 价税合计 |
| invoice_date | date | |
| status | varchar(20) | pending/approved/rejected |
| is_reimbursed | bool | |
| reimbursed_at | timestamptz | |
| reviewer_id | bigint (FK→users) | |
| review_time | timestamptz | |
| rejection_reason | text | |
| remarks | text | |
| is_deleted | bool | |
| extra_fields | json | |

### PurchaseRecord（购买记录）
| 字段 | 类型 | 说明 |
|------|------|------|
| record_id | bigint (PK) | |
| event_id | bigint (FK→events) | |
| uploader_id | bigint (FK→users) | |
| item_name | varchar(200) | 物品名称 |
| purchase_platform | varchar(100) | 购买平台 |
| purchase_date | date | |
| amount | numeric(12,2) | 金额 |
| receipt_image_url | text | 购物凭证图片 |
| receipt_image_name | varchar(255) | |
| receipt_file_md5 | varchar(64) | |
| cannot_invoice | bool | 无法开发票 |
| has_invoice | bool | 是否有关联发票 |
| invoice_file_key | text | 发票文件key |
| invoice_preview_key | text | |
| invoice_original_filename | varchar(255) | |
| invoice_md5 | varchar(64) | |
| invoice_type | varchar(50) | |
| invoice_number | varchar(50) | |
| invoice_tax_number | varchar(50) | 税号 |
| total_amount | numeric(12,2) | 发票价税合计 |
| invoice_date | date | |
| status | varchar(20) | pending/approved/rejected |
| is_reimbursed | bool | |
| reimbursed_at | timestamptz | |
| reviewer_id | bigint (FK→users) | |
| review_time | timestamptz | |
| rejection_reason | text | |
| remarks | text | |
| is_deleted | bool | |
| extra_fields | json | |

### Voucher（凭证）
| 字段 | 类型 | 说明 |
|------|------|------|
| voucher_id | bigint (PK) | |
| event_id | bigint (FK→events) | |
| uploader_id | bigint (FK→users) | |
| file_name | varchar(255) | |
| file_md5 | varchar(64) | |
| file_url | text | |
| item_name | varchar(200) | |
| voucher_type | varchar(50) | |
| purchase_channel | varchar(100) | |
| purchase_date | date | |
| amount | numeric(12,2) | |
| is_reimbursed | bool | |
| reimbursed_at | timestamptz | |
| remarks | text | |
| is_deleted | bool | |

### EventMember（赛事成员关联）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint (PK) | |
| event_id | bigint (FK→events) | |
| user_id | bigint (FK→users) | |
| role_in_event | varchar(20) | student/student_admin/teacher |
| join_time | timestamptz | |
| is_deleted | bool | |

> 唯一约束: (event_id, user_id)

### InvitationCode（邀请码）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint (PK) | |
| code | varchar(64) | 唯一，索引 |
| target_user_type | varchar(20) | |
| expires_at | timestamptz | |
| max_uses | int | -1不限 |
| used_count | int | |
| created_by | bigint (FK→users) | |
| is_active | bool | |

### SystemConfig（系统配置）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint (PK) | |
| config_key | varchar(128) | 唯一，索引 |
| config_value | text | |
| is_encrypted | bool | 是否加密存储 |
| description | varchar(255) | |
| updated_by | bigint (FK→users) | |

### ExportTask（导出任务）
| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | bigint (PK) | |
| event_id | bigint (FK→events) | |
| requester_id | bigint (FK→users) | |
| status | varchar(20) | pending/processing/completed/failed |
| columns_config | json | |
| file_path | text | |
| file_size | bigint | |
| data_snapshot_time | timestamptz | |
| record_count | int | |
| error_message | text | |
| progress_percent | int | 0-100 |
| progress_message | varchar(200) | |
| completed_at | timestamptz | |
| expires_at | timestamptz | |

### BackupRecord（备份记录）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint (PK) | |
| backup_type | varchar(20) | manual/scheduled/restore |
| backup_scope | varchar(20) | full/database |
| status | varchar(20) | pending/running/completed/failed |
| progress | int | 0-100 |
| progress_message | varchar(200) | |
| file_path | text | |
| file_size | bigint | |
| file_count | int | |
| error_message | text | |
| created_by | bigint (FK→users) | 定时备份时为 NULL |
| completed_at | timestamptz | |

---

## 附录: 接口路由汇总表

| # | 方法 | 路径 | 认证 | 权限 | 说明 |
|---|------|------|------|------|------|
| 1 | POST | `/api/auth/register` | ❌ | - | 用户注册 |
| 2 | POST | `/api/auth/login` | ❌ | - | 用户登录 |
| 3 | GET | `/api/auth/users` | ✅ | A/T/SA | 用户列表 |
| 4 | GET | `/api/auth/users/<id>` | ✅ | 本人 | 用户详情 |
| 5 | PUT | `/api/auth/users/<id>` | ✅ | A/本人 | 更新用户 |
| 6 | PUT | `/api/auth/users/<id>/password` | ✅ | 本人 | 修改密码 |
| 7 | DELETE | `/api/auth/users/<id>` | ✅ | A | 删除用户 |
| 8 | GET | `/api/auth/avatar` | ✅ | - | 获取头像 |
| 9 | POST | `/api/auth/avatar/upload` | ✅ | - | 上传头像 |
| 10 | DELETE | `/api/auth/avatar` | ✅ | - | 删除头像 |
| 11 | POST | `/api/events` | ✅ | - | 创建赛事 |
| 12 | GET | `/api/events` | ✅ | - | 赛事列表 |
| 13 | GET | `/api/events/<id>` | ✅ | - | 赛事详情 |
| 14 | PUT | `/api/events/<id>` | ✅ | A/T/SA | 更新赛事 |
| 15 | DELETE | `/api/events/<id>` | ✅ | A/T/SA | 删除赛事 |
| 16 | GET | `/api/events/<id>/members` | ✅ | - | 成员列表 |
| 17 | POST | `/api/events/<id>/members` | ✅ | A/T/SA | 添加成员 |
| 18 | PUT | `/api/events/<id>/members/<uid>` | ✅ | A/T/SA | 更新成员角色 |
| 19 | DELETE | `/api/events/<id>/members/<uid>` | ✅ | A/T/SA | 移除成员 |
| 20 | GET | `/api/events/stats/user-summary` | ✅ | - | 消费排名 |
| 21 | GET | `/api/invoices` | ✅ | - | 发票列表 |
| 22 | POST | `/api/invoices` | ✅ | - | 上传发票 |
| 23 | PUT | `/api/invoices/<id>` | ✅ | - | 更新发票 |
| 24 | DELETE | `/api/invoices/<id>` | ✅ | A/T/本人 | 删除发票 |
| 25 | POST | `/api/invoices/<id>/approve` | ✅ | A/T/SA | 审核发票 |
| 26 | POST | `/api/invoices/<id>/reimburse` | ✅ | A/T | 报销发票 |
| 27 | POST | `/api/invoices/batch-reimburse` | ✅ | A/T | 批量报销 |
| 28 | GET | `/api/invoices/<id>/preview` | ✅ | - | 预览图 |
| 29 | POST | `/api/invoices/<id>/generate-preview` | ✅ | - | 生成预览 |
| 30 | GET | `/api/invoices/<id>/download` | ✅ | - | 下载文件 |
| 31 | GET | `/api/events/<id>/records` | ✅ | - | 购买记录列表 |
| 32 | POST | `/api/events/<id>/records` | ✅ | - | 创建购买记录 |
| 33 | PUT | `/api/records/<id>` | ✅ | A/T/SA/本人 | 更新记录 |
| 34 | DELETE | `/api/records/<id>` | ✅ | A/T/SA/本人 | 删除记录 |
| 35 | POST | `/api/records/<id>/approve` | ✅ | A/T/SA | 审核记录 |
| 36 | POST | `/api/records/<id>/reimburse` | ✅ | A/T/SA | 报销记录 |
| 37 | GET | `/api/records/<id>/download-invoice` | ✅ | - | 下载关联发票 |
| 38 | GET | `/api/records/<id>/preview-invoice` | ✅ | - | 发票预览URL |
| 39 | POST | `/api/records/<id>/re-parse-invoice` | ✅ | - | 重新AI解析 |
| 40 | GET | `/api/vouchers` | ✅ | - | 凭证列表 |
| 41 | POST | `/api/vouchers` | ✅ | - | 创建凭证 |
| 42 | PUT | `/api/vouchers/<id>` | ✅ | - | 更新凭证 |
| 43 | DELETE | `/api/vouchers/<id>` | ✅ | A/T/本人 | 删除凭证 |
| 44 | GET | `/api/vouchers/<id>/download` | ✅ | - | 下载凭证 |
| 45 | POST | `/api/vouchers/batch-reimburse` | ✅ | A/T | 批量报销凭证 |
| 46 | GET | `/api/check-file-md5` | ✅ | - | MD5查重 |
| 47 | POST | `/api/upload-file` | ✅ | - | 通用文件上传 |
| 48 | POST | `/api/parse-invoice` | ✅ | - | 解析+上传发票 |
| 49 | POST | `/api/parse-image` | ✅ | - | 仅解析图片 |
| 50 | GET | `/api/invoices/<key>/preview` | ✅ | - | 按key获取预览 |
| 51 | GET | `/api/invoices/<key>/download` | ✅ | - | 按key下载文件 |
| 52 | GET | `/api/invitation-codes` | ✅ | A/T/SA | 邀请码列表 |
| 53 | POST | `/api/invitation-codes` | ✅ | A/T/SA | 创建邀请码 |
| 54 | POST | `/api/invitation-codes/verify` | ❌ | - | 验证邀请码 |
| 55 | POST | `/api/invitation-codes/<id>/toggle` | ✅ | A/T/SA | 启禁邀请码 |
| 56 | DELETE | `/api/invitation-codes/<id>` | ✅ | A | 删除邀请码 |
| 57 | POST | `/api/events/<id>/export` | ✅ | - | 创建导出任务 |
| 58 | GET | `/api/events/<id>/export/status` | ✅ | - | 导出状态查询 |
| 59 | GET | `/api/events/<id>/export/download` | ✅ | - | 下载导出文件 |
| 60 | GET | `/api/system/config` | ✅ | A | 获取系统配置 |
| 61 | PUT | `/api/system/config` | ✅ | A | 更新系统配置 |
| 62 | GET | `/api/system/check-update` | ✅ | A | 检查更新 |
| 63 | POST | `/api/system/test-model` | ✅ | A | 测试AI模型 |
| 64 | POST | `/api/system/backup` | ✅ | A | 手动备份 |
| 65 | GET | `/api/system/backups` | ✅ | A | 备份列表 |
| 66 | GET | `/api/system/backup/<id>/download` | ✅ | A | 下载备份 |
| 67 | DELETE | `/api/system/backup/<id>` | ✅ | A | 删除备份 |
| 68 | POST | `/api/system/backup/restore/<id>` | ✅ | A | 恢复备份 |
| 69 | GET | `/api/system/backup/config` | ✅ | A | 备份配置 |
| 70 | PUT | `/api/system/backup/config` | ✅ | A | 更新备份配置 |

> 角色缩写: A=admin, T=teacher, SA=student_admin, 本人=上传者/所属用户

---

## 附录 B: 文件存储后端

系统支持两种文件存储，通过 `STORAGE_BACKEND` 环境变量切换:

| 值 | 说明 |
|----|------|
| `local` | 本地存储，文件存于 `backend/uploads/`，通过 `/uploads/<path>` 访问 |
| `cos` | 腾讯云 COS，需配置 `COS_SECRET_ID`, `COS_SECRET_KEY`, `COS_REGION`, `COS_BUCKET` |

所有文件访问 URL 通过**预签名URL**生成（COS）或直接返回本地路径。

---

## 附录 C: AI 发票解析流程

```
上传发票文件
  ├── PDF 文件
  │   ├── PyMuPDF 渲染为 JPG
  │   ├── 上传原始 PDF 到存储
  │   ├── 上传 JPG 预览图到存储
  │   └── 用 JPG 调用 GLM-4V 视觉模型
  └── 图片文件 (PNG/JPG)
      ├── 直接上传到存储
      └── 直接调用 GLM-4V 视觉模型

AI 返回解析结果:
  - project_name → 物品名称
  - invoice_number → 发票号码
  - total_amount → 价税合计
  - invoice_date → 开票日期
```

> PDF 也支持 PyPDF2 直接文本提取 + 正则解析（无 AI 时的降级方案）
