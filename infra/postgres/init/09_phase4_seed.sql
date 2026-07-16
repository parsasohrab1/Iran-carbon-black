-- Phase 4 seed: training catalog for 350+ workforce rollout

INSERT INTO training.courses (id, title, description, domain, duration_minutes, target_roles, is_mandatory, content_url) VALUES
    ('TRN-SEC-01', 'امنیت سایبری و 2FA', 'آموزش احراز هویت دو مرحله‌ای و حفاظت از حساب کاربری', 'security', 45,
     '["operator","admin","manager"]'::jsonb, TRUE, '/training/sec-01'),
    ('TRN-EN-01', 'نگهداری پیش‌بینی‌کننده', 'کار با هشدارهای RUL و برنامه‌ریزی تعمیرات', 'energy', 90,
     '["operator","maintenance"]'::jsonb, TRUE, '/training/en-01'),
    ('TRN-QC-01', 'کنترل کیفیت هوشمند', 'ناهنجاری فرآیند و توصیه‌های بهینه‌سازی', 'quality', 75,
     '["operator","quality"]'::jsonb, TRUE, '/training/qc-01'),
    ('TRN-DM-01', 'تولید مبتنی بر تقاضا', 'خواندن پیش‌بینی تقاضا و برنامه تولید', 'demand', 60,
     '["planner","manager"]'::jsonb, TRUE, '/training/dm-01'),
    ('TRN-SC-01', 'خرید هوشمند مواد اولیه', 'پیشنهاد زمان خرید و مناقصات', 'supply', 60,
     '["procurement"]'::jsonb, FALSE, '/training/sc-01'),
    ('TRN-SM-01', 'فروش و CRM', 'پیش‌بینی فروش و مدیریت مشتریان کلیدی', 'sales', 60,
     '["sales","manager"]'::jsonb, FALSE, '/training/sm-01'),
    ('TRN-FI-01', 'داشبورد مدیریتی مالی', 'خواندن KPIها و جریان نقدی', 'finance', 45,
     '["finance","manager","executive"]'::jsonb, TRUE, '/training/fi-01'),
    ('TRN-CH-01', 'مدیریت تغییر سازمانی', 'پذیرش سیستم‌های AI و کاهش مقاومت', 'change', 90,
     '["all"]'::jsonb, TRUE, '/training/ch-01')
ON CONFLICT DO NOTHING;

INSERT INTO training.change_requests (title, description, domain, status, impact_level, created_by)
VALUES
    ('اجباری‌سازی 2FA برای تمام کاربران', 'فعال‌سازی اجباری احراز هویت دو مرحله‌ای در محیط production', 'security', 'proposed', 'high', 'admin'),
    ('استقرار داشبورد هیئت‌مدیره', 'انتشار داشبورد یکپارچه مالی-عملیاتی برای مدیران', 'finance', 'accepted', 'medium', 'admin'),
    ('پایلوت MQTT کیفیت روی خط 1', 'اتصال داده فرآیند کیفیت به ingestion', 'quality', 'deployed', 'medium', 'admin');

-- Mark admin must change default password in hardened deployments
UPDATE platform.users
SET must_change_password = TRUE,
    password_changed_at = NOW() - INTERVAL '180 days'
WHERE username = 'admin';
