-- Role Intelligence data (duplicates, unused, health scores)
INSERT INTO role_intelligence (tenant_id, role_id, role_name, analysis_type, score, details, recommendations, created_at, updated_at) VALUES
('gvnx','Z_FI_AP_CLERK','AP Clerk','health',78,'{"users":24,"tcodes":12,"auth_objects":34,"sod_conflicts":2,"unused_tcodes":3}','["Remove unused tcodes: FK09, FK07, FK05"]',NOW(),NOW()),
('gvnx','Z_FI_AP_MANAGER','AP Manager','health',45,'{"users":8,"tcodes":28,"auth_objects":67,"sod_conflicts":5,"unused_tcodes":8}','["Split role: separate vendor maintenance from payment","Remove 8 unused tcodes"]',NOW(),NOW()),
('gvnx','Z_FI_PAYMENT_ADMIN','Payment Admin','health',32,'{"users":5,"tcodes":35,"auth_objects":89,"sod_conflicts":7,"unused_tcodes":12}','["Critical: 7 SoD conflicts","Split into Payment Viewer and Payment Executor"]',NOW(),NOW()),
('gvnx','Z_FI_VENDOR_ADMIN','Vendor Admin','health',55,'{"users":6,"tcodes":18,"auth_objects":42,"sod_conflicts":3,"unused_tcodes":4}','["Separate vendor creation from vendor change"]',NOW(),NOW()),
('gvnx','Z_FI_GL_ACCOUNTANT','GL Accountant','health',82,'{"users":12,"tcodes":15,"auth_objects":28,"sod_conflicts":1,"unused_tcodes":2}','["Low risk - minor cleanup only"]',NOW(),NOW()),
('gvnx','Z_MM_BUYER','Buyer','health',65,'{"users":18,"tcodes":22,"auth_objects":45,"sod_conflicts":3,"unused_tcodes":5}','["Remove PO approval from buyer role"]',NOW(),NOW()),
('gvnx','Z_HR_ADMIN','HR Admin','health',40,'{"users":4,"tcodes":32,"auth_objects":78,"sod_conflicts":4,"unused_tcodes":10}','["Split HR master data from payroll access"]',NOW(),NOW()),
('gvnx','Z_IT_BASIS','Basis Admin','health',35,'{"users":3,"tcodes":45,"auth_objects":120,"sod_conflicts":6,"unused_tcodes":15}','["Critical: Over-privileged","Split into Basis Monitor and Basis Admin"]',NOW(),NOW()),
('gvnx','Z_IT_SECURITY','Security Admin','health',28,'{"users":2,"tcodes":38,"auth_objects":95,"sod_conflicts":8,"unused_tcodes":10}','["Critical: SU01+PFCG+SE16 combination"]',NOW(),NOW()),
('gvnx','SAP_ALL','Full Auth','health',5,'{"users":2,"tcodes":999,"auth_objects":999,"sod_conflicts":99,"unused_tcodes":900}','["CRITICAL: Remove immediately"]',NOW(),NOW()),
-- Duplicate detection
('gvnx','Z_FI_AP_CLERK','AP Clerk','duplicate',87,'{"similar_to":"Z_FIORI_AP","overlap_pct":87}','["Consider merging Z_FI_AP_CLERK and Z_FIORI_AP"]',NOW(),NOW()),
('gvnx','Z_MM_BUYER','Buyer','duplicate',72,'{"similar_to":"Z_MM_INVOICE","overlap_pct":72}','["High overlap - review if separate roles needed"]',NOW(),NOW()),
('gvnx','Z_HR_ADMIN','HR Admin','duplicate',65,'{"similar_to":"Z_HR_PAYROLL","overlap_pct":65}','["Significant overlap between HR Admin and Payroll"]',NOW(),NOW()),
-- Unused
('gvnx','SAP_NEW','New Auth','unused',0,'{"assigned_users":0,"last_used":"never","days_inactive":999}','["Remove role - never used"]',NOW(),NOW()),
('gvnx','Z_BW_REPORTER','BW Reporter','unused',15,'{"assigned_users":2,"last_used":"2025-03-14","days_inactive":564}','["No usage in 18+ months"]',NOW(),NOW());

