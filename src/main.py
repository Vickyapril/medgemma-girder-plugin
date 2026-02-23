"""
Main integration script
Combines DICOM processing + MedGemma analysis
"""

from .dicom_processor import DICOMProcessor
from .medgemma_client import MedGemmaClient
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_dicom_series(
    dicom_path: str,
    hf_token: str = None,
    output_dir: str = None,
    use_inference_api: bool = True
) -> dict:
    """
    Complete pipeline: DICOM → Images → MedGemma → Report
    
    Args:
        dicom_path: Path to DICOM directory
        hf_token: Hugging Face API token
        output_dir: Output directory for images and report
        use_inference_api: If True, use HF Inference API; if False, load model locally
    
    Returns:
        Complete analysis results
    """
    # Initialize processors
    dicom_processor = DICOMProcessor(num_slices=5)
    # Default to local model loading (more reliable)
    medgemma_client = MedGemmaClient(hf_token=hf_token, use_inference_api=use_inference_api)
    
    # Process DICOM series
    logger.info(f"Processing DICOM series from {dicom_path}")
    processed_data = dicom_processor.process_series(
        dicom_path,
        output_dir=output_dir
    )
    
    # Send to MedGemma
    logger.info("Sending to MedGemma API...")
    analysis_result = medgemma_client.analyze_images(
        images=processed_data['images'],
        metadata=processed_data['metadata']
    )
    
    # Generate report
    report = medgemma_client.generate_report(analysis_result)
    
    # Save report if output_dir provided
    if output_dir:
        report_path = Path(output_dir) / "medgemma_report.md"
        with open(report_path, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {report_path}")
    
    return {
        'metadata': processed_data['metadata'],
        'analysis': analysis_result,
        'report': report
    }


if __name__ == "__main__":
    # Example usage - use absolute imports when running as script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from src.dicom_processor import DICOMProcessor
    from src.medgemma_client import MedGemmaClient
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    dicom_path = "/Users/vigneshwar.gurunatha/Desktop/medgemma/dicom_extracted/infarct_young"
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    output_dir = "./output"
    
    Path(output_dir).mkdir(exist_ok=True)
    
    dicom_processor = DICOMProcessor(num_slices=5)
    medgemma_client = MedGemmaClient(hf_token=hf_token, use_inference_api=True)
    
    processed_data = dicom_processor.process_series(dicom_path, output_dir)
    analysis_result = medgemma_client.analyze_images(
        images=processed_data['images'],
        metadata=processed_data['metadata']
    )
    report = medgemma_client.generate_report(analysis_result)
    
    print(report)
