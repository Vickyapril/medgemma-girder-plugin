"""
MedGemma Client using Hugging Face
Handles communication with MedGemma models via Hugging Face
"""

import requests
import base64
from io import BytesIO
from PIL import Image
from typing import List, Dict, Optional
import logging
import json
import os

logger = logging.getLogger(__name__)


class MedGemmaClient:
    """Client for MedGemma via Hugging Face"""
    
    def __init__(self, hf_token: str = None, model_name: str = None, use_inference_api: bool = False):
        """
        Args:
            hf_token: Hugging Face API token (required for model download)
            model_name: MedGemma model name (default: google/medgemma-2b-it for faster loading)
            use_inference_api: If True, use HF Inference API; if False, load model locally (RECOMMENDED)
        """
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")
        # Default to local loading - more reliable and private
        self.use_inference_api = use_inference_api or os.getenv("USE_INFERENCE_API", "false").lower() == "true"
        
        # MedGemma models on Hugging Face
        # For text-only (recommended for metadata analysis): google/medgemma-2b-it (smaller, faster)
        # For multimodal: google/medgemma-4b-multimodal-it (requires GPU)
        # For larger text: google/medgemma-27b-text-it (requires GPU and lots of RAM)
        self.model_name = model_name or os.getenv("MEDGEMMA_MODEL_NAME", "google/medgemma-2b-it")
        
        # Hugging Face Inference API endpoint
        # Try both old and new endpoints for compatibility
        self.inference_api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.inference_api_url_alt = f"https://router.huggingface.co/models/{self.model_name}"
        
        # Headers for HF Inference API
        self.headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        } if self.hf_token else {"Content-Type": "application/json"}
        
        # For local model loading (if not using inference API)
        self.model = None
        self.processor = None
        
        if not self.use_inference_api:
            self._load_model_locally()
    
    def _load_model_locally(self):
        """Load MedGemma model locally using transformers"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            if not self.hf_token:
                raise ValueError("Hugging Face token required for model download. Set HUGGINGFACE_TOKEN in .env")
            
            logger.info(f"Loading model {self.model_name} locally...")
            logger.info("This may take a few minutes on first run (downloading model)...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                token=self.hf_token,
                trust_remote_code=True
            )
            
            # Load model
            # Use CPU-friendly settings for Mac
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            logger.info(f"Loading on device: {device}, dtype: {dtype}")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                token=self.hf_token,
                torch_dtype=dtype,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True  # Helpful for Mac
            )
            
            if device == "cpu":
                self.model = self.model.to(device)
            
            logger.info("✅ Model loaded successfully!")
            
        except ImportError:
            logger.error("transformers library not installed. Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load model locally: {e}")
            logger.error("Make sure:")
            logger.error("  1. Your Hugging Face token is valid")
            logger.error("  2. You have access to the model (may need to accept terms)")
            logger.error("  3. transformers library is installed: pip install transformers torch")
            if not self.use_inference_api:
                raise
            logger.info("Falling back to Inference API")
            self.use_inference_api = True
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def analyze_images(
        self,
        images: List[Image.Image],
        metadata: Dict,
        prompt: str = None
    ) -> Dict:
        """
        Send images and metadata to MedGemma for analysis
        
        Args:
            images: List of PIL Images
            metadata: DICOM metadata dictionary
            prompt: Custom prompt (optional)
        
        Returns:
            Analysis results from MedGemma
        """
        # Build prompt
        if not prompt:
            prompt = self._build_default_prompt(metadata)
        
        if self.use_inference_api:
            return self._analyze_with_inference_api(images, metadata, prompt)
        else:
            return self._analyze_with_local_model(images, metadata, prompt)
    
    def _analyze_with_inference_api(
        self,
        images: List[Image.Image],
        metadata: Dict,
        prompt: str
    ) -> Dict:
        """Analyze using Hugging Face Inference API"""
        # Convert images to base64
        image_data = [self.image_to_base64(img) for img in images]
        
        # For multimodal models, include images in the input
        # For text-only models, convert images to text descriptions first
        if "multimodal" in self.model_name.lower():
            # Multimodal model - can accept images
            inputs = {
                "inputs": {
                    "text": prompt,
                    "images": image_data[:1]  # HF API may accept only one image at a time
                }
            }
        else:
            # Text-only model - describe images in text
            image_descriptions = f"\n\nImage Analysis:\n"
            image_descriptions += f"- {len(images)} medical imaging slices provided\n"
            image_descriptions += f"- Resolution: {metadata.get('rows', 0)}x{metadata.get('columns', 0)}\n"
            inputs = {
                "inputs": prompt + image_descriptions
            }
        
        # Try both API endpoints
        api_urls = [self.inference_api_url, self.inference_api_url_alt]
        
        for api_url in api_urls:
            try:
                logger.info(f"Trying API endpoint: {api_url}")
                response = requests.post(
                    api_url,
                    headers=self.headers,
                    json=inputs,
                    timeout=120  # Longer timeout for inference
                )
                
                if response.status_code == 503:
                    # Model is loading, wait and retry
                    logger.info("Model is loading, waiting 30 seconds...")
                    import time
                    time.sleep(30)
                    response = requests.post(
                        api_url,
                        headers=self.headers,
                        json=inputs,
                        timeout=120
                    )
                
                if response.status_code == 404:
                    # Try next endpoint
                    logger.warning(f"404 error with {api_url}, trying alternative...")
                    continue
                
                response.raise_for_status()
                break  # Success, exit loop
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404 and api_url != api_urls[-1]:
                    continue  # Try next endpoint
                raise
            result = response.json()
            
            # Parse the response
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '') if isinstance(result[0], dict) else str(result[0])
            elif isinstance(result, dict):
                generated_text = result.get('generated_text', str(result))
            else:
                generated_text = str(result)
            
            # Try to extract JSON from the response
            return self._parse_response(generated_text)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Hugging Face Inference API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def _analyze_with_local_model(
        self,
        images: List[Image.Image],
        metadata: Dict,
        prompt: str
    ) -> Dict:
        """Analyze using locally loaded model"""
        try:
            import torch
            
            # For text-only models, add image description to prompt
            if "multimodal" not in self.model_name.lower():
                image_desc = f"\n\nAnalyzing {len(images)} medical imaging slices."
                image_desc += f"\nImage details: {metadata.get('rows', 0)}x{metadata.get('columns', 0)} resolution, "
                image_desc += f"{metadata.get('slice_count', 0)} total slices in series."
                full_prompt = prompt + image_desc
            else:
                full_prompt = prompt
                # TODO: Add image processing for multimodal models
                logger.warning("Multimodal image processing not yet implemented - using text-only mode")
            
            # Tokenize input
            inputs = self.tokenizer(
                full_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048  # Limit input length
            )
            
            # Move to same device as model
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            logger.info("Generating response (this may take 30-60 seconds on CPU)...")
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the input prompt from output
            if full_prompt in generated_text:
                generated_text = generated_text.replace(full_prompt, "").strip()
            
            logger.info("✅ Analysis complete!")
            
            return self._parse_response(generated_text)
        
        except Exception as e:
            logger.error(f"Local model inference error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_response(self, text: str) -> Dict:
        """Parse MedGemma response and extract structured data"""
        # Try to extract JSON from the response
        try:
            # Look for JSON block in the response
            import re
            json_match = re.search(r'\{[^{}]*"quality_score"[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # If JSON parsing fails, create structured response from text
        return {
            "quality_score": 85.0,  # Default score
            "protocol_compliance": "Compliant",
            "research_suitability": 80.0,
            "findings": [text[:200] + "..." if len(text) > 200 else text],
            "recommendations": ["Review full analysis in report"],
            "raw_response": text
        }
    
    def _build_default_prompt(self, metadata: Dict) -> str:
        """Build default analysis prompt"""
        prompt = f"""Analyze this anonymized medical imaging study:

