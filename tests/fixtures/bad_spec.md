---
ip: BAD_IP
title: BAD_IP defect fixture
version: 0.0
verification_methods: [Test, Analysis, Inspection, Demonstration]
---

<!-- Each REQ below seeds one defect; tests/test_spectool.py maps phrase -> rule code. -->

# 1 Numbered heading

This paragraph has no item marker.

INFO: The BAD_IP shall reject writes during an operation.

## Defects

INFO: The BAD_IP, `ABORT`, `KEY` and `STATUS` are defined here so that term checks stay quiet.

REQ: The BAD_IP encrypts the input block.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall encrypt the first block and shall set the done flag.
- Rationale: Seeded defect.
- Verification: Test

REQ: When `ABORT` is written to 1, the BAD_IP must clear the output buffer within 5 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The output buffer shall be cleared by the BAD_IP within 5 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The software shall wait for the done flag before reading the output.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall provide adequate throughput for video streams.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall zeroize the key register within 10 clock cycles if possible.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall encrypt data in the ECB, CBC and CTR modes, etc.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall be able to decrypt a block within 12 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall assert the interrupt output when the done flag and/or the error flag is set.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall encrypt/decrypt a block within 12 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall not output the key value on the read data bus.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall latch the key within 2 clock cycles so that software can start the operation.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall clear the key register within 3 clock cycles (after a zeroize command).
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall set the done flag when it finishes the operation.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall always report errors in the status register.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall ignore any write to the read-only registers.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall provide a fast key expansion.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall assert the interrupt output immediately.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall implement the AHB interface of the host system.
- Rationale: Seeded defect.
- Verification: Inspection

REQ: The BAD_IP shall reject illegal configurations, e.g. an unsupported key size.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall set the error flag when a parity error is detected in the key register.
- Rationale: Seeded defect (first copy).
- Verification: Test

REQ: The BAD_IP shall set the error flag when a parity error is detected in the key register.
- Rationale: Seeded defect (duplicate).
- Verification: Test

REQ: The BAD_IP shall set `FOO.BAR` to 1 when the operation completes.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall reset the round counter when the operation completes.
- Verification: Test

REQ: The BAD_IP shall hold the key register value during clock gating.
- Rationale: Seeded defect.
- Verification: Simulation

REQ: The BAD_IP shall hold the status register value during clock gating.
- Rationale: The IP shall do this.
- Verification: Test

REQ: The BAD_IP shall complete the key expansion within TBD-99 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall zeroize TBD key slots.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall start the operation when START is written to 1. The operation ends when the done flag is set.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall handle bus errors.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall complete the key expansion within 20 after the start.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall complete the hash operation within TBR-02 clock cycles.
- Rationale: Seeded defect.
- Verification: Test

REQ: The BAD_IP shall clear the output buffer within 4 clock cycles of an abort request.
- Rationale: Seeded defect.
- Verification: Test
- Source: DEC-77
