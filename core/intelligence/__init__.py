"""
Core Intelligence Package

Exports the GRCIntelligenceEngine — the central brain of GovernexPlus.
Also exports GRCDigitalTwin — the live connected GRC state model.
"""

from .engine import GRCIntelligenceEngine
from .digital_twin import GRCDigitalTwin

__all__ = ["GRCIntelligenceEngine", "GRCDigitalTwin"]
