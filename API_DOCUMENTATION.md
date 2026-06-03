# EasyInvoiceMgr API 接口文档

> 本文档完整记录了 EasyInvoiceMgr 前后端通信的所有 RESTful API 接口，供后端技术框架迁移时使用。
>
> **当前后端**: Flask + SQLAlchemy + JWT
> **当前前端**: Nuxt 3 + Axios
> **API Base URL**: `http://localhost:5000/api`
> **认证方式**: JWT Bearer Token（Header: `Authorization: Bearer <token>`）
> **响应格式**: 统一 JSON `{ code: number, message: string, data: any }`

---

## 目录

1. [通用说明](#通用说明)
2. [认证模块 - Auth](#1-认证模块---auth)
3. [赛事/项目管理 - Events](#2-赛事项目管理---events)
4. [购买记录 - Purchase Records](#3-购买记录---purchase-records)
5. [发票管理 - Invoices](#4-发票管理---invoices)
6. [凭证管理 - Vouchers](#5-凭证管理---vouchers)
7. [文件上传/解析 - Parse](#6-文件上传解析---parse)
8. [邀请码管理 - Invitation Codes](#7-邀请码管理---invitation-codes)
9. [系统配置 - System](#8-系统配置---system)
10. [导出管理 - Export](#9-导出管理---export)
11. [静态文件服务](#10-静态文件服务)
12. [数据模型参考](#11-数据模型参考)

---

## 通用说明

### 认证

```
Header: Authorization: Bearer <JWT_TOKEN>
```

- JWT Token 在 `/auth/login` 成功后获取
- 支持从 Header 和 Query String（`?token=xxx`）两种方式传递
- 未登录返回 `401`，权限不足返回 `403`

### 通用响应格式

```typescript
interface ApiResponse<T = any> {
  code: number    // 200=成功, 400=参数错误, 401=未登录, 403=权限不足, 404=不存在, 500=服务端错误
  message: string  // 提示信息
  data: T | null  // 响应数据
}
```

### 用户角色层级

| 角色 | `user_type` | 权限说明 |
|------|-------------|---------|
| 管理员 | `admin` | 所有权限 |
| 教师 | `teacher` | 管理赛事、发票审核、查看全局 |
| 学生管理员 | `student_admin` | 审核发票、管理学生、管理赛事成员 |
| 学生 | `student` | 上传凭证、查看自己的赛事 |

### 数据状态约定

- **软删除**: 所有实体使用 `is_deleted` 字段标记删除，不做物理删除
- **发票/购买记录审核状态**: `pending` → `approved` / `rejected`
- **赛事状态**: `ongoing` / `finished`

---

## 1. 认证模块 - Auth

**Blueprint Prefix**: `/api/auth`

### 1.1 用户注册

```
POST /api/auth/register
```

**Auth**: 无需认证

**Request Body**:
```typescript
{
  username: string           // 必填
  password: string           // 必填
  real_name: string          // 必填
  email?: string
  phone?: string
  user_type?: 'student' | 'teacher' | 'student_admin'  // 默认 'student'
  student_or_staff_id?: string
  invitation_code?: string   // 邀请码（可选但推荐）
}
```

**Response** (201):
```typescript
{
  code: 200,
  message: "success",
  data: {
    user_id: number
    username: string
    real_name: string
    email: string | null
    phone: string | null
    user_type: string
    student_or_staff_id: string | null
    account_status: "active"
  }
}
```

**错误码**: `1001` 用户名已存在, `1002` 邮箱已注册, 邀请码相关错误见 7.3

---

### 1.2 用户登录

```
POST /api/auth/login
```

**Auth**: 无需认证

**Request Body**:
```typescript
{
  username: string   // 必填
  password: string   // 必填
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    token: string    // JWT token, 前端存储在 localStorage('token')
    user: {
      user_id: number
      username: string
      real_name: string
      email: string | null
      phone: string | null
      user_type: string
      student_or_staff_id: string | null
      avatar_url: string | null
    }
  }
}
```

**错误码**: `1002` 用户名或密码错误, `1003` 账户已被禁用

**前端存储**:
- `localStorage.setItem('token', token)`
- `localStorage.setItem('user', JSON.stringify(user))`

---

### 1.3 获取用户列表

```
GET /api/auth/users
```

**Auth**: 需要登录，仅 `admin` / `teacher` / `student_admin` 可调用

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `search` | string | 否 | 搜索用户名/真实姓名/邮箱（模糊匹配）|
| `user_type` | string | 否 | 按用户类型筛选 |
| `page` | number | 否 | 页码（默认 1） |
| `page_size` | number | 否 | 每页条数（默认 10） |

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    total: number
    page: number
    page_size: number
    data: Array<{
      user_id: number
      username: string
      real_name: string
      email: string | null
      phone: string | null
      user_type: string
      student_or_staff_id: string | null
      account_status: string
      register_time: string  // ISO datetime
      avatar_url: string | null
    }>
  }
}
```

---

### 1.4 获取单个用户信息

```
GET /api/auth/users/:user_id
```

**Auth**: 需要登录，仅能获取自己的信息（`current_user_id === user_id`）

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    user_id: number
    username: string
    real_name: string
    email: string | null
    phone: string | null
    user_type: string
    student_or_staff_id: string | null
    avatar_url: string | null
    account_status: string
    register_time: string   // ISO datetime
    last_login_time: string // ISO datetime
  }
}
```

---

### 1.5 更新用户信息

```
PUT /api/auth/users/:user_id
```

**Auth**: 需要登录

**权限规则**:
- `admin`: 可修改任何用户的所有字段（`real_name`, `email`, `phone`, `student_or_staff_id`, `user_type`, `account_status`）
- 自己 (`current_user_id === user_id`): 可修改 `real_name`, `email`, `phone`, `student_or_staff_id`
- 其他角色: 403

**Request Body**:
```typescript
{
  real_name?: string
  email?: string
  phone?: string
  student_or_staff_id?: string
  user_type?: string          // 仅 admin
  account_status?: string     // 仅 admin
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    user_id: number
    username: string
    real_name: string
    email: string | null
    phone: string | null
    user_type: string
    student_or_staff_id: string | null
    account_status: string
  }
}
```

---

### 1.6 修改密码

```
PUT /api/auth/users/:user_id/password
```

**Auth**: 需要登录，仅能修改自己的密码

**Request Body**:
```typescript
{
  old_password: string   // 必填
  new_password: string   // 必填, 至少8位, 包含字母+数字
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "密码修改成功",
  data: null
}
```

**验证规则**:
- 新密码长度 ≥ 8
- 新密码必须包含至少一个字母
- 新密码必须包含至少一个数字
- 新密码不能与旧密码相同

---

### 1.7 删除用户（软删除）

```
DELETE /api/auth/users/:user_id
```

**Auth**: 仅 `admin`

**限制**: 不能删除 `admin` 类型用户

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: null
}
```

---

### 1.8 获取头像

```
GET /api/auth/avatar
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    avatar_url: string | null  // 如 "/uploads/avatars/1_abc123.png"
  }
}
```

---

### 1.9 上传头像

```
POST /api/auth/avatar/upload
```

**Auth**: 需要登录

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 图片文件（jpg/jpeg/png/webp, ≤5MB） |

**Response** (200):
```typescript
{
  code: 200,
  message: "头像上传成功",
  data: {
    avatar_url: string   // 上传后的URL
    file_md5: string     // 文件MD5
  }
}
```

**行为**: 上传新头像时会自动删除旧头像文件

---

### 1.10 删除头像

```
DELETE /api/auth/avatar
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "头像已删除",
  data: null
}
```

---

## 2. 赛事/项目管理 - Events

**Blueprint Prefix**: `/api`

### 2.1 创建赛事

```
POST /api/events
```

**Auth**: 所有已登录用户

**Request Body**:
```typescript
{
  event_name: string           // 必填
  event_start_time: string     // 必填, ISO datetime
  event_end_time: string       // 必填, ISO datetime, 必须晚于开始时间
  description?: string
  upload_start_time?: string   // ISO datetime
  upload_end_time?: string     // ISO datetime
  leader_id?: number           // 负责人 user_id
  total_budget?: number        // 默认 0, 不能为负
  need_invoice_review?: boolean // 默认 true, 是否需要发票审核
}
```

**Response** (201):
```typescript
{
  code: 200,
  message: "success",
  data: {
    event_id: number
    event_name: string
    description: string | null
    status: "ongoing"
    event_start_time: string | null
    event_end_time: string | null
    upload_start_time: string | null
    upload_end_time: string | null
    creator_id: number
    leader_id: number | null
    total_budget: number
    reimbursed_amount: number
    remaining_budget: number
    invoice_count: number
    invoice_total_amount: number
    need_invoice_review: boolean
  }
}
```

**副作用**: 自动将创建者和负责人添加为赛事成员

---

### 2.2 获取赛事列表

```
GET /api/events
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | number | 否 | 页码（默认 1） |
| `page_size` | number | 否 | 每页条数（默认 10） |
| `status` | string | 否 | 按状态筛选：`ongoing` / `finished` |

**权限过滤**:
- `admin` / `teacher`: 查看所有赛事
- 普通用户: 只能查看自己创建或为成员的赛事

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    total: number
    page: number
    page_size: number
    data: Array<{
      event_id: number
      event_name: string
      description: string | null
      status: "ongoing" | "finished"
      event_start_time: string | null
      event_end_time: string | null
      upload_start_time: string | null
      upload_end_time: string | null
      total_budget: number
      reimbursed_amount: number      // 动态计算：已报销总额
      remaining_budget: number        // total_budget - reimbursed_amount
      spent_amount: number            // 动态计算：所有支出总额
      invoice_total_amount: number    // 发票总额
      purchase_total_amount: number   // 购买记录总额
      invoice_count: number
      purchase_record_count: number
      voucher_count: number           // invoice_count + purchase_count
      creator_id: number
      leader_id: number | null
      leader_name: string | null
      need_invoice_review: boolean
    }>
  }
}
```

---

### 2.3 获取赛事详情

```
GET /api/events/:event_id
```

**Auth**: 需要登录，非 admin/teacher 用户只能查看自己有权限的赛事

**Response** (200): 与列表项结构相同，返回单个赛事完整数据

**错误码**: `2001` 赛事不存在

---

### 2.4 更新赛事

```
PUT /api/events/:event_id
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**Request Body**:
```typescript
{
  event_name?: string
  description?: string
  event_start_time?: string     // ISO datetime
  event_end_time?: string       // ISO datetime
  upload_start_time?: string
  upload_end_time?: string
  leader_id?: number
  total_budget?: number
  need_invoice_review?: boolean
}
```

**Response** (200): 返回更新后的赛事完整数据

**副作用**: 设置 `leader_id` 时自动将负责人添加为成员；修改 `total_budget` 时自动重算 `remaining_budget`

---

### 2.5 删除赛事（软删除）

```
DELETE /api/events/:event_id
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**限制**: 赛事下存在发票时不能删除（返回 400 提示先删除发票）

**Response** (200):
```typescript
{
  code: 200,
  message: "项目删除成功",
  data: null
}
```

---

### 2.6 获取赛事成员列表

```
GET /api/events/:event_id/members
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    members: Array<{
      user_id: number
      username: string
      real_name: string
      email: string | null
      phone: string | null
      user_type: string
      student_or_staff_id: string | null
      avatar_url: string | null
      role_in_event: string       // 赛事内角色: 'student' | 'teacher'
      created_at: string | null
    }>
    total_count: number
  }
}
```

---

### 2.7 添加赛事成员

```
POST /api/events/:event_id/members
```

**Auth**: 需要登录

**Request Body**:
```typescript
{
  user_id: number          // 必填
  role_in_event?: string   // 默认 'student'
}
```

**Response** (201):
```typescript
{
  code: 200,
  message: "添加成员成功",
  data: {
    member_id: number
    user_id: number
    role_in_event: string
  }
}
```

---

### 2.8 移除赛事成员

```
DELETE /api/events/:event_id/members/:user_id
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "移除成员成功",
  data: null
}
```

---

### 2.9 用户消费汇总排名

```
GET /api/events/stats/user-summary
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_id` | number | 否 | 指定赛事，不传则查询用户有权限的所有赛事 |

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    rankings: Array<{
      user_id: number
      real_name: string
      user_type: string
      total_amount: number       // 消费总额（记录+发票，按降序排列）
      record_count: number       // 记录总数
    }>
  }
}
```

---

## 3. 购买记录 - Purchase Records

**Blueprint Prefix**: `/api`

> **核心模块**: 这是前台最常使用的模块。购买记录同时管理"购物凭证"和"关联发票"。

### 3.1 获取购买记录列表

```
GET /api/events/:event_id/records
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `uploader_id` | number | 否 | 按上传人筛选 |

**权限**: 非 admin/teacher 用户只能查看自己创建/为成员的赛事

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    records: Array<{
      record_id: number
      event_id: number
      item_name: string
      purchase_platform: string
      purchase_date: string | null      // YYYY-MM-DD
      amount: number
      receipt_image_url: string | null  // 预签名URL或本地路径
      receipt_image_name: string | null
      cannot_invoice: boolean           // 是否无法开发票
      has_invoice: boolean              // 是否有关联发票
      invoice_file_key: string | null
      invoice_preview_key: string | null
      invoice_url: string | null        // 预签名URL
      invoice_preview_url: string | null // 预签名URL
      invoice_original_filename: string | null
      invoice_type: string | null
      invoice_number: string | null
      total_amount: number              // 发票总金额
      invoice_date: string | null       // YYYY-MM-DD
      status: "pending" | "approved" | "rejected"
      is_reimbursed: boolean
      remarks: string | null
      uploader_id: number
      uploader_name: string | null
      reviewer_name: string | null
      created_at: string | null         // ISO datetime
      rejection_reason: string | null
    }>
    total_count: number
    total_amount: string                // 所有记录金额之和
    invoice_total: string               // 有发票记录的发票总额
    pending_reimburse: string           // 待报销金额
  }
}
```

> **注意**: 此接口返回所有记录（不分页），图片URL在COS可用时会生成预签名URL（24小时有效期）

---

### 3.2 创建购买记录

```
POST /api/events/:event_id/records
```

**Auth**: 需要登录

**Request Body** (JSON):
```typescript
{
  // === 必填字段 ===
  item_name: string
  purchase_platform: string
  purchase_date: string           // YYYY-MM-DD
  amount: number
  receipt_image_url: string       // 购物凭证图片URL（必填）

  // === 可选字段 ===
  receipt_image_name?: string
  receipt_file_md5?: string

  // === 发票相关 ===
  cannot_invoice?: boolean        // 默认 false
  invoice_file_key?: string       // 关联发票文件key
  invoice_preview_key?: string    // 发票预览图key
  invoice_original_filename?: string
  invoice_md5?: string
  invoice_type?: string
  invoice_number?: string
  total_amount?: number           // 发票总额
  invoice_date?: string           // YYYY-MM-DD
  remarks?: string
}
```

**业务逻辑**:
- 如果赛事 `need_invoice_review = false`，记录自动设为 `approved`
- `cannot_invoice = true` 时忽略所有发票字段
- `invoice_file_key` 非空时自动设置 `has_invoice = true`
- 自动将上传人加为赛事成员

**Response** (201):
```typescript
{
  code: 200,
  message: "购买记录创建成功",
  data: {
    record_id: number
    item_name: string
    has_invoice: boolean
  }
}
```

---

### 3.3 更新购买记录

```
PUT /api/records/:record_id
```

**Auth**: 需要登录

**权限**: 记录上传人本人, 或 `admin`/`teacher`/`student_admin`

**Request Body** (JSON): 同创建参数，所有字段均为可选

**特殊字段**:
- `uploader_id`: 仅管理员可修改（转移上传人）
- `cannot_invoice`: 设为 `true` 时自动清除所有发票相关字段

**Response** (200):
```typescript
{
  code: 200,
  message: "更新成功",
  data: { record_id: number }
}
```

---

### 3.4 删除购买记录（软删除）

```
DELETE /api/records/:record_id
```

**Auth**: 需要登录

**权限**: 记录上传人本人, 或 `admin`/`teacher`/`student_admin`

**Response** (200):
```typescript
{
  code: 200,
  message: "删除成功",
  data: null
}
```

---

### 3.5 审核购买记录

```
POST /api/records/:record_id/approve
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**Request Body**:
```typescript
{
  status: "approved" | "rejected"    // 必填
  rejection_reason?: string          // 拒绝时必填
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "审核通过" | "已拒绝",
  data: null
}
```

---

### 3.6 报销购买记录

```
POST /api/records/:record_id/reimburse
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**前置条件**: 记录必须有发票 (`has_invoice = true`) 且未被报销

**Response** (200):
```typescript
{
  code: 200,
  message: "报销成功",
  data: null
}
```

**副作用**: 更新赛事的 `reimbursed_amount` 和 `remaining_budget`

---

### 3.7 下载购买记录关联发票

```
GET /api/records/:record_id/download-invoice
```

**Auth**: 需要登录

**Response**: 直接返回文件字节流（`Content-Disposition: attachment`）

**支持**: COS远程文件和本地文件

---

### 3.8 获取购买记录发票预览URL

```
GET /api/records/:record_id/preview-invoice
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    preview_url: string     // 预签名URL
    is_pdf: boolean         // 是否为PDF文件
  }
}
```

---

### 3.9 重新解析发票（AI识别）

```
POST /api/records/:record_id/re-parse-invoice
```

**Auth**: 需要登录

**前置条件**: 记录有关联发票文件 (`has_invoice = true`)

**行为**: 从存储中下载发票文件，PDF则先转JPG，再调用GLM视觉模型解析

**Response** (200):
```typescript
{
  code: 200,
  message: "重新解析成功",
  data: {
    parsed_info: {
      item_name: string
      invoice_number: string
      amount: number
      date: string
    }
    extraction_method: "glm_vision"
  }
}
```

---

## 4. 发票管理 - Invoices

**Blueprint Prefix**: `/api`

> 注意: 前台购买记录页面主要使用 [购买记录模块](#3-购买记录---purchase-records)，传统发票接口以下端点可能在前台中较少使用。

### 4.1 获取发票列表

```
GET /api/invoices
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_id` | number | 是 | 赛事ID |
| `page` | number | 否 | 页码（默认 1） |
| `page_size` | number | 否 | 每页条数（默认 20） |
| `uploader_id` | number | 否 | 按上传人筛选 |

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    data: Array<{
      invoice_id: number
      event_id: number
      uploader_id: number
      uploader_name: string | null
      file_name: string
      invoice_type: string | null
      invoice_number: string | null
      project_name: string
      amount: number
      total_amount: number
      invoice_date: string | null          // YYYY-MM-DD
      status: "pending" | "approved" | "rejected"
      reviewer_id: number | null
      reviewer_name: string | null
      review_time: string | null           // ISO datetime
      rejection_reason: string | null
      remarks: string | null
      is_reimbursed: boolean
      reimbursed_at: string | null         // ISO datetime
      created_at: string | null            // ISO datetime
      image_url: string | null             // 预签名URL或本地路径
    }>
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}
```

---

### 4.2 上传/创建发票

```
POST /api/invoices
```

**Auth**: 需要登录

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 发票文件（pdf/png/jpg/jpeg） |
| `event_id` | string | 赛事ID |
| `invoice_type` | string | 发票类型 |
| `invoice_number` | string | 发票号 |
| `project_name` | string | 项目名称 |
| `amount` | string | 金额 |
| `total_amount` | string | 总额（默认等于amount） |
| `invoice_date` | string | 开票日期 YYYY-MM-DD |
| `remarks` | string | 备注 |

**行为**: 自动检查MD5重复；如果是首次上传到该赛事，自动添加赛事成员

**Response** (200):
```typescript
{
  code: 200,
  message: "发票上传成功",
  data: {
    invoice_id: number
    file_name: string
    image_url: string    // 预签名URL或本地路径
  }
}
```

**错误码**: `4001` 发票重复上传（返回已存在的发票ID和上传时间）

---

### 4.3 更新发票信息

```
PUT /api/invoices/:invoice_id
```

**Auth**: 需要登录

**Request Body**:
```typescript
{
  invoice_type?: string
  project_name?: string
  amount?: number        // 修改金额会联动更新赛事统计
  invoice_date?: string  // YYYY-MM-DD
  invoice_number?: string
  remarks?: string
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "发票信息更新成功",
  data: null
}
```

---

### 4.4 删除发票（软删除）

```
DELETE /api/invoices/:invoice_id
```

**Auth**: 需要登录

**权限**: 上传人本人, 或 `admin`/`teacher`

**Response** (200):
```typescript
{
  code: 200,
  message: "发票删除成功",
  data: null
}
```

**副作用**: 更新赛事 `invoice_count` 和 `invoice_total_amount`

**错误码**: `3001` 发票不存在

---

### 4.5 审核发票

```
POST /api/invoices/:invoice_id/approve
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**Request Body**:
```typescript
{
  status: "approved" | "rejected"    // 必填
  rejection_reason?: string          // 拒绝时必填
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "审核成功",
  data: null
}
```

**副作用**: 审核通过时更新赛事 `reimbursed_amount` 和 `remaining_budget`

---

### 4.6 报销单张发票

```
POST /api/invoices/:invoice_id/reimburse
```

**Auth**: 仅 `admin` / `teacher`

**前置条件**: 发票状态为 `approved` 且未报销

**Response** (200):
```typescript
{
  code: 200,
  message: "发票报销成功",
  data: null
}
```

---

### 4.7 批量报销发票

```
POST /api/invoices/batch-reimburse
```

**Auth**: 仅 `admin` / `teacher`

**Request Body**:
```typescript
{
  invoice_ids: number[]    // 发票ID数组
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "成功报销 N 张发票",
  data: { count: number }
}
```

---

### 4.8 获取发票预览图

```
GET /api/invoices/:invoice_id/preview
```

**Auth**: 需要登录

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    preview_url: string | null
    has_preview: boolean
  }
}
```

---

### 4.9 生成发票预览图

```
POST /api/invoices/:invoice_id/generate-preview
```

**Auth**: 需要登录

**行为**: PDF文件直接使用原URL；图片文件使用预签名URL；设置 `preview_image_url` 字段

**Response** (200):
```typescript
{
  code: 200,
  message: "PDF文件直接作为预览" | "图片格式发票，直接使用原图",
  data: { preview_url: string }
}
```

---

### 4.10 下载发票文件

```
GET /api/invoices/:invoice_id/download
```

**Auth**: 需要登录

**Response**: 直接返回文件字节流

**支持**: COS远程文件（返回 `Response` 流）和本地文件（`send_file`）

---

## 5. 凭证管理 - Vouchers

**Blueprint Prefix**: `/api`

> 注意: 前台目前已主要使用购买记录模块，Voucher 接口可能为历史兼容保留。

### 5.1 获取凭证列表

```
GET /api/vouchers
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_id` | number | 是 | 赛事ID |
| `page` | number | 否 | 页码（默认 1） |
| `page_size` | number | 否 | 每页条数（默认 20） |

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    data: Array<{
      voucher_id: number
      event_id: number
      uploader_id: number
      uploader_name: string | null
      file_name: string
      item_name: string
      voucher_type: string | null
      purchase_channel: string | null
      purchase_date: string | null     // YYYY-MM-DD
      amount: number
      is_reimbursed: boolean
      reimbursed_at: string | null     // ISO datetime
      remarks: string | null
      created_at: string | null        // ISO datetime
      file_url: string | null          // 预签名URL或本地路径
      record_type: "voucher"
    }>
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}
```

