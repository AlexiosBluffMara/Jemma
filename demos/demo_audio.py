"""
Demo 3: Audio Understanding on Gemma 4 E4B.

Tests:
  1. Speech-to-text (ASR) with synthetic audio
  2. Audio description / classification

E4B audio specs:
  - Max 30 seconds
  - 16 kHz mono, float32 [-1, 1]
  - ~25 tokens/second
  - ~300M audio encoder parameters
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from e4b_loader import load_model_and_processor, generate, print_vram_stats


def create_test_audio(duration_seconds=3.0, sample_rate=16000):
    """Generate a synthetic audio signal (sine wave + noise) for testing.

    Returns:
        path to the saved .wav file
    """
    import soundfile as sf

    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), dtype=np.float32)
    # 440 Hz sine wave (A4 note) with some noise
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.05 * np.random.randn(len(t)).astype(np.float32)
    audio = np.clip(audio, -1.0, 1.0)

    path = os.path.join(os.path.dirname(__file__), "test_audio.wav")
    sf.write(path, audio, sample_rate)
    print(f"Created test audio: {path} ({duration_seconds}s, {sample_rate} Hz)")
    return path


def demo_audio_classification(model, processor):
    """Audio classification / description."""
    print("\n" + "=" * 60)
    print("TEST 1: Audio Classification / Description")
    print("=" * 60)

    audio_path = create_test_audio(duration_seconds=2.0)

    messages = [
        {"role": "user", "content": [
            {"type": "audio", "audio": audio_path},
            {"type": "text", "text": "Describe what you hear in this audio. What kind of sound is it? Is there speech, music, or other sounds?"}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=200)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s): {response}")

    if os.path.exists(audio_path):
        os.remove(audio_path)

    return len(response) > 10


def demo_asr_synthetic(model, processor):
    """ASR with a synthetic speech-like audio (tests the pipeline, not accuracy)."""
    print("\n" + "=" * 60)
    print("TEST 2: ASR Pipeline Test (Synthetic Audio)")
    print("=" * 60)

    audio_path = create_test_audio(duration_seconds=3.0)

    # Use the recommended ASR prompt from Google's docs
    asr_prompt = (
        "Transcribe the following speech segment in English into English text.\n\n"
        "Follow these specific instructions for formatting the answer:\n"
        "* Only output the transcription, with no newlines.\n"
        "* When transcribing numbers, write the digits."
    )

    messages = [
        {"role": "user", "content": [
            {"type": "audio", "audio": audio_path},
            {"type": "text", "text": asr_prompt}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=200)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s): {response}")
    print("(Note: synthetic sine wave — model should indicate no speech detected)")

    if os.path.exists(audio_path):
        os.remove(audio_path)

    # The pipeline ran without error = pass
    return True


def demo_audio_with_thinking(model, processor):
    """Audio understanding with thinking mode for more detailed analysis."""
    print("\n" + "=" * 60)
    print("TEST 3: Audio + Thinking Mode")
    print("=" * 60)

    audio_path = create_test_audio(duration_seconds=2.0)

    messages = [
        {"role": "user", "content": [
            {"type": "audio", "audio": audio_path},
            {"type": "text", "text": "Analyze this audio carefully. What is the dominant frequency? Is this speech, music, or a test signal? Think step by step."}
        ]}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=500, enable_thinking=True)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")

    if os.path.exists(audio_path):
        os.remove(audio_path)

    return len(response) > 10


if __name__ == "__main__":
    print("Loading Gemma 4 E4B for audio demos...")
    model, processor = load_model_and_processor()
    print_vram_stats()

    results = {}
    for name, fn in [
        ("audio_classification", demo_audio_classification),
        ("asr_synthetic", demo_asr_synthetic),
        ("audio_thinking", demo_audio_with_thinking),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback; traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("AUDIO DEMO RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print_vram_stats()