-- ECC to S/4HANA Migration Mappings for GvnX tenant
INSERT INTO migration_mappings (tenant_id, source_tcode, target_tcode, mapping_type, status, notes, created_at, updated_at) VALUES
('gvnx','FK01','BP','replaced','validated','Vendor creation now via Business Partner',NOW(),NOW()),
('gvnx','FK02','BP','replaced','validated','Vendor change now via Business Partner',NOW(),NOW()),
('gvnx','FK03','BP','replaced','validated','Vendor display now via Business Partner',NOW(),NOW()),
('gvnx','XK01','BP','replaced','validated','Vendor create (central) now via BP',NOW(),NOW()),
('gvnx','FD01','BP','replaced','validated','Customer create now via Business Partner',NOW(),NOW()),
('gvnx','FD02','BP','replaced','validated','Customer change now via Business Partner',NOW(),NOW()),
('gvnx','ME21N','ME21N','compatible','validated','PO creation - same in S/4HANA',NOW(),NOW()),
('gvnx','MIRO','MIRO','compatible','validated','Invoice verification - same',NOW(),NOW()),
('gvnx','FB60','FB60','compatible','validated','Vendor invoice - same',NOW(),NOW()),
('gvnx','F110','F110','compatible','validated','Payment run - same',NOW(),NOW()),
('gvnx','MB1A','MIGO','replaced','validated','Goods issue now via MIGO',NOW(),NOW()),
('gvnx','MB1B','MIGO','replaced','validated','Transfer posting now via MIGO',NOW(),NOW()),
('gvnx','MB11','MIGO','replaced','validated','Goods movement now via MIGO',NOW(),NOW()),
('gvnx','SE16','SE16N','replaced','validated','Table display replaced by SE16N',NOW(),NOW()),
('gvnx','FAGLL03','FAGLL03H','replaced','validated','GL display replaced by new GL',NOW(),NOW()),
('gvnx','KO01','Manage Internal Orders','replaced','validated','Replaced by Fiori app',NOW(),NOW()),
('gvnx','SU01','SU01','compatible','validated','User maintenance - same',NOW(),NOW()),
('gvnx','PFCG','PFCG','compatible','validated','Role maintenance - same',NOW(),NOW()),
('gvnx','PA30','PA30','compatible','validated','HR master data - same',NOW(),NOW()),
('gvnx','VA01','VA01','compatible','validated','Sales order - same',NOW(),NOW());

-- Privileged Access (Firefighter) Sessions & Logs
INSERT INTO firefighter_sessions (tenant_id, session_id, request_id, firefighter_id, user_id, system_id, status, started_at, ended_at, duration_minutes, activities_count, reviewed_by, review_status, review_notes, created_at, updated_at) VALUES
('gvnx','FFS-001','FF-REQ-001','FF_SAP_001','RAHUL00','SAP_PRD','completed',NOW()-interval '10 days',NOW()-interval '10 days' + interval '2 hours',120,18,'PRIYA01','approved','All activities consistent with reported incident',NOW(),NOW()),
('gvnx','FFS-002','FF-REQ-002','FF_SAP_002','AMIT002','SAP_PRD','completed',NOW()-interval '5 days',NOW()-interval '5 days' + interval '90 minutes',90,12,'SNEHA03','flagged','Unexpected SU01 activity during session',NOW(),NOW()),
('gvnx','FFS-003','FF-REQ-003','FF_SAP_001','VIKRA04','SAP_PRD','active',NOW()-interval '1 hour',NULL,NULL,4,NULL,'pending','Session in progress',NOW(),NOW()),
('gvnx','FFS-004','FF-REQ-004','FF_SAP_003','SURES08','SAP_QAS','completed',NOW()-interval '15 days',NOW()-interval '15 days' + interval '45 minutes',45,8,'RAHUL00','approved','Standard maintenance activity',NOW(),NOW()),
('gvnx','FFS-005','FF-REQ-005','FF_SAP_002','KIRAN14','SAP_PRD','completed',NOW()-interval '3 days',NOW()-interval '3 days' + interval '3 hours',180,25,'PRIYA01','pending','Awaiting controller review',NOW(),NOW());

