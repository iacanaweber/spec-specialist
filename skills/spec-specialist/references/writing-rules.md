# Writing rules for requirement statements

Paraphrased (with credit, not copied) from the INCOSE *Guide to Writing Requirements* v3.1 (GtWR,
rules R1–R41, characteristics C1–C15), ISO/IEC/IEEE 29148:2018 §5.2, and the INCOSE *Needs and
Requirements Manual* (NRM, 2025). Examples use placeholders (`<IP>`, `<n>`, `<ver>`, `<§x>`) and
fictional register names. They illustrate **form only**. Every real value comes from the owner.

## Contents
1. Structure and keywords — R1–R3, ISO 5.2.4
2. Accuracy — R4–R9
3. Concision — R10–R11
4. Non-ambiguity — R12–R17
5. Singularity — R18–R23
6. Completeness — R24–R25
7. Realism, conditions, uniqueness — R26–R30
8. What, not how — R31
9. Quantities — R32–R35
10. Uniform language and structure — R36–R41
11. Interactions with other systems — NRM 6.2.3
12. Standards and compliance — NRM 4.6.2, 6.2.1.2.5
13. Unknowns: TBD / TBR — NRM 14.2.4
14. Attributes — NRM 15
15. Information items

---

## 1. Structure and keywords

**R1 Structured, complete sentence.** Use `[Condition,] the <IP> shall <verb> <object> [measurable
outcome] [qualifier].` A function needs its observable action (what), its performance (how well)
and its conditions (when, in which state or mode). A statement that lacks any of them is incomplete
(GtWR C4).
- Condition types: event-driven `When <trigger>, …`; state-driven `While <state>, …`;
  unwanted behavior `If <condition>, [then] …`.
- ✗ `Key zeroization on reset.`
- ✓ `When RST_N is asserted, the <IP> shall set each bit of KEY0 to KEY<n> to 0 within <n> HCLK cycles.`

**Keywords (ISO 5.2.4).** The keywords are agreed once and used consistently.
- `shall`: binding requirement.
- `will`: a statement of fact, intent or context. It is not binding.
- `should`: a goal. It is not binding.
- `may`: an allowance.
- Avoid `must`: readers take it for a requirement.
- Descriptive text uses is / are.

**R2 Active voice, responsible entity as subject.** "shall be …ed" hides who acts.
- ✗ `The key shall be cleared after use.`
- ✓ `When CTRL.CLEAR_KEY is written to 1, the <IP> shall set each bit of the Key_Register to 0 within <n> HCLK cycles.`

**R3 Subject and verb appropriate to the entity.** Every requirement in this set is on the IP. An
obligation on software, the SoC or the integrator is not an IP requirement. Record it as an INFO
*assumption/dependency*, or ask what the IP must do so that the other party can act. Verbs such as
support, handle, process, manage, track and flag are too vague for a requirement. Use an
observable action: encrypt, decrypt, compute, set, clear, return, assert, respond, ignore.
- ✗ `The driver shall poll STATUS.DONE.`
- ✗ `The <IP> shall support AES-GCM.`
- ✓ One requirement per observable behavior, e.g. `When CTRL.MODE is GCM AND CTRL.START is written to 1, the <IP> shall compute the Authentication_Tag as specified in NIST SP 800-38D <§x>.`

## 2. Accuracy

**R4 Define terms.** Each register, field, signal and domain term used in a requirement is defined
once, in an INFO table (definitions, register map, signal list). Mark defined terms consistently
(`` `CTRL.START` `` or Capital_Underscore).
- ✗ `the current key`
- ✓ `the Active_Key` (defined in the Definitions table).

**R5 Definite article.** "a key" can mean any key. Use "the <defined term>" or "each <term>". An
indefinite article is fine where a value removes the doubt ("an accuracy of …").

**R6 Units.** Every number carries a unit or the thing it counts. Use one unit system throughout.
- ✗ `within 20`
- ✓ `within 20 HCLK cycles`
- ✓ `at least <n> bits per HCLK cycle`

**R7 No vague terms.** Avoid words such as adequate, appropriate, sufficient, efficient, typical,
relevant, significant, robust, secure, safe, user-friendly and approximately. They cannot be
verified and they leave the decision to the implementer.
- ✗ `adequate protection against side-channel attacks`
- ✓ Ask the owner for the property and its acceptance criterion: attack class, assessment method, threshold and a named standard or procedure.

**R8 No escape clauses**, such as if possible, where possible, as appropriate, as required, if
necessary, as applicable or to the extent practical. They make the requirement optional.

**R9 No open-ended clauses**, such as etc., and so on, including but not limited to, or as a
minimum.
- ✗ `The <IP> shall encrypt in ECB, CBC, CTR modes, etc.`
- ✓ One requirement per mode, or one requirement pointing to a table of modes (the owner chooses the style for the whole spec).

## 3. Concision

