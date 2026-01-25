"""
SIEM Connector Module for Governex+

Provides real-time security event reporting to SIEM systems,
email notifications, and advanced event correlation.
"""

from .connector import SIEMConnector, SIEMEvent, SIEMEventType, SIEMSeverity
from .correlator import EventCorrelator, CorrelationRule, ThreatPattern

__all__ = [
    'SIEMConnector',
    'SIEMEvent',
    'SIEMEventType',
    'SIEMSeverity',
    'EventCorrelator',
    'CorrelationRule',
    'ThreatPattern'
]
