"""
ZIP file processing module
Extracts ZIP files and validates DICOM contents
"""
import zipfile
import os
import tempfile
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ZIPProcessor:
    """Process ZIP files containing DICOM data"""
    
    def extract_zip(self, zip_path: str, extract_to: str = None) -> str:
        """
        Extract ZIP file to directory
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Destination directory (creates temp if None)
        
        Returns:
            Path to extracted directory
        """
        if extract_to is None:
            extract_to = tempfile.mkdtemp(prefix="medgemma_zip_")
        
        os.makedirs(extract_to, exist_ok=True)
        
        logger.info(f"Extracting {zip_path} to {extract_to}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        return extract_to
    
    def find_dicom_files(self, directory: str) -> List[str]:
        """
        Find all DICOM files in directory (recursive)
        
        Args:
            directory: Directory to search
        
        Returns:
            List of DICOM file paths
        """
        dicom_files = []
        path = Path(directory)
        
        # Search for .dcm files
        for file_path in path.rglob("*.dcm"):
            dicom_files.append(str(file_path))
        
        # Also check files without extension (common DICOM format)
        for file_path in path.rglob("*"):
            if file_path.is_file() and '.' not in file_path.name:
                try:
                    import pydicom
                    pydicom.dcmread(str(file_path))
                    dicom_files.append(str(file_path))
                except:
                    pass
        
        logger.info(f"Found {len(dicom_files)} DICOM files")
        return dicom_files
    
    def extract_metadata_from_zip(self, zip_path: str) -> Dict:
        """
        Extract metadata from ZIP file without full extraction
        
        Args:
            zip_path: Path to ZIP file
        
        Returns:
            Dictionary with ZIP metadata
        """
        metadata = {
            'zip_file': zip_path,
            'file_count': 0,
            'dicom_count': 0,
            'total_size': 0
        }
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            metadata['file_count'] = len(file_list)
            
            for file_info in zip_ref.infolist():
                metadata['total_size'] += file_info.file_size
                if file_info.filename.endswith('.dcm') or '.' not in file_info.filename:
                    metadata['dicom_count'] += 1
        
        return metadata