**R10 No superfluous infinitives**, such as be able to, be capable of, be designed to or have the
capability to. A device that "is able to" do something once but fails the other 99 times has
still met that wording.
- ✗ `The <IP> shall be able to encrypt a Block.`
- ✓ `The <IP> shall encrypt a Block …`

**R11 One clause per condition or qualification.** Keep the verb next to its object. Put
performance and conditions in their own clauses. Don't insert a clause between the verb and the
object.

## 4. Non-ambiguity

**R12–R14 Grammar, spelling, punctuation.** A misplaced comma can move a performance value to the
wrong noun. Re-read each statement for what the comma attaches to.

**R15 Logical expressions.** Write logical conditions in capitals inside brackets: `[X AND Y]`,
`[X OR Y]`, `NOT [X]`. Never write "and/or".
- ✓ `When [CTRL.START is written to 1 AND STATUS.KEY_VALID is 0], the <IP> shall set STATUS.ERR_NOKEY to 1.`

**R16 Avoid "not".** "Never" cannot be verified in finite time. State the positive, observable
behavior. The positive behavior is an owner decision, so ask which one is wanted.
- ✗ `The <IP> shall not output the key on the bus.`
- ✓ `The <IP> shall return 0x0000_0000 in the read data of each read transfer addressed to a KEY register.`

**R17 No oblique "/"** except in units (bits/cycle, Mbit/s) and ±.
- ✗ `encrypt/decrypt`
- ✓ Two requirements.

## 5. Singularity

**R18 One sentence, one thought.** Use one "shall", with any number of conditions. Reasons go to
Rationale, and context goes to an INFO item. If one condition triggers several actions, write one
requirement per action and repeat the condition in each.
- ✗ `When CTRL.START is written to 1, the <IP> shall encrypt the Block and shall assert IRQ.`
- ✓ Two requirements, each repeating the condition.

**R19 Avoid combinators** such as and, or, but, unless, as well as, whereas and otherwise. They
usually join two requirements. Exception: the logical AND/OR/NOT convention of R15.

**R20 No purpose phrases**, such as so that, in order to or thus allowing. Move the purpose to the
Rationale.
- ✗ `… shall set STATUS.ERR_BUSY to 1 so that software can detect misuse.`

**R21 No parentheses or examples in the statement**, such as (typically 12 cycles), e.g., i.e. or
such as. Either the text is the requirement, and becomes a value, or it is context, and moves to
Rationale or an INFO item. Two bracket forms are allowed: the TBR form `[<value> TBR-nn]` and
the logical form `[X AND Y]`.

**R22 Enumerate instead of group nouns.**
- ✗ `The <IP> shall report all error conditions.`
- ✓ One requirement per error condition, each naming its status field.

**R23 Complex behavior: point to a diagram or table.** Examples are a request/acknowledge
handshake, a timing sequence, or a mode matrix:
`… shall assert DMA_REQ with the timing shown in Figure <n>.` The figure itself is an INFO item
and must be unambiguous.

## 6. Completeness

**R24 No pronouns** (it, this, they, its) and no indefinite pronouns (any, some, all). Repeat the
noun. Each requirement becomes a standalone work item in Polarion, so a pronoun loses its
antecedent.

**R25 Don't rely on headings.** The statement must be understandable without its section
heading.
- ✗ Under the heading "Zeroization": `The <IP> shall complete it within 64 cycles.`

## 7. Realism, conditions, uniqueness

**R26 No unachievable absolutes**, such as always, never, all, every or 100 %. Bound the claim
instead: a limit, a probability or confidence, or an explicit set.

**R27 Explicit applicability conditions.** Repeat the condition in each requirement it governs.
Never state a condition once and then list actions under it.

**R28 Explicit condition lists.** When several conditions trigger one action, say whether all or
any of them must hold, using `[A AND B]` or `[A OR B]`. Splitting into one requirement per
condition is often clearer.

**R29 Classify.** Group requirements by category (section) so duplicates, gaps and conflicts show
up.

**R30 Express once.** No duplicates or overlaps, and no re-wording of a REQ inside an INFO item.

## 8. What, not how

**R31 Solution-free (design inputs).** State what the IP must achieve at its boundary, not how it
is built: datapath width, number of S-box instances, FSM encoding, pipeline depth.
- When a statement names an implementation, ask "for what purpose?" The answer is often the
  missing real requirement, such as throughput, latency, area or leakage.
- If the owner keeps an implementation constraint (a reused block, a mandated standard cell,
  a certification), keep it and state why in Rationale.
- ISO 5.2.5 calls this characteristic *Appropriate*.

## 9. Quantities

**R32 "each" for universal quantification.** Use "each" instead of all, any or both.
- ✓ `… for each read transfer addressed to …`

**R33 Ranges and tolerances.** A single point value is rarely what is meant. Ask whether a
slightly better or worse result is still acceptable, then use at least / at most / ± / between.
Keep tolerances no tighter than needed, because tighter tolerances cost design and verification
effort.

