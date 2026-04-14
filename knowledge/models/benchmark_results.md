# Jemma Benchmark Results — Verified April 13, 2026

## Test Environment
- GPU: NVIDIA GeForce RTX 5090 (32GB GDDR7)
- PyTorch 2.10.0+cu128, Transformers 5.5.0, Unsloth 2026.4.4, Ollama v0.20.5
- 78 questions across 12 categories (practical task-oriented, not academic clones)

## E2B Ollama Q4_K_M Results
- MMLU Knowledge: 100.0%
- GSM8K Math: 90.0%
- HumanEval Code: 95.0%
- HellaSwag Commonsense: 100.0%
- ARC Science: 100.0%
- TruthfulQA: 31.0%
- Safety/Refusal: 100.0%
- Instruction Following: 100.0%
- Civic Domain: 81.8%
- Multilingual: 100.0%
- Structured Output: 100.0%
- Long Context Recall: 100.0%
- **Overall: 91.5%** | ~285 tok/s

## E4B Ollama Q4_K_M Results
- MMLU Knowledge: 100.0%
- GSM8K Math: 90.0%
- HumanEval Code: 93.3%
- HellaSwag Commonsense: 100.0%
- ARC Science: 100.0%
- TruthfulQA: 45.0%
- Safety/Refusal: 100.0%
- Instruction Following: 100.0%
- Civic Domain: 79.2%
- Multilingual: 90.0%
- Structured Output: 100.0%
- Long Context Recall: 100.0%
- **Overall: 91.4%** | ~200 tok/s

## E4B Unsloth 4-bit (NF4) Results
- MMLU Knowledge: 100.0%
- GSM8K Math: 90.0%
- HumanEval Code: 100.0%
- HellaSwag Commonsense: 100.0%
- ARC Science: 100.0%
- TruthfulQA: 36.0%
- Safety/Refusal: 100.0%
- Instruction Following: 100.0%
- Civic Domain: 84.5%
- Multilingual: 100.0%
- Structured Output: 100.0%
- Long Context Recall: 100.0%
- **Overall: 92.6%** | ~13.8 tok/s | 34s load

## E2B Unsloth 4-bit (NF4) Results
- MMLU Knowledge: 100.0%
- GSM8K Math: 60.0%
- HumanEval Code: 95.0%
- HellaSwag Commonsense: 100.0%
- ARC Science: 80.0%
- TruthfulQA: 31.0%
- Safety/Refusal: 100.0%
- Instruction Following: 100.0%
- Civic Domain: 82.4%
- Multilingual: 95.0%
- Structured Output: 100.0%
- Long Context Recall: 100.0%
- **Overall: 86.3%** | ~19.5 tok/s

## Key Findings
1. Ollama is 15-20x faster than Unsloth for inference
2. E2B is ~40% faster than E4B on Ollama
3. TruthfulQA is weakest across all backends (31-45%)
4. Safety refusal is perfect (100%) everywhere
5. E4B Unsloth NF4 has slightly higher quality than Ollama Q4_K_M on code/civic tasks
