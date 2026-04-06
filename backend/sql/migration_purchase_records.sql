-- ============================================
-- 购买记录表迁移脚本
-- 将发票管理升级为购买记录管理
-- ============================================

-- 1. 创建购买记录表
CREATE TABLE IF NOT EXISTS purchase_records (
    record_id BIGSERIAL PRIMARY KEY,
    
    -- 关联信息
    event_id BIGINT NOT NULL REFERENCES events(event_id),
    uploader_id BIGINT NOT NULL REFERENCES users(user_id),
    
    -- 购物基本信息（必填）
    item_name VARCHAR(200) NOT NULL, -- 购买物品名称/项目名称
    purchase_platform VARCHAR(100) NOT NULL, -- 购买平台：淘宝、闲鱼、拼多多等
    purchase_date DATE NOT NULL, -- 购物时间
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0), -- 实际开销
    
    -- 购物凭证（必填）
    receipt_image_url TEXT NOT NULL, -- 购物凭证图片URL
    receipt_image_name VARCHAR(255), -- 凭证文件名
    receipt_file_md5 VARCHAR(64), -- 用于去重校验
    
    -- 发票信息（可选，后续补充或同时上传）
    has_invoice BOOLEAN DEFAULT FALSE, -- 是否有发票
    invoice_url TEXT, -- 发票文件URL
    invoice_name VARCHAR(255), -- 发票文件名
    invoice_md5 VARCHAR(64), -- 发票MD5
    invoice_preview_url TEXT, -- 发票预览图
    invoice_type VARCHAR(50), -- 发票类型：餐饮、交通、住宿等
    invoice_number VARCHAR(50), -- 发票号码
    total_amount DECIMAL(12, 2) DEFAULT 0.00, -- 价税合计（系统提取）
    invoice_date DATE, -- 开票日期（系统提取）
    
    -- 审核和报销状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/approved/rejected
    is_reimbursed BOOLEAN DEFAULT FALSE,
    reimbursed_at TIMESTAMP WITH TIME ZONE,
    reviewer_id BIGINT REFERENCES users(user_id),
    review_time TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    
    -- 辅助信息
    remarks TEXT, -- 备注
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    extra_fields JSONB
);

-- 2. 创建索引
CREATE INDEX idx_purchase_records_event ON purchase_records(event_id);
CREATE INDEX idx_purchase_records_uploader ON purchase_records(uploader_id);
CREATE INDEX idx_purchase_records_status ON purchase_records(status);
CREATE INDEX idx_purchase_records_invoice ON purchase_records(has_invoice);
CREATE INDEX idx_purchase_records_date ON purchase_records(purchase_date);
CREATE INDEX idx_purchase_records_md5 ON purchase_records(receipt_file_md5);

-- 3. 添加触发器自动更新 updated_at
CREATE TRIGGER trigger_purchase_records_update 
BEFORE UPDATE ON purchase_records
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- 4. 更新赛事表字段（添加购买记录统计）
ALTER TABLE events ADD COLUMN IF NOT EXISTS purchase_record_count INTEGER DEFAULT 0;
ALTER TABLE events ADD COLUMN IF NOT EXISTS purchase_total_amount DECIMAL(12, 2) DEFAULT 0.00;
ALTER TABLE events ADD COLUMN IF NOT EXISTS pending_reimburse_amount DECIMAL(12, 2) DEFAULT 0.00;

COMMENT ON COLUMN purchase_records.item_name IS '购买物品名称';
COMMENT ON COLUMN purchase_records.purchase_platform IS '购买平台：淘宝、闲鱼、拼多多、京东等';
COMMENT ON COLUMN purchase_records.amount IS '实际开销金额';
COMMENT ON COLUMN purchase_records.receipt_image_url IS '购物凭证图片URL';
COMMENT ON COLUMN purchase_records.has_invoice IS '是否已上传发票';
COMMENT ON COLUMN purchase_records.total_amount IS '价税合计（发票信息，系统OCR提取）';
COMMENT ON COLUMN purchase_records.status IS '状态：pending待审核/approved已通过/rejected已拒绝';

-- ============================================
-- 数据验证查询
-- ============================================
SELECT COUNT(*) as total_records FROM purchase_records;
