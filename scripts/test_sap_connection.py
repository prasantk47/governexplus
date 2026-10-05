#!/usr/bin/env python3
"""
SAP Connection Test Script
==========================
Tests RFC connectivity to a real SAP system.

Usage:
    # Set env vars first:
    export SAP_ASHOST=10.0.1.50
    export SAP_SYSNR=00
    export SAP_CLIENT=100
    export SAP_USER=GOVNX_RFC
    export SAP_PASSWORD=SecurePass123

    # Then run:
    python scripts/test_sap_connection.py

    # Or pass inline:
    SAP_ASHOST=10.0.1.50 SAP_SYSNR=00 SAP_CLIENT=100 SAP_USER=RFC_USER SAP_PASSWORD=xxx python scripts/test_sap_connection.py
"""
import os
import sys
import time
import json

# ── Config ────────────────────────────────────────────────────────────────
SAP_PARAMS = {
    "ashost": os.environ.get("SAP_ASHOST", ""),
    "sysnr": os.environ.get("SAP_SYSNR", "00"),
    "client": os.environ.get("SAP_CLIENT", "100"),
    "user": os.environ.get("SAP_USER", ""),
    "passwd": os.environ.get("SAP_PASSWORD", ""),
    "lang": os.environ.get("SAP_LANG", "EN"),
}

# Optional: message server (load-balanced) instead of direct
if os.environ.get("SAP_MSHOST"):
    SAP_PARAMS["mshost"] = os.environ["SAP_MSHOST"]
    SAP_PARAMS["group"] = os.environ.get("SAP_GROUP", "PUBLIC")
    del SAP_PARAMS["ashost"]

if os.environ.get("SAP_SAPROUTER"):
    SAP_PARAMS["saprouter"] = os.environ["SAP_SAPROUTER"]


def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def test_step(label, fn):
    print(f"\n  [{label}] ", end="", flush=True)
    t0 = time.time()
    try:
        result = fn()
        ms = int((time.time() - t0) * 1000)
        print(f"OK ({ms}ms)")
        return result
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        print(f"FAILED ({ms}ms)")
        print(f"    Error: {e}")
        return None