---

### 5.2 创建凭证

```
POST /api/vouchers
```

**Auth**: 需要登录

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 凭证文件（pdf/png/jpg/jpeg） |
| `event_id` | string | 赛事ID |
| `item_name` | string | 物品名称（必填） |
| `voucher_type` | string | 凭证类型 |
| `purchase_channel` | string | 购买渠道 |
| `purchase_date` | string | 购买日期 YYYY-MM-DD |
| `amount` | string | 金额 |
| `remarks` | string | 备注 |

**Response** (200):
```typescript
{
  code: 200,
  message: "凭证上传成功",
  data: {
    voucher_id: number
    file_name: string
  }
}
```

---

### 5.3 更新凭证

```
PUT /api/vouchers/:voucher_id
```

**Auth**: 需要登录

**Request Body**:
```typescript
{
  item_name?: string
  voucher_type?: string
  purchase_channel?: string
  purchase_date?: string    // YYYY-MM-DD
  amount?: number           // 修改金额会联动更新赛事统计
  remarks?: string
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "凭证信息更新成功",
  data: null
}
```

---

### 5.4 删除凭证（软删除）

```
DELETE /api/vouchers/:voucher_id
```

**Auth**: 需要登录

**权限**: 上传人本人, 或 `admin`/`teacher`

