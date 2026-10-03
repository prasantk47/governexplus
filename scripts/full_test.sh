#!/bin/bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"username":"prasant","password":"GvnX2026!","tenant_id":"gvnx"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
H="Authorization: Bearer $TOKEN"
T="X-Tenant-ID: gvnx"

echo "=== Violations ==="
curl -s "http://127.0.0.1:8000/risk/violations" -H "$H" -H "$T" | head -c 150
echo ""
echo "=== Risk Register ==="
curl -s "http://127.0.0.1:8000/risk-management/risks" -H "$H" -H "$T" | head -c 150
echo ""
echo "=== Controls ==="
curl -s "http://127.0.0.1:8000/process-control/controls" -H "$H" -H "$T" | head -c 150
echo ""
echo "=== Dashboard ==="
curl -s "http://127.0.0.1:8000/dashboard/stats" -H "$H" -H "$T"
echo ""
echo "=== GRC Health ==="
curl -s "http://127.0.0.1:8000/grc-intelligence/health" -H "$H" -H "$T" | head -c 200
echo ""
