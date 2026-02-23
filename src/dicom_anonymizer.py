"""
DICOM Anonymization Module
Removes PHI (Protected Health Information) from DICOM files
"""
import pydicom
from pathlib import Path
from typing import List, Dict
import logging
import shutil

logger = logging.getLogger(__name__)


class DICOMAnonymizer:
    """Anonymize DICOM files by removing PHI"""
    
    # Tags to remove/clear (PHI tags)
    PHI_TAGS = [
        'PatientName',
        'PatientID',
        'PatientBirthDate',
        'PatientSex',
        'PatientAge',
        'PatientAddress',
        'PatientTelephoneNumbers',
        'InstitutionName',
        'InstitutionAddress',
        'ReferringPhysicianName',
        'PerformingPhysicianName',
        'OperatorName',
        'StudyDate',
        'StudyTime',
        'AccessionNumber',
        'StudyInstanceUID',  # Sometimes anonymized
        'SeriesInstanceUID',  # Sometimes anonymized
    ]
    
    # Tags to keep but anonymize
    TAGS_TO_ANONYMIZE = {
        'PatientName': 'ANONYMOUS',
        'PatientID': 'ANONYMOUS',
    }
    
    def anonymize_file(self, dicom_path: str, output_path: str = None) -> str:
        """
        Anonymize a single DICOM file
        
        Args:
            dicom_path: Path to DICOM file
            output_path: Output path (overwrites original if None)
        
        Returns:
            Path to anonymized file
        """
        if output_path is None:
            output_path = dicom_path
        
        # Read DICOM file
        ds = pydicom.dcmread(dicom_path)
        
        # Remove PHI tags
        for tag_name in self.PHI_TAGS:
            if hasattr(ds, tag_name):
                if tag_name in self.TAGS_TO_ANONYMIZE:
                    setattr(ds, tag_name, self.TAGS_TO_ANONYMIZE[tag_name])
                else:
                    delattr(ds, tag_name)
        
        # Save anonymized file
        ds.save_as(output_path)
        logger.info(f"Anonymized {dicom_path}")
        
        return output_path
    
    def anonymize_directory(self, dicom_dir: str, output_dir: str = None) -> List[str]:
        """
        Anonymize all DICOM files in directory
        
        Args:
            dicom_dir: Directory containing DICOM files
            output_dir: Output directory (overwrites if None)
        
        Returns:
            List of anonymized file paths
        """
        if output_dir is None:
            output_dir = dicom_dir
        else:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        dicom_files = list(Path(dicom_dir).glob("*.dcm"))
        anonymized_files = []
        
        for dicom_file in dicom_files:
            output_path = Path(output_dir) / dicom_file.name
            anonymized_path = self.anonymize_file(str(dicom_file), str(output_path))
            anonymized_files.append(anonymized_path)
        
        logger.info(f"Anonymized {len(anonymized_files)} DICOM files")
        return anonymized_files
