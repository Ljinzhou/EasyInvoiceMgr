-- ============================================
-- 1. 枚举类型定义
-- ============================================

-- 用户角色类型
CREATE TYPE user_type_enum AS ENUM ('admin', 'teacher', 'student_admin', 'student');

-- 赛事状态
CREATE TYPE event_status_enum AS ENUM ('ongoing', 'finished');

-- 发票审核状态
CREATE TYPE invoice_status_enum AS ENUM ('approved', 'pending', 'rejected');

-- 账号状态
CREATE TYPE account_status_enum AS ENUM ('active', 'disabled');

-- 赛事中成员的角色
CREATE TYPE event_role_enum AS ENUM ('teacher', 'student_admin', 'student');

-- ============================================
-- 2. 核心数据表定义
-- ============================================

-- 2.1 用户表
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- 存储加密后的密码
    real_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    user_type user_type_enum NOT NULL DEFAULT 'student',
    organization VARCHAR(100), -- 所属组织/部门
    student_or_staff_id VARCHAR(50), -- 学号/工号
    avatar_url TEXT, -- 头像URL
    account_status account_status_enum NOT NULL DEFAULT 'active',
    register_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    extra_fields JSONB -- 预留扩展字段
);

-- 2.2 赛事表
CREATE TABLE events (
    event_id BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(200) NOT NULL,
    description TEXT,
    status event_status_enum NOT NULL DEFAULT 'ongoing',
    
    -- 时间管理
    event_start_time TIMESTAMP WITH TIME ZONE,
    event_end_time TIMESTAMP WITH TIME ZONE,
    upload_start_time TIMESTAMP WITH TIME ZONE,
    upload_end_time TIMESTAMP WITH TIME ZONE,
    
    -- 人员管理 (创建人/负责人)
    creator_id BIGINT NOT NULL REFERENCES users(user_id),
    leader_id BIGINT REFERENCES users(user_id), -- 赛事负责人ID
    
    -- 财务信息
    total_budget DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_budget >= 0),
    reimbursed_amount DECIMAL(12, 2) DEFAULT 0.00 CHECK (reimbursed_amount >= 0),
    -- 剩余资金通常通过计算得出，但为了高频查询性能在此冗余存储
    remaining_budget DECIMAL(12, 2) DEFAULT 0.00 CHECK (remaining_budget >= 0),
    invoice_count INTEGER DEFAULT 0, -- 发票总数量
    invoice_total_amount DECIMAL(12, 2) DEFAULT 0.00, -- 发票总金额
    voucher_count INTEGER DEFAULT 0, -- 凭证总数量
    voucher_total_amount DECIMAL(12, 2) DEFAULT 0.00, -- 凭证总金额
    need_invoice_review BOOLEAN NOT NULL DEFAULT TRUE, -- 是否需要审核发票
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    extra_fields JSONB
);

-- 2.3 用户-赛事关联表 (event_members)
-- 实现多对多关系，并定义用户在具体赛事中的角色
CREATE TABLE event_members (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role_in_event event_role_enum NOT NULL, -- 指导老师、学生管理员、参赛学生
    join_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- 确保同一赛事中同一用户只有一条有效记录
    UNIQUE (event_id, user_id) 
);

-- 2.4 发票表
CREATE TABLE invoices (
    invoice_id BIGSERIAL PRIMARY KEY,
    
    -- 关联信息
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    uploader_id BIGINT NOT NULL REFERENCES users(user_id), -- 上传人
    
    -- 文件信息 (对象存储)
    file_name VARCHAR(255) NOT NULL,
    file_md5 VARCHAR(64), -- 用于文件去重校验
    image_url TEXT NOT NULL, -- 对象存储URL
    preview_image_url TEXT, -- 预览图URL（PDF转JPG后存储）
    
    -- 发票具体信息
    invoice_type VARCHAR(50), -- 发票类型 (如：餐饮、交通、住宿)
    invoice_number VARCHAR(50), -- 发票号码 (可选)
    project_name VARCHAR(200) NOT NULL, -- 发票项目名称
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0), -- 不含税金额
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0), -- 价税合计（系统自动提取，用户不可修改）
    invoice_date DATE NOT NULL, -- 开票日期
    
    -- 审核信息 (当前状态)
    status invoice_status_enum NOT NULL DEFAULT 'approved', -- 默认审核通过
    is_reimbursed BOOLEAN NOT NULL DEFAULT FALSE, -- 是否已报销
    reimbursed_at TIMESTAMP WITH TIME ZONE, -- 报销时间
    reviewer_id BIGINT REFERENCES users(user_id), -- 当前审核人ID
    review_time TIMESTAMP WITH TIME ZONE, -- 当前审核时间
    rejection_reason TEXT, -- 拒绝原因
    
    -- 辅助信息
    remarks TEXT, -- 备注信息
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    extra_fields JSONB
);

