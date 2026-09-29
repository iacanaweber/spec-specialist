# Spec template and file format

The outline is the ISO/IEC/IEEE 29148 §8.4.2 SyRS outline, tailored for an IP block. Annex C
allows tailoring. The changes:
- Verification is a per-requirement attribute instead of a parallel chapter (ISO 9.5.18).
- Sections that have no content are left out, because a short spec is easier to verify.
- Context lives in INFO items next to the requirements it explains.

## Front matter

```yaml
---
ip: AES_IP                      # exact entity name; subject of every requirement (required)
title: AES_IP Functional Requirements Specification
version: 0.1
owner: <name>
date: <YYYY-MM-DD>
verification_methods: [Test, Analysis, Inspection, Demonstration]
required_attributes: [Rationale, Verification]
csv_columns: [Type, Level, Title, Description, Rationale, Verification, Source]
csv_delimiter: ","              # use ";" if your Excel/Polarion import expects it
type_names: {heading: Heading, info: Information, req: Requirement}
---
```

CSV column names that spectool understands:

| Column | Heading row | INFO row | REQ row |
|--------|-------------|----------|---------|
| Type | `type_names.heading` | `type_names.info` | `type_names.req` |
| Level | 1–6 | | |
| Title | heading text | | `Title` attribute, if present |
| Description | | body (Markdown) | statement |
| Text | heading text | body | statement |
| Section / Section Title / Ref | computed position | computed position | computed position |
| any other name | | | value of the attribute with that name (e.g. Rationale, Source) |

## Syntax

- **Headings:** `#` to `######`, with no manual numbers. Numbers are computed.
- **`INFO:`** at the start of a line. The item continues until the next `INFO:`, `REQ:` or
  heading. It may contain paragraphs, lists, tables, fenced code and images
  (`![caption](path)`).
- **`REQ:`** at the start of a line: one sentence, which may wrap over several lines. Then come
  `- Name: value` attribute bullets. A blank line ends the item. Indent a line to continue a long
  attribute value.
- **Defined terms:** registers, fields and signals go in backticks (`` `CTRL.START` ``) or
  Capital_Underscore style. Each one is defined in an INFO table.
- **Notation:** logical conditions use `[A AND B]`; tentative values use `[<value> TBR-nn]`;
  unknown values use `TBD-nn`.
- **HTML comments** `<!-- … -->` are ignored by spectool. Don't hide content in them.
- **No requirement IDs.** Polarion assigns them. Add `- ID: <Polarion ID>` only after Polarion has
  created one.

## Outline

Use only the sections that have content. Section names are suggestions.

```markdown
# Introduction
## Purpose
INFO: <1–3 sentences: what the IP is for.>
## Scope
INFO: <What the IP does. What is explicitly outside it.>
## Context
INFO: <External systems and what crosses each boundary.>

| External system | Interaction (direction, object) | Defined in |
|-----------------|---------------------------------|------------|

## Definitions
INFO: <Terms and acronyms used in requirements.>

| Term | Definition |
|------|------------|

## Conventions
INFO: "shall" marks a binding requirement; INFO items are context and do not add obligations. TBD-nn marks an unknown value and [<value> TBR-nn] a value awaiting confirmation. Verification methods: <list>.

# References
## Normative
INFO: <Documents whose content is invoked by requirements: ID, version/date, title.>
## Informative
INFO: <Documents for guidance only.>

# Interface definitions
## Register map
INFO: <Register/field table: name, offset, bits, access, reset value, description.>
## Signals
INFO: <Port/signal table: name, direction, width, description, clock domain.>

# Requirements
## <Function A>
INFO: <Optional short context for this function.>
REQ: …
## <Function B>
## States and modes            (if in scope)
## Security                    (if in scope)
## Clock, reset, power and test (if in scope)
## Compliance                  (if in scope)
## Design constraints          (only owner-mandated constraints, each with Rationale)

# Assumptions and dependencies
INFO: <What the IP relies on from software, the SoC and other blocks. These are not requirements on the IP.>
```

Grouping requirements by function, with performance written in the same requirement as the
function, follows NRM 6.2.1.1. The owner may prefer category sections (Functional, Performance,
Interactions, …) as in ISO 9.5. Pick one style and keep it for the whole spec.

## Notes file (`<spec>.notes.md`)

The notes file is working memory for the spec. It is not exported. spectool cross-checks its
TBD/TBR and DEC identifiers against the spec.

```markdown
# <IP> spec — working notes

## Open values (TBD / TBR)
| ID | Where | Missing information | Resolver | Status |
|----|-------|---------------------|----------|--------|
| TBR-01 | §3.1 REQ 2 (DONE latency) | value from timing analysis | <name> | Open |

## Open questions
| ID | Question | Unblocks | Status |
|----|----------|----------|--------|
| Q-01 | Error response or silent ignore for writes to read-only registers? | §4.2 bus errors | Open |

## Decisions
| ID | Date | Decision | Decided by |
|----|------|----------|------------|
| DEC-01 | <YYYY-MM-DD> | <what was decided, in one line> | <owner> |
```

- Number the IDs sequentially and never reuse one.
- When a TBD/TBR is resolved, set its status to Resolved and put the value in the spec.
- `Source: DEC-nn` in a requirement points to the decision that justifies it.