**Response** (200):
```typescript
{
  code: 200,
  message: "凭证删除成功",
  data: null
}
```

**错误码**: `3001` 凭证不存在

---

### 5.5 下载凭证文件

```
GET /api/vouchers/:voucher_id/download
```

**Auth**: 需要登录

**Response**: 直接返回文件字节流

---

### 5.6 批量报销凭证

```
POST /api/vouchers/batch-reimburse
```

**Auth**: 仅 `admin` / `teacher`

**Request Body**:
```typescript
{
  voucher_ids: number[]
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "成功报销 N 张凭证",
  data: { count: number }
}
```

---

### 5.7 检查文件MD5去重

```
GET /api/check-file-md5
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `md5` | string | 是 | 文件MD5值 |
| `event_id` | string | 否 | 赛事ID |

**行为**: 先在 `PurchaseRecord` 表查 `receipt_file_md5`，再在 `Voucher` 表查 `file_md5`

**Response** (200):
```typescript
// 找到重复
{
  code: 200,
  message: "找到重复文件",
  data: {
    exists: true
    uploader_name: string
    upload_time: string
    file_name: string
    type: "receipt" | "voucher"
  }
}
// 未找到重复
{
  code: 200,
  message: "未找到重复文件",
  data: { exists: false }
}
```

---

## 6. 文件上传/解析 - Parse

**Blueprint Prefix**: `/api`

> 此模块提供通用的文件上传和AI发票解析能力

### 6.1 通用文件上传（不解析）

```
POST /api/upload-file
```

**Auth**: 需要登录（支持JWT Query参数）

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 文件（pdf/png/jpg/jpeg） |

**Response** (200):
```typescript
{
  code: 200,
  message: "上传成功",
  data: {
    image_url: string | null        // 文件访问URL
    file_key: string                // COS中的文件key，如 "invoices/abc123.pdf"
    preview_url: string | null      // 预览URL
    file_md5: string
    original_filename: string
    file_type: string               // pdf/png/jpg/jpeg
  }
}
```

---

### 6.2 图片解析（不上传存储）

```
POST /api/parse-image
```

**Auth**: 需要登录

**用途**: 仅对图片进行AI解析，不保存到存储。适用于客户端已将PDF转为图片后的解析场景。

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 图片文件，不支持PDF |

**Response** (200):
```typescript
{
  code: 200,
  message: "解析完成",
  data: {
    parsed_info: {
      item_name: string       // 项目名称
      invoice_number: string  // 发票号码
      amount: number          // 金额
      date: string            // 日期
    } | null                  // AI服务不可用时为null
    filename: string
  }
}
```

---

### 6.3 发票上传+解析

```
POST /api/parse-invoice
```

**Auth**: 需要登录

**Content-Type**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 发票文件（pdf/png/jpg/jpeg） |
| `preview_file` | File | （可选）客户端预生成的预览图 |

**完整处理流程**:
1. 验证文件格式和大小
2. 计算MD5并检查重复（在 PurchaseRecord 表中）
3. 上传原始文件到对象存储（COS）/本地
4. 如果PDF：服务端渲染转JPG（优先客户端预览图）
5. 上传预览图到COS/本地
6. 调用GLM视觉模型AI解析发票信息
7. 返回文件URL和解析结果

**Response** (200):
```typescript
{
  code: 200,
  message: "解析完成" | "文件上传成功",
  data: {
    file_key: string            // COS key 或本地路径
    preview_key: string | null  // 预览图 key
    file_url: string            // 文件访问URL
    preview_url: string         // 预览URL
    original_filename: string
    file_type: string           // pdf/png/jpg/jpeg
    is_pdf: boolean
    pdf_page_count: number      // PDF页数（仅PDF）
    file_md5: string
    parsed_info: {              // AI解析结果，失败时为null
      item_name: string
      invoice_number: string
      amount: number
      date: string
    } | null
    extraction_method: "glm_vision" | null
  }
}
```

**错误码**: `409` 发票文件重复

---

### 6.4 获取发票文件预览URL

```
GET /api/invoices/:file_key/preview
```

**Auth**: 需要登录

**URL参数**: `file_key` 为路径参数（支持子路径，如 `invoices/abc/preview`）

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    preview_url: string        // 预签名URL（COS可用时）或本地路径
  }
}
```

