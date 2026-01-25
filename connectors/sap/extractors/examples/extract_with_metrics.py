#!/usr/bin/env python3
"""
Example: SAP Extraction with Metrics and Retry

This script demonstrates the retry, metrics, and rate limiting
capabilities of the SAP RFC extractors.

Features shown:
- Automatic retry with exponential backoff
- Performance metrics collection
- Rate limiting for SAP protection
- Error handling and classification

Usage:
    python extract_with_metrics.py FF_FIN_01 20240101 20240131
"""

import sys
import json
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors import (
    FirefighterSessionExtractor,
    UserMasterExtractor,
    TransactionUsageExtractor,
)
from connectors.sap.extractors.tcode_usage_hana import HANAOptimizedTCodeExtractor
from connectors.sap.extractors.utils import (
    get_metrics,
    RateLimiter,
    set_rate_limiter,
    SAPErrorClassifier,
)


def main():
    # Parse arguments
    if len(sys.argv) < 4:
        print("Usage: python extract_with_metrics.py <ff_user> <from_date> <to_date>")
        print("Example: python extract_with_metrics.py FF_FIN_01 20240101 20240131")
        sys.exit(1)

    ff_user = sys.argv[1]
    from_date = sys.argv[2]
    to_date = sys.argv[3]

    print(f"Extraction with metrics for: {ff_user}")
    print(f"Period: {from_date} to {to_date}")
    print("-" * 50)

    # Configure rate limiter (10 calls/sec, burst of 20)
    print("\n=== CONFIGURING RATE LIMITER ===")
    rate_limiter = RateLimiter(calls_per_second=10.0, burst=20)
    set_rate_limiter(rate_limiter)
    print("Rate limiter configured: 10 calls/sec, burst 20")

    # Initialize extractors
    user_extractor = UserMasterExtractor()
    hana_extractor = HANAOptimizedTCodeExtractor()

    # Extract user status
    print("\n=== EXTRACTING USER STATUS ===")
    start = time.time()

    try:
        user_status = user_extractor.get_firefighter_status(ff_user)
        print(f"User status retrieved in {(time.time() - start)*1000:.1f}ms")
        print(f"  Available: {user_status['available']}")
        print(f"  Locked: {user_status['is_locked']}")
        print(f"  Roles: {user_status['role_count']}")
    except Exception as e:
        print(f"Error getting user status: {e}")
        error_type = SAPErrorClassifier.classify(e)
        print(f"Error classification: {error_type}")

    # Extract transaction usage with HANA optimization
    print("\n=== EXTRACTING TRANSACTION USAGE (HANA) ===")
    start = time.time()

    result = hana_extractor.extract(
        username=ff_user,
        from_date=from_date,
        to_date=to_date
    )

    print(f"Extraction completed in {(time.time() - start)*1000:.1f}ms")
    print(f"  Records: {result.record_count}")
    print(f"  Success: {result.success}")

    if result.data:
        # Analyze results
        restricted_count = len([r for r in result.data if r.get("is_restricted")])
        total_duration = sum(r.get("duration_ms", 0) for r in result.data)

        print(f"  Restricted tcodes: {restricted_count}")
        print(f"  Total duration: {total_duration}ms")

    # Test chunked extraction
    print("\n=== TESTING CHUNKED EXTRACTION ===")
    chunk_count = 0
    total_records = 0

    for chunk_result in hana_extractor.extract_chunked(
        username=ff_user,
        from_date=from_date,
        to_date=to_date,
        chunk_size=1000
    ):
        chunk_count += 1
        total_records += chunk_result.record_count
        print(f"  Chunk {chunk_count}: {chunk_result.record_count} records")

        # Limit to 5 chunks for demo
        if chunk_count >= 5:
            print("  (Limited to 5 chunks for demo)")
            break

    print(f"  Total chunks: {chunk_count}")
    print(f"  Total records: {total_records}")

    # Show collected metrics
    print("\n=== COLLECTED METRICS ===")
    metrics = get_metrics()

    print("\nInternal Metrics:")
    internal = metrics.get("internal", {})

    # Counters
    if internal.get("counters"):
        print("\n  Counters:")
        for name, value in internal["counters"].items():
            print(f"    {name}: {value}")

    # Summaries (timing)
    if internal.get("summaries"):
        print("\n  Timing (summaries):")
        for name, stats in internal["summaries"].items():
            print(f"    {name}:")
            print(f"      Count: {stats['count']}")
            print(f"      Avg: {stats['avg']*1000:.1f}ms")
            print(f"      Min: {stats['min']*1000:.1f}ms")
            print(f"      Max: {stats['max']*1000:.1f}ms")

    # Gauges
    if internal.get("gauges"):
        print("\n  Gauges:")
        for name, value in internal["gauges"].items():
            print(f"    {name}: {value}")

    print(f"\nPrometheus available: {metrics.get('prometheus_available', False)}")

    # Test error classification
    print("\n=== ERROR CLASSIFICATION DEMO ===")
    test_errors = [
        "COMMUNICATION_FAILURE: Connection reset",
        "NO_AUTHORITY for S_TCODE",
        "TABLE_NOT_FOUND: ZXYZ",
        "Unknown error occurred",
    ]

    for error_msg in test_errors:
        error_class = SAPErrorClassifier.classify(Exception(error_msg))
        retryable = SAPErrorClassifier.is_retryable(Exception(error_msg))
        print(f"  '{error_msg[:40]}...'")
        print(f"    Class: {error_class}, Retryable: {retryable}")

    # Export metrics summary
    output_file = f"extraction_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "firefighter": ff_user,
            "period": {"from": from_date, "to": to_date},
            "extraction_results": {
                "record_count": result.record_count,
                "success": result.success,
                "duration_ms": result.duration_ms,
            },
            "metrics": internal,
        }, f, indent=2)

    print(f"\nMetrics exported to: {output_file}")


if __name__ == "__main__":
    main()
