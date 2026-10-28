"""
Extract security controls, risks, and best practices from
ANAO 'Security and Control for SAP R/3' handbook (220 pages).

Outputs:
  - scripts/anao_controls.json  (structured controls)
  - Prints summary statistics
"""

import json
import re
import os

INPUT = os.path.join(os.path.dirname(__file__), "anao_full_text.txt")
OUTPUT = os.path.join(os.path.dirname(__file__), "anao_controls.json")

with open(INPUT, "r", encoding="utf-8") as f:
    raw = f.read()

# Split into pages
pages = {}
for m in re.finditer(r"===PAGE (\d+)===\n(.*?)(?=\n===PAGE |\Z)", raw, re.S):
    pages[int(m.group(1))] = m.group(2)

print(f"Loaded {len(pages)} pages")

# ── Module detection ──────────────────────────────────────────
MODULE_RANGES = [
    ("MM", "Procurement to Payables", 9, 36),
    ("FI", "Financial Accounting", 37, 75),
    ("FI-AA", "Asset Accounting", 76, 106),
    ("CO", "Controlling", 107, 114),
    ("HR", "Human Resources", 115, 136),
    ("BC", "Basis Component - Environment", 137, 148),
    ("BC-SEC", "Basis Component - Security", 149, 162),
    ("BC-CHG", "Basis Component - Change Control", 163, 168),
    ("BC-INT", "Basis Component - Interfaces", 169, 175),
    ("BC-CNV", "Basis Component - Data Conversion", 176, 188),
]


def get_module(page_num):
    for mod_id, mod_name, start, end in MODULE_RANGES:
        if start <= page_num <= end:
            return mod_id, mod_name
    return "GEN", "General"


# ── Extract controls ──────────────────────────────────────────
controls = []
control_id = 0

# Patterns for best practice procedures
# The PDF uses bullet points with best practice text
# Key risk areas are identifiable by headers

# Extract section headers and their content
current_section = ""
current_subsection = ""

for page_num in sorted(pages.keys()):
    text = pages[page_num]
    mod_id, mod_name = get_module(page_num)

    if mod_id == "GEN":
        continue

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect section headers (typically uppercase or bold-like)
        if len(line) > 5 and line == line.title() and len(line) < 100:
            if any(kw in line.lower() for kw in [
                "significant risk", "configuration", "security consideration",
                "key risk", "best practice", "useful report",
                "overview", "master file", "master data",
            ]):
                current_section = line

        # Detect risk/control descriptions
        # Best practices are typically formatted as bullet points
        if line.startswith("•") or line.startswith("�") or line.startswith("-"):
            practice_text = line.lstrip("•�- ").strip()
            # Collect continuation lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if (not next_line or next_line.startswith("•") or
                    next_line.startswith("�") or next_line.startswith("-") or
                    next_line.startswith("===") or
                    (len(next_line) > 5 and next_line == next_line.title())):
                    break
                practice_text += " " + next_line
                j += 1

            practice_text = practice_text.strip()
            if len(practice_text) > 20:  # Skip very short fragments
                control_id += 1

                # Determine severity/priority
                priority = "important"  # default
                if any(kw in practice_text.lower() for kw in [
                    "critical", "must ", "shall ", "essential",
                    "segregat", "separation of dut", "sod",
                    "unauthori", "fraud", "misappropriat",
                ]):
                    priority = "critical"
                elif any(kw in practice_text.lower() for kw in [
                    "desirable", "may assist", "consider",
                    "where possible", "optional",
                ]):
                    priority = "desirable"

                # Determine control type
                control_type = "preventive"
                if any(kw in practice_text.lower() for kw in [
                    "review", "monitor", "report", "reconcil",
                    "check", "verify", "audit", "inspect",
                ]):
                    control_type = "detective"
                elif any(kw in practice_text.lower() for kw in [
                    "correct", "remediat", "fix", "resolv",
                ]):
                    control_type = "corrective"

                # Determine control nature
                control_nature = "manual"
                if any(kw in practice_text.lower() for kw in [
                    "automat", "system", "configur", "sap standard",
                    "authoriz", "workflow", "tolerance",
                ]):
                    control_nature = "automated"
                elif any(kw in practice_text.lower() for kw in [
                    "combination", "both manual and",
                ]):
                    control_nature = "hybrid"

                # Detect related SAP objects
                tcodes = re.findall(r"\b([A-Z]{1,4}\d{2,3}[A-Z]?)\b", practice_text)
                auth_objects = re.findall(r"\b(S_[A-Z_]+|F_[A-Z_]+|M_[A-Z_]+|P_[A-Z_]+)\b", practice_text)
                tables = re.findall(r"\b([A-Z]{3,5}\d{3,4})\b", practice_text)

                # Categorize by risk domain
                risk_domain = "access_control"
                text_lower = practice_text.lower()
                if any(kw in text_lower for kw in ["segregat", "separation", "conflict", "incompatible"]):
                    risk_domain = "segregation_of_duties"
                elif any(kw in text_lower for kw in ["master data", "master file", "vendor master", "customer master"]):
                    risk_domain = "master_data_governance"
                elif any(kw in text_lower for kw in ["change", "transport", "modification"]):
                    risk_domain = "change_management"
                elif any(kw in text_lower for kw in ["password", "logon", "lock", "user id"]):
                    risk_domain = "authentication"
                elif any(kw in text_lower for kw in ["reconcil", "clearing", "balance"]):
                    risk_domain = "reconciliation"
                elif any(kw in text_lower for kw in ["report", "log", "audit trail", "monitor"]):
                    risk_domain = "monitoring_logging"
                elif any(kw in text_lower for kw in ["interface", "batch input", "bdc", "idoc"]):
                    risk_domain = "interface_controls"
                elif any(kw in text_lower for kw in ["backup", "recovery", "disaster"]):
                    risk_domain = "business_continuity"
                elif any(kw in text_lower for kw in ["payroll", "salary", "wage", "personnel"]):
                    risk_domain = "payroll_hr"

                controls.append({
                    "id": f"ANAO-{mod_id}-{control_id:04d}",
                    "module": mod_id,
                    "module_name": mod_name,
                    "section": current_section,
                    "page": page_num,
                    "description": practice_text,
                    "priority": priority,
                    "control_type": control_type,
                    "control_nature": control_nature,
                    "risk_domain": risk_domain,
                    "sap_tcodes": list(set(tcodes)),
                    "sap_auth_objects": list(set(auth_objects)),
                    "sap_tables": list(set(tables)),
                    "framework_mappings": [],
                })

            i = j
            continue
        i += 1