---

### 6.5 下载发票文件

```
GET /api/invoices/:file_key/download
```

**Auth**: 需要登录

**URL参数**: `file_key` 为路径参数

**Response**: 直接返回文件字节流

---

## 7. 邀请码管理 - Invitation Codes

**Blueprint Prefix**: `/api`

### 7.1 获取邀请码列表

```
GET /api/invitation-codes
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | number | 否 | 页码（默认 1） |
| `page_size` | number | 否 | 每页条数（默认 20） |

**权限过滤**: `teacher` 只能看自己创建的邀请码

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    data: Array<{
      id: number
      code: string                     // 格式: {prefix}-{timestamp}-{random}
      target_user_type: string         // admin/teacher/student_admin/student
      target_user_type_text: string    // 中文名称
      expires_at: string | null        // ISO datetime
      max_uses: number                 // -1 表示无限次
      used_count: number
      created_by: number
      creator_name: string | null
      is_active: boolean               // 综合判断：激活且未过期且未用尽
      status: "active" | "expired" | "used_out" | "disabled"
      created_at: string               // ISO datetime
    }>
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}
```

---

### 7.2 创建邀请码

```
POST /api/invitation-codes
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**权限限制**:
- `student_admin`: 只能生成 `student` / `student_admin` 类型
- `teacher`: 不能生成 `admin` 类型

**Request Body**:
```typescript
{
  target_user_type?: string    // 默认 'student'，可选：admin/teacher/student_admin/student
  expires_days?: number        // 默认 30，范围 1-365
  quantity?: number            // 默认 1，范围 1-20
  max_uses?: number            // 默认 -1（无限次）
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "成功生成 N 个邀请码",
  data: {
    codes: Array<{
      code: string
      target_user_type: string
      expires_at: string       // ISO datetime
    }>
    count: number
  }
}
```

**邀请码格式**: `{PREFIX}-{YYYYMMDDHHmm}-{16位随机大写字母数字}`
- `TCH` = teacher
- `ADM` = student_admin
- `STU` = student

---

### 7.3 验证邀请码

```
POST /api/invitation-codes/verify
```

**Auth**: 无需认证

**Request Body**:
```typescript
{
  code: string    // 邀请码字符串
}
```

**Response** (200):
```typescript
// 有效
{
  code: 200,
  message: "邀请码有效",
  data: {
    valid: true
    target_user_type: string
  }
}

