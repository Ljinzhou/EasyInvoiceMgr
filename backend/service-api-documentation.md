# 服务层接口文档

## 1. 接口概述

本文档定义了EasyInvoiceMgr系统的服务层API接口，包括用户管理、赛事管理、发票管理等功能模块。所有接口均采用RESTful设计风格，使用JSON格式进行数据交互。

## 2. 认证方式

所有需要认证的接口均采用JWT（JSON Web Token）认证机制。客户端需要在请求头中添加以下认证信息：

```
Authorization: Bearer {token}
```

## 3. 响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

### 错误响应

```json
{
  "code": 错误码,
  "message": "错误信息",
  "data": null
}
```

## 4. 接口定义

### 4.1 用户管理模块

#### 4.1.1 用户注册

- **接口路径**: `POST /api/users/register`
- **请求参数**:
  ```json
  {
    "username": "string",
    "password": "string",
    "real_name": "string",
    "email": "string",
    "phone": "string",
    "user_type": "admin/teacher/student_admin/student",
    "organization": "string",
    "student_or_staff_id": "string"
  }
  ```
- **响应数据**:
  ```json
  {
    "user_id": "bigint",
    "username": "string",
    "real_name": "string",
    "email": "string",
    "phone": "string",
    "user_type": "string",
    "organization": "string",
    "student_or_staff_id": "string",
    "account_status": "active"
  }
  ```

#### 4.1.2 用户登录

- **接口路径**: `POST /api/users/login`
- **请求参数**:
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **响应数据**:
  ```json
  {
    "token": "string",
    "user": {
      "user_id": "bigint",
      "username": "string",
      "real_name": "string",
      "email": "string",
      "phone": "string",
      "user_type": "string",
      "organization": "string",
      "student_or_staff_id": "string"
    }
  }
  ```

#### 4.1.3 获取用户信息

- **接口路径**: `GET /api/users/{user_id}`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "user_id": "bigint",
    "username": "string",
    "real_name": "string",
    "email": "string",
    "phone": "string",
    "user_type": "string",
    "organization": "string",
    "student_or_staff_id": "string",
    "avatar_url": "string",
    "account_status": "string",
    "register_time": "timestamp",
    "last_login_time": "timestamp"
  }
  ```

#### 4.1.4 更新用户信息

- **接口路径**: `PUT /api/users/{user_id}`
- **认证方式**: JWT
- **请求参数**:
  ```json
  {
    "real_name": "string",
    "email": "string",
    "phone": "string",
    "organization": "string",
    "student_or_staff_id": "string",
    "avatar_url": "string"
  }
  ```
- **响应数据**:
  ```json
  {
    "user_id": "bigint",
    "username": "string",
    "real_name": "string",
    "email": "string",
    "phone": "string",
    "user_type": "string",
    "organization": "string",
    "student_or_staff_id": "string",
    "avatar_url": "string"
  }
  ```

#### 4.1.5 修改密码

- **接口路径**: `PUT /api/users/{user_id}/password`
- **认证方式**: JWT
- **请求参数**:
  ```json
  {
    "old_password": "string",
    "new_password": "string"
  }
  ```
- **响应数据**:
  ```json
  {
    "message": "密码修改成功"
  }
  ```

#### 4.1.6 禁用/启用用户

- **接口路径**: `PUT /api/users/{user_id}/status`
- **认证方式**: JWT (管理员权限)
- **请求参数**:
  ```json
  {
    "status": "active/disabled"
  }
  ```
- **响应数据**:
  ```json
  {
    "user_id": "bigint",
    "account_status": "string"
  }
  ```

### 4.2 赛事管理模块

#### 4.2.1 创建赛事

- **接口路径**: `POST /api/events`
- **认证方式**: JWT (管理员/教师权限)
- **请求参数**:
  ```json
  {
    "event_name": "string",
    "description": "string",
    "category": "string",
    "location": "string",
    "event_start_time": "timestamp",
    "event_end_time": "timestamp",
    "upload_start_time": "timestamp",
    "upload_end_time": "timestamp",
    "leader_id": "bigint",
    "total_budget": "decimal"
  }
  ```
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "event_name": "string",
    "description": "string",
    "category": "string",
    "location": "string",
    "status": "ongoing",
    "event_start_time": "timestamp",
    "event_end_time": "timestamp",
    "upload_start_time": "timestamp",
    "upload_end_time": "timestamp",
    "creator_id": "bigint",
    "leader_id": "bigint",
    "total_budget": "decimal",
    "reimbursed_amount": "decimal",
    "remaining_budget": "decimal",
    "invoice_count": "integer",
    "invoice_total_amount": "decimal"
  }
  ```

