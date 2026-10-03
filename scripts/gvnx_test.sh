#!/bin/bash
RESP=$(curl -s -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"username":"prasant","password":"GvnX2026!","tenant_id":"gvnx"}')
TOKEN=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
echo "TOKEN_LEN=${#TOKEN}"
echo "--- Users ---"
curl -s http://127.0.0.1:8000/users/ -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: gvnx" | head -c 200
echo ""
echo "--- Dashboard ---"
curl -s http://127.0.0.1:8000/dashboard/stats -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: gvnx"
echo ""
echo "--- Risks ---"
curl -s http://127.0.0.1:8000/risk-management/risks -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: gvnx" | head -c 200
echo ""
echo "--- Controls count ---"
curl -s "http://127.0.0.1:8000/process-control/controls" -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: gvnx" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else d)"
