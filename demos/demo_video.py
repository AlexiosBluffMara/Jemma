"""
Demo 4: Video Understanding on Gemma 4 E4B.

Tests:
  1. Synthetic video analysis (generated frames)
  2. Video description with thinking mode

E4B video specs:
  - Max 60 seconds at 1 fps
  - Processed as frame sequences
  - Lower token budgets per frame recommended
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from e4b_loader import load_model_and_processor, generate, print_vram_stats


def create_test_video(duration_seconds=5, fps=1, width=320, height=240):
    """Generate a synthetic test video with moving shapes.

    Creates an MP4 with a circle moving across frames.

    Returns:
        path to the saved .mp4 file
    """
    import av
    from PIL import Image, ImageDraw

    path = os.path.join(os.path.dirname(__file__), "test_video.mp4")
    num_frames = duration_seconds * fps

    container = av.open(path, mode="w")
    stream = container.add_stream("mpeg4", rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"

    for i in range(num_frames):
        # Create frame with a moving red circle
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        # Circle moves left to right
        x = int((i / max(num_frames - 1, 1)) * (width - 60)) + 30
        y = height // 2
        draw.ellipse([x - 30, y - 30, x + 30, y + 30], fill="red", outline="black")

        # Frame counter
        draw.text((10, 10), f"Frame {i+1}/{num_frames}", fill="black")

        frame = av.VideoFrame.from_image(img)
        for packet in stream.encode(frame):
            container.mux(packet)

    # Flush encoder
    for packet in stream.encode():
        container.mux(packet)
    container.close()

    print(f"Created test video: {path} ({duration_seconds}s, {fps} fps, {num_frames} frames)")
    return path


def demo_video_description(model, processor):
    """Describe a synthetic video."""
    print("\n" + "=" * 60)
    print("TEST 1: Video Description")
    print("=" * 60)

    video_path = create_test_video(duration_seconds=5, fps=1)

    messages = [
        {"role": "user", "content": [
            {"type": "video", "video": video_path},
            {"type": "text", "text": "Describe what happens in this video. What objects are present and how do they move?"}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=300)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")

    if os.path.exists(video_path):
        os.remove(video_path)

    return len(response) > 20


def demo_video_thinking(model, processor):
    """Video analysis with thinking mode."""
    print("\n" + "=" * 60)
    print("TEST 2: Video + Thinking Mode")
    print("=" * 60)

    video_path = create_test_video(duration_seconds=3, fps=1)

    messages = [
        {"role": "user", "content": [
            {"type": "video", "video": video_path},
            {"type": "text", "text": "Analyze this video carefully. How many frames are there? What direction does the object move? Think step by step."}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=500, enable_thinking=True)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")

    if os.path.exists(video_path):
        os.remove(video_path)

    return len(response) > 20


def demo_video_frame_counting(model, processor):
    """Frame-level understanding test."""
    print("\n" + "=" * 60)
    print("TEST 3: Frame-Level Understanding")
    print("=" * 60)

    video_path = create_test_video(duration_seconds=4, fps=1)

    messages = [
        {"role": "user", "content": [
            {"type": "video", "video": video_path},
            {"type": "text", "text": "For each frame in this video, describe the position of the red circle. Is it on the left, center, or right side of the frame?"}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=400)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")

    if os.path.exists(video_path):
        os.remove(video_path)

    return len(response) > 20


if __name__ == "__main__":
    print("Loading Gemma 4 E4B for video demos...")
    # Use lower token budget per frame for video (70 tokens/frame)
    model, processor = load_model_and_processor(max_soft_tokens=70)
    print_vram_stats()

    results = {}
    for name, fn in [
        ("video_description", demo_video_description),
        ("video_thinking", demo_video_thinking),
        ("video_frame_counting", demo_video_frame_counting),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback; traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("VIDEO DEMO RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print_vram_stats()