#### 4.2.2 获取赛事列表

- **接口路径**: `GET /api/events`
- **认证方式**: JWT
- **请求参数**:
  - `page`: 页码 (可选)
  - `page_size`: 每页数量 (可选)
  - `status`: 赛事状态 (可选)
  - `category`: 赛事类别 (可选)
- **响应数据**:
  ```json
  {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "data": [
      {
        "event_id": "bigint",
        "event_name": "string",
        "description": "string",
        "category": "string",
        "location": "string",
        "status": "string",
        "event_start_time": "timestamp",
        "event_end_time": "timestamp",
        "total_budget": "decimal",
        "reimbursed_amount": "decimal",
        "remaining_budget": "decimal",
        "invoice_count": "integer"
      }
    ]
  }
  ```

#### 4.2.3 获取赛事详情

- **接口路径**: `GET /api/events/{event_id}`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "event_name": "string",
    "description": "string",
    "category": "string",
    "location": "string",
    "status": "string",
    "event_start_time": "timestamp",
    "event_end_time": "timestamp",
    "upload_start_time": "timestamp",
    "upload_end_time": "timestamp",
    "creator_id": "bigint",
    "leader_id": "bigint",
    "total_budget": "decimal",
    "reimbursed_amount": "decimal",
    "remaining_budget": "decimal",
    "invoice_count": "integer",
    "invoice_total_amount": "decimal"
  }
  ```

#### 4.2.4 更新赛事信息

- **接口路径**: `PUT /api/events/{event_id}`
- **认证方式**: JWT (管理员/教师权限)
- **请求参数**:
  ```json
  {
    "event_name": "string",
    "description": "string",
    "category": "string",
    "location": "string",
    "event_start_time": "timestamp",
    "event_end_time": "timestamp",
    "upload_start_time": "timestamp",
    "upload_end_time": "timestamp",
    "leader_id": "bigint",
    "total_budget": "decimal"
  }
  ```
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "event_name": "string",
    "description": "string",
    "category": "string",
    "location": "string",
    "status": "string",
    "event_start_time": "timestamp",
    "event_end_time": "timestamp",
    "upload_start_time": "timestamp",
    "upload_end_time": "timestamp",
    "leader_id": "bigint",
    "total_budget": "decimal"
  }
  ```

#### 4.2.5 结束赛事

- **接口路径**: `PUT /api/events/{event_id}/status`
- **认证方式**: JWT (管理员/教师权限)
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "status": "finished"
  }
  ```

### 4.3 用户-赛事关联模块

#### 4.3.1 添加赛事成员

- **接口路径**: `POST /api/event-members`
- **认证方式**: JWT (管理员/教师/学生管理员权限)
- **请求参数**:
  ```json
  {
    "event_id": "bigint",
    "user_id": "bigint",
    "role_in_event": "teacher/student_admin/student"
  }
  ```
- **响应数据**:
  ```json
  {
    "id": "bigint",
    "event_id": "bigint",
    "user_id": "bigint",
    "role_in_event": "string",
    "join_time": "timestamp"
  }
  ```

#### 4.3.2 获取赛事成员列表

- **接口路径**: `GET /api/events/{event_id}/members`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "members": [
      {
        "user_id": "bigint",
        "username": "string",
        "real_name": "string",
        "role_in_event": "string",
        "join_time": "timestamp"
      }
    ]
  }
  ```

