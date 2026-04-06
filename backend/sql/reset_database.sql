-- ============================================
-- 数据库重置脚本 - 清空所有业务数据
-- 保留表结构和系统配置
-- ============================================

-- 1. 关闭外键约束检查
SET session_replication_role = 'replica';

-- 2. 清空购买记录表（先删除有外键引用的表）
DELETE FROM purchase_records;
ALTER SEQUENCE IF EXISTS purchase_records_record_id_seq RESTART WITH 1;

-- 3. 清空发票记录表
DELETE FROM invoices;
ALTER SEQUENCE IF EXISTS invoices_invoice_id_seq RESTART WITH 1;

-- 4. 清空赛事成员表
DELETE FROM event_members;
ALTER SEQUENCE IF EXISTS event_members_id_seq RESTART WITH 1;

-- 5. 清空邀请码表
DELETE FROM invitation_codes;
ALTER SEQUENCE IF EXISTS invitation_codes_id_seq RESTART WITH 1;

-- 6. 清空赛事/项目表
DELETE FROM events;
ALTER SEQUENCE IF EXISTS events_event_id_seq RESTART WITH 1;

-- 7. 清空凭证表
DELETE FROM vouchers;
ALTER SEQUENCE IF EXISTS vouchers_voucher_id_seq RESTART WITH 1;

-- 8. 重置用户数据（保留admin账号）
-- 先查看当前用户
SELECT user_id, username, real_name, user_type, account_status FROM users;

-- 如果需要完全重置用户（除admin外），取消下面注释：
-- DELETE FROM users WHERE user_type != 'admin';
-- ALTER SEQUENCE IF EXISTS users_user_id_seq RESTART WITH 1;

-- 9. 重新开启外键约束检查
SET session_replication_role = 'origin';

-- 10. 验证清理结果
SELECT 
    (SELECT COUNT(*) FROM events) as events_count,
    (SELECT COUNT(*) FROM invoices) as invoices_count,
    (SELECT COUNT(*) FROM purchase_records) as purchases_count,
    (SELECT COUNT(*) FROM invitation_codes) as invite_codes_count,
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM event_members) as members_count;

-- ============================================
-- 对象存储清理说明：
-- ============================================
-- 
-- 如果使用本地文件存储，请手动删除以下目录中的文件：
--   - backend/static/uploads/invoices/
--   - backend/static/uploads/receipts/
--
-- 如果使用云存储（如阿里OSS、腾讯COS、AWS S3）：
--   1. 登录对应云服务控制台
--   2. 找到对应的存储桶(Bucket)
--   3. 删除 uploads 目录下的所有文件
--
-- 或者通过命令行工具清理（以阿里OSS为例）：
--   ossutil rm oss://your-bucket/uploads/ -r -f
