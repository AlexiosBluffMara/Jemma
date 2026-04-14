# Civic Data Sources — Town of Normal, ISU, Chicago

## Data Inventory (as of April 2026)
- **civic_data.db**: 48.5 MB SQLite database
  - 28 pages (scraped civic web content)
  - 135 datasets (metadata and samples)
  - 236 contacts (civic officials directory)
  - 5,319 chunks (text segments for RAG)
  - 299 embeddings (sentence-transformer vectors)

## Training Data
- **civic_sft_train.jsonl**: 8,129 samples (4.8 MB)
  - Format: `{"messages": [system, user, assistant], "_meta": {...}}`
  - Topics: food inspections, building violations, business licenses, crime reports
- **civic_sft_val.jsonl**: validation split (246 KB)

## Kaggle Datasets (downloaded)
- chicago_311_requests.csv — Service requests (potholes, graffiti, etc.)
- chicago_building_violations.csv — Code violations
- chicago_business_licenses.csv — Active/expired licenses
- chicago_crimes.csv — Crime incident reports
- chicago_food_inspections.csv — Restaurant inspection results
- chicago_libraries.csv — Library locations and programs
- chicago_police_stations.csv — Station locations and districts
- chicago_public_health.csv — Clinic locations
- chicago_traffic_crashes.csv — Vehicle crash records

## Synthetic Datasets
- blueprint_interpretation.jsonl — Construction blueprint QA
- building_codes.jsonl — Building code compliance
- construction_qa.jsonl — Construction domain knowledge
- disaster_assessment.jsonl — Emergency/disaster evaluation
- image_descriptions.jsonl — Visual scene descriptions
- materials_database.jsonl — Construction materials specs
- multistream_stats.jsonl — Multi-modal statistics
- object_detection_labels.jsonl — Object detection training data
- safety_inspections.jsonl — Safety inspection reports

## Data Sources
- Town of Normal, IL official website
- Illinois State University public records
- Chicago Data Portal (data.cityofchicago.org)
- Kaggle public civic datasets
- HuggingFace open datasets
- Data.illinois.gov (state-level data)

## Data Growth Strategy
The AutoResearch loop continuously generates new training samples by:
1. Querying the model on civic topics
2. Scoring responses against known facts
3. Adding high-quality Q&A pairs to the training dataset
4. Re-training periodically with expanded data