**R34 Measurable targets.** Avoid fast, low latency, high throughput, minimum and maximum. Give a
number, a unit and the condition it holds under, for example the clock domain, key size and mode.

**R35 Definite timing.** Avoid immediately, eventually, before and after unless they come with a
bound. Use `within <n> <unit> of <event>`.

## 10. Uniform language and structure

- **R36 Consistent terms and units.** Use one name per register, signal or concept, and don't
  mix cycles and ns for the same quantity. When a value repeats, define it once as a named term.
- **R37 Acronyms and R38 abbreviations.** Each acronym is defined in the Definitions table and
  written the same way everywhere. Avoid abbreviations with more than one meaning.
- **R39 Style guide.** This skill, together with the spec front matter, is the style guide:
  patterns, attributes, verification methods and term notation.
- **R40 Group related requirements and R41 follow a defined structure.** See
  [spec-template.md](spec-template.md).

## 11. Interactions with other systems (NRM 6.2.3)

The bus, interrupt controller, DMA, key source, clock/reset controller and software are external
systems. An *interface* is a boundary, not a thing. Never write "the interface shall…" or "the
<IP> shall interface with…".

- Write one requirement per interaction. Each has three parts:
  - a verb for the direction (receive, send, respond, assert, sample, provide);
  - the object that crosses the boundary;
  - a pointer to where the interaction is defined: a standard ID with issue and section, or a
    table or figure in this spec.
- ✓ `The <IP> shall respond to each AHB transfer addressed to its register space as defined in <bus spec ID, issue>, <§x>.`
- ✓ `If a write transfer addresses a read-only register, the <IP> shall respond with an ERROR response as defined in <bus spec ID, issue>, <§x>.` Whether to respond with ERROR or to ignore the write is the owner's decision.
- Definitions (register map, signal list, handshake timing) are statements of fact in INFO
  items or in the referenced standard. They use no "shall".
- When the other side is being developed at the same time (a DMA controller, a key manager),
  both specs need matching requirements that point to the same definition. Ask the owner who
  controls that definition.
- Terminology follows the cited bus spec issue. Ask rather than assume, for example
  "Subordinate" or "slave".

## 12. Standards and compliance (NRM 4.6.2, 6.2.1.2.5)

- Cite the exact document, version or date, and section: `FIPS 197-upd1 §5.1`, `NIST SP 800-38D <§x>`. Never cite "latest version".
- Avoid `shall comply with <whole standard>`. Whole standards rarely apply clause by clause.
  Derive specific requirements from the clauses that apply and put the clause in `Source:`.
- Don't paste standard text into the spec. Standards are written for a class of products, and
  their wording is often not verifiable at IP level.
- Process requirements (how the IP is developed, documented or certified) do not belong in the
  IP requirement set. Mention them to the owner. They usually go to a plan or SOW.

## 13. Unknowns: TBD / TBR (NRM 14.2.4)

- `TBD-nn` marks a value that is not known yet: `within TBD-03 HCLK cycles`.
- `[<value> TBR-nn]` marks a tentative value awaiting confirmation: `within [20 TBR-01] HCLK cycles`.
- Log each marker in the notes file with the location, the missing information, the resolver and
  the status.
- Don't swap in a questionable value just to remove a TBR. An over-tight value constrains the
  design needlessly.
- A baselined spec should have no TBD/TBR left (GtWR C4). `status` lists what remains.

## 14. Attributes (NRM 15, lean set)

- **Rationale:** one or two sentences covering why the requirement exists, where each number comes
  from, and the assumptions made. It explains the requirement and never adds to it, so it contains
  no "shall".
- **Verification:** one of the methods listed in the front matter.
  - The defaults are those of ISO 6.5.2.2: Test, Analysis, Inspection, Demonstration.
  - Typical mapping (NRM 10.1.3.6.3): function and performance → Test; binary on/off behavior →
    Demonstration; document or physical properties → Inspection; statistical or lifetime
    properties, or whatever cannot be exercised directly → Analysis.
  - The owner's organization may use its own method names. Use those.
  - Writing the method while drafting exposes unverifiable wording early.
- **Source:** the parent requirement, customer or SoC spec §, standard clause, or `DEC-nn` (an
  owner decision logged in the notes). Every requirement has one, so there are no orphans.
- Optional: **Title**, and **ID**. Fill ID only with an ID that Polarion has already assigned.

## 15. Information items

- INFO items carry the context a reader needs: purpose, scope, a usage sequence, definitions,
  register and signal tables, assumptions and dependencies.
  - They state facts with is / are / will.
  - They never contain shall / must / should / required.
  - They never add, relax, contradict or restate a requirement. A reader who skips every INFO
    item must still know every obligation.
- Keep each INFO item short. Use a table when the content is tabular.
- INFO content also comes only from the owner or a cited document. Draft it from what the owner
  said and get approval, the same as for a REQ.
