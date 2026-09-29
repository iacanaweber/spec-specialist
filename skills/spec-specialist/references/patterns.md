# Statement patterns

The patterns follow the ISO/IEC/IEEE 29148 §5.2.4 construct
`[Condition] [Subject] [Action] [Object] [Constraint]`, the condition types in GtWR R1/R27, and
the NRM 6.2 templates. `<IP>` is the exact entity name from the front matter. Placeholders in
angle brackets are filled by the owner. Pick the pattern first, then ask for whatever slot is
still empty.

## Requirements

| Use | Pattern |
|-----|---------|
| Always applies | `The <IP> shall <verb> <object> <performance>.` |
| Event-driven | `When <trigger event>, the <IP> shall <verb> <object> <performance>.` |
| State/mode-driven | `While <state or mode>, the <IP> shall <verb> <object> <performance>.` |
| Unwanted behavior / error | `If <condition>, [then] the <IP> shall <response>.` |
| Combined logic | `When [<A> AND <B>], the <IP> shall …` · `If [<A> OR <B>], …` (GtWR R15, R28) |
| Time-bounded response | `… shall <verb> <object> within <n> <unit> of <event>.` |
| Rate/throughput | `… shall <verb> <object> at a rate of at least <n> <unit> per <unit> while <condition>.` |
| Variants by table | `… shall <verb> <object> with the <characteristics> listed in Table <n>.` (NRM 6.2.1.2.1: one table row per variant, each verified) |
| Interaction, existing definition | `The <IP> shall <verb> <object> [to/from <external system>] as defined in <doc ID, issue>, <§x>.` |
| Interaction, "thing" crossing | `The <IP> shall <use/provide> <object> having the characteristics defined in <doc/table>.` (NRM 6.2.3.5) |
| Complex timing | `… shall <verb> <object> with the timing shown in Figure <n>.` (GtWR R23) |
| Standard-derived | `The <IP> shall <specific behavior> as specified in <standard, version>, <§x>.` + `Source: <standard> <§x>` |
| Resource limit | `The <IP> shall limit <resource> to at most <value> <unit> while <operating condition>.` (NRM 6.2.1.3.6) |
| Implementation constraint | `The <IP> shall <constraint>.` + Rationale stating why the design is constrained (GtWR R31 exception) |
| Threshold + goal | `The <IP> shall <verb> <object> with a <measure> of at least <threshold>.` Put the goal in Rationale, or as a separate "should" item only if the owner wants goals in the set (NRM 6.2.1.3.2). |

### One function, several performance values

NRM 6.2.1.2.1 offers two consistent styles. The owner picks one for the whole spec.
1. **Family.** One requirement per performance characteristic, each repeating the function and its
   condition. This is easy to trace and verify, but produces more items.
2. **Table.** One requirement pointing to a table (row = variant, columns = values). The spec is
   more compact, and verification must still cover every row.

## Information items (facts, no "shall")

| Use | Pattern |
|-----|---------|
| Definition | `<Term> is <definition>.` (or a Definitions table) |
| Register map | `The registers of the <IP> are defined in the following table.` + table |
| Interface definition | `<Thing> has the characteristics defined in Table <n>.` · `<Signal> is <description>.` (NRM 6.2.3.4) |
| Usage context | `Software writes the key and the input block, then starts the operation.` (describes use; creates no obligation) |
| Assumption / dependency | `The <IP> assumes that <external party/condition>.` · `<External system> provides <thing>.` |
| Scope boundary | `<Function> is outside the scope of the <IP>.` |

## Unknowns

| Situation | Notation |
|-----------|----------|
| Value not known yet | `within TBD-<nn> HCLK cycles` |
| Value proposed, not confirmed | `within [<value> TBR-<nn>] HCLK cycles` |
| Reference not yet available | `as defined in <doc> TBD-<nn>` |

Log each marker in the notes file (location, missing information, resolver, status).

## Crypto-IP illustrations (form only; values are placeholders)

- `When CTRL.START is written to 1 while STATUS.BUSY is 0, the <IP> shall encrypt the Block held in DATA_IN0 to DATA_IN3 as specified in FIPS 197-upd1, Section 5.1.`
- `The <IP> shall set STATUS.DONE to 1 within <n> HCLK cycles of CTRL.START being written to 1.`
- `If CTRL.START is written to 1 while STATUS.BUSY is 1, the <IP> shall set STATUS.ERR_BUSY to 1.`
- `When CTRL.ZEROIZE is written to 1, the <IP> shall set each bit of KEY0 to KEY<n> to 0 within <n> HCLK cycles.`
- `The <IP> shall return 0x0000_0000 in the read data of each read transfer addressed to a KEY register.`
- `While STATUS.BUSY is 1, the <IP> shall ignore each write transfer addressed to DATA_IN0 to DATA_IN3.` (Ignoring the write versus reporting an error is the owner's choice.)
- `If a transfer addresses an offset that is not listed in the register map, the <IP> shall respond with an ERROR response as defined in <bus spec ID, issue>, <§x>.`
