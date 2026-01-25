#!/usr/bin/env python3
"""
Example: Extract Firefighter Session Audit Evidence

This script demonstrates how to use the FirefighterSessionExtractor
to pull complete audit evidence from SAP for a firefighter session.

Usage:
    python extract_firefighter_session.py FF_FIN_01 20240101 20240131
"""

import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors import (
    FirefighterSessionExtractor,
    SAPExtractorConfig,
)


def main():
    # Parse arguments
    if len(sys.argv) < 4:
        print("Usage: python extract_firefighter_session.py <ff_user> <from_date> <to_date>")
        print("Example: python extract_firefighter_session.py FF_FIN_01 20240101 20240131")
        sys.exit(1)

    ff_user = sys.argv[1]
    from_date = sys.argv[2]
    to_date = sys.argv[3]

    print(f"Extracting session evidence for {ff_user}")
    print(f"Period: {from_date} to {to_date}")
    print("-" * 50)

    # Initialize extractor (uses mock mode if pyrfc not available)
    extractor = FirefighterSessionExtractor()

    # Extract full session evidence
    evidence = extractor.extract_session(
        firefighter_id=ff_user,
        from_date=from_date,
        to_date=to_date,
        include_authorizations=True,
        include_changes=True
    )

    # Print summary
    print("\n=== SESSION SUMMARY ===")
    print(f"Session ID: {evidence.session_id}")
    print(f"Firefighter: {evidence.firefighter_id}")
    print(f"System: {evidence.system_id}")
    print(f"Start: {evidence.session_start}")
    print(f"End: {evidence.session_end}")
    print(f"Duration: {evidence.duration_minutes} minutes")

    print("\n=== STATISTICS ===")
    stats = evidence.statistics
    print(f"Transactions: {stats['transaction_count']}")
    print(f"Unique TCodes: {stats['unique_tcodes']}")
    print(f"Restricted TCodes: {stats['restricted_tcode_count']}")
    print(f"Changes: {stats['change_count']}")
    print(f"Risk Score: {stats['risk_score']}")

    print("\n=== AUDIT FLAGS ===")
    for flag in stats.get('audit_flags', []):
        print(f"  {flag}")

    print("\n=== RISK FACTORS ===")
    for factor in stats.get('risk_factors', []):
        print(f"  - {factor}")

    # Verify integrity
    print("\n=== EVIDENCE INTEGRITY ===")
    verification = extractor.verify_session_evidence(evidence)
    print(f"Valid: {verification['is_valid']}")
    print(f"Checksum: {verification['stored_checksum'][:32]}...")

    # Generate audit report
    print("\n=== GENERATING AUDIT REPORT ===")
    report = extractor.extract_audit_report(ff_user, from_date, to_date)

    # Save to file
    output_file = f"ff_session_{ff_user}_{from_date}_{to_date}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report saved to: {output_file}")

    print("\n=== COMPLIANCE STATUS ===")
    print(f"Status: {report['executive_summary']['compliance_status']}")


if __name__ == "__main__":
    main()
