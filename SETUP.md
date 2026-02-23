# Setup Guide - Using Hugging Face Token

## Step 1: Get Your Hugging Face Token

1. Go to https://huggingface.co/settings/tokens
2. Create a new token (read access is enough for Inference API)
3. Copy your token

## Step 2: Set Up Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and paste your token
# HUGGINGFACE_TOKEN=hf_your_token_here
```

**Important:** Never commit your `.env` file to git! It's already in `.gitignore`.

## Step 3: Install Dependencies

```bash
# Activate your virtual environment (if using one)
source venv_girder/bin/activate  # or your venv path

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Test the Setup

### Option A: Test DICOM Processing (No API needed)

```python
from src.dicom_processor import DICOMProcessor

processor = DICOMProcessor(num_slices=5)
result = processor.process_series(
    "/Users/vigneshwar.gurunatha/Desktop/medgemma/dicom_extracted/infarct_young",
    output_dir="./test_output"
)

print(f"✓ Processed {result['total_slices']} slices")
print(f"✓ Selected {result['selected_slices']} key slices")
print(f"✓ Metadata: {result['metadata']}")
```

### Option B: Test Full Pipeline (Requires HF Token)

```bash
# Make sure your .env file has HUGGINGFACE_TOKEN set
python src/main.py
```

## Available MedGemma Models

The code supports these MedGemma models on Hugging Face:

1. **google/medgemma-27b-text-it** (Default)
   - Text-only model
   - Best for metadata analysis
   - Works with Inference API

2. **google/medgemma-4b-multimodal-it**
   - Multimodal (text + images)
   - Can analyze actual images
   - Requires Inference API or local GPU

## Using Inference API vs Local Model

### Inference API (Recommended - No GPU needed)
- ✅ Works on Mac without GPU
- ✅ Free tier available
- ✅ No model download needed
- ⚠️ Requires internet connection
- ⚠️ May have rate limits

Set in `.env`:
```
USE_INFERENCE_API=true
```

### Local Model (Requires GPU)
- ✅ No internet needed after download
- ✅ No rate limits
- ✅ Full control
- ❌ Requires GPU (CUDA)
- ❌ Large model download (~50GB+)

Set in `.env`:
```
USE_INFERENCE_API=false
```

## Troubleshooting

### "Model is loading" error
- First request to HF Inference API may take 30-60 seconds
- The code automatically retries after waiting
- This is normal for free-tier models

### "Token not found" error
- Make sure `.env` file exists
- Check that `HUGGINGFACE_TOKEN` is set correctly
- Verify token has read access

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.9+ required)

## Security Notes

- ✅ Your token is stored locally in `.env` (not committed to git)
- ✅ Data stays on your machine (Inference API only receives anonymized data)
- ✅ No PHI is sent to Hugging Face (only anonymized metadata/images)
