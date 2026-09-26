"""
Tests for the Role Drift Detection engine.

Uses the built-in in-memory landscape snapshots -- no DB setup required.
"""

import pytest

from core.drift.detector import (
    DriftDetector,
    DriftReport,
    DriftSummary,
    DriftSeverity,
    DriftType,
)


@pytest.fixture
def detector():
    return DriftDetector()


# ---------------------------------------------------------------------------
# TestSystemAndRoleLists
# ---------------------------------------------------------------------------

class TestSystemAndRoleLists:
    def test_get_systems_returns_list(self, detector):
        systems = detector.get_systems()
        assert isinstance(systems, list)
        assert len(systems) >= 2

    def test_known_systems_present(self, detector):
        systems = detector.get_systems()
        assert "DEV" in systems
        assert "PROD" in systems

    def test_list_roles_returns_list(self, detector):
        roles = detector.list_roles()
        assert isinstance(roles, list)
        assert len(roles) >= 10

    def test_known_roles_present(self, detector):
        roles = detector.list_roles()
        assert "Z_FI_AP_CLERK" in roles


# ---------------------------------------------------------------------------
# TestDetectDrift
# ---------------------------------------------------------------------------

class TestDetectDrift:
    def test_detect_drift_returns_report(self, detector):
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert isinstance(report, DriftReport)

    def test_aligned_role_has_no_findings(self, detector):
        """Z_FI_AP_CLERK is aligned across all systems."""
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert report.overall_severity == DriftSeverity.INFO
        assert len(report.findings) == 0

    def test_drifted_role_has_findings(self, detector):
        """Z_FI_GL_POSTING has an extra ACTVT value in DEV."""
        report = detector.detect_drift("Z_FI_GL_POSTING")
        assert len(report.findings) >= 1

    def test_missing_role_is_critical(self, detector):
        """Z_MM_PURCHASE_ORDER is missing from PROD."""
        report = detector.detect_drift("Z_MM_PURCHASE_ORDER")
        assert report.overall_severity == DriftSeverity.CRITICAL

    def test_report_has_role_name(self, detector):
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert report.role_name == "Z_FI_AP_CLERK"

    def test_report_has_systems_present(self, detector):
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert isinstance(report.systems_present, list)
        assert len(report.systems_present) >= 2

    def test_report_has_drift_hash(self, detector):
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert isinstance(report.drift_hash, dict)

    def test_aligned_role_is_not_drifted(self, detector):
        report = detector.detect_drift("Z_FI_AP_CLERK")
        assert report.is_drifted is False

    def test_drifted_role_is_flagged(self, detector):
        report = detector.detect_drift("Z_FI_GL_POSTING")
        assert report.is_drifted is True

    def test_finding_has_drift_type_attribute(self, detector):
        report = detector.detect_drift("Z_FI_GL_POSTING")
        for finding in report.findings:
            assert hasattr(finding, "drift_type")
            assert finding.drift_type in DriftType

    def test_finding_has_severity_attribute(self, detector):
        report = detector.detect_drift("Z_FI_GL_POSTING")
        for finding in report.findings:
            assert hasattr(finding, "severity")
            assert finding.severity in DriftSeverity


# ---------------------------------------------------------------------------
# TestScanAllDrift
# ---------------------------------------------------------------------------

class TestScanAllDrift:
    def test_scan_all_returns_list(self, detector):
        reports = detector.scan_all_drift()
        assert isinstance(reports, list)

    def test_scan_all_covers_all_roles(self, detector):
        roles = detector.list_roles()
        reports = detector.scan_all_drift()
        assert len(reports) == len(roles)

    def test_scan_all_results_are_drift_reports(self, detector):
        reports = detector.scan_all_drift()
        for r in reports:
            assert isinstance(r, DriftReport)

    def test_scan_all_contains_aligned_and_drifted(self, detector):
        reports = detector.scan_all_drift()
        severities = {r.overall_severity for r in reports}
        assert DriftSeverity.INFO in severities
        assert len(severities) > 1


# ---------------------------------------------------------------------------
# TestDriftSummary
# ---------------------------------------------------------------------------

class TestDriftSummary:
    def test_get_drift_summary_returns_summary(self, detector):
        summary = detector.get_drift_summary()
        assert isinstance(summary, DriftSummary)

    def test_summary_total_matches_role_count(self, detector):
        summary = detector.get_drift_summary()
        roles = detector.list_roles()
        assert summary.total_roles_scanned == len(roles)

    def test_summary_in_sync_plus_drifted_equals_total(self, detector):
        summary = detector.get_drift_summary()
        assert summary.roles_in_sync + summary.roles_drifted == summary.total_roles_scanned

    def test_summary_drift_percentage_in_range(self, detector):
        summary = detector.get_drift_summary()
        assert 0.0 <= summary.drift_percentage <= 100.0

    def test_summary_has_severity_breakdown(self, detector):
        summary = detector.get_drift_summary()
        assert isinstance(summary.by_severity, dict)

    def test_summary_has_systems_compared(self, detector):
        summary = detector.get_drift_summary()
        assert isinstance(summary.systems_compared, list)

    def test_summary_has_most_drifted_roles(self, detector):
        summary = detector.get_drift_summary()
        assert isinstance(summary.most_drifted_roles, list)

    def test_summary_roles_drifted_positive(self, detector):
        summary = detector.get_drift_summary()
        assert summary.roles_drifted >= 1


# ---------------------------------------------------------------------------
# TestCompareSystems
# ---------------------------------------------------------------------------

class TestCompareSystems:
    def test_compare_systems_returns_list(self, detector):
        reports = detector.compare_systems("DEV", "PROD")
        assert isinstance(reports, list)

    def test_compare_same_system_returns_no_drift(self, detector):
        reports = detector.compare_systems("DEV", "DEV")
        for r in reports:
            assert r.overall_severity == DriftSeverity.INFO

    def test_compare_dev_prod_finds_differences(self, detector):
        reports = detector.compare_systems("DEV", "PROD")
        drifted = [r for r in reports if r.overall_severity != DriftSeverity.INFO]
        assert len(drifted) >= 1
