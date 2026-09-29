# Question bank — crypto IP specifications

Use this bank to **ask**. The answers are owner decisions and never defaults. Ask only what the
function at hand needs and what the spec, the notes, the provided documents and the session have
not already answered. Offer options where they help, with the proposed one first, and never pick
one silently. Structure follows NRM 4.3.4.2 (information to elicit) and 4.5.6 (completeness).
Crypto and bus topics are domain prompts.

## Contents
1. Setup
2. Scope and context
3. Per function (generic slots)
4. Block ciphers and AEAD
5. Hash and MAC
6. Random number generation
7. Public-key and PQC accelerators
8. Control, status, interrupts
9. Data movement
10. Bus behavior (AHB and similar)
11. Keys, zeroization, access control
12. Security countermeasures
13. States and modes
14. Performance
15. Compliance and verification
16. Closing questions

## 1. Setup
- What is the exact entity name used as the subject of every requirement (for example `AES_IP`)?
- Where does the spec live, and under which file name?
- Which reference documents apply? Give the ID, version or date, and the sections that matter:
  bus spec, algorithm standards, customer or SoC requirements, company templates.
- Which verification methods does your organization use (default: Test, Analysis, Inspection,
  Demonstration)?
- Which columns and delimiter does your Polarion import expect? What are the item type names
  (Heading, Information, Requirement)?
- Besides functional requirements, which categories are in scope: states/modes, security,
  performance, compliance, clock/reset/power/test/debug?
- How should enumerable variants such as key sizes and modes be written: one requirement each,
  or one requirement pointing to a table?

## 2. Scope and context
- What problem does the IP solve, and for which product or SoC? (Purpose: at most 3 sentences.)
- What is explicitly outside the IP? Examples: padding, key generation, protocol framing,
  software-side checks.
- Which external systems does the IP interact with? For each one, what crosses the boundary in
  which direction, and where is that interaction defined? Candidates: bus manager(s), interrupt
  controller, DMA, key source (OTP, PUF, key manager), entropy source, clock/reset controller,
  power controller, debug/test controller, software driver.
- Is the IP new, or does it evolve an existing one? If it evolves an existing IP, which document
  describes the baseline, and what changes?
- Which assumptions about the environment and the software are you making?

## 3. Per function (generic slots)
For each function, expressed as a verb/object pair such as "encrypt block" or "load key", ask:
- **Trigger or condition:** which event, state or mode, or configuration starts it or allows it?
- **Inputs:** where does each one come from (register, port, DMA)? In which format and bit/byte
  order?
- **Outputs:** where does each one go, and who consumes it? An output with no consumer suggests
  an unnecessary function.
- **Observable result:** what can be checked at the IP boundary?
- **Performance:** how fast, how many, how well, with units, and under which conditions (clock,
  key size, mode)? Is it a hard bound or a goal?
- **Off-nominal:** what should happen on each of these?
  - an invalid or unsupported configuration;
  - a start while busy;
  - a read before done;
  - an abort, or a reset in the middle of an operation;
  - a detected error or fault.
- **Security:** can key material or intermediate data become observable? What must be cleared,
  and when?
- **Priority and criticality:** which items are essential, and which could be dropped if the
  project is de-scoped?

## 4. Block ciphers and AEAD
- Which algorithms, standard versions, directions (encrypt, decrypt), key sizes and modes?
- IV, nonce or counter: who provides it? What width does it have, and what happens on counter
  wrap?
- For AEAD: which tag lengths? Is AAD supported? Does the IP compare tags, or does software? What
  is the result on a tag mismatch?
- Message length limits, partial final blocks, padding (hardware or software), multi-part
  messages.
- Decryption key schedule: derived by the IP, or loaded by software? Is there a precompute step?
- Context save and restore for interleaved messages: needed, and in what form?

## 5. Hash and MAC
- Which algorithms and output sizes (SHA-2, SHA-3, SHAKE, HMAC, CMAC, …) and which standard
  versions?
- Padding by hardware or by software? What is the maximum message length? Is multi-part
  (streaming) input supported, and can the intermediate state be exported or imported?
- HMAC and CMAC key sizes and key source. Is the output truncated?

## 6. Random number generation
- Entropy source: which one, and what are its health tests and failure responses?
- Conditioning and DRBG: which mechanisms, and which standard (for example the NIST SP 800-90
  series)?
- Output rate and output interface, reseed policy, behavior while not ready or on failure.

## 7. Public-key and PQC accelerators
- Operations (modular exponentiation, point multiplication, sign, verify, KEM), curves,
  parameter sets and operand sizes.
- Operand memory, loading, and result format.
- Timing or leakage properties required (for example execution time independent of secret data),
  and how they will be verified.

## 8. Control, status, interrupts
- Start, abort and soft-reset controls, and the behavior of each in every state.
- Status flags and their clear semantics (read-to-clear, write-1-to-clear, …).
- Interrupt sources, enable/mask, clear, and the level or pulse behavior at the output.
- Reset value of each register field, and its behavior after reset.

## 9. Data movement
- Register-based, FIFO or DMA? FIFO depths and thresholds? Flow control and back-pressure?
- DMA request and acknowledge protocol, burst sizes, and behavior on underflow or overflow.
- Data alignment, endianness, and the mapping from register words to algorithm blocks.

## 10. Bus behavior (AHB and similar)
- Which bus, and which specification issue (for example AMBA AHB)? Which role (subordinate)? What
  data width and address space size?
- Which transfer sizes are supported (byte, halfword, word)? Unaligned accesses? Bursts?
  Wait-state limits?
- Which accesses produce an ERROR response, and which are ignored? Candidates: unmapped offset,
  write to a read-only register, read of a write-only register, access while locked or busy,
  security or privilege violation.
- Protection and security attributes (for example HPROT or HNONSEC): are they used, and how?

## 11. Keys, zeroization, access control
- Key sources (a software-written register, a hardware key port, a key slot) and how a source is
  selected.
- Key readability (read value of key registers), key validity status, and usage restrictions (for
  example encrypt-only keys).
- Zeroization triggers (command, reset, alarm, lifecycle change), scope (keys, data, state),
  completion time and completion status.
- Lock bits, and who can access what: secure/non-secure, privileged, debug.

## 12. Security countermeasures
- Side-channel: which attack classes are in scope, which assessment method and pass criterion,
  and which standard or internal procedure applies?
- Fault injection: what is detected, how the IP responds (alarm, zeroize, lock, error status),
  and how this is verified.
- Test and debug modes (scan, JTAG, debug registers): what must happen to secrets in each mode?
- Certification targets that impose requirements (for example FIPS 140-3 level, Common Criteria,
  SESIP): which clauses apply to the IP itself?

## 13. States and modes
- Which states exist (for example idle, busy, done, error, zeroizing, low-power)?
- For each state, which events move the IP to which state? What is allowed, and what is ignored
  or flagged in each state?
- Behavior on clock gating, power-down, retention, and reset in each state.

## 14. Performance
- Throughput per algorithm, mode and key size: which clock, which conditions, which unit?
- Latency from start to done, key setup latency, time to first output.
- Constraints the owner sets as requirements (maximum frequency, area, power). Why is each one a
  requirement?

## 15. Compliance and verification
- Which standards and clauses must be shown to be met, and by what evidence (for example
  known-answer tests)?
- Who verifies each category (the IP team or the SoC team), and at which level?

## 16. Closing questions (ask at the end of every function and of the spec)
- What should I have asked and didn't?
- Which misuse cases or loss scenarios worry you?
- What are you assuming to be true for these answers to hold?
- Is there anything a reader would need to know that isn't written yet (as an INFO item)?