-- 2.6 凭证表 (vouchers)
CREATE TABLE vouchers (
    voucher_id BIGSERIAL PRIMARY KEY,
    
    -- 关联信息
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    uploader_id BIGINT NOT NULL REFERENCES users(user_id),
    
    -- 文件信息
    file_name VARCHAR(255) NOT NULL,
    file_md5 VARCHAR(64), -- 用于文件去重校验
    file_url TEXT NOT NULL, -- 对象存储URL
    
    -- 凭证具体信息
    item_name VARCHAR(200) NOT NULL, -- 物品名称
    voucher_type VARCHAR(50), -- 类型（如：办公用品、设备、耗材等）
    purchase_channel VARCHAR(100), -- 购买渠道
    purchase_date DATE, -- 购入日期
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0), -- 购入金额
    
    -- 报销状态
    is_reimbursed BOOLEAN NOT NULL DEFAULT FALSE, -- 是否已报销
    reimbursed_at TIMESTAMP WITH TIME ZONE, -- 报销时间
    
    -- 辅助信息
    remarks TEXT, -- 备注
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 2.8 购买记录表 (purchase_records)
CREATE TABLE purchase_records (
    record_id BIGSERIAL PRIMARY KEY,

    -- 关联信息
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    uploader_id BIGINT NOT NULL REFERENCES users(user_id),

    -- 物品信息
    item_name VARCHAR(200) NOT NULL,
    purchase_platform VARCHAR(100) NOT NULL,
    purchase_date DATE NOT NULL,
    amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (amount >= 0),

    -- 购物凭证文件
    receipt_image_url TEXT NOT NULL,
    receipt_image_name VARCHAR(255),
    receipt_file_md5 VARCHAR(64),

    -- 发票信息
    has_invoice BOOLEAN DEFAULT FALSE,
    invoice_file_key TEXT,
    invoice_preview_key TEXT,
    invoice_original_filename VARCHAR(255),
    invoice_md5 VARCHAR(64),
    invoice_type VARCHAR(50),
    invoice_number VARCHAR(50),
    invoice_tax_number VARCHAR(50),
    total_amount DECIMAL(12, 2) DEFAULT 0.00 CHECK (total_amount >= 0),
    invoice_date DATE,

    -- 审核信息
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_reimbursed BOOLEAN NOT NULL DEFAULT FALSE,
    reimbursed_at TIMESTAMP WITH TIME ZONE,
    reviewer_id BIGINT REFERENCES users(user_id),
    review_time TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- 辅助信息
    remarks TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    extra_fields JSONB
);

