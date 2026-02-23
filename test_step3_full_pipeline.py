"""
Step 3: Test Full Pipeline
DICOM → Images → MedGemma → Report
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import analyze_dicom_series

def test_full_pipeline():
    print("=" * 60)
    print("STEP 3: Testing Full Pipeline")
    print("=" * 60)
    
    # Get token
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("❌ ERROR: HUGGINGFACE_TOKEN not found")
        return False
    
    # Paths
    dicom_path = "/Users/vigneshwar.gurunatha/Desktop/medgemma/dicom_extracted/infarct_young"
    output_dir = "./test_output_pipeline"
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"\n1. DICOM path: {dicom_path}")
    print(f"2. Output directory: {output_dir}")
    print(f"3. Token: {hf_token[:10]}...{hf_token[-10:]}")
    
    print("\n4. Starting full pipeline...")
    print("   This will:")
    print("   - Extract DICOM slices")
    print("   - Convert to images")
    print("   - Send to MedGemma via Hugging Face")
    print("   - Generate analysis report")
    print("\n   ⚠️  Note: First API call may take 30-60 seconds (model loading)")
    print("   ⚠️  Note: This makes a real API call to Hugging Face\n")
    
    try:
        results = analyze_dicom_series(
            dicom_path=dicom_path,
            hf_token=hf_token,
            output_dir=output_dir,
            use_inference_api=True
        )
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Full pipeline completed")
        print("=" * 60)
        
        print("\n📊 Results Summary:")
        print(f"   - Metadata extracted: ✅")
        print(f"   - Images processed: ✅")
        print(f"   - MedGemma analysis: ✅")
        
        if 'analysis' in results:
            analysis = results['analysis']
            print(f"\n📈 Analysis Results:")
            print(f"   - Quality Score: {analysis.get('quality_score', 'N/A')}")
            print(f"   - Research Suitability: {analysis.get('research_suitability', 'N/A')}")
            print(f"   - Protocol Compliance: {analysis.get('protocol_compliance', 'N/A')}")
        
        print(f"\n📄 Report saved to: {output_dir}/medgemma_report.md")
        print(f"\n📁 Output files:")
        for file in Path(output_dir).glob("*"):
            if file.is_file():
                print(f"   - {file.name}")
        
        # Show a preview of the report
        report_path = Path(output_dir) / "medgemma_report.md"
        if report_path.exists():
            print(f"\n📝 Report Preview (first 500 chars):")
            print("-" * 60)
            with open(report_path, 'r') as f:
                preview = f.read()[:500]
                print(preview)
                if len(f.read()) > 500:
                    print("...")
            print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   - Check your Hugging Face token is valid")
        print("   - Check internet connection")
        print("   - First request may timeout - try again")
        return False

if __name__ == "__main__":
    success = test_full_pipeline()
    if success:
        print("\n✅ Step 3 Complete! Full pipeline works.")
        print("   Ready for Step 4: Girder Plugin Integration")
    sys.exit(0 if success else 1)
