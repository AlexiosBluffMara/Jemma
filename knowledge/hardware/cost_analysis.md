# Hardware Cost & Deployment Analysis

## Local Hardware Options

### RTX 5090 (Tested — Recommended)
- **MSRP**: $1,999 (one-time)
- **VRAM**: 32GB GDDR7
- **TDP**: 575W
- **Bandwidth**: 1.8 TB/s
- **Electricity**: ~$0.15/kWh × 0.575kW = ~$0.086/hr at full load
- **Amortized (3yr, 8hr/day)**: $1,999 / (365×3×8) = ~$0.23/hr total cost
- **Capability**: Runs E2B + E4B simultaneously, QLoRA fine-tuning, all multimodal demos
- **Jemma perf**: E4B at 200 tok/s (Ollama), E2B at 285 tok/s, training at 200 steps in ~5 min
- **Privacy**: Complete data sovereignty — nothing leaves the machine

### RTX 4090 (Previous Gen)
- **MSRP**: $1,599
- **VRAM**: 24GB GDDR6X
- **TDP**: 450W
- **Bandwidth**: 1.0 TB/s
- **Limitation**: Can run E4B Q4 (~10GB) but tight for simultaneous tasks
- **Amortized (3yr)**: ~$0.18/hr

### RTX 5080 (Budget Option)
- **MSRP**: $999
- **VRAM**: 16GB GDDR7
- **TDP**: 360W
- **Limitation**: E2B only for comfortable operation, E4B Q4 possible but no headroom
- **Amortized (3yr)**: ~$0.11/hr

### Apple M4 Ultra (Mac Studio)
- **MSRP**: $3,999+ (192GB unified memory config)
- **Unified Memory**: Up to 192GB
- **Advantage**: Can run 31B at full precision
- **Disadvantage**: Slower inference than NVIDIA CUDA, no Unsloth support
- **Amortized (3yr)**: ~$0.46/hr

## Cloud Options

### Google Cloud Run (Serverless)
- **Machine**: L4 GPU
- **Cost**: ~$0.70/hr (on-demand)
- **VRAM**: 24GB
- **Capability**: E2B/E4B inference, not for training
- **Best for**: Burst inference, demos, API serving
- **Privacy**: Google Cloud regions, data processing agreements needed

### Google Cloud Compute (A100)
- **Cost**: $1.50-3.80/hr depending on region/commitment
- **VRAM**: 40GB or 80GB
- **Capability**: All models at bf16, training feasible
- **Best for**: Full-size evaluation, heavy training runs

### Google Cloud Compute (H100)
- **Cost**: $4.50-8.00/hr
- **VRAM**: 80GB HBM3
- **Capability**: 31B at full precision, multi-model serving
- **Best for**: Maximum performance, competition-grade benchmarks

### AWS/Azure Equivalents
- **AWS p5 (H100)**: ~$5.12/hr (on-demand)
- **Azure ND H100**: ~$4.85/hr
- **Vast.ai H100**: ~$2.50-3.50/hr (community GPU marketplace)

## Cost Comparison: 1 Year of Operation

| Scenario | Upfront | Monthly | Annual Total | $/query (1K/day) |
|----------|---------|---------|-------------|------------------|
| RTX 5090 Local (8hr/day) | $1,999 | ~$19 elec | $2,227 | $0.006 |
| RTX 4090 Local (8hr/day) | $1,599 | ~$15 elec | $1,779 | $0.005 |
| Cloud L4 (8hr/day) | $0 | ~$168 | $2,016 | $0.006 |
| Cloud A100 (8hr/day) | $0 | ~$456-912 | $5,472-10,944 | $0.015-0.030 |
| Cloud H100 (2hr/day) | $0 | ~$270-480 | $3,240-5,760 | $0.009-0.016 |
| OpenAI GPT-4o-mini API | $0 | varies | ~$3,650 (1K q/day) | $0.010 |
| Claude 3.5 Haiku API | $0 | varies | ~$2,920 (1K q/day) | $0.008 |

## Privacy & Data Sovereignty Analysis

### Full Local (RTX 5090) — MAXIMUM PRIVACY
- **Data leaves machine**: Never
- **Regulatory compliance**: GDPR Art. 5(1)(f), CCPA, HIPAA-suitable
- **Audit trail**: Complete local logging
- **Model weights**: Apache 2.0, no phone-home
- **Risk**: Physical theft, local compromise only
- **Verdict**: Ideal for civic data, PII, CJIS-grade workloads

### Cloud Hosted (GCP/AWS)
- **Data leaves machine**: Yes — to cloud provider
- **Regulatory compliance**: Depends on region/config (GCP FedRAMP, SOC 2)
- **Data processing agreement**: Required
- **Model weights**: Self-hosted on cloud instances (still Apache 2.0)
- **Risk**: Cloud provider access, subpoena vulnerability, egress fees
- **Verdict**: Acceptable for non-sensitive civic data with proper DPA

### API Services (OpenAI/Anthropic)
- **Data leaves machine**: Yes — to third-party servers
- **Regulatory compliance**: Varies, OpenAI has SOC 2 Type II
- **Data retention**: Training data opt-out available but trust-required
- **Model weights**: Proprietary, no inspection possible
- **Risk**: Prompt logging, model updates changing behavior, vendor lock-in
- **Verdict**: NOT suitable for sensitive civic data without explicit approval

## Recommendation Matrix

| Priority | Best Option | Runner-up |
|----------|-------------|-----------|
| Maximum privacy | RTX 5090 Local | RTX 4090 Local |
| Lowest long-term cost | RTX 5090 Local | RTX 4090 Local |
| Maximum performance | Cloud H100 | RTX 5090 Local |
| Easiest setup | Cloud L4 (serverless) | API services |
| CJIS/HIPAA compliance | RTX 5090 Local (air-gapped) | GCP w/ BAA |
| Scalability | Cloud A100 cluster | RTX 5090 + Cloud hybrid |
| Hackathon demo | RTX 5090 Local | Cloud L4 backup |

## Break-Even Analysis
The RTX 5090 pays for itself vs Cloud L4 at: $1,999 / ($0.70/hr × 8hr/day × 30) = **~12 months**.
Vs A100: $1,999 / ($3/hr × 8hr/day × 30) = **~3 months**.
For any deployment lasting more than 3-12 months, local hardware wins decisively on cost.