// 无效
{
  code: 200,                          // 注意：即使无效也返回200
  message: "该邀请码已过期",            // 或 "已被禁用" / "使用次数已达上限"
  data: {
    valid: false
    reason: "expired" | "disabled" | "used_out"
  }
}
```

**错误码**: `404` 邀请码不存在

---

### 7.4 切换邀请码启用/禁用状态

```
POST /api/invitation-codes/:code_id/toggle
```

**Auth**: 仅 `admin` / `teacher` / `student_admin`

**权限**: `teacher` 只能操作自己创建的邀请码

**Response** (200):
```typescript
{
  code: 200,
  message: "邀请码已启用" | "邀请码已禁用",
  data: { is_active: boolean }
}
```

---

### 7.5 删除邀请码

```
DELETE /api/invitation-codes/:code_id
```

**Auth**: 仅 `admin`

**Response** (200):
```typescript
{
  code: 200,
  message: "邀请码已删除",
  data: null
}
```

---

## 8. 系统配置 - System

**Blueprint Prefix**: `/api`

> 所有系统配置接口仅限 `admin` 角色访问

### 8.1 获取系统配置

```
GET /api/system/config
```

**Auth**: 仅 `admin`

**Response** (200):
```typescript
{
  code: 200,
  data: {
    ai_model: {
      value: string              // 实际值
      is_encrypted: false
      description: string
      updated_at: string | null
      has_value: boolean
    }
    ai_api_key: {
      value: string              // 脱敏显示: 前4位 + **** + 后4位
      is_encrypted: true
      description: string
      updated_at: string | null
      has_value: boolean
    }
    ai_api_url: {
      value: string
      is_encrypted: false
      description: string
      updated_at: string | null
      has_value: boolean
    }
    _version: {
      value: string              // 当前应用版本号
    }
  }
}
```

---

### 8.2 更新系统配置

```
PUT /api/system/config
```

**Auth**: 仅 `admin`

**Request Body**:
```typescript
{
  configs: {
    ai_model?: string            // AI模型名称
    ai_api_key?: string          // API密钥（加密存储）
    ai_api_url?: string          // API地址
  }
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "配置保存成功",
  data: {
    updated_keys: string[]       // 实际更新的配置键列表
  }
}
```

---

### 8.3 检查更新

```
GET /api/system/check-update
```

**Auth**: 仅 `admin`

**行为**: 查询 GitHub Releases API (`Ljinzhou/EasyInvoiceMgr`) 获取最新版本

**Response** (200):
```typescript
{
  code: 200,
  data: {
    current_version: string          // 当前版本
    latest_version: string           // 最新版本
    has_update: boolean
    update_info: {
      version: string
      release_name: string
      release_notes: string          // Markdown格式
      download_url: string
      published_at: string
    } | null
    update_commands: {
      pull: string
      build: string
      restart: string
      full: string                   // git pull && docker compose build && docker compose up -d
    }
    manual_steps: {
      title: string
      description: string
      steps: Array<{
        step: number
        title: string
        command: string
        description: string
      }>
      one_liner: string
      note: string
    }
  }
}
```

---

### 8.4 测试AI模型连通性

```
POST /api/system/test-model
```

**Auth**: 仅 `admin`

**行为**: 发送简单文本消息到配置的AI API验证连通性

**Response** (200):
```typescript
{
  code: 200,
  message: "模型连接测试成功",
  data: {
    model: string
    latency_ms: number       // 请求耗时（毫秒）
    reply: string            // 模型回复内容
  }
}
```

---

### 8.5 手动触发备份

```
POST /api/system/backup
```

**Auth**: 仅 `admin`

**限制**: 同一时间只能有一个备份任务运行（409冲突）

**Response** (200):
```typescript
{
  code: 200,
  message: "备份任务已创建",
  data: {
    id: number          // 备份记录ID
    status: "pending"
  }
}
```

---

### 8.6 获取备份记录列表

```
GET /api/system/backups
```

**Auth**: 仅 `admin`

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | number | 否 | 页码（默认 1） |
| `per_page` | number | 否 | 每页条数（默认 20，最大100） |

**Response** (200):
```typescript
{
  code: 200,
  data: {
    items: Array<{
      id: number
      backup_type: "manual" | "scheduled" | "restore"
      backup_scope: "full" | "database"
      status: "pending" | "running" | "completed" | "failed"
      progress: number               // 0-100
      progress_message: string | null
      file_size: number | null       // 字节
      file_count: number | null      // 打包文件数
      error_message: string | null
      created_at: string | null      // ISO datetime
      completed_at: string | null    // ISO datetime
      created_by_name: string | null
    }>
    total: number
    page: number
    per_page: number
  }
}
```

---

### 8.7 下载备份文件

```
GET /api/system/backup/:backup_id/download
```

**Auth**: 仅 `admin`

**前置条件**: 备份状态为 `completed` 且文件存在

**Response**: 直接返回文件字节流（`send_file`）

---

### 8.8 删除备份

```
DELETE /api/system/backup/:backup_id
```

**Auth**: 仅 `admin`

**行为**: 删除数据库记录和磁盘上的备份文件

**Response** (200):
```typescript
{
  code: 200,
  message: "备份已删除"
}
```

---

### 8.9 从备份恢复

```
POST /api/system/backup/restore/:backup_id
```

**Auth**: 仅 `admin`

**Request Body**:
```typescript
{
  confirm: true    // 必须显式确认
}
```

**前置条件**: 备份状态为 `completed` 且文件存在

**Response** (200):
```typescript
{
  code: 200,
  message: "恢复任务已启动",
  data: { backup_id: number }
}
```

---

### 8.10 获取定时备份配置

```
GET /api/system/backup/config
```

**Auth**: 仅 `admin`

**Response** (200):
```typescript
{
  code: 200,
  data: {
    enabled: boolean
    frequency: "daily" | "weekly" | "monthly"
    time: string              // "HH:MM" 格式
    retention_count: number   // 保留备份数量
  }
}
```

---

### 8.11 更新定时备份配置

```
PUT /api/system/backup/config
```

**Auth**: 仅 `admin`

**Request Body**:
```typescript
{
  enabled: boolean               // 是否启用
  frequency: "daily" | "weekly" | "monthly"
  time: string                   // "HH:MM"
  retention_count: number        // 1-100
}
```

**Response** (200):
```typescript
{
  code: 200,
  message: "备份配置已保存"
}
```

---

## 9. 导出管理 - Export

**Blueprint Prefix**: `/api`

### 9.1 创建导出任务

```
POST /api/events/:event_id/export
```

**Auth**: 需要登录

**Request Body**:
```typescript
{
  columns: string[]      // 要导出的列名数组（必填，至少一个）
  options?: object       // 导出选项
}
```

**行为**: 先检查缓存（相同事件+相同列配置），命中缓存直接返回已有任务ID；否则创建新任务并异步执行导出

**Response** (200):
```typescript
// 缓存命中
{
  code: 200,
  message: "存在缓存的导出结果",
  data: {
    task_id: number
    status: string
    cached: true
  }
}
// 新任务
{
  code: 200,
  message: "导出任务已创建",
  data: {
    task_id: number
    status: "pending"
  }
}
```

---

### 9.2 查询导出任务状态

```
GET /api/events/:event_id/export/status
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | number | 是 | 任务ID |

