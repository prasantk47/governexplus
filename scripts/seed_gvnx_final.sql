-- GvnX Tenant: Managers, Approvers, Controls, Migration Mappings
-- Run: sudo -u postgres psql -d governexplus -f seed_gvnx_final.sql

-- 1. MANAGERS
UPDATE users SET manager_user_id='RAHUL00' WHERE tenant_id='gvnx' AND department='Finance' AND user_id!='RAHUL00';
UPDATE users SET manager_user_id='AMIT002' WHERE tenant_id='gvnx' AND department='IT' AND user_id!='AMIT002';
UPDATE users SET manager_user_id='SNEHA03' WHERE tenant_id='gvnx' AND department='HR' AND user_id!='SNEHA03';
UPDATE users SET manager_user_id='VIKRA04' WHERE tenant_id='gvnx' AND department='Procurement' AND user_id!='VIKRA04';
UPDATE users SET manager_user_id='ANJAL05' WHERE tenant_id='gvnx' AND department='Sales' AND user_id!='ANJAL05';
UPDATE users SET manager_user_id='PRASANT' WHERE tenant_id='gvnx' AND user_id IN ('RAHUL00','AMIT002','SNEHA03','VIKRA04','ANJAL05');
UPDATE users SET is_platform_user=true WHERE tenant_id='gvnx' AND user_id IN ('RAHUL00','AMIT002','SNEHA03','VIKRA04','ANJAL05','PRIYA01','RAJES06','SURES08','DEEPA09');

-- 2. APPROVERS
INSERT INTO approvers (tenant_id,approver_id,user_id,approver_name,approver_email,approver_type,scope,is_active,created_at,updated_at) VALUES
('gvnx','APR-FIN','RAHUL00','Rahul Sharma','rahul.sharma@gvnx.com','manager','{"department":"Finance"}',true,NOW(),NOW()),
('gvnx','APR-IT','AMIT002','Amit Kumar','amit.kumar@gvnx.com','manager','{"department":"IT"}',true,NOW(),NOW()),
('gvnx','APR-HR','SNEHA03','Sneha Reddy','sneha.reddy@gvnx.com','manager','{"department":"HR"}',true,NOW(),NOW()),
('gvnx','APR-PROC','VIKRA04','Vikram Singh','vikram.singh@gvnx.com','manager','{"department":"Procurement"}',true,NOW(),NOW()),
('gvnx','APR-SALES','ANJAL05','Anjali Gupta','anjali.gupta@gvnx.com','manager','{"department":"Sales"}',true,NOW(),NOW()),
('gvnx','APR-SEC','PRIYA01','Priya Patel','priya.patel@gvnx.com','security','{"scope":"all"}',true,NOW(),NOW()),
('gvnx','APR-RISK','RAJES06','Rajesh Nair','rajesh.nair@gvnx.com','risk_owner','{"scope":"all"}',true,NOW(),NOW()),
('gvnx','APR-COMP','SURES08','Suresh Iyer','suresh.iyer@gvnx.com','compliance','{"scope":"all"}',true,NOW(),NOW()),
('gvnx','APR-CISO','DEEPA09','Deepa Menon','deepa.menon@gvnx.com','ciso','{"scope":"all"}',true,NOW(),NOW()),
('gvnx','APR-CFO','PRASANT','Prasant','prasant@governexplus.com','executive','{"scope":"all"}',true,NOW(),NOW());

-- 3. APPROVAL RULES
INSERT INTO approval_rules (tenant_id,rule_id,rule_name,rule_type,conditions,approver_chain,priority,is_active,created_at,updated_at) VALUES
('gvnx','RULE-LOW','Low Risk','risk_based','{"risk_level":"low"}','["manager"]',1,true,NOW(),NOW()),
('gvnx','RULE-MED','Medium Risk','risk_based','{"risk_level":"medium"}','["manager","role_owner"]',2,true,NOW(),NOW()),
('gvnx','RULE-HIGH','High Risk','risk_based','{"risk_level":"high"}','["manager","security","risk_owner"]',3,true,NOW(),NOW()),
('gvnx','RULE-CRIT','Critical Risk','risk_based','{"risk_level":"critical"}','["manager","security","risk_owner","ciso","executive"]',4,true,NOW(),NOW());