#### 4.3.3 更新成员角色

- **接口路径**: `PUT /api/event-members/{id}`
- **认证方式**: JWT (管理员/教师权限)
- **请求参数**:
  ```json
  {
    "role_in_event": "teacher/student_admin/student"
  }
  ```
- **响应数据**:
  ```json
  {
    "id": "bigint",
    "event_id": "bigint",
    "user_id": "bigint",
    "role_in_event": "string"
  }
  ```

#### 4.3.4 移除赛事成员

- **接口路径**: `DELETE /api/event-members/{id}`
- **认证方式**: JWT (管理员/教师权限)
- **响应数据**:
  ```json
  {
    "message": "成员已移除"
  }
  ```

#### 4.3.5 获取用户参与的赛事

- **接口路径**: `GET /api/users/{user_id}/events`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "user_id": "bigint",
    "events": [
      {
        "event_id": "bigint",
        "event_name": "string",
        "status": "string",
        "role_in_event": "string",
        "join_time": "timestamp"
      }
    ]
  }
  ```

### 4.4 发票管理模块

#### 4.4.1 上传发票

- **接口路径**: `POST /api/invoices`
- **认证方式**: JWT
- **请求参数**:
  - `form-data` 格式
    - `event_id`: 赛事ID (number)
    - `invoice_type`: 发票类型 (string)
    - `invoice_code`: 发票代码 (string, 可选)
    - `invoice_number`: 发票号码 (string, 可选)
    - `tax_number`: 发票税号 (string)
    - `project_name`: 发票项目名称 (string)
    - `amount`: 发票金额 (decimal)
    - `invoice_date`: 开票日期 (date)
    - `remarks`: 备注信息 (string, 可选)
    - `file`: 发票图片文件 (file)

- **响应数据**:
  ```json
  {
    "invoice_id": "bigint",
    "event_id": "bigint",
    "uploader_id": "bigint",
    "file_name": "string",
    "file_md5": "string",
    "image_url": "string",
    "invoice_type": "string",
    "invoice_code": "string",
    "invoice_number": "string",
    "tax_number": "string",
    "project_name": "string",
    "amount": "decimal",
    "invoice_date": "date",
    "status": "approved",
    "remarks": "string"
  }
  ```

#### 4.4.2 获取发票列表

- **接口路径**: `GET /api/invoices`
- **认证方式**: JWT
- **请求参数**:
  - `page`: 页码 (可选)
  - `page_size`: 每页数量 (可选)
  - `event_id`: 赛事ID (可选)
  - `status`: 发票状态 (可选)
  - `uploader_id`: 上传人ID (可选)
  - `invoice_date_start`: 开票日期开始 (可选)
  - `invoice_date_end`: 开票日期结束 (可选)
- **响应数据**:
  ```json
  {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "data": [
      {
        "invoice_id": "bigint",
        "event_id": "bigint",
        "event_name": "string",
        "uploader_id": "bigint",
        "uploader_name": "string",
        "file_name": "string",
        "image_url": "string",
        "invoice_type": "string",
        "project_name": "string",
        "amount": "decimal",
        "invoice_date": "date",
        "status": "string",
        "remarks": "string",
        "created_at": "timestamp"
      }
    ]
  }
  ```

#### 4.4.3 获取发票详情

- **接口路径**: `GET /api/invoices/{invoice_id}`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "invoice_id": "bigint",
    "event_id": "bigint",
    "event_name": "string",
    "uploader_id": "bigint",
    "uploader_name": "string",
    "file_name": "string",
    "file_md5": "string",
    "image_url": "string",
    "invoice_type": "string",
    "invoice_code": "string",
    "invoice_number": "string",
    "tax_number": "string",
    "project_name": "string",
    "amount": "decimal",
    "invoice_date": "date",
    "status": "string",
    "reviewer_id": "bigint",
    "reviewer_name": "string",
    "review_time": "timestamp",
    "rejection_reason": "string",
    "remarks": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp"
  }
  ```