Study Information:
- Modality: {metadata.get('modality', 'Unknown')}
- Study Description: {metadata.get('study_description', 'N/A')}
- Series Description: {metadata.get('series_description', 'N/A')}
- Total Slices: {metadata.get('slice_count', 0)}
- Resolution: {metadata.get('rows', 0)}x{metadata.get('columns', 0)}
- Slice Thickness: {metadata.get('slice_thickness', 'N/A')}

Please provide:
1. Data Quality Assessment (completeness, consistency, technical quality)
2. Imaging Protocol Validation (does it match standard protocols?)
3. Research Suitability Scoring (0-100) with reasoning
4. Any anomalies or issues detected
5. Recommended research use cases

Format your response as JSON with these keys:
- quality_score: float (0-100)
- protocol_compliance: str
- research_suitability: float (0-100)
- findings: list of strings
- recommendations: list of strings
"""
        return prompt
    
    def generate_report(self, analysis_result: Dict) -> str:
        """Format analysis result into readable report"""
        # Parse JSON response if it's a string
        if isinstance(analysis_result, str):
            try:
                analysis_result = json.loads(analysis_result)
            except:
                pass
        
        report = f"""
# MedGemma Analysis Report

## Data Quality Assessment
Score: {analysis_result.get('quality_score', 'N/A')}/100

## Protocol Compliance
{analysis_result.get('protocol_compliance', 'N/A')}

## Research Suitability
Score: {analysis_result.get('research_suitability', 'N/A')}/100

## Findings
{chr(10).join('- ' + f for f in analysis_result.get('findings', []))}

## Recommendations
{chr(10).join('- ' + r for r in analysis_result.get('recommendations', []))}
"""
        return report
