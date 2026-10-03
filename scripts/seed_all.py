#!/usr/bin/env python3
"""Seed ALL control libraries (1283 + 1000 + 4500) into GvnX tenant."""
import pandas as pd
import paramiko

T = "gvnx"

owners = {"Record":"RAHUL00","Procure":"VIKRA04","P2P":"VIKRA04","Order":"ANJAL05","O2C":"ANJAL05","Hire":"SNEHA03","H2R":"SNEHA03","Acquire":"RAHUL00","Asset":"RAHUL00","Plan":"VIKRA04","Inventory":"VIKRA04","Treasury":"RAHUL00","Tax":"RAHUL00","Master":"RAHUL00","Project":"RAHUL00","Quality":"VIKRA04","Plant":"AMIT002","Intercompany":"RAHUL00","R2R":"RAHUL00","IT":"AMIT002","ITGC":"AMIT002","Interface":"AMIT002","Data":"AMIT002","Compliance":"SURES08","Cyber":"DEEPA09","Revenue":"ANJAL05","Supply":"VIKRA04","Third":"VIKRA04","TPRM":"VIKRA04","ESG":"SURES08","Priv":"DEEPA09","PRIVACY":"DEEPA09","AI":"AMIT002","APP":"AMIT002","BCDR":"AMIT002","PHYS":"AMIT002","REG":"SURES08","Access":"AMIT002","Audit":"SURES08","Risk":"RAHUL00","Physical":"AMIT002"}
FREQ = {"daily":"DAILY","weekly":"WEEKLY","monthly":"MONTHLY","quarterly":"QUARTERLY","annually":"ANNUAL","annual":"ANNUAL","per transaction":"CONTINUOUS","continuous":"CONTINUOUS","real-time":"CONTINUOUS","event-driven":"CONTINUOUS"}

def get_owner(p):
    for k,v in owners.items():
        if k.lower() in str(p).lower(): return v
    return "RAHUL00"

def s(v): return "" if pd.isna(v) else str(v).replace("'","").strip()

print("Reading files...")
df1 = pd.read_excel("C:/Users/Welcome/Downloads/SAP_GRC_Integrated_1000plus_Real_World_Scenarios.xlsx", sheet_name="1000+ Scenarios")
df2 = pd.read_excel("C:/Users/Welcome/Downloads/SAP_GRC_Process_Control_1000_Atomic_Controls.xlsx")
df3 = pd.read_excel("C:/Users/Welcome/Downloads/SAP_GRC_Integrated_Enterprise_Master_Library_4500.xlsx", sheet_name="Master Library")
print(f"  {len(df1)} + {len(df2)} + {len(df3)} = {len(df1)+len(df2)+len(df3)}")

lines = [f"DELETE FROM control_tests WHERE tenant_id='{T}';", f"DELETE FROM process_controls WHERE tenant_id='{T}';"]
seen = set()
count = 0

def add(sid, ctrl, obj, risk, proc, sub, nat, exe, freq, rat=""):
    global count
    sid = s(sid); ctrl = s(ctrl)
    if not sid or not ctrl or sid in seen: return
    seen.add(sid)
    n = "PREVENTIVE" if "prevent" in str(nat).lower() else "DETECTIVE"
    e = "AUTOMATED" if "auto" in str(exe).lower() or "semi" in str(exe).lower() else "MANUAL"
    f = FREQ.get(str(freq).lower(), "CONTINUOUS")
    k = "true" if n=="PREVENTIVE" or "high" in str(rat).lower() else "false"
    o = get_owner(proc)
    lines.append(f"INSERT INTO process_controls (tenant_id,control_id,name,objective,description,control_type,control_nature,frequency,process_name,subprocess_name,owner_id,key_control,status,version,is_active,created_at,updated_at) VALUES ('{T}','{sid}','{s(ctrl)[:250]}','{s(obj)[:250]}','{s(risk)[:400]}','{n}','{e}','{f}','{s(proc)[:200]}','{s(sub)[:200]}','{o}',{k},'ACTIVE',1,true,NOW(),NOW());")
    count += 1

for _,r in df1.iterrows(): add(r.get("Scenario ID"), r.get("Process Control"), r.get("Risk Objective"), r.get("Real-World Risk Scenario"), r.get("Business Process / Module"), r.get("Subprocess / Scenario"), r.get("Control Nature"), r.get("Execution"), r.get("Frequency"), r.get("Risk Rating"))
print(f"  After file 1: {count}")

for _,r in df2.iterrows(): add(r.get("Control ID"), r.get("Control Statement"), r.get("Control Objective"), r.get("Risk Addressed"), r.get("Domain"), r.get("Process"), r.get("Nature"), r.get("Automation"), r.get("Frequency"))
print(f"  After file 2: {count}")

for _,r in df3.iterrows(): add(r.get("GRC ID"), r.get("Control / Scenario Statement"), r.get("Risk Addressed"), r.get("Detailed Flow"), str(r.get("Module Name","") or r.get("Domain / Area","")), str(r.get("Object","") or r.get("Domain / Area","")), r.get("Nature"), r.get("Automation"), r.get("Frequency"))
print(f"  After file 3: {count}")

lines.append(f"SELECT 'total' as i, count(*) FROM process_controls WHERE tenant_id='{T}' UNION ALL SELECT 'key', count(*) FROM process_controls WHERE tenant_id='{T}' AND key_control=true UNION ALL SELECT 'preventive', count(*) FROM process_controls WHERE tenant_id='{T}' AND control_type='PREVENTIVE' UNION ALL SELECT 'detective', count(*) FROM process_controls WHERE tenant_id='{T}' AND control_type='DETECTIVE' ORDER BY i;")

sql = "\n".join(lines)
with open("d:/Governexplus/scripts/seed_all_controls.sql", "w", encoding="utf-8") as f:
    f.write(sql)
print(f"SQL: {count} controls ({len(sql)//1024} KB)")

print("Uploading...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("212.47.75.51", username="root", password="l4yiVUCmI51v3aJ4g0wZvg", timeout=10)
sftp = ssh.open_sftp()
sftp.put("d:/Governexplus/scripts/seed_all_controls.sql", "/tmp/seed_all.sql")
sftp.close()
print("Executing...")
stdin, stdout, stderr = ssh.exec_command("sudo -u postgres psql -d governexplus -f /tmp/seed_all.sql 2>&1 | tail -10", timeout=120)
print(stdout.read().decode("utf-8", errors="replace"))
ssh.close()
print("DONE")
