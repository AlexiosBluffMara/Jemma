# Second Brain dataset and pipeline plan

## Project direction
The strongest version of a Gemma-based **Second Brain** for this workspace is a **multimodal operational memory assistant**:

- remembers conversations, meetings, and notes,
- retrieves structured incident, inspection, and maintenance records,
- answers grounded questions over that memory,
- optionally reasons over construction/safety/infrastructure images.

That gives a clearer hackathon story than a generic chatbot while still supporting high-impact tracks such as safety, resilience, and education.

## Best public dataset starting points
These are the best first-wave public datasets to use as building blocks.

| Dataset | Modality | Best use |
| --- | --- | --- |
| SQuAD | text | grounded QA and retrieval evaluation |
| HotpotQA | text | multi-hop retrieval evaluation |
| MultiWOZ 2.2 | dialogue | multi-turn assistant behavior and state tracking |
| DailyDialog | dialogue | conversational polish and intent flow |
| Meeting Transcripts | text | summarization, recall, action-item extraction |
| Industrial Safety and Health Analytics | tabular + text | incident memory and safety recommendations |
| OSHA Injury Data | tabular | trend summaries and risk retrieval |
| Aircraft Historical Maintenance Dataset | structured + text | maintenance-log retrieval and troubleshooting memory |
| LA Building and Safety Inspections | structured | inspection history and compliance lookup |
| National Bridge Inventory | structured | infrastructure memory and asset-level retrieval |
| Hard Hat Detection | image | PPE detection |
| Construction Site Safety Image Dataset | image | construction hazard scene understanding |
| Worksite Safety Monitoring Dataset | image | safety compliance classification/detection |
| Surface Crack Detection | image | defect and crack detection |
| RDD 2022 | image | road and highway damage detection |

## Recommended dataset bundles
### Fast MVP
- MultiWOZ 2.2
- Meeting Transcripts
- SQuAD
- Industrial Safety and Health Analytics
- Aircraft Historical Maintenance Dataset

This is the fastest path to a useful text-first assistant that can remember, summarize, retrieve, and answer.

### Strong demo MVP
- Industrial Safety and Health Analytics
- OSHA Injury Data
- Hard Hat Detection
- Construction Site Safety Image Dataset
- RDD 2022

This is the best short-term path for a visually compelling safety or field-inspection assistant.

### Ambitious multimodal version
- MultiWOZ 2.2
- Meeting Transcripts
- HotpotQA
- Aircraft Historical Maintenance Dataset
- LA Building and Safety Inspections
- National Bridge Inventory
- Construction Site Safety Image Dataset
- Hard Hat Detection
- RDD 2022

## Compliance guidance
### Safest sources
- Kaggle datasets with clear, documented licenses
- StackExchange data when attribution and license obligations are preserved
- self-created or synthetic project data

### Use with caution
- embedding indexes built from third-party text
- mixed-source web corpora
- private or semi-private operational documents

### Avoid for hackathon speed
- Reddit dumps with unclear downstream rights
- broad web-scraped corpora without a provenance ledger
- any source with missing license terms or personal-data concerns

### Required project discipline
Maintain a dataset ledger with:

- source name and URL,
- license and terms URL,
- allowed use notes,
- attribution requirements,
- privacy notes,
- whether embedding/indexing is allowed,
- whether redistribution is allowed,
- final decision: `use`, `use-with-limits`, or `do-not-use`.

## Easiest practical pipeline
### 1. Ingest raw sources into cloud storage
Use a single bucket layout such as:

- `gs://jemma-raw/`
- `gs://jemma-parsed/`
- `gs://jemma-embeddings/`

Load:

- Kaggle/public datasets,
- internal Reddit or StackExchange dumps only after a license/privacy pass,
- domain CSVs, JSONL, inspection tables, and image datasets.

### 2. Parse and normalize with a cloud dataflow stage
Use a Dataflow or Beam pipeline to:

- normalize schemas,
- redact obvious sensitive fields,
- split long documents into chunks,
- convert records into chat pairs, summaries, retrieval chunks, and eval sets,
- write canonical JSONL and parquet outputs.

### 3. Create Gemini embeddings in the cloud
Use the cloud project to build embeddings for:

- retrieval chunks,
- safety incidents,
- inspection and maintenance logs,
- meeting and conversational memory records.

Keep embeddings and metadata in a managed vector store or a simple chunk-plus-index export that can be mirrored locally.

### 4. Train locally on the RTX 5090
Use the local Unsloth notebook for:

- instruction tuning on prepared JSONL chat data,
- domain adaptation for second-brain prompts,
- focused safety and maintenance response behavior,
- fast iteration on LoRA checkpoints.

Keep the heavy base-model download, training loop, adapter checkpoints, and exports on the local SSD.

### 5. Use cloud + local together
The easiest split is:

- **cloud:** ingestion, cleaning, chunking, embedding, large-scale preprocessing,
- **local 5090:** LoRA fine-tuning, smoke evals, export, and rapid iteration,
- **runtime app:** retrieve from the embedding index, then call the locally adapted Gemma model for grounded answers.

## Construction and infrastructure angle
For a construction-focused variant, prioritize:

- Hard Hat Detection
- Construction Site Safety Image Dataset
- Worksite Safety Monitoring Dataset
- Surface Crack Detection
- RDD 2022
- OSHA Injury Data
- bridge and inspection tables

That combination supports:

- PPE checks,
- hazard spotting,
- crack or roadway defect identification,
- inspection memory,
- safety recommendation retrieval.

## Suggested first implementation scope
Build the first version around:

1. a text-first retrieval memory assistant,
2. one visual safety or crack-detection capability,
3. a dataset ledger and provenance discipline from day one,
4. local QLoRA fine-tuning on the 5090 with cloud preprocessing upstream.
