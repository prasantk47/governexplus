"""
Custom Transaction Analysis Module
Analyzes custom SAP transactions (Z*/Y*) to detect behavior and SoD risks.
"""

from .analyzer import CustomTcodeAnalyzer

__all__ = ["CustomTcodeAnalyzer"]
