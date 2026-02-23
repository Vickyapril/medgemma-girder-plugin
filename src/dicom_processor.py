"""
DICOM Processing Module
Extracts key slices and converts to images for MedGemma analysis
"""

import pydicom
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class DICOMProcessor:
    """Process DICOM files for MedGemma analysis"""
    
    def __init__(self, num_slices: int = 5):
        """
        Args:
            num_slices: Number of representative slices to extract
        """
        self.num_slices = num_slices
    
    def load_dicom_series(self, dicom_path: str) -> List[pydicom.Dataset]:
        """Load all DICOM files from directory"""
        dicom_files = []
        path = Path(dicom_path)
        
        for file_path in path.glob("*.dcm"):
            try:
                ds = pydicom.dcmread(str(file_path))
                dicom_files.append(ds)
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        # Sort by SliceLocation if available
        dicom_files.sort(key=lambda x: getattr(x, 'SliceLocation', 0))
        return dicom_files
    
    def extract_key_slices(self, dicom_files: List[pydicom.Dataset]) -> List[pydicom.Dataset]:
        """Extract representative slices from series"""
        if len(dicom_files) <= self.num_slices:
            return dicom_files
        
        # Strategy: evenly spaced + middle slice
        indices = []
        total = len(dicom_files)
        
        # Middle slice
        indices.append(total // 2)
        
        # Evenly spaced slices
        step = total // (self.num_slices - 1)
        for i in range(0, total, step):
            if i not in indices and len(indices) < self.num_slices:
                indices.append(i)
        
        return [dicom_files[i] for i in sorted(indices)]
    
    def dicom_to_image(self, dicom: pydicom.Dataset, output_path: str = None) -> Image.Image:
        """Convert DICOM pixel array to PIL Image"""
        # Get pixel array
        pixel_array = dicom.pixel_array.astype(np.float32)
        
        # Apply rescale if available (for CT/MR)
        slope = getattr(dicom, 'RescaleSlope', 1.0)
        intercept = getattr(dicom, 'RescaleIntercept', 0.0)
        pixel_array = pixel_array * slope + intercept
        
        # Normalize to 0-255
        pixel_array = pixel_array - pixel_array.min()
        if pixel_array.max() > 0:
            pixel_array = (pixel_array / pixel_array.max()) * 255
        
        # Convert to uint8
        pixel_array = pixel_array.astype(np.uint8)
        
        # Create PIL Image
        img = Image.fromarray(pixel_array)
        
        if output_path:
            img.save(output_path)
        
        return img
    
    def extract_metadata(self, dicom_files: List[pydicom.Dataset]) -> Dict:
        """Extract anonymized metadata from DICOM files"""
        if not dicom_files:
            return {}
        
        first_dicom = dicom_files[0]
        
        # Extract only safe, anonymized metadata
        metadata = {
            "modality": getattr(first_dicom, 'Modality', 'Unknown'),
            "study_description": getattr(first_dicom, 'StudyDescription', ''),
            "series_description": getattr(first_dicom, 'SeriesDescription', ''),
            "slice_count": len(dicom_files),
            "rows": getattr(first_dicom, 'Rows', 0),
            "columns": getattr(first_dicom, 'Columns', 0),
            "slice_thickness": getattr(first_dicom, 'SliceThickness', ''),
            "pixel_spacing": str(getattr(first_dicom, 'PixelSpacing', '')),
            "manufacturer": getattr(first_dicom, 'Manufacturer', ''),
            "manufacturer_model": getattr(first_dicom, 'ManufacturerModelName', ''),
        }
        
        return metadata
    
    def process_series(self, dicom_path: str, output_dir: str = None) -> Dict:
        """
        Main processing function
        Returns: {
            'images': [PIL.Image],
            'metadata': Dict,
            'image_paths': [str]
        }
        """
        # Load DICOM series
        dicom_files = self.load_dicom_series(dicom_path)
        
        if not dicom_files:
            raise ValueError("No DICOM files found")
        
        # Extract key slices
        key_slices = self.extract_key_slices(dicom_files)
        
        # Convert to images
        images = []
        image_paths = []
        
        for i, dicom in enumerate(key_slices):
            if output_dir:
                output_path = Path(output_dir) / f"slice_{i:03d}.png"
                img = self.dicom_to_image(dicom, str(output_path))
                image_paths.append(str(output_path))
            else:
                img = self.dicom_to_image(dicom)
            
            images.append(img)
        
        # Extract metadata
        metadata = self.extract_metadata(dicom_files)
        
        return {
            'images': images,
            'metadata': metadata,
            'image_paths': image_paths,
            'total_slices': len(dicom_files),
            'selected_slices': len(key_slices)
        }
