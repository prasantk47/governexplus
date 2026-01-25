"""
HRIS Connectors

Integrations with HR Information Systems for JML automation.
"""

from .workday import WorkdayConnector, WorkdayConfig, WorkdayWorker, WorkdayOrganization
from .successfactors import SuccessFactorsConnector, SuccessFactorsConfig, SFEmployee, SFOrganization

__all__ = [
    # Workday
    "WorkdayConnector",
    "WorkdayConfig",
    "WorkdayWorker",
    "WorkdayOrganization",
    # SuccessFactors
    "SuccessFactorsConnector",
    "SuccessFactorsConfig",
    "SFEmployee",
    "SFOrganization"
]
