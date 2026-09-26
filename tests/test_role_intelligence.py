"""
Tests for the Role Intelligence Engine.

Uses the built-in in-memory role catalogue — no DB setup required.
"""

import pytest

from core.role_intelligence.engine import (
    RoleIntelligenceEngine,
    SimilarityResult,
    DuplicateGroup,
    RoleHealthScore,
    ConsolidationPlan,
    UsageReport,
    NamingReport,
    ConsolidationRisk,
    _SEED_CATALOGUE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    # Pass seed catalogue directly to bypass DB and preserve R001-style IDs
    return RoleIntelligenceEngine(catalogue=_SEED_CATALOGUE)


# ---------------------------------------------------------------------------
# TestCatalogueBasics
# ---------------------------------------------------------------------------

class TestCatalogueBasics:
    def test_catalogue_has_expected_size(self, engine):
        assert len(engine._catalogue) >= 40

    def test_index_keys_match_catalogue_ids(self, engine):
        for role in engine._catalogue:
            assert role["id"] in engine._index

    def test_get_role_raises_on_unknown_id(self, engine):
        with pytest.raises(KeyError, match="ZZUNKNOWN"):
            engine._get_role("ZZUNKNOWN")

    def test_get_role_returns_dict(self, engine):
        role = engine._get_role("R001")
        assert isinstance(role, dict)
        assert role["id"] == "R001"


# ---------------------------------------------------------------------------
# TestSimilarityAnalysis
# ---------------------------------------------------------------------------

class TestSimilarityAnalysis:
    def test_returns_similarity_result(self, engine):
        result = engine.analyze_similarity("R001", "R002")
        assert isinstance(result, SimilarityResult)

    def test_scores_in_valid_range(self, engine):
        result = engine.analyze_similarity("R001", "R002")
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.transaction_score <= 1.0
        assert 0.0 <= result.auth_object_score <= 1.0
        assert 0.0 <= result.org_value_score <= 1.0

    def test_highly_similar_roles_score_high(self, engine):
        """R001 (Z_FI_AP_PROCESSOR) and R002 (Z_FI_AP_CLERK) share many transactions."""
        result = engine.analyze_similarity("R001", "R002")
        assert result.overall_score >= 0.50

    def test_shared_transactions_are_subsets(self, engine):
        result = engine.analyze_similarity("R001", "R002")
        role_a_txns = set(engine._get_role("R001")["transactions"])
        role_b_txns = set(engine._get_role("R002")["transactions"])
        for txn in result.shared_transactions:
            assert txn in role_a_txns
            assert txn in role_b_txns

    def test_unique_to_a_not_in_b(self, engine):
        result = engine.analyze_similarity("R001", "R009")
        role_b_txns = set(engine._get_role("R009")["transactions"])
        for txn in result.unique_to_a:
            assert txn not in role_b_txns

    def test_serialization_to_dict(self, engine):
        d = engine.analyze_similarity("R001", "R002").to_dict()
        assert "role_a" in d
        assert "role_b" in d
        assert "overall_score" in d
        assert "recommendation" in d

    def test_role_identity_similarity_is_high(self, engine):
        """A role compared to itself should yield very high similarity via jaccard."""
        result = engine.analyze_similarity("R001", "R001")
        assert result.overall_score >= 0.90

    def test_distinct_roles_score_lower(self, engine):
        """Finance AP role vs HR Time Admin should have lower similarity."""
        result = engine.analyze_similarity("R001", "R022")
        # Expect lower overall — different process, auth objects, org values
        assert result.overall_score < 0.80


# ---------------------------------------------------------------------------
# TestDuplicateDetection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def test_find_duplicates_returns_list(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        assert isinstance(groups, list)

    def test_duplicate_groups_have_at_least_two_roles(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        for group in groups:
            assert len(group.roles) >= 2

    def test_canonical_role_in_group(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        for group in groups:
            assert group.recommended_canonical in group.roles

    def test_retirement_candidates_exclude_canonical(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        for group in groups:
            assert group.recommended_canonical not in group.retirement_candidates

    def test_group_ids_are_unique(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        ids = [g.group_id for g in groups]
        assert len(ids) == len(set(ids))

    def test_high_threshold_returns_fewer_groups(self, engine):
        groups_70 = engine.find_duplicates(threshold=0.70)
        groups_95 = engine.find_duplicates(threshold=0.95)
        assert len(groups_95) <= len(groups_70)

    def test_serialization_to_dict(self, engine):
        groups = engine.find_duplicates(threshold=0.70)
        if groups:
            d = groups[0].to_dict()
            assert "group_id" in d
            assert "roles" in d
            assert "similarity_score" in d
            assert "recommended_canonical" in d


# ---------------------------------------------------------------------------
# TestRoleHealthScore
# ---------------------------------------------------------------------------

class TestRoleHealthScore:
    def test_health_score_returns_role_health_score(self, engine):
        score = engine.calculate_health("R001")
        assert isinstance(score, RoleHealthScore)

    def test_score_in_valid_range(self, engine):
        score = engine.calculate_health("R001")
        assert 0 <= score.overall_score <= 100

    def test_grade_is_valid(self, engine):
        score = engine.calculate_health("R001")
        assert score.grade in ("A", "B", "C", "D", "F")

    def test_role_with_owner_scores_higher_than_without(self, engine):
        """R001 has owner 'Maria.Gonzalez'; R006 has no owner."""
        score_with_owner = engine.calculate_health("R001")
        score_no_owner = engine.calculate_health("R006")
        assert score_with_owner.overall_score > score_no_owner.overall_score

    def test_role_with_sod_conflict_loses_points(self, engine):
        """R006 has has_sod_conflict=True — SoD dimension should be 0."""
        score = engine.calculate_health("R006")
        assert score.dimension_scores["sod_conflicts"] == 0

    def test_unused_role_gets_lower_score(self, engine):
        """R007 has user_count=0 and last_used 400 days ago."""
        score = engine.calculate_health("R007")
        assert score.dimension_scores["user_count"] == 0

    def test_never_used_role_gets_zero_usage_score(self, engine):
        """R043 has last_used=None."""
        score = engine.calculate_health("R043")
        assert score.dimension_scores["recent_usage"] == 0

    def test_issues_list_is_list(self, engine):
        score = engine.calculate_health("R001")
        assert isinstance(score.issues, list)

    def test_recommendations_present_for_bad_role(self, engine):
        score = engine.calculate_health("R007")
        assert len(score.recommendations) > 0

    def test_calculate_health_all_returns_all_roles(self, engine):
        scores = engine.calculate_health_all()
        assert len(scores) == len(engine._catalogue)

    def test_health_all_sorted_ascending(self, engine):
        scores = engine.calculate_health_all()
        for i in range(len(scores) - 1):
            assert scores[i].overall_score <= scores[i + 1].overall_score


# ---------------------------------------------------------------------------
# TestUsageAnalytics
# ---------------------------------------------------------------------------

class TestUsageAnalytics:
    def test_get_usage_stats_returns_usage_report(self, engine):
        report = engine.get_usage_stats()
        assert isinstance(report, UsageReport)

    def test_total_roles_matches_catalogue(self, engine):
        report = engine.get_usage_stats()
        assert report.total_roles == len(engine._catalogue)

    def test_unused_roles_have_zero_users(self, engine):
        report = engine.get_usage_stats()
        for stat in report.unused_roles:
            assert stat.user_count == 0
            assert stat.is_unused is True

    def test_active_roles_have_multiple_users(self, engine):
        report = engine.get_usage_stats()
        for stat in report.active_roles:
            assert stat.user_count > 2

    def test_retirement_candidates_exist(self, engine):
        report = engine.get_usage_stats()
        assert len(report.retirement_candidates) >= 1

    def test_serialization_to_dict(self, engine):
        d = engine.get_usage_stats().to_dict()
        assert "total_roles" in d
        assert "unused_count" in d
        assert "retirement_candidates" in d


# ---------------------------------------------------------------------------
# TestConsolidationPlan
# ---------------------------------------------------------------------------

class TestConsolidationPlan:
    def test_recommend_consolidation_returns_plan(self, engine):
        plan = engine.recommend_consolidation(threshold=0.70)
        assert isinstance(plan, ConsolidationPlan)

    def test_plan_total_roles_matches_catalogue(self, engine):
        plan = engine.recommend_consolidation(threshold=0.70)
        assert plan.total_roles_analysed == len(engine._catalogue)

    def test_plan_roles_saveable_non_negative(self, engine):
        plan = engine.recommend_consolidation(threshold=0.70)
        assert plan.total_roles_saveable >= 0

    def test_serialization_to_dict(self, engine):
        plan = engine.recommend_consolidation(threshold=0.70)
        d = plan.to_dict()
        assert "total_roles_analysed" in d
        assert "consolidation_groups" in d
        assert "total_roles_saveable" in d


# ---------------------------------------------------------------------------
# TestNamingConventionAnalysis
# ---------------------------------------------------------------------------

class TestNamingConventionAnalysis:
    def test_analyze_naming_returns_naming_report(self, engine):
        report = engine.analyze_naming()
        assert isinstance(report, NamingReport)

    def test_total_roles_matches_catalogue(self, engine):
        report = engine.analyze_naming()
        assert report.total_roles == len(engine._catalogue)

    def test_compliant_plus_non_compliant_equals_total(self, engine):
        report = engine.analyze_naming()
        assert report.compliant_count + report.non_compliant_count == report.total_roles

    def test_antipattern_roles_are_non_compliant(self, engine):
        """Roles with TEMP, COPY, TEST, OLD in name should be flagged."""
        report = engine.analyze_naming()
        flagged_names = {issue.role_name for issue in report.issues}
        # R006 is Z_AP_TEMP — should be flagged
        assert any("TEMP" in n.upper() or "OLD" in n.upper() or "COPY" in n.upper()
                   for n in flagged_names)

    def test_convention_summary_has_expected_keys(self, engine):
        report = engine.analyze_naming()
        summary = report.convention_summary
        assert "single_role_pattern" in summary
        assert "forbidden_tokens" in summary

    def test_serialization_to_dict(self, engine):
        d = engine.analyze_naming().to_dict()
        assert "total_roles" in d
        assert "compliance_rate" in d
        assert "issues" in d


# ---------------------------------------------------------------------------
# TestFullAnalysis
# ---------------------------------------------------------------------------

class TestFullAnalysis:
    def test_run_full_analysis_returns_dict(self, engine):
        result = engine.run_full_analysis()
        assert isinstance(result, dict)

    def test_full_analysis_has_summary_key(self, engine):
        result = engine.run_full_analysis()
        assert "summary" in result
        summary = result["summary"]
        assert "total_roles" in summary
        assert "average_health_score" in summary

    def test_full_analysis_has_all_sections(self, engine):
        result = engine.run_full_analysis()
        for section in ("usage", "duplicates", "consolidation", "health_scores", "naming"):
            assert section in result


# ---------------------------------------------------------------------------
# TestGetOverview
# ---------------------------------------------------------------------------

class TestGetOverview:
    def test_get_overview_returns_dict(self, engine):
        overview = engine.get_overview()
        assert isinstance(overview, dict)

    def test_overview_has_expected_keys(self, engine):
        overview = engine.get_overview()
        for key in ("total_roles", "average_health_score", "grade_distribution",
                    "roles_by_business_process", "unused_roles", "roles_without_owner"):
            assert key in overview

    def test_overview_ownership_rate_valid(self, engine):
        overview = engine.get_overview()
        assert 0.0 <= overview["ownership_rate_pct"] <= 100.0
