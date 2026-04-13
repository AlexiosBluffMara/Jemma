"""
Demo 1: Text + Thinking mode on Gemma 4 E4B.

Tests:
  1. Basic text generation
  2. Chain-of-thought reasoning (thinking mode)
  3. System prompt adherence
  4. Multi-turn conversation
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from e4b_loader import load_model_and_processor, generate, print_vram_stats


def demo_basic_text(model, processor):
    """Basic text generation — sanity check."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Text Generation")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "What are the three branches of the US federal government? Answer in one sentence."}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=100)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s): {response}")
    return True


def demo_thinking(model, processor):
    """Chain-of-thought reasoning with thinking mode enabled."""
    print("\n" + "=" * 60)
    print("TEST 2: Thinking Mode (Chain-of-Thought)")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "A farmer has 17 sheep. All but 9 run away. How many sheep does the farmer have left? Think step by step."}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=500, enable_thinking=True)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s):\n{response}")
    return True


def demo_system_prompt(model, processor):
    """System prompt adherence test."""
    print("\n" + "=" * 60)
    print("TEST 3: System Prompt Adherence")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "You are Jemma, a local AI safety operations assistant for the Town of Normal, Illinois. Always identify yourself as Jemma. Keep responses under 50 words."},
        {"role": "user", "content": "Who are you and what do you do?"}
    ]

    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=100)
    elapsed = time.time() - t0

    print(f"Response ({elapsed:.1f}s): {response}")
    return True


def demo_multiturn(model, processor):
    """Multi-turn conversation test."""
    print("\n" + "=" * 60)
    print("TEST 4: Multi-Turn Conversation")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Remember this number: 42."},
    ]

    t0 = time.time()
    r1 = generate(model, processor, messages, max_new_tokens=50)
    print(f"Turn 1 ({time.time()-t0:.1f}s): {r1}")

    messages.append({"role": "assistant", "content": r1})
    messages.append({"role": "user", "content": "What number did I ask you to remember?"})

    t0 = time.time()
    r2 = generate(model, processor, messages, max_new_tokens=50)
    print(f"Turn 2 ({time.time()-t0:.1f}s): {r2}")

    return "42" in r2


if __name__ == "__main__":
    print("Loading Gemma 4 E4B for text demos...")
    model, processor = load_model_and_processor()
    print_vram_stats()

    results = {}
    for name, fn in [
        ("basic_text", demo_basic_text),
        ("thinking", demo_thinking),
        ("system_prompt", demo_system_prompt),
        ("multiturn", demo_multiturn),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"FAILED: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("TEXT DEMO RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print_vram_stats()