-- 4. FIREFIGHTER CONFIGS
INSERT INTO firefighter_id_configs (tenant_id,firefighter_id,description,system_id,owner_user_id,controller_user_id,max_session_hours,max_extensions,requires_ticket,is_active,created_at,updated_at) VALUES
('gvnx','FF_SAP_001','Basis Emergency','SAP_PRD','AMIT002','PRIYA01',4,2,true,true,NOW(),NOW()),
('gvnx','FF_SAP_002','Finance Emergency','SAP_PRD','RAHUL00','SURES08',4,1,true,true,NOW(),NOW()),
('gvnx','FF_SAP_003','Security Emergency','SAP_PRD','DEEPA09','PRIYA01',2,1,true,true,NOW(),NOW());

-- 5. ROLE OWNERS
UPDATE roles SET owner_user_id='RAHUL00',owner_email='rahul.sharma@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'Z_FI%';
UPDATE roles SET owner_user_id='VIKRA04',owner_email='vikram.singh@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'Z_MM%';
UPDATE roles SET owner_user_id='ANJAL05',owner_email='anjali.gupta@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'Z_SD%';
UPDATE roles SET owner_user_id='SNEHA03',owner_email='sneha.reddy@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'Z_HR%';
UPDATE roles SET owner_user_id='AMIT002',owner_email='amit.kumar@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'Z_IT%';
UPDATE roles SET owner_user_id='AMIT002',owner_email='amit.kumar@gvnx.com' WHERE tenant_id='gvnx' AND role_id LIKE 'SAP_%';

-- 6. RISK OWNERS
UPDATE enterprise_risks SET risk_owner_id='RAHUL00',risk_owner_name='Rahul Sharma' WHERE tenant_id='gvnx' AND category='financial';
UPDATE enterprise_risks SET risk_owner_id='AMIT002',risk_owner_name='Amit Kumar' WHERE tenant_id='gvnx' AND category='it_cyber';
UPDATE enterprise_risks SET risk_owner_id='SURES08',risk_owner_name='Suresh Iyer' WHERE tenant_id='gvnx' AND category='compliance';
UPDATE enterprise_risks SET risk_owner_id='VIKRA04',risk_owner_name='Vikram Singh' WHERE tenant_id='gvnx' AND category='operational';
UPDATE enterprise_risks SET risk_owner_id='PRASANT',risk_owner_name='Prasant' WHERE tenant_id='gvnx' AND category='strategic';

-- 7. AUDITORS
INSERT INTO auditor_resources (tenant_id,auditor_id,name,email,title,skills,certifications,available_hours_per_month,is_active,created_at,updated_at) VALUES
('gvnx','AUD-001','Sarah Chen','sarah@gvnx.com','Senior IT Auditor','["IT audit","SAP","SoD"]','["CISA","CISSP"]',140,true,NOW(),NOW()),
('gvnx','AUD-002','Mohammed R','mohammed@gvnx.com','Financial Auditor','["SOX","IFRS"]','["CIA","CPA"]',160,true,NOW(),NOW()),
('gvnx','AUD-003','Li Wei','li.wei@gvnx.com','Data Analytics Auditor','["Python","SQL","fraud"]','["CISA","CFE"]',140,true,NOW(),NOW());

