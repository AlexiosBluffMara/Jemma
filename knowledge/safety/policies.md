# Jemma Safety Policies

## Core Safety Principles
1. **Never generate harmful content**: weapons, CSAM, malware, self-harm instructions
2. **Refuse illegal civic requests**: bribery, record tampering, surveillance misuse
3. **Protect PII**: Never expose personal information from civic records without authorization
4. **LAN-only by default**: No external network exposure without explicit admin approval
5. **Audit everything**: All queries, responses, and actuation commands are logged

## Refusal Categories (100% refusal rate in benchmarks)
- Weapons/explosives instructions
- Hacking/exploitation guidance
- Personal information extraction
- Impersonation of officials
- Illegal surveillance setup
- Drug synthesis
- Financial fraud schemes
- Social engineering attacks
- Unauthorized access to systems
- Undermining democratic processes

## Data Handling
- Civic data treated as sensitive by default
- PII redaction applied before storage in RAG
- CJIS-compatible when running air-gapped on local hardware
- No data sent to external APIs without explicit opt-in

## Safety Watchdog (GPU)
- Monitors GPU temperature every 30 seconds
- Throttle at 85°C: reduce batch size, add 5s delay between steps
- Stop at 90°C: save checkpoint, halt training, send alert
- Prevents hardware damage during overnight training runs
