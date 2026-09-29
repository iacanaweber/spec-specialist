# DEMO_AES spec — working notes

Not exported. Holds what is still open and what the owner decided.

## Open values (TBD / TBR)

| ID | Where | Missing information | Resolver | Status |
|----|-------|---------------------|----------|--------|
| TBR-01 | Block encryption, DONE latency | Latency value pending timing analysis | Spec Owner | Open |

## Open questions

| ID | Question | Unblocks | Status |
|----|----------|----------|--------|

## Decisions

| ID | Date | Decision | Decided by |
|----|------|----------|------------|
| DEC-01 | 2026-09-29 | Single-block ECB encryption, FIPS 197-upd1 | Spec Owner |
| DEC-02 | 2026-09-29 | DONE latency bound tracked as TBR-01 | Spec Owner |
| DEC-03 | 2026-09-29 | START while BUSY sets ERR_BUSY | Spec Owner |
| DEC-04 | 2026-09-29 | Key registers read as zero | Spec Owner |