**Response** (200):
```typescript
{
  code: 200,
  message: "success",
  data: {
    task_id: number
    status: "pending" | "running" | "completed" | "failed"
    progress_percent: number       // 0-100
    progress_message: string
    record_count: number | null
    file_size: number | null
    created_at: string | null      // "YYYY-MM-DD HH:mm:ss"
    completed_at: string | null    // "YYYY-MM-DD HH:mm:ss"
    error_message: string | null
  }
}
```

---

### 9.3 下载导出文件

```
GET /api/events/:event_id/export/download
```

**Auth**: 需要登录

**Query Parameters**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | number | 是 | 任务ID |

**前置条件**: 任务状态为 `completed`，文件未过期

**Response**: 直接返回文件字节流（Excel文件）

**错误码**: `410` 导出文件已过期

---

## 10. 静态文件服务

> 这些路由定义在 `app.py` 中，不属于任何 Blueprint

### 10.1 本地文件访问

```
GET /uploads/<path:filename>
GET /api/uploads/<path:filename>    // 兼容别名
```

**Auth**: 无需认证（但CORS限制）

**安全**: 禁止 `..` 路径遍历

**支持格式**: PNG, JPG, JPEG, GIF, PDF

**Response**: 直接返回文件，设置正确的 `Content-Type` 和 `Cache-Control: public, max-age=3600`

**前端代理**: Nuxt Nitro 在开发环境下将 `/uploads/**` 代理到 `http://localhost:5000`

---

## 11. 数据模型参考

### User 表 (`users`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | BigInt PK | 自增主键 |
| `username` | String(50) UNIQUE | 用户名 |
| `password_hash` | String(255) | Werkzeug hash |
| `real_name` | String(50) | 真实姓名 |
| `email` | String(100) UNIQUE | 邮箱 |
| `phone` | String(20) | 电话 |
| `user_type` | String(20) | admin/teacher/student_admin/student |
| `organization` | String(100) | 组织/学校 |
| `student_or_staff_id` | String(50) | 学号/工号 |
| `avatar_url` | Text | 头像URL |
| `account_status` | String(20) | active/disabled |
| `register_time` | DateTime | 注册时间 |
| `last_login_time` | DateTime | 最后登录时间 |
| `is_deleted` | Boolean | 软删除标记 |
| `extra_fields` | JSON | 扩展字段 |

### Event 表 (`events`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `event_id` | BigInt PK | 自增主键 |
| `event_name` | String(200) | 赛事名称 |
| `description` | Text | 描述 |
| `status` | String(20) | ongoing/finished |
| `event_start_time` | DateTime | 开始时间 |
| `event_end_time` | DateTime | 结束时间 |
| `upload_start_time` | DateTime | 上传开始时间 |
| `upload_end_time` | DateTime | 上传截止时间 |
| `creator_id` | FK→users | 创建者 |
| `leader_id` | FK→users | 负责人 |
| `total_budget` | Numeric(12,2) | 总预算 |
| `reimbursed_amount` | Numeric(12,2) | 已报销金额 |
| `remaining_budget` | Numeric(12,2) | 剩余预算 |
| `invoice_count` | Integer | 发票数量 |
| `invoice_total_amount` | Numeric(12,2) | 发票总额 |
| `purchase_record_count` | Integer | 购买记录数 |
| `voucher_count` | Integer | 凭证数量 |
| `voucher_total_amount` | Numeric(12,2) | 凭证总额 |
| `need_invoice_review` | Boolean | 是否需要发票审核 |
| `is_deleted` | Boolean | 软删除 |

### EventMember 表 (`event_members`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInt PK | 自增主键 |
| `event_id` | FK→events | 赛事ID |
| `user_id` | FK→users | 用户ID |
| `role_in_event` | String(20) | 赛事内角色 |
| `is_deleted` | Boolean | 软删除 |

**唯一约束**: `(event_id, user_id)`