-- Firefighter Activity Logs
INSERT INTO firefighter_activities (tenant_id, session_id, activity_type, transaction_code, description, timestamp, details, created_at, updated_at) VALUES
('gvnx','FFS-001','transaction','SM37','Job overview - checked failed jobs',NOW()-interval '10 days' + interval '5 minutes','{"action":"display","object":"background_jobs"}',NOW(),NOW()),
('gvnx','FFS-001','transaction','SM21','System log review',NOW()-interval '10 days' + interval '12 minutes','{"action":"display","object":"system_log"}',NOW(),NOW()),
('gvnx','FFS-001','transaction','SM36','Reschedule failed job',NOW()-interval '10 days' + interval '25 minutes','{"action":"execute","object":"job_ZFIN_POSTING","job_id":"12345"}',NOW(),NOW()),
('gvnx','FFS-001','transaction','SM50','Process overview check',NOW()-interval '10 days' + interval '30 minutes','{"action":"display","object":"work_processes"}',NOW(),NOW()),
('gvnx','FFS-002','transaction','SM37','Job monitoring',NOW()-interval '5 days' + interval '3 minutes','{"action":"display"}',NOW(),NOW()),
('gvnx','FFS-002','transaction','SU01','User maintenance - UNEXPECTED',NOW()-interval '5 days' + interval '15 minutes','{"action":"change","object":"user_VENDOR01","field":"lock_status"}',NOW(),NOW()),
('gvnx','FFS-002','transaction','SE16','Table display - sensitive',NOW()-interval '5 days' + interval '22 minutes','{"action":"display","table":"USR02","records":50}',NOW(),NOW()),
('gvnx','FFS-002','transaction','SM21','System log check',NOW()-interval '5 days' + interval '40 minutes','{"action":"display"}',NOW(),NOW()),
('gvnx','FFS-003','transaction','SM37','Job overview',NOW()-interval '55 minutes','{"action":"display"}',NOW(),NOW()),
('gvnx','FFS-003','transaction','SM21','System log',NOW()-interval '45 minutes','{"action":"display"}',NOW(),NOW()),
('gvnx','FFS-003','transaction','DB02','Database monitor',NOW()-interval '30 minutes','{"action":"display","object":"tablespace_usage"}',NOW(),NOW()),
('gvnx','FFS-003','transaction','SM50','Work process overview',NOW()-interval '15 minutes','{"action":"display"}',NOW(),NOW());

-- Access Request Logs (wider scenarios)
INSERT INTO access_request_logs (tenant_id, request_id, request_type, requester_user_id, requester_name, requested_roles, justification, priority, status, risk_level, approver_id, approver_name, approved_at, provisioned_at, created_at, updated_at) VALUES
('gvnx','AR-001','role_assignment','ARJUN10','Arjun Das','["Z_FI_AP_CLERK","Z_FI_AR_CLERK"]','New hire - AP team member','medium','approved','low','RAHUL00','Rahul Sharma',NOW()-interval '20 days',NOW()-interval '19 days',NOW()-interval '21 days',NOW()),
('gvnx','AR-002','role_assignment','KAVIT11','Kavitha Rao','["Z_FI_PAYMENT_ADMIN"]','Temporary payment processing during year-end','high','approved','high','PRIYA01','Priya Patel',NOW()-interval '15 days',NOW()-interval '14 days',NOW()-interval '16 days',NOW()),
('gvnx','AR-003','role_assignment','MANOJ12','Manoj Pillai','["Z_IT_BASIS","Z_IT_SECURITY"]','IT team lead promotion - needs admin access','high','pending_approval','critical',NULL,NULL,NULL,NULL,NOW()-interval '2 days',NOW()),
('gvnx','AR-004','role_removal','DINESH40','Dinesh Thakur','["SAP_ALL"]','Compliance remediation - remove SAP_ALL','critical','approved','critical','SNEHA03','Sneha Reddy',NOW()-interval '5 days',NOW()-interval '5 days',NOW()-interval '6 days',NOW()),
('gvnx','AR-005','role_assignment','POOJA21','Pooja Saxena','["Z_MM_BUYER","Z_MM_PO_APPROVER"]','Cross-training in procurement','medium','rejected','high','VIKRA04','Vikram Singh',NULL,NULL,NOW()-interval '8 days',NOW()),
('gvnx','AR-006','temporary_access','GAURAV20','Gaurav Verma','["Z_FI_CONTROLLER"]','Month-end closing support - 2 weeks','medium','approved','medium','RAHUL00','Rahul Sharma',NOW()-interval '3 days',NOW()-interval '3 days',NOW()-interval '4 days',NOW()),
('gvnx','AR-007','role_assignment','MEGHA29','Megha Dhawan','["Z_SD_SALES_REP","Z_SD_ORDER_ADMIN"]','Transfer to sales department','low','approved','low','AMIT002','Amit Kumar',NOW()-interval '12 days',NOW()-interval '11 days',NOW()-interval '13 days',NOW()),
('gvnx','AR-008','role_assignment','TARUN30','Tarun Jain','["Z_HR_PAYROLL"]','Backup payroll processor','medium','pending_approval','medium',NULL,NULL,NULL,NULL,NOW()-interval '1 day',NOW()),
('gvnx','AR-009','emergency_access','SURES08','Suresh Iyer','["FF_SAP_001"]','Production job failure - immediate fix needed','critical','approved','critical','PRIYA01','Priya Patel',NOW()-interval '10 days',NOW()-interval '10 days',NOW()-interval '10 days',NOW()),
('gvnx','AR-010','role_removal','LAKSH13','Lakshmi S','["Z_FI_TREASURY","Z_FI_CONTROLLER"]','Employee termination - immediate deprovisioning','critical','approved','low','SNEHA03','Sneha Reddy',NOW()-interval '7 days',NOW()-interval '7 days',NOW()-interval '7 days',NOW());

