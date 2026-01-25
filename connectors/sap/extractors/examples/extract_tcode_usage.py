#!/usr/bin/env python3
"""
Example: Extract Transaction Usage for Firefighter

This script demonstrates how to extract and analyze
transaction code usage during a firefighter session.

Usage:
    python extract_tcode_usage.py <ff_user> <from_date> <to_date>
"""

import sys
from collections import Counter

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors import TransactionUsageExtractor


def main():
    # Parse arguments
    if len(sys.argv) < 4:
        print("Usage: python extract_tcode_usage.py <ff_user> <from_date> <to_date>")
        print("Example: python extract_tcode_usage.py FF_FIN_01 20240101 20240115")
        sys.exit(1)

    ff_user = sys.argv[1]
    from_date = sys.argv[2]
    to_date = sys.argv[3]

    print(f"Extracting transaction usage for {ff_user}")
    print(f"Period: {from_date} to {to_date}")
    print("-" * 50)

    # Initialize extractor
    extractor = TransactionUsageExtractor()

    # Get usage summary
    print("\n=== USAGE SUMMARY ===")
    summary = extractor.get_usage_summary(ff_user, from_date, to_date)

    print(f"Total executions: {summary['total_executions']}")
    print(f"Unique TCodes: {summary['unique_tcodes']}")
    print(f"Unique Programs: {summary['unique_programs']}")
    print(f"RFC Calls: {summary['rfc_calls']}")

    print("\n=== TOP TRANSACTIONS ===")
    for tcode, count in summary['top_tcodes']:
        print(f"  {tcode}: {count} executions")

    print("\n=== DURATION STATS ===")
    print(f"Average: {summary['duration_stats']['average_ms']:.2f}ms")
    print(f"Max: {summary['duration_stats']['max_ms']}ms")
    print(f"Total: {summary['duration_stats']['total_ms']}ms")

    print("\n=== RESTRICTED USAGE ===")
    restricted = summary['restricted_usage']
    print(f"Count: {restricted['count']}")
    if restricted['tcodes']:
        print(f"TCodes: {', '.join(restricted['tcodes'])}")

    # Get restricted tcode details
    print("\n=== RESTRICTED TCODE DETAILS ===")
    restricted_result = extractor.get_restricted_tcode_usage(
        ff_user, from_date, to_date
    )

    for record in restricted_result.data:
        print(f"\n{record['tcode']} at {record['datetime']}")
        print(f"  Risk: {record['risk_level']}")
        print(f"  Reason: {record['risk_reason']}")
        print(f"  Duration: {record['duration_ms']}ms")

    # Run anomaly detection
    print("\n=== ANOMALY DETECTION ===")
    anomalies = extractor.detect_anomalies(
        ff_user, from_date, to_date, baseline_days=30
    )

    print(f"Analysis period: {anomalies['analysis_period']}")
    print(f"Baseline period: {anomalies['baseline_period']}")
    print(f"Anomaly count: {anomalies['anomaly_count']}")
    print(f"Risk score: {anomalies['risk_score']}")

    if anomalies['anomalies']:
        print("\nDetected anomalies:")
        for anomaly in anomalies['anomalies']:
            print(f"  [{anomaly['severity'].upper()}] {anomaly['type']}")
            print(f"    {anomaly['description']}")

    # Show hourly distribution
    print("\n=== HOURLY DISTRIBUTION ===")
    dist = summary['hourly_distribution']
    for hour, count in sorted(dist.items()):
        if count > 0:
            bar = "#" * min(count, 50)
            print(f"{hour}: {bar} ({count})")


if __name__ == "__main__":
    main()