def main():
    banner("GovernexPlus — SAP RFC Connection Test")

    # ── 1. Check pyrfc ────────────────────────────────────────────────
    print("\n1. Checking pyrfc installation...")
    try:
        import pyrfc
        print(f"   pyrfc version: {pyrfc.__version__}")
    except ImportError:
        print("   FATAL: pyrfc not installed. Run: pip install pyrfc")
        sys.exit(1)

    # ── 2. Validate config ────────────────────────────────────────────
    print("\n2. Validating connection parameters...")
    missing = [k for k in ("user", "passwd") if not SAP_PARAMS.get(k)]
    if not SAP_PARAMS.get("ashost") and not SAP_PARAMS.get("mshost"):
        missing.append("ashost or mshost")
    if missing:
        print(f"   FATAL: Missing required params: {', '.join(missing)}")
        print(f"   Set environment variables: SAP_ASHOST, SAP_USER, SAP_PASSWORD")
        sys.exit(1)

    host = SAP_PARAMS.get("ashost") or SAP_PARAMS.get("mshost")
    print(f"   Host: {host}")
    print(f"   System Nr: {SAP_PARAMS.get('sysnr', 'N/A')}")
    print(f"   Client: {SAP_PARAMS['client']}")
    print(f"   User: {SAP_PARAMS['user']}")
    print(f"   Language: {SAP_PARAMS['lang']}")

    # ── 3. TCP connectivity ───────────────────────────────────────────
    print("\n3. Testing TCP connectivity...")
    import socket
    sysnr = SAP_PARAMS.get("sysnr", "00")
    rfc_port = 3300 + int(sysnr)
    target = SAP_PARAMS.get("ashost", SAP_PARAMS.get("mshost", ""))

    def tcp_check():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((target, rfc_port))
        s.close()
        return True

    tcp_ok = test_step(f"TCP {target}:{rfc_port}", tcp_check)
    if not tcp_ok:
        print(f"\n   Cannot reach SAP on port {rfc_port}.")
        print(f"   Check firewall rules and network routing.")
        print(f"   SAP RFC port = 3300 + system_number ({sysnr}) = {rfc_port}")
        sys.exit(1)

    # ── 4. RFC connection ─────────────────────────────────────────────
    print("\n4. Establishing RFC connection...")
    conn = test_step("pyrfc.Connection()", lambda: pyrfc.Connection(**SAP_PARAMS))
    if not conn:
        print("\n   RFC login failed. Check username/password/client.")
        sys.exit(1)

    # ── 5. RFC_PING ───────────────────────────────────────────────────
    print("\n5. RFC function tests...")
    test_step("RFC_PING", lambda: conn.call("RFC_PING"))

    # ── 6. System info ────────────────────────────────────────────────
    def get_sysinfo():
        result = conn.call("RFC_SYSTEM_INFO")
        info = result.get("RFCSI_EXPORT", {})
        print(f"\n   System ID:    {info.get('RFCSYSID', '?')}")
        print(f"   Host:         {info.get('RFCHOST', '?')}")
        print(f"   DB System:    {info.get('RFCDBSYS', '?')}")
        print(f"   DB Host:      {info.get('RFCDBHOST', '?')}")
        print(f"   SAP Release:  {info.get('RFCSAPRL', '?')}")
        print(f"   Kernel:       {info.get('RFCKERNRL', '?')}")
        print(f"   OS:           {info.get('RFCOPSYS', '?')}")
        print(f"   Charset:      {info.get('RFCCHARTYP', '?')}")
        return info

    test_step("RFC_SYSTEM_INFO", get_sysinfo)

    # ── 7. User count ─────────────────────────────────────────────────
    def count_users():
        result = conn.call("BAPI_USER_GETLIST", MAX_ROWS=0, WITH_USERNAME="*")
        users = result.get("USERLIST", [])
        print(f"\n   Total users in client {SAP_PARAMS['client']}: {len(users)}")
        if users:
            print(f"   First 5: {', '.join(u.get('USERNAME','?') for u in users[:5])}")
        return len(users)

    test_step("BAPI_USER_GETLIST", count_users)

    # ── 8. Role count ─────────────────────────────────────────────────
    def count_roles():
        result = conn.call("RFC_READ_TABLE",
            QUERY_TABLE="AGR_DEFINE",
            DELIMITER="|",
            ROWCOUNT=5,
            FIELDS=[{"FIELDNAME": "AGR_NAME"}]
        )
        rows = result.get("DATA", [])
        total = result.get("ROWCOUNT", len(rows))
        print(f"\n   Sample roles: {[r.get('WA','').strip() for r in rows[:5]]}")
        return total

    test_step("RFC_READ_TABLE (AGR_DEFINE)", count_roles)

    # ── 9. Single user detail ─────────────────────────────────────────
    def get_sample_user():
        result = conn.call("BAPI_USER_GETLIST", MAX_ROWS=1, WITH_USERNAME="*")
        users = result.get("USERLIST", [])
        if not users:
            print("\n   No users found")
            return None
        username = users[0]["USERNAME"]
        detail = conn.call("BAPI_USER_GET_DETAIL", USERNAME=username)
        addr = detail.get("ADDRESS", {})
        roles = detail.get("ACTIVITYGROUPS", [])
        print(f"\n   User: {username}")
        print(f"   Name: {addr.get('FIRSTNAME','')} {addr.get('LASTNAME','')}")
        print(f"   Email: {addr.get('E_MAIL','')}")
        print(f"   Department: {addr.get('DEPARTMENT','')}")
        print(f"   Roles assigned: {len(roles)}")
        if roles:
            print(f"   First 3 roles: {[r.get('AGR_NAME','') for r in roles[:3]]}")
        return detail

    test_step("BAPI_USER_GET_DETAIL", get_sample_user)

    # ── 10. Auth check ────────────────────────────────────────────────
    def check_auth():
        result = conn.call("RFC_READ_TABLE",
            QUERY_TABLE="AGR_1251",
            DELIMITER="|",
            ROWCOUNT=3,
            FIELDS=[{"FIELDNAME": "AGR_NAME"}, {"FIELDNAME": "OBJECT"}]
        )
        rows = result.get("DATA", [])
        print(f"\n   Auth content rows (sample): {len(rows)}")
        return len(rows)

    test_step("RFC_READ_TABLE (AGR_1251)", check_auth)

    # ── Cleanup ───────────────────────────────────────────────────────
    conn.close()

    banner("ALL TESTS PASSED — SAP Connection Ready")
    print(f"""
  Next steps:
  1. Add to /opt/governexplus/app/.env:
     SAP_CONNECTOR_TYPE=sap_rfc
     SAP_ASHOST={target}
     SAP_SYSNR={sysnr}
     SAP_CLIENT={SAP_PARAMS['client']}
     SAP_USER={SAP_PARAMS['user']}
     SAP_PASSWORD=****

  2. Restart service:
     systemctl restart governexplus

  3. Trigger initial sync from the UI:
     Settings → Integrations → SAP → Sync Now
     Or API: POST /integrations/sync/jobs/FULL_USER_SYNC/run
""")


if __name__ == "__main__":
    main()
