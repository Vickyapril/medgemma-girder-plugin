"""
MedGemma-Girder Plugin
Intelligent Research Data Management Platform
"""

from .dicom_processor import DICOMProcessor
from .medgemma_client import MedGemmaClient
from .main import analyze_dicom_series

__version__ = "1.0.0"
__all__ = ['DICOMProcessor', 'MedGemmaClient', 'analyze_dicom_series']
