"""
Tests for the Identity Correlation engine.

Uses the built-in in-memory cluster data -- no DB setup required.
"""

import pytest
from core.identity_correlation.engine import (
    IdentityCorrelationEngine,
    IdentityCluster,
    OrphanAccount,
    CrossSystemRisk,
    CorrelationResult,
    CorrelationStats,
)


@pytest.fixture
def engine():
    return IdentityCorrelationEngine()


class TestOverview:
    def test_returns_stats(self, engine):
        stats = engine.get_overview()
        assert isinstance(stats, CorrelationStats)

    def test_has_total_accounts(self, engine):
        stats = engine.get_overview()
        assert stats.total_accounts >= 20

    def test_has_total_clusters(self, engine):
        stats = engine.get_overview()
        assert stats.total_clusters >= 5

    def test_has_by_system_counts(self, engine):
        stats = engine.get_overview()
        assert isinstance(stats.by_system, dict)
        assert len(stats.by_system) >= 2


class TestCorrelateAll:
    def test_returns_list_of_clusters(self, engine):
        clusters = engine.correlate_all()
        assert isinstance(clusters, list)
        assert len(clusters) >= 5

    def test_clusters_are_identity_cluster_objects(self, engine):
        clusters = engine.correlate_all()
        assert all(isinstance(c, IdentityCluster) for c in clusters)

    def test_clusters_have_accounts(self, engine):
        clusters = engine.correlate_all()
        for c in clusters:
            assert len(c.accounts) >= 1


class TestGetCluster:
    def test_returns_cluster_by_id(self, engine):
        clusters = engine.correlate_all()
        first = clusters[0]
        fetched = engine.get_cluster(first.cluster_id)
        assert fetched is not None
        assert fetched.cluster_id == first.cluster_id

    def test_unknown_cluster_raises(self, engine):
        with pytest.raises((KeyError, ValueError)):
            engine.get_cluster("ZZZNOTREAL")


class TestCorrelateUser:
    def test_returns_correlation_result(self, engine):
        # Get a known account from the first cluster
        clusters = engine.correlate_all()
        first_account = clusters[0].accounts[0]
        result = engine.correlate_user(first_account.username, first_account.system.value)
        assert isinstance(result, CorrelationResult)

    def test_result_has_matched_accounts(self, engine):
        clusters = engine.correlate_all()
        acct = clusters[0].accounts[0]
        result = engine.correlate_user(acct.username, acct.system.value)
        assert isinstance(result.matched_accounts, list)


class TestFindOrphans:
    def test_returns_list(self, engine):
        orphans = engine.find_orphans()
        assert isinstance(orphans, list)

    def test_orphans_are_orphan_account_objects(self, engine):
        orphans = engine.find_orphans()
        for o in orphans:
            assert isinstance(o, OrphanAccount)

    def test_orphans_have_reason(self, engine):
        orphans = engine.find_orphans()
        for o in orphans:
            assert isinstance(o.reason, str)
            assert len(o.reason) > 0


class TestCrossSystemRisk:
    def test_get_all_risks(self, engine):
        risks = engine.get_all_cross_system_risks()
        assert isinstance(risks, list)

    def test_risks_are_cross_system_risk_objects(self, engine):
        risks = engine.get_all_cross_system_risks()
        for r in risks:
            assert isinstance(r, CrossSystemRisk)

    def test_risks_have_description(self, engine):
        risks = engine.get_all_cross_system_risks()
        for r in risks:
            assert isinstance(r.description, str)
            assert len(r.description) > 0