#### 4.4.4 更新发票信息

- **接口路径**: `PUT /api/invoices/{invoice_id}`
- **认证方式**: JWT
- **请求参数**:
  ```json
  {
    "invoice_type": "string",
    "invoice_code": "string",
    "invoice_number": "string",
    "tax_number": "string",
    "project_name": "string",
    "amount": "decimal",
    "invoice_date": "date",
    "remarks": "string"
  }
  ```
- **响应数据**:
  ```json
  {
    "invoice_id": "bigint",
    "invoice_type": "string",
    "invoice_code": "string",
    "invoice_number": "string",
    "tax_number": "string",
    "project_name": "string",
    "amount": "decimal",
    "invoice_date": "date",
    "remarks": "string",
    "updated_at": "timestamp"
  }
  ```

#### 4.4.5 删除发票

- **接口路径**: `DELETE /api/invoices/{invoice_id}`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "message": "发票已删除"
  }
  ```

#### 4.4.6 审核发票

- **接口路径**: `PUT /api/invoices/{invoice_id}/review`
- **认证方式**: JWT (管理员/教师/学生管理员权限)
- **请求参数**:
  ```json
  {
    "status": "approved/rejected",
    "rejection_reason": "string" // 拒绝时必填
  }
  ```
- **响应数据**:
  ```json
  {
    "invoice_id": "bigint",
    "status": "string",
    "reviewer_id": "bigint",
    "review_time": "timestamp",
    "rejection_reason": "string"
  }
  ```

#### 4.4.7 获取赛事发票统计

- **接口路径**: `GET /api/events/{event_id}/invoice-statistics`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "event_id": "bigint",
    "invoice_count": "integer",
    "invoice_total_amount": "decimal",
    "approved_count": "integer",
    "approved_amount": "decimal",
    "pending_count": "integer",
    "pending_amount": "decimal",
    "rejected_count": "integer",
    "rejected_amount": "decimal"
  }
  ```

### 4.5 审核记录模块

#### 4.5.1 获取发票审核记录

- **接口路径**: `GET /api/invoices/{invoice_id}/audit-logs`
- **认证方式**: JWT
- **响应数据**:
  ```json
  {
    "invoice_id": "bigint",
    "logs": [
      {
        "log_id": "bigint",
        "reviewer_id": "bigint",
        "reviewer_name": "string",
        "action": "string",
        "comment": "string",
        "created_at": "timestamp"
      }
    ]
  }
  ```

#### 4.5.2 获取用户审核记录

- **接口路径**: `GET /api/users/{user_id}/audit-logs`
- **认证方式**: JWT
- **请求参数**:
  - `page`: 页码 (可选)
  - `page_size`: 每页数量 (可选)
  - `start_time`: 开始时间 (可选)
  - `end_time`: 结束时间 (可选)
- **响应数据**:
  ```json
  {
    "total": "integer",
    "page": "integer",
    "page_size": "integer",
    "data": [
      {
        "log_id": "bigint",
        "invoice_id": "bigint",
        "invoice_project_name": "string",
        "invoice_amount": "decimal",
        "action": "string",
        "comment": "string",
        "created_at": "timestamp"
      }
    ]
  }
  ```

## 5. 错误码定义

| 错误码 | 描述 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 501 | 接口未实现 |
| 1001 | 用户名已存在 |
| 1002 | 密码错误 |
| 1003 | 用户不存在 |
| 2001 | 赛事不存在 |
| 2002 | 赛事已结束 |
| 3001 | 发票不存在 |
| 3002 | 发票上传失败 |
| 3003 | 发票已审核 |
