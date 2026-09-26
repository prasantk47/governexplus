"""
Tests for the Fiori Security Analyzer engine.

Uses the built-in in-memory app catalog and mock users -- no DB setup required.
"""

import pytest
from core.fiori.analyzer import (
    FioriSecurityAnalyzer,
    FioriApp,
    FioriAccessTrace,
    AppRequirements,
    TileDiagnosis,
    CatalogAnalysis,
    LayerStatus,
    ErrorPattern,
)


@pytest.fixture
def analyzer():
    return FioriSecurityAnalyzer()


class TestListApps:
    def test_returns_list(self, analyzer):
        apps = analyzer.list_apps()
        assert isinstance(apps, list)

    def test_at_least_30_apps(self, analyzer):
        assert len(analyzer.list_apps()) >= 30

    def test_apps_are_fiori_app_objects(self, analyzer):
        apps = analyzer.list_apps()
        assert all(isinstance(a, FioriApp) for a in apps)

    def test_apps_have_required_attributes(self, analyzer):
        for app in analyzer.list_apps():
            assert app.app_id
            assert app.name
            assert app.catalog_id
            assert isinstance(app.odata_services, list)


class TestGetAppRequirements:
    def test_returns_app_requirements(self, analyzer):
        reqs = analyzer.get_app_requirements("F0842A")
        assert isinstance(reqs, AppRequirements)

    def test_has_app_id(self, analyzer):
        reqs = analyzer.get_app_requirements("F0842A")
        assert reqs.app_id == "F0842A"

    def test_requirements_have_auth_objects(self, analyzer):
        reqs = analyzer.get_app_requirements("F0842A")
        assert isinstance(reqs.auth_objects, list)
        assert len(reqs.auth_objects) > 0

    def test_requirements_have_odata_service(self, analyzer):
        reqs = analyzer.get_app_requirements("F0842A")
        assert isinstance(reqs.odata_services, list)
        assert len(reqs.odata_services) > 0

    def test_unknown_app_raises(self, analyzer):
        with pytest.raises((KeyError, ValueError)):
            analyzer.get_app_requirements("ZZZNOTREAL")


class TestTraceApp:
    def test_returns_trace(self, analyzer):
        trace = analyzer.trace_app("F0842A", "U001")
        assert isinstance(trace, FioriAccessTrace)

    def test_trace_has_overall_status(self, analyzer):
        trace = analyzer.trace_app("F0842A", "U001")
        assert trace.overall_status in LayerStatus

    def test_trace_has_chain(self, analyzer):
        trace = analyzer.trace_app("F0842A", "U001")
        assert isinstance(trace.chain, list)
        assert len(trace.chain) > 0

    def test_trace_has_summary(self, analyzer):
        trace = analyzer.trace_app("F0842A", "U001")
        assert isinstance(trace.summary, str)
        assert len(trace.summary) > 0


class TestDiagnoseTileError:
    def test_returns_tile_diagnosis(self, analyzer):
        diag = analyzer.diagnose_tile_error("F0842A", "U001")
        assert isinstance(diag, TileDiagnosis)

    def test_diagnosis_has_root_cause(self, analyzer):
        diag = analyzer.diagnose_tile_error("F0842A", "U001")
        assert isinstance(diag.root_cause, str)

    def test_diagnosis_has_remediation(self, analyzer):
        diag = analyzer.diagnose_tile_error("F0842A", "U001")
        assert isinstance(diag.remediation_steps, list)


class TestAnalyzeCatalog:
    def test_returns_catalog_analysis(self, analyzer):
        analysis = analyzer.analyze_catalog("SAP_MM_BC_PO_MANAGE")
        assert isinstance(analysis, CatalogAnalysis)

    def test_catalog_has_apps(self, analyzer):
        analysis = analyzer.analyze_catalog("SAP_MM_BC_PO_MANAGE")
        assert analysis.app_count >= 1


class TestListCatalogs:
    def test_returns_list(self, analyzer):
        catalogs = analyzer.list_catalogs()
        assert isinstance(catalogs, list)
        assert len(catalogs) >= 1

    def test_catalog_entries_have_id(self, analyzer):
        catalogs = analyzer.list_catalogs()
        for c in catalogs:
            assert "catalog_id" in c


class TestListOdataServices:
    def test_returns_list(self, analyzer):
        services = analyzer.list_odata_services()
        assert isinstance(services, list)
        assert len(services) >= 1