-- 2.9 导出任务表 (export_tasks)
CREATE TABLE export_tasks (
    task_id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    requester_id BIGINT NOT NULL REFERENCES users(user_id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/processing/completed/failed
    columns_config JSONB,
    file_path TEXT,
    file_size BIGINT,
    data_snapshot_time TIMESTAMP WITH TIME ZONE,
    record_count INTEGER,
    error_message TEXT,
    progress_percent INTEGER DEFAULT 0,
    progress_message VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- 2.7 邀请码表 (invitation_codes)
CREATE TABLE invitation_codes (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL, -- 邀请码
    target_user_type user_type_enum NOT NULL DEFAULT 'student', -- 目标用户类型
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- 过期时间
    max_uses INTEGER NOT NULL DEFAULT -1, -- 最大使用次数(-1为无限)
    used_count INTEGER NOT NULL DEFAULT 0, -- 已使用次数
    created_by BIGINT NOT NULL REFERENCES users(user_id), -- 创建人
    is_active BOOLEAN NOT NULL DEFAULT TRUE, -- 是否有效
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.10 系统配置表 (system_configs)
-- 键值对存储系统配置，支持加密敏感字段
CREATE TABLE system_configs (
    id BIGSERIAL PRIMARY KEY,
    config_key VARCHAR(128) UNIQUE NOT NULL,
    config_value TEXT NOT NULL DEFAULT '',
    is_encrypted BOOLEAN NOT NULL DEFAULT FALSE,
    description VARCHAR(255),
    updated_by BIGINT REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.5 审核记录表 (audit_logs)
-- 记录发票的每一次状态变更，便于追溯
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(invoice_id),
    reviewer_id BIGINT NOT NULL REFERENCES users(user_id),
    action invoice_status_enum NOT NULL, -- 审核动作
    comment TEXT, -- 审核意见
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. 索引设计 (性能优化)
-- ============================================

-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_email ON users(email);

-- 赛事表索引
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_creator ON events(creator_id);
CREATE INDEX idx_events_time ON events(event_start_time, event_end_time);

-- 关联表索引
CREATE INDEX idx_event_members_user ON event_members(user_id);
CREATE INDEX idx_event_members_event ON event_members(event_id);
-- 复合索引用于快速查找某用户在某赛事下的角色
CREATE INDEX idx_event_members_composite ON event_members(event_id, user_id, role_in_event);

-- 发票表索引 (高频查询字段)
CREATE INDEX idx_invoices_event ON invoices(event_id);
CREATE INDEX idx_invoices_uploader ON invoices(uploader_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_md5 ON invoices(file_md5); -- 用于秒传/去重检测
CREATE INDEX idx_invoices_date ON invoices(invoice_date);

-- 系统配置表索引
CREATE INDEX idx_system_configs_key ON system_configs(config_key);

-- 审核记录索引
CREATE INDEX idx_audit_logs_invoice ON audit_logs(invoice_id);
CREATE INDEX idx_audit_logs_reviewer ON audit_logs(reviewer_id);

-- 凭证表索引
CREATE INDEX idx_vouchers_event ON vouchers(event_id);
CREATE INDEX idx_vouchers_uploader ON vouchers(uploader_id);
CREATE INDEX idx_vouchers_md5 ON vouchers(file_md5);

-- 邀请码索引
CREATE INDEX idx_invitation_codes_code ON invitation_codes(code);
CREATE INDEX idx_invitation_codes_creator ON invitation_codes(created_by);
CREATE INDEX idx_invitation_codes_active ON invitation_codes(is_active, expires_at);

-- 购买记录索引
CREATE INDEX idx_purchase_records_event ON purchase_records(event_id);
CREATE INDEX idx_purchase_records_uploader ON purchase_records(uploader_id);
CREATE INDEX idx_purchase_records_status ON purchase_records(status);

-- 导出任务索引
CREATE INDEX idx_export_tasks_event ON export_tasks(event_id);
CREATE INDEX idx_export_tasks_status ON export_tasks(status);

-- ============================================
-- 4. 触发器设计 (自动维护 updated_at)
-- ============================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有主要表添加更新时间触发器
CREATE TRIGGER trigger_users_update BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_events_update BEFORE UPDATE ON events
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_invoices_update BEFORE UPDATE ON invoices
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_event_members_update BEFORE UPDATE ON event_members
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_vouchers_update BEFORE UPDATE ON vouchers
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_purchase_records_update BEFORE UPDATE ON purchase_records
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_export_tasks_update BEFORE UPDATE ON export_tasks
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trigger_system_configs_update BEFORE UPDATE ON system_configs
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================
-- 5. 默认数据插入
-- ============================================

-- 管理员账户由应用启动时自动创建/更新（使用安全哈希），此处不再硬编码

