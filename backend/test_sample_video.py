"""
Quick test: generate a sample video using the updated pipeline
with LLM-powered natural narration.
"""
import os
import sys
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.gamma_service import generate_presentation
from app.services.pptx_to_images import pptx_to_images, extract_slide_texts
from app.services.video_pipeline import generate_production_video
from app.config import settings

# Sample product data (AU Small Finance Bank Credit Card)
product_data = {
    "name": "AU Small Finance Bank Credit Card",
    "category_name": "Credit Card",
    "sub_type": "Credit Card",
    "payout": "Rs 750",
    "benefits_text": (
        "Lifetime Free Credit Card\n"
        "Cashback on every transaction\n"
        "Fuel surcharge waiver up to Rs 100/month\n"
        "No minimum CIBIL score required\n"
        "Instant digital card activation\n"
        "Complimentary lounge access"
    ),
    "how_works_text": (
        "Step 1: Open GroMo App and search AU SFB Credit Card\n"
        "Step 2: Share product link with customer\n"
        "Step 3: Customer fills application form with PAN and Aadhaar\n"
        "Step 4: eKYC verification via OTP\n"
        "Step 5: Card approved and dispatched within 7 days\n"
        "Step 6: You earn commission on successful activation — Check GroMo App for latest payout"
    ),
    "terms_conditions_text": (
        "Age: 21-65 years\n"
        "Income: Min Rs 15,000/month\n"
        "Documents: PAN Card, Aadhaar Card\n"
        "No joining fee, no annual fee\n"
        "Credit limit based on profile assessment"
    ),
}

output_dir = os.path.join(os.path.dirname(__file__), "test_output", "sample_video")
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print("STEP 1: Generating Gamma AI Presentation...")
print("=" * 60)

try:
    gamma_result = generate_presentation(
        product_data=product_data,
        job_type="single_product",
        language="hinglish",
        num_slides=8,
    )
    print(f"Gamma URL: {gamma_result.get('gamma_url')}")
    print(f"PPTX URL: {bool(gamma_result.get('pptx_url'))}")

    pptx_url = gamma_result.get("pptx_url")
    if not pptx_url:
        print("ERROR: No PPTX URL returned from Gamma!")
        sys.exit(1)

    # Download PPTX
    from app.services.gamma_service import download_pptx
    pptx_path = os.path.join(output_dir, "presentation.pptx")
    download_pptx(pptx_url, pptx_path)
    print(f"PPTX downloaded: {pptx_path}")

except Exception as e:
    print(f"Gamma generation failed: {e}")
    print("Proceeding without Gamma (will use DALL-E fallback)...")
    pptx_path = None

print()
print("=" * 60)
print("STEP 2: Converting PPTX to slide images...")
print("=" * 60)

gamma_slide_images = None
gamma_slide_texts = None

if pptx_path and os.path.exists(pptx_path):
    slides_dir = os.path.join(output_dir, "gamma_slides")
    gamma_slide_images = pptx_to_images(pptx_path, slides_dir)
    gamma_slide_texts = extract_slide_texts(pptx_path)
    print(f"Converted {len(gamma_slide_images)} slide images")
    print(f"Extracted text from {len(gamma_slide_texts)} slides")
    for st in gamma_slide_texts:
        print(f"  Slide {st['slide_num']}: {st['title'][:50]}...")

print()
print("=" * 60)
print("STEP 3: Generating video with NATURAL narration...")
print("=" * 60)

script_text = "GroMo Partner Training for AU Small Finance Bank Credit Card"

def progress(pct, msg):
    print(f"  [{pct:3d}%] {msg}")

result = generate_production_video(
    product_data=product_data,
    script_text=script_text,
    output_dir=output_dir,
    language="hinglish",
    on_progress=progress,
    gamma_slide_images=gamma_slide_images,
    gamma_slide_texts=gamma_slide_texts,
)

print()
print("=" * 60)
print("DONE!")
print("=" * 60)
print(f"Video: {result['video_path']}")
print(f"Duration: {result['duration']:.1f}s")
print(f"Slides: {result['num_slides']}")
print(f"Source: {result['source']}")
print(f"\nOpen video: open '{result['video_path']}'")
