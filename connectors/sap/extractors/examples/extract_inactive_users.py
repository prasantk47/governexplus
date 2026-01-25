#!/usr/bin/env python3
"""
Example: Extract Inactive Firefighter Users

This script demonstrates how to identify dormant/inactive
firefighter accounts that haven't been used recently.

Usage:
    python extract_inactive_users.py [days_threshold]
"""

import sys

# Add project root to path
sys.path.insert(0, "d:/grc-zero-trust-platform")

from connectors.sap.extractors import UserMasterExtractor


def main():
    # Parse arguments
    days_threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 90

    print(f"Extracting inactive firefighter users")
    print(f"Threshold: {days_threshold} days")
    print("-" * 50)

    # Initialize extractor
    extractor = UserMasterExtractor()

    # Extract inactive users
    result = extractor.get_inactive_users(
        days_threshold=days_threshold,
        user_pattern="FF_*"
    )

    print(f"\nFound {result.record_count} firefighter users")
    print(f"Extraction time: {result.duration_ms}ms")
    print(f"Checksum: {result.checksum[:16]}...")

    if result.errors:
        print(f"Errors: {result.errors}")

    print("\n=== USER STATUS ===")
    for user in result.data:
        status = "LOCKED" if user['lock_status']['locked'] else "ACTIVE"
        print(f"\n{user['username']} [{status}]")
        print(f"  Type: {user['user_type_text']}")
        print(f"  Valid: {user['valid_from']} to {user['valid_to']}")
        print(f"  Password changed: {user['password_change_date']}")

        if user['lock_status']['locked']:
            print(f"  Lock reason: ", end="")
            if user['lock_status']['admin_lock']:
                print("Admin lock", end=" ")
            if user['lock_status']['wrong_password']:
                print("Wrong password", end=" ")
            print()


if __name__ == "__main__":
    main()