-- 8. BUSINESS PROCESS CONTROLS (P2P, O2C, R2R, HR, IT, Treasury, Warehouse)
DELETE FROM process_controls WHERE tenant_id='gvnx';
INSERT INTO process_controls (tenant_id,control_id,name,objective,description,control_type,control_nature,frequency,process_name,subprocess_name,owner_id,owner_name,key_control,status,version,is_active,created_at,updated_at) VALUES
('gvnx','CTL-P2P-001','Three-Way Match','Payments match PO+GR+Invoice','Automated 3-way match before payment','preventive','automated','continuous','Procure-to-Pay','Invoice Verification','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-002','Vendor Dual Approval','No unauthorized vendors','New vendors require secondary approval','preventive','manual','continuous','Procure-to-Pay','Vendor Management','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-003','Vendor Bank Verification','No bank fraud','Bank changes require callback','preventive','manual','continuous','Procure-to-Pay','Vendor Management','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-004','PO Authorization Limits','Enforce PO approval','PO approval by value threshold','preventive','automated','continuous','Procure-to-Pay','Purchase Orders','VIKRA04','Vikram Singh',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-005','Duplicate Invoice Check','Detect duplicates','System checks duplicate invoices','detective','automated','continuous','Procure-to-Pay','Invoice Verification','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-006','GR/IR Reconciliation','GR matches invoice','Monthly GR/IR recon','detective','manual','monthly','Procure-to-Pay','Invoice Verification','RAHUL00','Rahul Sharma',false,'active',1,true,NOW(),NOW()),
('gvnx','CTL-P2P-007','Payment Run Authorization','Control payments','Dual auth for payment runs','preventive','manual','continuous','Procure-to-Pay','Payment Processing','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-O2C-001','Credit Limit Check','No risky sales','Auto credit check before order','preventive','automated','continuous','Order-to-Cash','Sales Orders','ANJAL05','Anjali Gupta',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-O2C-002','Pricing Authorization','Correct pricing','Non-standard pricing needs approval','preventive','manual','continuous','Order-to-Cash','Pricing','ANJAL05','Anjali Gupta',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-O2C-003','Credit Memo Auth','Control credits','Credits require independent approval','preventive','manual','continuous','Order-to-Cash','Billing','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-R2R-001','Journal Entry Approval','Valid postings','Manual journals require approval','preventive','manual','continuous','Record-to-Report','Journal Entries','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-R2R-002','Period-End Close','Complete closing','Close checklist with sign-off','detective','manual','monthly','Record-to-Report','Closing','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-R2R-003','Bank Reconciliation','Cash accuracy','Monthly bank recon','detective','manual','monthly','Record-to-Report','Treasury','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-R2R-004','Account Reconciliation','BS accuracy','Monthly key account recon','detective','manual','monthly','Record-to-Report','Closing','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-R2R-005','Intercompany Recon','IC accuracy','Quarterly IC balance recon','detective','manual','quarterly','Record-to-Report','Consolidation','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-HR-001','Payroll Reconciliation','Payroll accuracy','Monthly payroll vs HR recon','detective','manual','monthly','HR/Payroll','Payroll','SNEHA03','Sneha Reddy',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-HR-002','Ghost Employee Detection','No fictitious employees','Quarterly payroll vs headcount','detective','manual','quarterly','HR/Payroll','Payroll','SNEHA03','Sneha Reddy',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-HR-003','Termination Deprovisioning','Timely access removal','Auto access removal within 24h','preventive','automated','continuous','HR/Payroll','Employee Lifecycle','SNEHA03','Sneha Reddy',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-001','Password Policy','Strong auth','System enforces password rules','preventive','automated','continuous','IT Security','Access Management','AMIT002','Amit Kumar',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-002','User Access Review','Periodic validation','Quarterly access review by managers','detective','manual','quarterly','IT Security','Access Management','AMIT002','Amit Kumar',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-003','SoD Enforcement','Prevent conflicts','Auto SoD with remediation','preventive','automated','continuous','IT Security','Access Management','PRIYA01','Priya Patel',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-004','Change Management','Control changes','Changes need approval+testing','preventive','manual','continuous','IT Operations','Change Management','AMIT002','Amit Kumar',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-005','Privileged Access Monitor','Monitor admins','FF sessions logged and reviewed','detective','automated','continuous','IT Security','Privileged Access','DEEPA09','Deepa Menon',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-IT-006','Backup Verification','Data recoverable','Daily backup verification','detective','automated','daily','IT Operations','Infrastructure','AMIT002','Amit Kumar',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-WH-001','Inventory Count','Inventory accuracy','Annual physical count','detective','manual','annual','Warehouse','Inventory','VIKRA04','Vikram Singh',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-WH-002','Goods Receipt Verification','GR accuracy','Physical verification against PO','preventive','manual','continuous','Warehouse','Goods Receipt','VIKRA04','Vikram Singh',false,'active',1,true,NOW(),NOW()),
('gvnx','CTL-TR-001','Wire Transfer Auth','Control transfers','Dual auth for wires','preventive','manual','continuous','Treasury','Payments','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW()),
('gvnx','CTL-TR-002','Signatory Authority','Control mandates','Bank signatory needs board approval','preventive','manual','continuous','Treasury','Banking','RAHUL00','Rahul Sharma',true,'active',1,true,NOW(),NOW());

-- 9. MIGRATION MAPPINGS (correct columns: ecc_tcode, s4_tcode)
INSERT INTO migration_mappings (tenant_id,ecc_tcode,s4_tcode,status,notes,created_at,updated_at) VALUES
('gvnx','FK01','BP','validated','Vendor creation via BP',NOW(),NOW()),
('gvnx','FK02','BP','validated','Vendor change via BP',NOW(),NOW()),
('gvnx','FK03','BP','validated','Vendor display via BP',NOW(),NOW()),
('gvnx','FD01','BP','validated','Customer create via BP',NOW(),NOW()),
('gvnx','FD02','BP','validated','Customer change via BP',NOW(),NOW()),
('gvnx','MB1A','MIGO','validated','Goods issue via MIGO',NOW(),NOW()),
('gvnx','MB1B','MIGO','validated','Transfer posting via MIGO',NOW(),NOW()),
('gvnx','MB11','MIGO','validated','Goods movement via MIGO',NOW(),NOW()),
('gvnx','SE16','SE16N','validated','Table display replaced',NOW(),NOW()),
('gvnx','FAGLL03','FAGLL03H','validated','New GL display',NOW(),NOW()),
('gvnx','ME21N','ME21N','validated','PO creation same',NOW(),NOW()),
('gvnx','MIRO','MIRO','validated','Invoice verification same',NOW(),NOW()),
('gvnx','F110','F110','validated','Payment run same',NOW(),NOW()),
('gvnx','SU01','SU01','validated','User maintenance same',NOW(),NOW()),
('gvnx','PFCG','PFCG','validated','Role maintenance same',NOW(),NOW());

-- VERIFY
SELECT item, cnt FROM (
SELECT 'managers' as item, count(*) as cnt FROM users WHERE tenant_id='gvnx' AND manager_user_id IS NOT NULL
UNION ALL SELECT 'approvers', count(*) FROM approvers WHERE tenant_id='gvnx'
UNION ALL SELECT 'approval_rules', count(*) FROM approval_rules WHERE tenant_id='gvnx'
UNION ALL SELECT 'ff_configs', count(*) FROM firefighter_id_configs WHERE tenant_id='gvnx'
UNION ALL SELECT 'roles_with_owner', count(*) FROM roles WHERE tenant_id='gvnx' AND owner_user_id IS NOT NULL
UNION ALL SELECT 'controls', count(*) FROM process_controls WHERE tenant_id='gvnx'
UNION ALL SELECT 'key_controls', count(*) FROM process_controls WHERE tenant_id='gvnx' AND key_control=true
UNION ALL SELECT 'auditors', count(*) FROM auditor_resources WHERE tenant_id='gvnx'
UNION ALL SELECT 'platform_users', count(*) FROM users WHERE tenant_id='gvnx' AND is_platform_user=true
UNION ALL SELECT 'migration_maps', count(*) FROM migration_mappings WHERE tenant_id='gvnx'
) x ORDER BY item;
