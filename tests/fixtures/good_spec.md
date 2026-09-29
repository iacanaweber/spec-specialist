---
ip: DEMO_AES
title: DEMO_AES Functional Requirements Specification
version: 0.1
owner: Spec Owner
date: 2026-09-29
verification_methods: [Test, Analysis, Inspection, Demonstration]
required_attributes: [Rationale, Verification]
csv_columns: [Type, Level, Title, Description, Rationale, Verification, Source]
csv_delimiter: ","
type_names: {heading: Heading, info: Information, req: Requirement}
---

<!-- Fictional IP used as a format example and as a spectool test fixture.
     Values are illustrative only. -->

# Introduction

## Purpose

INFO: This document specifies the functional requirements of the DEMO_AES. The DEMO_AES is a fictional block-cipher IP used as a format example.

## Scope

INFO: The DEMO_AES encrypts 128-bit data blocks with a 128-bit key. Key generation and message padding are outside the scope of the DEMO_AES.

## Definitions

INFO: The following terms are used in the requirements.

| Term | Definition |
|------|------------|
| DEMO_AES | The IP specified by this document. |
| HCLK | The bus clock of the DEMO_AES. |
| Block | A 128-bit data unit processed by one operation. |

## Register map

INFO: The registers of the DEMO_AES are defined in the following table. Each register is 32 bits wide.

| Register | Field | Bits | Access | Description |
|----------|-------|------|--------|-------------|
| CTRL | START | 0 | W | Starts one operation. |
| STATUS | BUSY | 0 | R | Operation in progress. |
| STATUS | DONE | 1 | R/W1C | Operation complete. |
| STATUS | ERR_BUSY | 2 | R/W1C | START written while BUSY is 1. |
| KEY0..KEY3 | KEY | 31:0 | W | Key words. |
| DATA_IN0..DATA_IN3 | DATA | 31:0 | W | Input block words. |
| DATA_OUT0..DATA_OUT3 | DATA | 31:0 | R | Output block words. |

# Requirements

## Block encryption

INFO: Software writes the key and the input block, then starts the operation. The result is available in the output registers when the operation completes.

REQ: When `CTRL.START` is written to 1 while `STATUS.BUSY` is 0, the DEMO_AES shall encrypt the Block held in `DATA_IN0` to `DATA_IN3` as specified in FIPS 197-upd1, Section 5.1.
- Rationale: Core function of the IP.
- Verification: Test
- Source: DEC-01

REQ: The DEMO_AES shall set `STATUS.DONE` to 1 within [20 TBR-01] HCLK cycles of `CTRL.START` being written to 1.
- Rationale: Latency budget of the host system; value pending timing analysis.
- Verification: Test
- Source: DEC-02

REQ: If `CTRL.START` is written to 1 while `STATUS.BUSY` is 1, the DEMO_AES shall set `STATUS.ERR_BUSY` to 1.
- Rationale: Makes a start request during an operation observable to software.
- Verification: Test
- Source: DEC-03

## Key protection

REQ: The DEMO_AES shall return 0x0000_0000 in the read data of each read transfer addressed to a `KEY0` to `KEY3` register.
- Rationale: Key material is write-only for software.
- Verification: Test
- Source: DEC-04
