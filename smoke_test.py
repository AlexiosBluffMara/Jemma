"""Quick smoke test — load E4B, generate one text response."""
import sys, os, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "demos"))

from e4b_loader import load_model_and_processor, generate, print_vram_stats

try:
    print("=== QUICK SMOKE TEST ===", flush=True)
    model, processor = load_model_and_processor()
    print_vram_stats()

    messages = [{"role": "user", "content": "Say hello in exactly 5 words."}]
    t0 = time.time()
    response = generate(model, processor, messages, max_new_tokens=30)
    print(f"\nResponse ({time.time()-t0:.1f}s): {response}", flush=True)
    print("=== SMOKE TEST COMPLETE ===", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    traceback.print_exc()
