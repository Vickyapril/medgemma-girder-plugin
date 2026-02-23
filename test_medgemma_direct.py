"""
Test MedGemma with Direct Model Loading
This bypasses the API and loads the model directly
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.medgemma_client import MedGemmaClient

def test_direct_model():
    print("=" * 60)
    print("Testing MedGemma with Direct Model Loading")
    print("=" * 60)
    
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("❌ ERROR: HUGGINGFACE_TOKEN not found")
        return False
    
    print(f"\n1. Token: {hf_token[:10]}...{hf_token[-10:]}")
    print("2. Loading model directly (no API)...")
    print("   This will download the model on first run (may take 5-10 minutes)")
    print("   Subsequent runs will be faster (model cached)")
    
    try:
        # Use local loading (use_inference_api=False)
        client = MedGemmaClient(
            hf_token=hf_token,
            model_name="google/medgemma-2b-it",  # Smaller model for testing
            use_inference_api=False  # Load locally!
        )
        
        print("\n3. Testing with sample metadata...")
        test_metadata = {
            "modality": "MR",
            "study_description": "Cardiac MRI",
            "series_description": "T1-weighted",
            "slice_count": 512,
            "rows": 684,
            "columns": 630,
            "slice_thickness": "0.21"
        }
        
        # Create a simple test prompt
        prompt = client._build_default_prompt(test_metadata)
        
        print("4. Running inference (this may take 30-60 seconds on CPU)...")
        # Test with empty images list (text-only model)
        result = client.analyze_images(
            images=[],  # Empty for text-only model
            metadata=test_metadata,
            prompt=prompt
        )
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! MedGemma is working!")
        print("=" * 60)
        print("\n📊 Results:")
        print(f"   Quality Score: {result.get('quality_score', 'N/A')}")
        print(f"   Research Suitability: {result.get('research_suitability', 'N/A')}")
        print(f"   Protocol Compliance: {result.get('protocol_compliance', 'N/A')}")
        
        if 'raw_response' in result:
            print(f"\n📝 Raw Response (first 200 chars):")
            print(f"   {result['raw_response'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   1. Make sure transformers is installed: pip install transformers torch")
        print("   2. Check your Hugging Face token is valid")
        print("   3. You may need to accept model terms on Hugging Face website")
        print("   4. Model download requires internet connection")
        return False

if __name__ == "__main__":
    success = test_direct_model()
    if success:
        print("\n✅ MedGemma direct loading works!")
        print("   You can now use this in your full pipeline!")
    sys.exit(0 if success else 1)