-- Certification campaign items
INSERT INTO certification_campaigns (tenant_id, campaign_id, campaign_name, campaign_type, status, total_items, completed_items, certified_items, revoked_items, owner_id, due_date, created_at, updated_at) VALUES
('gvnx','CERT-Q3-2026','Q3-2026 User Access Review','user_access','in_progress',180,142,128,14,'PRIYA01',NOW()+interval '14 days',NOW()-interval '30 days',NOW()),
('gvnx','CERT-FF-2026','Firefighter Access Review Q3','firefighter_review','completed',12,12,10,2,'SNEHA03',NOW()-interval '10 days',NOW()-interval '45 days',NOW()-interval '10 days'),
('gvnx','CERT-PRIV-2026','Privileged Access Review','privileged_access','pending',25,0,0,0,'VIKRA04',NOW()+interval '30 days',NOW()-interval '5 days',NOW());

-- Control test results with more detail
INSERT INTO control_tests (tenant_id, test_id, control_id, test_type, testing_period_start, testing_period_end, sample_size, tester_id, tester_name, result, exceptions_found, conclusion, status, created_at, updated_at)
SELECT 'gvnx', 'TST-' || substr(md5(random()::text),1,12), c.id,
    (ARRAY['operating_effectiveness','design','walkthrough'])[floor(random()*3+1)],
    NOW()-interval '90 days', NOW(), 25,
    'RAHUL00', 'Rahul Sharma',
    (ARRAY['effective','effective','effective','effective','ineffective','partially_effective'])[floor(random()*6+1)],
    floor(random()*5)::int,
    'Test completed per approved procedure',
    'completed', NOW(), NOW()
FROM process_controls c WHERE c.tenant_id = 'gvnx';

-- Audit logs for activity trail
INSERT INTO audit_logs (tenant_id, user_id, action, action_category, target_type, target_id, details, ip_address, success, timestamp, created_at) VALUES
('gvnx','PRASANT','user_login','authentication','auth','prasant','{"method":"password"}','106.222.235.26',true,NOW()-interval '2 hours',NOW()),
('gvnx','RAHUL00','user_login','authentication','auth','rahul00','{"method":"password"}','10.0.1.50',true,NOW()-interval '1 hour',NOW()),
('gvnx','PRIYA01','user_login','authentication','auth','priya01','{"method":"sso"}','10.0.1.51',true,NOW()-interval '45 minutes',NOW()),
('gvnx','RAHUL00','risk_analysis','risk','ara','user_analysis','{"user":"KAVIT11","violations_found":3}','10.0.1.50',true,NOW()-interval '30 minutes',NOW()),
('gvnx','PRIYA01','access_request_approved','access','request','AR-002','{"requester":"KAVIT11","roles":["Z_FI_PAYMENT_ADMIN"]}','10.0.1.51',true,NOW()-interval '15 days',NOW()),
('gvnx','SNEHA03','certification_decision','compliance','certification','CERT-Q3-2026','{"action":"revoke","user":"DINESH40","role":"SAP_ALL"}','10.0.1.53',true,NOW()-interval '5 days',NOW()),
('gvnx','VIKRA04','firefighter_approve','emergency','firefighter','FF-REQ-003','{"firefighter_id":"FF_SAP_001","user":"VIKRA04"}','10.0.1.54',true,NOW()-interval '1 hour',NOW()),
('gvnx','RAHUL00','control_test_completed','compliance','control','CTL-001','{"result":"effective","exceptions":1}','10.0.1.50',true,NOW()-interval '3 days',NOW()),
('gvnx','SYSTEM','sod_violation_detected','risk','violation','VIO-001','{"rule":"SOD-FI-001","user":"KAVIT11","severity":"high"}','system',true,NOW()-interval '10 days',NOW()),
('gvnx','SYSTEM','kri_breach','risk','kri','KRI-001','{"kri":"Open SoD Violations","value":125,"threshold":100}','system',true,NOW()-interval '2 days',NOW());
