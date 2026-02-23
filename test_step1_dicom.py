"""
Step 1: Test DICOM Processing (No API needed)
This verifies that DICOM files can be loaded and converted to images
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.dicom_processor import DICOMProcessor

def test_dicom_processing():
    print("=" * 60)
    print("STEP 1: Testing DICOM Processing")
    print("=" * 60)
    
    # Path to your DICOM data
    dicom_path = "/Users/vigneshwar.gurunatha/Desktop/medgemma/dicom_extracted/infarct_young"
    output_dir = "./test_output"
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"\n1. Loading DICOM files from: {dicom_path}")
    processor = DICOMProcessor(num_slices=5)
    
    try:
        # Process the DICOM series
        print("2. Processing DICOM series...")
        result = processor.process_series(dicom_path, output_dir=output_dir)
        
        print("\n✅ SUCCESS!")
        print(f"   - Total slices found: {result['total_slices']}")
        print(f"   - Key slices extracted: {result['selected_slices']}")
        print(f"   - Images saved to: {output_dir}")
        print(f"\n   Metadata:")
        for key, value in result['metadata'].items():
            print(f"     - {key}: {value}")
        
        print(f"\n   Image files created:")
        for img_path in result['image_paths']:
            print(f"     - {img_path}")
        
        print("\n✅ Step 1 Complete! DICOM processing works.")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dicom_processing()
    sys.exit(0 if success else 1)
