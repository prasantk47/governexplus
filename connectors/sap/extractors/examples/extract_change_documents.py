#!/usr/bin/env python3
"""
Example: Extract Change Documents for Firefighter Session

This script demonstrates how to extract change documents
(CDHDR/CDPOS) made during a firefighter session.

Usage:
    python extract_change_documents.py <ff_user> <from_date> <to_date>
"""

import sys
import json

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors import ChangeDocumentExtractor


def main():
    # Parse arguments
    if len(sys.argv) < 4:
        print("Usage: python extract_change_documents.py <ff_user> <from_date> <to_date>")
        print("Example: python extract_change_documents.py FF_FIN_01 20240101 20240115")
        sys.exit(1)

    ff_user = sys.argv[1]
    from_date = sys.argv[2]
    to_date = sys.argv[3]

    print(f"Extracting change documents for {ff_user}")
    print(f"Period: {from_date} to {to_date}")
    print("-" * 50)

    # Initialize extractor
    extractor = ChangeDocumentExtractor()

    # Get change summary
    print("\n=== CHANGE SUMMARY ===")
    summary = extractor.get_change_summary(ff_user, from_date, to_date)

    print(f"Total changes: {summary['total_changes']}")
    print(f"Total fields changed: {summary['total_fields_changed']}")
    print(f"Unique objects changed: {summary['unique_objects_changed']}")
    print(f"High-risk changes: {summary['high_risk_changes']}")

    print("\n=== BY OBJECT CLASS ===")
    for obj_class, count in summary['by_object_class'].items():
        print(f"  {obj_class}: {count}")

    print("\n=== CHANGE TYPES ===")
    for change_type, count in summary['change_types'].items():
        print(f"  {change_type}: {count}")

    print("\n=== TRANSACTIONS USED ===")
    for tcode in summary['transactions_used']:
        print(f"  {tcode}")

    # Get user-specific changes
    print("\n=== USER MASTER CHANGES ===")
    user_changes = extractor.get_user_changes(from_date, to_date, changed_by=ff_user)

    for change in user_changes.data:
        print(f"\nChanged: {change['object_id']} at {change['datetime']}")
        print(f"  Transaction: {change.get('transaction', 'N/A')}")

        classification = change.get('change_classification', {})
        if classification:
            print(f"  Category: {classification.get('category')}")
            print(f"  Severity: {classification.get('severity')}")
            print(f"  Description: {classification.get('description')}")

        for detail in change.get('details', []):
            print(f"    {detail['field_name']}: '{detail['old_value']}' -> '{detail['new_value']}'")

    # Get sensitive changes
    print("\n=== SENSITIVE CHANGES ===")
    sensitive = extractor.get_sensitive_changes(from_date, to_date, username=ff_user)

    for change in sensitive.data:
        risk_level = change.get('risk_level', 'unknown')
        print(f"\n[{risk_level.upper()}] {change['object_class']}: {change['object_id']}")
        print(f"  Changed at: {change['datetime']}")
        print(f"  Reason: {change.get('sensitivity_reason')}")

        risk = change.get('risk_assessment', {})
        if risk:
            print(f"  Risk score: {risk.get('risk_score')}")
            for factor in risk.get('risk_factors', []):
                print(f"    - {factor}")


if __name__ == "__main__":
    main()
