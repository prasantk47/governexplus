#!/usr/bin/env python3
"""
Example: Delta Extraction for Firefighter Activity

This script demonstrates delta (incremental) extraction of
firefighter transaction activity using the HANA-optimized extractor.

Delta extraction:
- Only retrieves records since last successful run
- Tracks state in extractor_state.json
- Ideal for near-real-time monitoring

Usage:
    python extract_firefighter_delta.py FF_FIN_01 [default_days]
"""

import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors.tcode_usage_hana import HANAOptimizedTCodeExtractor
from connectors.sap.extractors.state import (
    get_state_manager,
    get_last_run,
    ExtractionState
)
from connectors.sap.extractors.utils import get_metrics


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python extract_firefighter_delta.py <ff_user> [default_days]")
        print("Example: python extract_firefighter_delta.py FF_FIN_01 7")
        sys.exit(1)

    ff_user = sys.argv[1]
    default_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    # Create unique extraction key
    extraction_key = f"ff_stad_{ff_user}"

    print(f"Delta extraction for firefighter: {ff_user}")
    print(f"Extraction key: {extraction_key}")
    print(f"Default lookback: {default_days} days")
    print("-" * 50)

    # Check last run
    last_run = get_last_run(extraction_key)
    if last_run:
        print(f"Last successful run: {last_run.isoformat()}")
    else:
        print(f"First run - will extract last {default_days} days")

    # Initialize HANA-optimized extractor
    extractor = HANAOptimizedTCodeExtractor(batch_size=5000)

    # Execute delta extraction
    print("\n=== EXTRACTING DELTA ===")
    result = extractor.extract_delta(
        username=ff_user,
        extraction_key=extraction_key,
        default_days=default_days
    )

    # Print results
    print(f"\nExtraction completed:")
    print(f"  Success: {result.success}")
    print(f"  Records: {result.record_count}")
    print(f"  Duration: {result.duration_ms}ms")
    print(f"  Checksum: {result.checksum[:16]}...")

    if result.errors:
        print(f"  Errors: {result.errors}")

    # Show sample records
    if result.data:
        print(f"\n=== SAMPLE RECORDS (first 5) ===")
        for record in result.data[:5]:
            print(f"\n  {record['tcode']} at {record['datetime']}")
            print(f"    Duration: {record['duration_ms']}ms")
            print(f"    Restricted: {record['is_restricted']}")

    # Show restricted activity
    restricted = [r for r in result.data if r.get("is_restricted")]
    if restricted:
        print(f"\n=== RESTRICTED ACTIVITY ({len(restricted)} records) ===")
        for record in restricted:
            print(f"  {record['tcode']} at {record['datetime']}")

    # Show state after extraction
    print("\n=== EXTRACTION STATE ===")
    state_mgr = get_state_manager()
    state = state_mgr.get_state(extraction_key)

    if state:
        print(f"  Last run: {state.last_run_timestamp}")
        print(f"  Last date: {state.last_run_date}")
        print(f"  Last time: {state.last_run_time}")
        print(f"  Records: {state.records_extracted}")
        print(f"  Failures: {state.consecutive_failures}")

    # Show metrics
    print("\n=== METRICS ===")
    metrics = get_metrics()
    internal = metrics.get("internal", {})

    if internal.get("summaries"):
        for name, stats in internal["summaries"].items():
            if "stad" in name.lower():
                print(f"  {name}:")
                print(f"    Count: {stats['count']}")
                print(f"    Avg: {stats['avg']:.3f}s")
                print(f"    Max: {stats['max']:.3f}s")

    # Save results
    output_file = f"ff_delta_{ff_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "extraction_key": extraction_key,
            "timestamp": datetime.now().isoformat(),
            "record_count": result.record_count,
            "data": result.data[:100],  # Limit to first 100 for file
            "metrics": internal,
        }, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