### Invoice 表 (`invoices`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `invoice_id` | BigInt PK | 自增主键 |
| `event_id` | FK→events | 赛事ID |
| `uploader_id` | FK→users | 上传者 |
| `file_name` | String(255) | 文件名 |
| `file_md5` | String(64) | 文件MD5（去重用） |
| `image_url` | Text | 发票图片URL/key |
| `preview_image_url` | Text | 预览图URL/key |
| `invoice_type` | String(50) | 发票类型 |
| `invoice_number` | String(50) | 发票号 |
| `project_name` | String(200) | 项目名称 |
| `amount` | Numeric(12,2) | 金额 |
| `total_amount` | Numeric(12,2) | 总额 |
| `invoice_date` | Date | 开票日期 |
| `status` | String(20) | pending/approved/rejected |
| `is_reimbursed` | Boolean | 是否已报销 |
| `reimbursed_at` | DateTime | 报销时间 |
| `reviewer_id` | FK→users | 审核人 |
| `review_time` | DateTime | 审核时间 |
| `rejection_reason` | Text | 拒绝原因 |
| `remarks` | Text | 备注 |
| `is_deleted` | Boolean | 软删除 |

### PurchaseRecord 表 (`purchase_records`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `record_id` | BigInt PK | 自增主键 |
| `event_id` | FK→events | 赛事ID |
| `uploader_id` | FK→users | 上传者 |
| `item_name` | String(200) | 物品名称 |
| `purchase_platform` | String(100) | 购买平台 |
| `purchase_date` | Date | 购买日期 |
| `amount` | Numeric(12,2) | 金额 |
| `receipt_image_url` | Text | 购物凭证图片URL |
| `receipt_image_name` | String(255) | 凭证文件名 |
| `receipt_file_md5` | String(64) | 凭证文件MD5 |
| `cannot_invoice` | Boolean | 不能开发票 |
| `has_invoice` | Boolean | 是否有关联发票 |
| `invoice_file_key` | Text | 发票COS key |
| `invoice_preview_key` | Text | 发票预览图COS key |
| `invoice_original_filename` | String(255) | 发票原始文件名 |
| `invoice_md5` | String(64) | 发票文件MD5 |
| `invoice_type` | String(50) | 发票类型 |
| `invoice_number` | String(50) | 发票号 |
| `invoice_tax_number` | String(50) | 税号 |
| `total_amount` | Numeric(12,2) | 发票总额 |
| `invoice_date` | Date | 开票日期 |
| `status` | String(20) | pending/approved/rejected |
| `is_reimbursed` | Boolean | 是否已报销 |
| `reimbursed_at` | DateTime | 报销时间 |
| `reviewer_id` | FK→users | 审核人 |
| `review_time` | DateTime | 审核时间 |
| `rejection_reason` | Text | 拒绝原因 |
| `remarks` | Text | 备注 |
| `is_deleted` | Boolean | 软删除 |

### Voucher 表 (`vouchers`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `voucher_id` | BigInt PK | 自增主键 |
| `event_id` | FK→events | 赛事ID |
| `uploader_id` | FK→users | 上传者 |
| `file_name` | String(255) | 文件名 |
| `file_md5` | String(64) | MD5 |
| `file_url` | Text | 文件URL/key |
| `item_name` | String(200) | 物品名称 |
| `voucher_type` | String(50) | 凭证类型 |
| `purchase_channel` | String(100) | 购买渠道 |
| `purchase_date` | Date | 购买日期 |
| `amount` | Numeric(12,2) | 金额 |
| `is_reimbursed` | Boolean | 是否报销 |
| `reimbursed_at` | DateTime | 报销时间 |
| `remarks` | Text | 备注 |
| `is_deleted` | Boolean | 软删除 |

### InvitationCode 表 (`invitation_codes`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInt PK | 自增主键 |
| `code` | String(64) UNIQUE | 邀请码 |
| `target_user_type` | String(20) | 目标用户类型 |
| `expires_at` | DateTime | 过期时间 |
| `max_uses` | Integer | 最大使用次数（-1=无限） |
| `used_count` | Integer | 已使用次数 |
| `created_by` | FK→users | 创建者 |
| `is_active` | Boolean | 是否激活 |
| `created_at` | DateTime | 创建时间 |

### SystemConfig 表 (`system_configs`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInt PK | 自增主键 |
| `config_key` | String(128) UNIQUE | 配置键 |
| `config_value` | Text | 配置值（可加密） |
| `is_encrypted` | Boolean | 是否加密存储 |
| `description` | String(255) | 描述 |
| `updated_by` | FK→users | 更新者 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### ExportTask 表 (`export_tasks`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | BigInt PK | 自增主键 |
| `event_id` | FK→events | 赛事ID |
| `requester_id` | FK→users | 请求者 |
| `status` | String(20) | pending/running/completed/failed |
| `columns_config` | JSON | 列配置 |
| `file_path` | Text | 导出文件路径 |
| `file_size` | BigInt | 文件大小 |
| `data_snapshot_time` | DateTime | 数据快照时间 |
| `record_count` | Integer | 记录数 |
| `error_message` | Text | 错误信息 |
| `progress_percent` | Integer | 0-100 |
| `progress_message` | String(200) | 进度信息 |
| `expires_at` | DateTime | 过期时间 |

### BackupRecord 表 (`backup_records`)
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInt PK | 自增主键 |
| `backup_type` | String(20) | manual/scheduled/restore |
| `backup_scope` | String(20) | full/database |
| `status` | String(20) | pending/running/completed/failed |
| `progress` | Integer | 0-100 |
| `progress_message` | String(200) | 进度信息 |
| `file_path` | Text | 备份文件路径 |
| `file_size` | BigInt | 文件大小 |
| `file_count` | Integer | 打包文件数 |
| `error_message` | Text | 错误信息 |
| `created_by` | FK→users | 创建者（定时备份为NULL） |
| `created_at` | DateTime | 创建时间 |
| `completed_at` | DateTime | 完成时间 |

---

## 附录A: 前端API调用速查表

| 前端页面/组件 | 调用的API端点 | 方法 |
|-------------|-------------|------|
| `pages/login.vue` | `/auth/login` | POST |
| `pages/register.vue` | `/invitation-codes/verify`, `/auth/register` | POST |
| `pages/dashboard.vue` | `/events/stats/user-summary` | GET |
| `pages/events/create.vue` | `/events/:id`, `/events/:id` (PUT), `/events` (POST) | GET/PUT/POST |
| `pages/events/[id]/members.vue` | `/events/:id`, `/events/:id/members` | GET |
| `pages/events/[id]/export.vue` | `/events/:id`, `/events/:id/export`, `.../export/status`, `.../export/download` | GET/POST |
| `pages/projects/index.vue` | `/events/:id` (PUT/DELETE), `/events/:id/members` (POST) | PUT/DELETE/POST |
| `pages/purchases/[id].vue` | `/events/:id`, `/events/:id/records`, `/invoices`, `/upload-file`, `/parse-invoice`, `/parse-image`, `/records/:id` (PUT/DELETE), `/records/:id/approve`, `/records/:id/reimburse`, `/records/:id/re-parse-invoice`, `/auth/users` | ALL |
| `pages/invitation-codes/index.vue` | `/invitation-codes` (GET/POST/DELETE), `/invitation-codes/:id/toggle` | GET/POST/DELETE |
| `pages/users/index.vue` | `/auth/users` (GET/POST/PUT/DELETE), `/events` (GET), `/events/:id/members` (POST) | ALL |
| `pages/settings/index.vue` | `/system/config` (GET/PUT), `/system/test-model`, `/system/check-update`, `/system/backup`, `/system/backups`, `/system/backup/config`, `/system/backup/restore/:id`, `/system/backup/:id` (DELETE) | ALL |
| `layouts/default.vue` | `/auth/users/:id` (PUT), `/auth/users/:id/password` | PUT |
| `components/AvatarUpload.vue` | `/auth/avatar/upload`, `/auth/avatar` (DELETE) | POST/DELETE |
| `composables/useUserSearch.ts` | `/auth/users?search=` | GET |
| `stores/eventStore.ts` | `/events` | GET |

