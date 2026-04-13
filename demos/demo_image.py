"""
Demo 2: Image Understanding on Gemma 4 E4B.

Tests:
  1. Image captioning from URL
  2. OCR / text extraction
  3. Object detection with bounding boxes
  4. Local image understanding
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from e4b_loader import load_model_and_processor, generate, print_vram_stats

# Test images — public domain / permissively licensed
TEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Camponotus_flavomarginatus_ant.jpg/320px-Camponotus_flavomarginatus_ant.jpg"
OCR_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Google_2015_logo.svg/250px-Google_2015_logo.svg.png"


def demo_image_caption(model, processor):
    """Image captioning with a generated test image."""
    print("\n" + "=" * 60)
    print("TEST 1: Image Captioning")
    print("=" * 60)

    from PIL import Image, ImageDraw

    # Create a scene image
    img = Image.new("RGB", (400, 300), "#87CEEB")  # sky blue background
    draw = ImageDraw.Draw(img)
    # Green ground
    draw.rectangle([0, 200, 400, 300], fill="#228B22")
    # Yellow sun
    draw.ellipse([300, 20, 380, 100], fill="#FFD700")
    # Brown house
    draw.rectangle([100, 120, 250, 200], fill="#8B4513")
    # Red roof
    draw.polygon([(90, 120), (175, 60), (260, 120)], fill="#B22222")
    # White door
    draw.rectangle([155, 150, 195, 200], fill="white")

    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Describe this image in detail. What objects do you see?"}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=300)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")
    return len(response) > 20


def demo_ocr(model, processor):
    """OCR — extract text from generated image."""
    print("\n" + "=" * 60)
    print("TEST 2: OCR / Text Extraction")
    print("=" * 60)

    from PIL import Image, ImageDraw

    # Create an image with text
    img = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Town of Normal, Illinois", fill="black")
    draw.text((20, 60), "Population: 52,736", fill="darkblue")
    draw.text((20, 100), "Founded: 1865", fill="darkgreen")
    draw.text((20, 140), "Jemma Safety Report #42", fill="red")

    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Extract and list all visible text in this image."}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=200)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s): {response}")
    return len(response) > 5


def demo_bbox(model, processor):
    """Object detection with bounding boxes."""
    print("\n" + "=" * 60)
    print("TEST 3: Object Detection (Bounding Boxes)")
    print("=" * 60)

    from PIL import Image, ImageDraw

    # Create image with distinct objects
    img = Image.new("RGB", (500, 400), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill="red")       # Red square top-left
    draw.ellipse([300, 50, 450, 200], fill="blue")        # Blue circle top-right
    draw.polygon([(200, 350), (250, 250), (300, 350)], fill="green")  # Green triangle bottom

    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Detect all distinct objects in this image. For each object, provide its name and bounding box coordinates as [y_min, x_min, y_max, x_max] normalized to a 1000x1000 grid."}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=500)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")
    return len(response) > 10


def demo_local_image(model, processor):
    """Local image understanding — generate a test image and analyze it."""
    print("\n" + "=" * 60)
    print("TEST 4: Local Image Analysis")
    print("=" * 60)

    from PIL import Image, ImageDraw, ImageFont

    # Generate a simple test image with geometric shapes and text
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill="red", outline="black")
    draw.ellipse([200, 50, 350, 200], fill="blue", outline="black")
    draw.text((100, 250), "Jemma Test Image", fill="black")

    test_path = os.path.join(os.path.dirname(__file__), "test_image.png")
    img.save(test_path)
    print(f"Created test image: {test_path}")

    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Describe what you see in this image. What shapes and colors are present? What text is visible?"}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=300)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")

    # Cleanup
    if os.path.exists(test_path):
        os.remove(test_path)

    return len(response) > 20


if __name__ == "__main__":
    print("Loading Gemma 4 E4B for image demos...")
    # Use higher token budget for image understanding
    model, processor = load_model_and_processor(max_soft_tokens=560)
    print_vram_stats()

    results = {}
    for name, fn in [
        ("image_caption", demo_image_caption),
        ("ocr", demo_ocr),
        ("bbox", demo_bbox),
        ("local_image", demo_local_image),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback; traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("IMAGE DEMO RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print_vram_stats()
