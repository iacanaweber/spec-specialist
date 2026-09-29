# Review checklist

`spectool lint` covers the mechanical rules. This checklist covers what needs judgment. The
characteristics (C1–C15) are those of GtWR v3.1 and ISO/IEC/IEEE 29148 §5.2.5–5.2.6. The set
checks follow NRM 6.2.6.2 and NRM 7.

**Verification versus validation.** Checking *form* against the rules is requirements
verification. Checking that the text says what the owner *means* is requirements validation, and
only the owner can confirm it (NRM 7.2). Report findings. Do not silently correct content.

## Per requirement (C1–C9)

| Check | Question to ask of the statement |
|-------|----------------------------------|
| C1 Necessary | What breaks if this requirement is removed? Does it trace to a Source? Is it gold plating, or already covered by another requirement? |
| C2 Appropriate | Is it about the IP (not software, the SoC or the designer)? Is it a *what* at the IP boundary, not a *how* (microarchitecture)? |
| C3 Unambiguous | Could two engineers implement or test it differently? Look for undefined terms, scope of commas, and "and"/"or" meaning. |
| C4 Complete | Does it state what, how well and under which conditions? For an interaction, does it point to the definition? Is it understandable without its heading or its neighbors? |
| C5 Singular | Is there one capability or constraint? Several conditions are fine. |
| C6 Feasible | Is anything physically impossible or conflicting? Is a value suspiciously tight? Raise it as a question for the owner. |
| C7 Verifiable | Can a pass/fail criterion be written from the text alone? Is the Verification method plausible for it? |
| C8 Correct | Does it match its Source (document clause, parent requirement, DEC-nn)? The owner confirms. |
| C9 Conforming | Does it follow a pattern from patterns.md, the keyword rules, and the term notation? |

## Per set (C10–C15)

| Check | What to look at |
|-------|-----------------|
| C10 Complete | Each function has performance. Each state and mode has defined behavior. Off-nominal cases (invalid input or configuration, start while busy, abort, reset mid-operation, detected fault) have responses. Each external interaction has a requirement and a definition pointer. The in-scope categories are covered. |
| C11 Consistent | The same term and unit are used everywhere. There are no conflicting values (one latency in two places). There are no duplicates or overlaps between REQs, or between a REQ and an INFO item. |
| C12 Feasible | Taken together, can the values be met (throughput versus area versus clock)? Raise questions for the owner; do not decide. |
| C13 Comprehensible | Would a new reader understand the IP from the INFO items plus the REQs? Are context items missing? |
| C14 Able to be validated | Do the requirements, taken together, express what the owner intends for the IP? Confirm with the owner. |
| C15 Correct | Does the set reflect its sources as a whole? Is every source item covered by at least one requirement? |

## Information items

- Look for hidden requirements: an INFO item that states a behavior that must be verified ("the
  IP returns zero on key reads"). Propose moving it to a REQ, or rewording it as context.
- An INFO item must not contradict or relax a REQ, and must not restate a REQ in other words.
- Register and signal tables must agree with the REQs: every field a REQ names exists, with the
  same name.

## Interface audit (NRM 6.2.3.8)

List the external systems from the Scope/Context section. For each system, check:
1. Every interaction has its own requirement.
2. Every such requirement points to where the interaction is defined.
3. The definition exists and names the same objects.
4. For a system developed in parallel, the counterpart spec has the matching requirement. Ask the
   owner.

Also flag any use of "interface" as a noun or verb inside a requirement.

## Completeness prompts (NRM 4.5.6, 6.2.6.2)

- Does every input have a source, and every output a destination?
- For every numeric value: where does it come from (Rationale or Source), and is it a bound or a
  range?
- For every standard cited: is the exact version given, and only the applicable clauses?
- Is every assumption recorded, as an INFO assumption or in Rationale?
- Are TBD/TBR items all logged, each with a resolver?

## Reporting format

One table, most severe first. Skip lint findings that are false positives.

| Ref | Defect | Rule / characteristic | Proposed fix |
|-----|--------|-----------------------|--------------|
| §3.1 REQ 2 | two actions in one statement | GtWR R18 / C5 | split into "…set STATUS.DONE…" and "…assert IRQ…", each with the same condition |

- A proposed fix that changes content (a value, a behavior, a response) goes to the owner as a
  question, not as a rewording.
- Apply fixes only after approval. Run `lint` again afterwards.