## 附录B: API端点完整索引

| # | Method | Path | Auth Required | Admin Only | 模块 |
|---|--------|------|---------------|------------|------|
| 1 | POST | `/api/auth/register` | No | No | Auth |
| 2 | POST | `/api/auth/login` | No | No | Auth |
| 3 | GET | `/api/auth/users` | Yes | No* | Auth |
| 4 | GET | `/api/auth/users/:user_id` | Yes | No | Auth |
| 5 | PUT | `/api/auth/users/:user_id` | Yes | No | Auth |
| 6 | PUT | `/api/auth/users/:user_id/password` | Yes | No | Auth |
| 7 | DELETE | `/api/auth/users/:user_id` | Yes | Yes | Auth |
| 8 | GET | `/api/auth/avatar` | Yes | No | Auth |
| 9 | POST | `/api/auth/avatar/upload` | Yes | No | Auth |
| 10 | DELETE | `/api/auth/avatar` | Yes | No | Auth |
| 11 | POST | `/api/events` | Yes | No | Events |
| 12 | GET | `/api/events` | Yes | No | Events |
| 13 | GET | `/api/events/:event_id` | Yes | No | Events |
| 14 | PUT | `/api/events/:event_id` | Yes | No* | Events |
| 15 | DELETE | `/api/events/:event_id` | Yes | No* | Events |
| 16 | GET | `/api/events/:event_id/members` | Yes | No | Events |
| 17 | POST | `/api/events/:event_id/members` | Yes | No | Events |
| 18 | DELETE | `/api/events/:event_id/members/:user_id` | Yes | No | Events |
| 19 | GET | `/api/events/stats/user-summary` | Yes | No | Events |
| 20 | GET | `/api/events/:event_id/records` | Yes | No | Records |
| 21 | POST | `/api/events/:event_id/records` | Yes | No | Records |
| 22 | PUT | `/api/records/:record_id` | Yes | No | Records |
| 23 | DELETE | `/api/records/:record_id` | Yes | No | Records |
| 24 | POST | `/api/records/:record_id/approve` | Yes | No* | Records |
| 25 | POST | `/api/records/:record_id/reimburse` | Yes | No* | Records |
| 26 | GET | `/api/records/:record_id/download-invoice` | Yes | No | Records |
| 27 | GET | `/api/records/:record_id/preview-invoice` | Yes | No | Records |
| 28 | POST | `/api/records/:record_id/re-parse-invoice` | Yes | No | Records |
| 29 | GET | `/api/invoices` | Yes | No | Invoices |
| 30 | POST | `/api/invoices` | Yes | No | Invoices |
| 31 | PUT | `/api/invoices/:invoice_id` | Yes | No | Invoices |
| 32 | DELETE | `/api/invoices/:invoice_id` | Yes | No | Invoices |
| 33 | POST | `/api/invoices/:invoice_id/approve` | Yes | No* | Invoices |
| 34 | POST | `/api/invoices/:invoice_id/reimburse` | Yes | No* | Invoices |
| 35 | POST | `/api/invoices/batch-reimburse` | Yes | No* | Invoices |
| 36 | GET | `/api/invoices/:invoice_id/preview` | Yes | No | Invoices |
| 37 | POST | `/api/invoices/:invoice_id/generate-preview` | Yes | No | Invoices |
| 38 | GET | `/api/invoices/:invoice_id/download` | Yes | No | Invoices |
| 39 | GET | `/api/vouchers` | Yes | No | Vouchers |
| 40 | POST | `/api/vouchers` | Yes | No | Vouchers |
| 41 | PUT | `/api/vouchers/:voucher_id` | Yes | No | Vouchers |
| 42 | DELETE | `/api/vouchers/:voucher_id` | Yes | No | Vouchers |
| 43 | GET | `/api/vouchers/:voucher_id/download` | Yes | No | Vouchers |
| 44 | POST | `/api/vouchers/batch-reimburse` | Yes | No* | Vouchers |
| 45 | GET | `/api/check-file-md5` | Yes | No | Vouchers |
| 46 | POST | `/api/upload-file` | Yes | No | Parse |
| 47 | POST | `/api/parse-image` | Yes | No | Parse |
| 48 | POST | `/api/parse-invoice` | Yes | No | Parse |
| 49 | GET | `/api/invoices/:file_key/preview` | Yes | No | Parse |
| 50 | GET | `/api/invoices/:file_key/download` | Yes | No | Parse |
| 51 | GET | `/api/invitation-codes` | Yes | No* | InvCodes |
| 52 | POST | `/api/invitation-codes` | Yes | No* | InvCodes |
| 53 | POST | `/api/invitation-codes/verify` | No | No | InvCodes |
| 54 | POST | `/api/invitation-codes/:id/toggle` | Yes | No* | InvCodes |
| 55 | DELETE | `/api/invitation-codes/:id` | Yes | Yes | InvCodes |
| 56 | GET | `/api/system/config` | Yes | Yes | System |
| 57 | PUT | `/api/system/config` | Yes | Yes | System |
| 58 | GET | `/api/system/check-update` | Yes | Yes | System |
| 59 | POST | `/api/system/test-model` | Yes | Yes | System |
| 60 | POST | `/api/system/backup` | Yes | Yes | System |
| 61 | GET | `/api/system/backups` | Yes | Yes | System |
| 62 | GET | `/api/system/backup/:id/download` | Yes | Yes | System |
| 63 | DELETE | `/api/system/backup/:id` | Yes | Yes | System |
| 64 | POST | `/api/system/backup/restore/:id` | Yes | Yes | System |
| 65 | GET | `/api/system/backup/config` | Yes | Yes | System |
| 66 | PUT | `/api/system/backup/config` | Yes | Yes | System |
| 67 | POST | `/api/events/:event_id/export` | Yes | No | Export |
| 68 | GET | `/api/events/:event_id/export/status` | Yes | No | Export |
| 69 | GET | `/api/events/:event_id/export/download` | Yes | No | Export |
| 70 | GET | `/uploads/<path:filename>` | No | No | Static |
| 71 | GET | `/api/uploads/<path:filename>` | No | No | Static |

> \* 表示仅特定角色可访问（admin/teacher/student_admin）

---

> 文档生成日期：2026-06-04
> 项目：EasyInvoiceMgr
> 当前版本（dev分支）：1.3.2+
