from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

router = APIRouter()

# Metrics
REQUEST_COUNT = Counter(
    'grc_requests_total', 'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'grc_request_duration_seconds', 'Request latency',
    ['method', 'endpoint']
)
ACTIVE_TENANTS = Gauge('grc_active_tenants', 'Number of active tenants')
SOD_RULES_LOADED = Gauge('grc_sod_rules_loaded', 'Number of SoD rules loaded')
VIOLATIONS_OPEN = Gauge('grc_violations_open', 'Number of open violations')


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
