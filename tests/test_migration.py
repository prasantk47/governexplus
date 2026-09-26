"""
Tests for the Migration Analyzer engine (ECC -> S/4HANA).

Uses the built-in in-memory knowledge base -- no DB setup required.
"""

import pytest

from core.migration.analyzer import (
    MigrationAnalyzer,
    MigrationStatus,
    MigrationRisk,
    AuthChangeType,
    TransactionImpact,
    AuthObjectChange,
    TRANSACTION_MAPPING,
    OBSOLETE_TRANSACTIONS,
    AUTH_OBJECT_CHANGES,
    FIORI_APP_CATALOG,
)


@pytest.fixture
def analyzer():
    return MigrationAnalyzer()


# ---------------------------------------------------------------------------
# TestKnowledgeBaseContents
# ---------------------------------------------------------------------------

class TestKnowledgeBaseContents:
    def test_transaction_mapping_is_large(self):
        assert len(TRANSACTION_MAPPING) >= 50

    def test_obsolete_transactions_exist(self):
        assert len(OBSOLETE_TRANSACTIONS) >= 15

    def test_auth_object_changes_exist(self):
        assert len(AUTH_OBJECT_CHANGES) >= 10

    def test_fiori_app_catalog_exists(self):
        assert len(FIORI_APP_CATALOG) >= 10

    def test_known_tcodes_present(self):
        for tcode in ("FB01", "ME21N", "VA01", "PA30", "SU01"):
            assert tcode in TRANSACTION_MAPPING

    def test_obsolete_tcodes_have_required_fields(self):
        for tcode, entry in OBSOLETE_TRANSACTIONS.items():
            assert "tcode" in entry
            assert "description" in entry
            assert "reason" in entry
            assert "business_process" in entry

    def test_auth_changes_have_required_fields(self):
        for obj_name, change in AUTH_OBJECT_CHANGES.items():
            assert isinstance(change, AuthObjectChange)
            assert change.object_name
            assert change.change_type in AuthChangeType

    def test_b_bupa_rlt_is_new_object(self):
        change = AUTH_OBJECT_CHANGES.get("B_BUPA_RLT")
        assert change is not None
        assert change.change_type == AuthChangeType.NEW

    def test_s_fiori_app_is_new_object(self):
        change = AUTH_OBJECT_CHANGES.get("S_FIORI_APP")
        assert change is not None
        assert change.change_type == AuthChangeType.NEW


# ---------------------------------------------------------------------------
# TestAnalyzeTransactions
# ---------------------------------------------------------------------------

class TestAnalyzeTransactions:
    def test_returns_transaction_impact(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_A", ["FB01", "ME21N"])
        assert isinstance(impact, TransactionImpact)

    def test_compatibility_pct_in_range(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_A", ["FB01", "ME21N", "VA01"])
        assert 0.0 <= impact.compatibility_pct <= 100.0

    def test_all_compatible_gives_100_pct(self, analyzer):
        compatible_tcodes = [
            tcode for tcode, m in TRANSACTION_MAPPING.items()
            if m.status == MigrationStatus.COMPATIBLE
        ][:5]
        impact = analyzer.analyze_transactions("ROLE_COMPAT", compatible_tcodes)
        assert impact.compatibility_pct == 100.0

    def test_replaced_tcodes_identified(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_B", ["XK01"])
        assert len(impact.replaced) >= 1

    def test_fiori_only_tcodes_identified(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_C", ["ME28"])
        assert len(impact.fiori_only) >= 1

    def test_unknown_tcodes_captured(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_D", ["ZZNOTREAL", "FB01"])
        assert "ZZNOTREAL" in impact.unknown

    def test_empty_tcode_list(self, analyzer):
        impact = analyzer.analyze_transactions("EMPTY_ROLE", [])
        assert impact.compatibility_pct == 100.0

    def test_impact_to_dict(self, analyzer):
        impact = analyzer.analyze_transactions("ROLE_F", ["FB01", "XK01"])
        d = impact.to_dict()
        assert "role_id" in d
        assert "compatible" in d
        assert "replaced" in d
        assert "compatibility_pct" in d


# ---------------------------------------------------------------------------
# TestGetObsoleteTcodes
# ---------------------------------------------------------------------------

class TestGetObsoleteTcodes:
    def test_obsolete_returns_list(self, analyzer):
        obsolete = analyzer.get_obsolete_transactions()
        assert isinstance(obsolete, list)

    def test_obsolete_list_non_empty(self, analyzer):
        obsolete = analyzer.get_obsolete_transactions()
        assert len(obsolete) >= 15

    def test_obsolete_entries_have_fields(self, analyzer):
        obsolete = analyzer.get_obsolete_transactions()
        for entry in obsolete:
            assert "tcode" in entry
            assert "description" in entry
            assert "reason" in entry


# ---------------------------------------------------------------------------
# TestGetFioriApps
# ---------------------------------------------------------------------------

class TestGetFioriApps:
    def test_fiori_apps_returns_list(self, analyzer):
        apps = analyzer.get_fiori_apps()
        assert isinstance(apps, list)

    def test_fiori_apps_non_empty(self, analyzer):
        apps = analyzer.get_fiori_apps()
        assert len(apps) >= 10

    def test_fiori_apps_have_required_fields(self, analyzer):
        apps = analyzer.get_fiori_apps()
        for app in apps:
            assert "app_id" in app
            assert "name" in app


# ---------------------------------------------------------------------------
# TestAuthObjectChanges
# ---------------------------------------------------------------------------

class TestAuthObjectChanges:
    def test_get_auth_changes_returns_list(self, analyzer):
        changes = analyzer.get_auth_object_changes()
        assert isinstance(changes, list)

    def test_auth_changes_non_empty(self, analyzer):
        changes = analyzer.get_auth_object_changes()
        assert len(changes) >= 10

    def test_auth_changes_are_dicts(self, analyzer):
        changes = analyzer.get_auth_object_changes()
        for c in changes:
            assert isinstance(c, dict)
            assert "object_name" in c
            assert "change_type" in c


# ---------------------------------------------------------------------------
# TestOverviewStats
# ---------------------------------------------------------------------------

class TestOverviewStats:
    def test_overview_returns_dict(self, analyzer):
        stats = analyzer.get_overview_stats()
        assert isinstance(stats, dict)

    def test_overview_has_transaction_mappings(self, analyzer):
        stats = analyzer.get_overview_stats()
        assert "transaction_mappings" in stats
        assert stats["transaction_mappings"] >= 50
