-- Phase 4 seed: training catalog for 350+ workforce rollout

INSERT INTO training.courses (id, title, description, domain, duration_minutes, target_roles, is_mandatory, content_url) VALUES
    ('TRN-SEC-01', 'Cybersecurity and 2FA', 'Training on two-factor authentication and user account protection', 'security', 45,
     '["operator","admin","manager"]'::jsonb, TRUE, '/training/sec-01'),
    ('TRN-EN-01', 'Predictive maintenance', 'Working with RUL alerts and maintenance planning', 'energy', 90,
     '["operator","maintenance"]'::jsonb, TRUE, '/training/en-01'),
    ('TRN-QC-01', 'Smart quality control', 'Process anomalies and optimization recommendations', 'quality', 75,
     '["operator","quality"]'::jsonb, TRUE, '/training/qc-01'),
    ('TRN-DM-01', 'Demand-driven manufacturing', 'Reading the demand forecast and production plan', 'demand', 60,
     '["planner","manager"]'::jsonb, TRUE, '/training/dm-01'),
    ('TRN-SC-01', 'Smart raw material purchasing', 'Purchase timing suggestions and tenders', 'supply', 60,
     '["procurement"]'::jsonb, FALSE, '/training/sc-01'),
    ('TRN-SM-01', 'Sales and CRM', 'Sales forecasting and key customer management', 'sales', 60,
     '["sales","manager"]'::jsonb, FALSE, '/training/sm-01'),
    ('TRN-FI-01', 'Financial management dashboard', 'Reading KPIs and cash flow', 'finance', 45,
     '["finance","manager","executive"]'::jsonb, TRUE, '/training/fi-01'),
    ('TRN-CH-01', 'Organizational change management', 'Adoption of AI systems and reducing resistance', 'change', 90,
     '["all"]'::jsonb, TRUE, '/training/ch-01')
ON CONFLICT DO NOTHING;

INSERT INTO training.change_requests (title, description, domain, status, impact_level, created_by)
VALUES
    ('Enforce 2FA for all users', 'Mandatory activation of two-factor authentication in the production environment', 'security', 'proposed', 'high', 'admin'),
    ('Deploy the board dashboard', 'Publishing an integrated financial-operational dashboard for managers', 'finance', 'accepted', 'medium', 'admin'),
    ('Quality MQTT pilot on line 1', 'Connecting quality process data to ingestion', 'quality', 'deployed', 'medium', 'admin');

-- Mark admin must change default password in hardened deployments
UPDATE platform.users
SET must_change_password = TRUE,
    password_changed_at = NOW() - INTERVAL '180 days'
WHERE username = 'admin';