# ── Deduplicate similar controls ──────────────────────────────
seen = set()
unique_controls = []
for c in controls:
    # Normalize for dedup
    key = c["description"][:80].lower().strip()
    if key not in seen:
        seen.add(key)
        unique_controls.append(c)

# Re-number
for idx, c in enumerate(unique_controls, 1):
    c["id"] = f"ANAO-{c['module']}-{idx:04d}"

# ── Add framework mappings ────────────────────────────────────
for c in unique_controls:
    mappings = []
    text_lower = c["description"].lower()

    # COBIT mappings
    if c["risk_domain"] == "segregation_of_duties":
        mappings.append({"framework": "COBIT", "control": "DSS05.04"})
        mappings.append({"framework": "SOX", "control": "ITGC-AC"})
    if c["risk_domain"] == "access_control":
        mappings.append({"framework": "COBIT", "control": "DSS05.04"})
    if c["risk_domain"] == "change_management":
        mappings.append({"framework": "COBIT", "control": "BAI06.01"})
        mappings.append({"framework": "SOX", "control": "ITGC-CM"})
    if c["risk_domain"] == "monitoring_logging":
        mappings.append({"framework": "COBIT", "control": "MEA01.03"})
    if c["risk_domain"] == "authentication":
        mappings.append({"framework": "COBIT", "control": "DSS05.05"})
        mappings.append({"framework": "ISO27001", "control": "A.9.4.3"})
    if c["risk_domain"] == "business_continuity":
        mappings.append({"framework": "COBIT", "control": "DSS04.01"})
        mappings.append({"framework": "ISO27001", "control": "A.17.1.1"})
    if c["risk_domain"] == "interface_controls":
        mappings.append({"framework": "COBIT", "control": "BAI03.05"})
    if c["risk_domain"] == "reconciliation":
        mappings.append({"framework": "SOX", "control": "FSCP-RC"})

    # ISO 27001 mappings
    if "password" in text_lower:
        mappings.append({"framework": "ISO27001", "control": "A.9.4.3"})
    if "access" in text_lower and "authoriz" in text_lower:
        mappings.append({"framework": "ISO27001", "control": "A.9.2.3"})
    if "audit" in text_lower or "log" in text_lower:
        mappings.append({"framework": "ISO27001", "control": "A.12.4.1"})

    # NIST CSF
    if c["risk_domain"] in ("access_control", "authentication"):
        mappings.append({"framework": "NIST_CSF", "control": "PR.AC"})
    if c["risk_domain"] == "monitoring_logging":
        mappings.append({"framework": "NIST_CSF", "control": "DE.CM"})

    c["framework_mappings"] = mappings

# ── Statistics ────────────────────────────────────────────────
print(f"\nTotal controls extracted: {len(unique_controls)}")
print(f"\nBy module:")
mod_counts = {}
for c in unique_controls:
    mod_counts[c["module"]] = mod_counts.get(c["module"], 0) + 1
for mod, count in sorted(mod_counts.items(), key=lambda x: -x[1]):
    print(f"  {mod:8s}: {count}")

print(f"\nBy priority:")
pri_counts = {}
for c in unique_controls:
    pri_counts[c["priority"]] = pri_counts.get(c["priority"], 0) + 1
for pri, count in sorted(pri_counts.items(), key=lambda x: -x[1]):
    print(f"  {pri:12s}: {count}")

print(f"\nBy risk domain:")
dom_counts = {}
for c in unique_controls:
    dom_counts[c["risk_domain"]] = dom_counts.get(c["risk_domain"], 0) + 1
for dom, count in sorted(dom_counts.items(), key=lambda x: -x[1]):
    print(f"  {dom:25s}: {count}")

print(f"\nBy control type:")
type_counts = {}
for c in unique_controls:
    type_counts[c["control_type"]] = type_counts.get(c["control_type"], 0) + 1
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t:12s}: {count}")

# Controls with SAP tcodes
with_tcodes = sum(1 for c in unique_controls if c["sap_tcodes"])
with_auth = sum(1 for c in unique_controls if c["sap_auth_objects"])
print(f"\nWith SAP T-codes: {with_tcodes}")
print(f"With Auth objects: {with_auth}")

# ── Save ──────────────────────────────────────────────────────
output = {
    "source": "ANAO - Security and Control for SAP R/3 Handbook",
    "source_year": 1998,
    "pages": 220,
    "total_controls": len(unique_controls),
    "controls": unique_controls,
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {OUTPUT}")
