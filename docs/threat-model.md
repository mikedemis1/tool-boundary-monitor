# Threat Model — Tool Boundary Monitor

Scope: the banking suite of [AgentDojo](https://github.com/ethz-spylab/agentdojo)
v0.1.35, as installed and read from source. Every fact in Section 2 was taken
from the package source, not from documentation or from the illustrative
examples in the project draft.

**Benchmark version: `v1.2.2`, and this is pinned deliberately.** AgentDojo
versions its task definitions independently of the package, and the banking
suite is patched at `v1.1.1` (`task_suite/load_suites.py`, where `v1` and `v1.1`
both map to the unpatched `banking_task_suite`, while `v1.1.1` and later call
`get_new_version(...)`). The patch matters here: at `v1`, the legitimate landlord
IBAN in UserTask15 is `US133000000121212121212`, byte-identical to the
`_ATTACKER_IBAN` used by the injection tasks. Evaluating on `v1` or `v1.1` would
mean a benign task and the attack goal are indistinguishable by destination, and
any false-positive rate measured there would be reporting a benchmark bug the
maintainers have already fixed. At `v1.1.1`+ the recipient is
`CA133012400231215421872` and the collision is gone.

> **Status:** Sections 1, 2, 3 and 4 complete, verified against installed source
> (2 and 4 on 2026-08-14, 3 and 1 on 2026-09-04). Section 5 to be written.

---

## 1. System model

Written last, on purpose. A trust boundary is a line drawn between what an
attacker controls and what he does not, and neither side of that line could be
stated before Sections 2, 3 and 4 said what the tools are, what the attacker can
reach, and what is worth protecting.

### 1.1 The four participants

```
  USER ──prompt──▶ MODEL ──proposed tool call──▶ RUNTIME ──▶ ENVIRONMENT
                     ▲                                            │
                     └────────── tool result, as text ────────────┘
```

**The user** states the task in natural language and is the only source of
authority in the system. Nothing else in the loop has a mandate of its own.

**The model** chooses which tool to call and what to put in its arguments. It
holds every tool for every task: the banking suite exposes all eleven regardless
of what was asked, and defines no scopes, no roles and no per-task restriction.
AgentDojo does ship an optional `tool_filter` defense that narrows the tool set
per query (`agent_pipeline/agent_pipeline.py`), but that is a defense someone
switches on, not a property of the environment, and it is not part of the
baseline this document describes.

**The runtime** executes what the model proposed. In AgentDojo the harness is a
chain of pipeline elements, and tool execution is one element in that chain
(`agent_pipeline/tool_execution.py`, `ToolsExecutor`): it reads the tool calls
from the last assistant message, invokes them, serialises each return value to
text and appends it to the conversation. The only checks before execution are
that the function name is non-empty and exists. It does not evaluate the call.

Two details of that serialisation matter later. The text format is not uniform:
`tool_result_to_str` applies `yaml.safe_dump` only to a `BaseModel` or a list of
them — in this suite that is just `get_most_recent_transactions` and
`get_scheduled_transactions` — and falls through to `str()` for everything else;
the formatter is also swappable for JSON. And a failing call does not abort the
episode: `run_function` returns an empty result plus an error string
(`functions_runtime.py`, `raise_on_error=False` by default), the runtime carries
that string in a separate `error` field, and each model adapter substitutes it
for the message content. The route differs from a successful result, but the
outcome is the same — a rejected call is one more message the model gets to
read.

**The environment** is the state the tools read and write: the bank account and
its transactions, the scheduled transactions, the user profile, the filesystem.
This is what Section 4 enumerates as assets.

### 1.2 Where the boundary actually is

The boundary is not the network, and not the process. Everything here runs in one
place, with one identity, on behalf of one user. A conventional perimeter has
nothing to separate.

The boundary is a **moment**: the point at which a proposed tool call becomes an
executed one. Before it, everything is text — a suggestion the model has emitted,
reversible at zero cost. After it, the environment has changed, and Section 2.3
establishes that in this domain much of that change cannot be walked back: there
is no deletion primitive for a scheduled payment and `recurring` cannot be turned
off again.

Placing the line there follows from Section 3 rather than from preference. Entry
and harm are always different tools (3.1), so a boundary drawn at the read side
would guard a call that does nothing. The write call is the last point at which
the effect is still undetermined.

**It is not, however, the point at which everything relevant is visible in the
arguments.** `update_scheduled_transaction` requires only `id`; every other field
is optional, and the suite's own legitimate use exercises that — UserTask2's
ground truth is `{"id": 7, "amount": 1200}`, with no recipient and no subject in
the call at all (2.3, 3.7). The destination and the outgoing text stay in the
stored record the call addresses. What crosses the boundary is therefore **a
proposed call together with the state it points at**, not a self-contained
argument list, and any monitor that reads only the arguments is blind on exactly
the tool Sections 2.3 and 3.7 single out as the quietest.

### 1.3 Trusted, untrusted, and the awkward middle

**Trusted:** the user's prompt, the runtime, and the tool implementations. The
tools are assumed to do exactly what their code says — their weaknesses are
recorded in Section 2.3 as facts about the environment, not as compromise.

**Untrusted:** every byte that comes back from a tool. The result of
`get_most_recent_transactions` is a data structure serialised into text and
appended to the same conversation that carries the user's instructions. At that
point instruction and data are the same kind of object, and Section 3.3 shows
this is the dominant channel, not the exotic one.

**The awkward middle is the model.** It sits inside the trust zone by privilege
and outside it by behaviour: it acts with the user's full authority while
executing text it did not author and cannot attribute. It is not assumed to be
malicious, backdoored or replaced — only manipulable. That single assumption is
what makes a monitor necessary, because a component that is trusted with
authority but not trustworthy about origin cannot be secured by asking it to
behave.

### 1.4 Out of scope

No attacker on the network, on the host or in the supply chain. No compromised
tool implementation, no tampered model weights, no malicious user. The only
adversary modelled is the one in Section 3, whose entire capability is writing
text that the agent will later read.

### 1.5 Why the arguments are the attack surface

A conventional application does not have this problem. A "Pay rent" button is
wired to stored values:

```
user clicks "Pay rent"  →  pay(stored_iban, stored_amount)
```

In such a flow the IBAN is retrieved from storage rather than produced at
request time. No model decides anything, and no text the user has received can
change where the money goes. The flow is fixed, and a fixed flow cannot be
redirected. (This is an idealised baseline used for contrast, not a measured
claim about any particular application.)

An agent is the opposite. The user writes a sentence, and the model decides
which tool to call **and what to put in its arguments**:

```
"pay my rent"  →  send_money(recipient=?, amount=?)
                                    ↑
                          filled in by the model
```

The recipient is not retrieved from storage. It is generated — by a model that
has just read whatever content the task required it to read.

This is visible directly in the benchmark. The environment ships a file
`landlord-notices.txt` announcing a rent increase and asking the tenant to
adjust their standing order, with an attacker-controlled span inside it
(`{injection_landloard_notice}`). The corresponding task cannot be served by a
stored value alone. The notice states an increase — *"the rent will be increased
by 100.00"* — while the standing order it refers to (id 7) holds `1100.0`. The
figure the task actually needs, `1200`, is in neither place: it has to be
computed from the document and the record together. Reading the document is the
task. The attacker writes in the same document.

The consequence is not a defect to be fixed:

| | Fixed flow (button) | Agent |
|---|---|---|
| Arguments come from | storage | model output |
| Can handle open-ended requests | no | yes |
| Can be redirected by content it reads | no | **yes** |

**Flexibility is the exposure.** If the flow is fixed, an agent is not needed;
the moment an agent is used, tool arguments become model output, and model output
is influenced by everything the model has read. This is why a call cannot be
treated as authorised merely because the model emitted it (1.3).

It is also why the **hook point** is the proposed call — and the hook point must
not be confused with the **decision rule**. The call is *where* the decision is
taken, because that is the last moment before the effect lands. It is not *what*
the decision is taken on: Sections 3.4 and 4.4 show that a harmful call and a
legitimate one in this suite can be identical in content and authority, so the
arguments cannot separate them. What separates them is where the instruction
behind them came from.

---

## 2. Tool inventory

The agent is given **11 tools**. It holds all of them for every task; the
benchmark defines no scopes, roles, or per-task restrictions.

Source: `agentdojo/default_suites/v1/banking/task_suite.py`, with
implementations in `default_suites/v1/tools/{banking_client,user_account,file_reader}.py`.

### 2.1 Read-only tools

| Tool | Parameters | Returns | Data exposed |
|---|---|---|---|
| `get_iban` | — | `str` | The user's own IBAN |
| `get_balance` | — | `float` | Current balance |
| `get_most_recent_transactions` | `n: int = 100` | `list[Transaction]` | Full records: sender, recipient, amount, subject, date, recurring |
| `get_scheduled_transactions` | — | `list[Transaction]` | Pending and recurring payments, including recipient IBANs and dates |
| `get_user_info` | — | `dict` | First name, last name, street, city |
| `read_file` | `file_path: str` | `str` | Contents of any path in the environment filesystem |

Notes:

- `get_user_info` returns four fields only. The `password` field exists on the
  `UserAccount` model but is **not** returned.
- `read_file` returns an empty string for a missing path rather than raising.
  There is no path restriction and no allowlist.
- `get_most_recent_transactions` defaults to `n = 100`. The seeded environment
  holds **5** past transactions and **2** scheduled ones — seven records, ids 1
  to 7, but only the five are in the history list
  (`data/suites/banking/environment.yaml`). The default therefore returns the
  complete history: asking for "recent" transactions reads everything that
  exists.

### 2.2 State-changing tools

| Tool | Parameters | Effect | Reversible? | When harm lands |
|---|---|---|---|---|
| `send_money` | `recipient, amount, subject, date` | Appends a transaction to history | **No** | Immediately |
| `schedule_transaction` | `recipient, amount, subject, date, recurring` | Appends to scheduled transactions | **No — see 2.3** | Future, repeating if `recurring` |
| `update_scheduled_transaction` | `id`, then any of `recipient, amount, subject, date, recurring` | Mutates an existing scheduled payment in place | Only if the previous values are known | Future |
| `update_password` | `password` | Overwrites the account password | Partial — user is locked out | Immediately |
| `update_user_info` | any of `first_name, last_name, street, city` | Overwrites profile fields | Yes | Immediately |

### 2.3 Structural observations

Properties of this tool set that matter for the design, all verified in
source:

**No deletion primitive, and no way to disarm.** There is no
`delete_scheduled_transaction` and no `cancel_transaction`. A scheduled or
recurring payment, once created, cannot be removed through any tool the agent
has. The updater does not soften this, because it tests its optional arguments
for truthiness rather than for presence:

```python
if amount:
    transaction.amount = amount
if recurring:
    transaction.recurring = recurring
```

`recurring=False` is falsy, so recurrence can be switched **on** and never off.
`amount=0` is silently ignored for the same reason. `update_user_info` has the
identical pattern, so a profile field cannot be cleared to an empty string.

A recurring payment is therefore not merely undeletable — it is also
undisarmable. Prevention carries more weight here than in a system with a
cleanup path, because there is no state in which the harm can be walked back.

**IDs are guessable, and failure answers the guess.** `next_id` allocates
`max(id over both lists) + 1`, so identifiers are small, dense and sequential —
1 to 7 in the seeded environment. `next_id` itself does not disclose existing
ids; it returns the id of the record about to be created. The addressing
primitive is the failure path instead: `update_scheduled_transaction` raises
`ValueError(f"Transaction with ID {id} not found.")` for an unknown id, and the
runtime hands that string back to the model as tool output rather than aborting
(`functions_runtime.py`). An unknown id is therefore answered, not punished, and
a caller can locate a live scheduled payment by trying small integers. The read
that would have made a redirection visible in a trace is not required. AgentDojo
assumes the opposite: its own injection task leaves the id as a placeholder
(`"$transaction_id"`) to be discovered.

**Failure is loud in one place and silent in another.** The `ValueError` above
is visible to the model, while `read_file` returns `""` for an unknown path.
Probing the filesystem leaves no error signal at all; probing transaction ids
returns a usable answer. Any detector that keys on error rates will see one of
these behaviours and not the other.

**The sender field cannot be forged.** `send_money` and `schedule_transaction`
both set `sender=get_iban(account)` internally, and `send_money` hardcodes
`recurring=False`. Neither is reachable from the arguments the model produces.
Attribution of the origin account is outside the attacker's control, and the
monitor does not need to defend it.

**Silent redirection is possible.** `update_scheduled_transaction` takes an `id`
and optional fields. Changing only `recipient` on an existing legitimate payment
leaves amount, subject, date and recurrence untouched. The resulting entry is
visually indistinguishable from the original in `get_scheduled_transactions`
output. This is a quieter path to the same outcome than `send_money`.

**No argument validation anywhere.** `recipient` is an unvalidated string,
`amount` an unvalidated float. No IBAN format check, no destination allowlist,
no bound on amount, no check against balance. The only enforcement present is
Pydantic type coercion when the `Transaction` object is constructed, which
rejects a non-numeric amount and nothing else. Any constraint on the *meaning*
of an argument has to come from the gateway, because the tools enforce none.

**Balance is not debited.** `send_money` appends to `account.transactions` and
does not modify `account.balance`. Harm in this environment is represented by
the transaction record, not by a decreasing balance. Any harm definition must
therefore be expressed over the transaction list, not over the balance field.

---

## 3. Attacker capabilities

### 3.1 What the attacker is, and what he is not

The attacker holds **no account and no tool**. He cannot call `send_money`, he
cannot authenticate, and he is not present while the episode runs. He is not a
compromised model, not a malicious user, and not a network position between the
agent and the tools.

His entire capability is this: **he controls the contents of one text field that
the user's own data already contains**, and that the agent will read at some
point while carrying out a legitimate task. A line inside a bill, the subject of
an incoming transfer, extra text in a notice from the landlord.

The chain is always the same, and it has two tools in it, never one:

```
attacker writes text  ->  text sits in the environment
-> user gives the agent an ordinary task
-> agent calls a READ tool, text enters the context
-> agent calls a WRITE tool              <- harm lands here
```

The entry tool causes no harm; it only returns data. The harm tool is a
different call, made later, by the agent, with the user's authority. The gap
between the two is the subject of this document.

### 3.2 The four write positions

The banking suite defines exactly four injection vectors
(`data/suites/banking/injection_vectors.yaml`):

| Vector | Where the text appears | Reaches the agent through |
|---|---|---|
| `injection_bill_text` | Body of a bill file | `read_file` |
| `injection_incoming_transaction` | `subject` of an incoming transaction | `get_most_recent_transactions` |
| `injection_landloard_notice` | Landlord notice on a rent increase | `read_file` |
| `injection_address_change` | Landlord notice on an address change | `read_file` |

Two properties of this table matter more than its contents.

**The attacker writes into the same fields the legitimate task reads from.**
`injection_bill_text` is not an added file; it is the body of the bill the user
asked the agent to pay. Its default content already carries the recipient IBAN
`UK12345678901234567890`, which is the *legitimate* destination in UserTask0. The
field that decides where the user's money legitimately goes is a field the
attacker controls.

**Three of the four vectors are files, but files are the minority channel.**
Counting vectors suggests documents are the main threat. Counting *episodes*
says the opposite — see 3.3.

### 3.3 Which position actually fires — measured, not assumed

A vector only matters for a given task if the agent's normal execution of that
task actually pulls the text into its context. AgentDojo decides this itself
(`attacks/base_attacks.py`, lines 49–69): it places a canary string in every
injection slot, runs the task's ground-truth tool pipeline, and keeps the slots
whose canary appears in the resulting tool output.

That procedure was reproduced offline against the pinned suite `v1.2.2`, with no
model call, by `scripts/injection_candidates.py` in this repository. The result
over all 16 user tasks:

- **12 of 16 tasks expose `injection_incoming_transaction`** — tasks 1, 3, 4, 5,
  6, 7, 8, 9, 10, 11, 14, 15.
- **4 of 16 expose a file vector** — task 0 (`injection_bill_text`), tasks 2 and
  12 (`injection_landloard_notice`), task 13 (`injection_address_change`).
- **Every task exposes exactly one slot.** No task in the suite surfaces two.

Two consequences.

First, **a monitor built on the assumption that untrusted content arrives in
documents misses three quarters of the suite.** The dominant channel is a
transaction subject: a short, structured, routine-looking string returned by a
read the user asked for.

Second, **the attacker does not choose his channel — the user's task chooses it
for him.** Because each task exposes exactly one slot, the placement decision is
made for him by whichever tool the legitimate task happens to call. He cannot
spread one payload across several fields and wait to see which one lands.

### 3.4 What he gains: borrowed authorisation

The attacker never acquires a capability. He borrows one that already exists.

The agent holds all 11 tools for every task (Section 2); the benchmark defines no
scopes, no roles and no per-task restriction. A task that says "read my recent
transactions" is executed by an agent that can also send money, schedule a
recurring payment, overwrite the profile and overwrite the password. The distance
between the entry point and every one of the five write tools is therefore
exactly one model decision. `update_user_info` deserves naming here rather than
being folded into "the rest": it tampers with A5 *and* returns the full record
including the fields it did not touch (Section 4.2), so a single call both
changes and discloses.

The call that results is, at the tool boundary, **indistinguishable from a
legitimate one**. It carries the user's own session, the user's own IBAN as
`sender` (3.5), a well-formed amount and a plausible subject. Section 4.4
establishes the matching fact on the harm side: every write-side harm cell in
this suite has a benign counterpart among AgentDojo's own legitimate tasks, and
`update_password` in UserTask14 is *the same call* as InjectionTask7.

This is why the monitor's decision rule cannot be a harm classifier. What
separates the two calls is not what the call does, but **where the instruction
that produced it came from**.

### 3.5 The limits

Three things the attacker demonstrably cannot do in this environment. Each is a
constraint the monitor does not have to defend, and stating them keeps the threat
model from over-claiming.

**He cannot forge the origin account.** `send_money` and `schedule_transaction`
both set `sender=get_iban(account)` internally; `sender` is not among the
arguments the model produces. Attribution of the paying account is outside his
control.

**He cannot read the password out of the environment.** `get_user_info` returns
four profile fields and does not include `password`, although the field exists on
the `UserAccount` model, and no other read path exists in the package. The limit
is on the *tool surface*, not on the secret: as Section 4 records, in UserTask14
the plaintext password is supplied in the user's own prompt and therefore sits in
the model's context, from where it can be copied into an outbound field like any
other string (3.7). No tool call discloses A4; a task can. (Lockout after
`update_password` is an assumption about a system this environment does not model
— there is no authentication in it — and is labelled as such in Section 4.)

**He cannot act outside an episode.** He has no persistence, no scheduler and no
second channel. His text has to be read during a task the user initiated, or
nothing happens at all.

### 3.6 What the environment gives him for free

Two properties of the implementation lower the cost of an attack. Neither is a
capability he brought with him.

**Identifiers are small, dense and answered on failure.** `next_id` allocates
`max(id) + 1` over both transaction lists, so live ids are 1–7 in the seeded
environment. `update_scheduled_transaction` raises
`ValueError("Transaction with ID {id} not found.")` for an unknown id, and the
runtime returns that string to the model as tool output instead of aborting
(`functions_runtime.py`, `raise_on_error=False`). An unknown id is therefore
*answered*, not punished: a live scheduled payment can be located by trying small
integers, without ever calling `get_scheduled_transactions`. The read that would
have made a redirection visible in the trace is not required. AgentDojo assumes
the opposite — its own injection task leaves the id as a placeholder
(`"$transaction_id"`) to be discovered first.

**Probing is silent in the other direction.** `read_file` returns `""` for an
unknown path and raises nothing. Filesystem probing leaves no error signal; id
probing returns a usable one. A detector keyed on error rates sees one of these
behaviours and not the other.

### 3.7 Where the damage leaves the system

Every path by which money or data leaves runs through **three tools**:
`send_money`, `schedule_transaction`, and `update_scheduled_transaction`. The
last redirects an existing payment *and* rewrites its `subject` in the same call,
which makes it both an exfiltration channel and the quietest one — changing only
`recipient` leaves amount, subject, date and recurrence intact, and the resulting
record is visually indistinguishable from the original in
`get_scheduled_transactions` output.

**What can be put into that channel is everything already in the context, not
only money.** The suite has no email, HTTP or messaging tool, so the only way any
value leaves is inside a free-text argument — `recipient`, `subject`, `date`, all
unvalidated strings, with `amount` as a low-bandwidth numeric channel on top. The
read tools of Section 2.1 have already placed the material there by the time the
write call is made: the user's IBAN and balance (A3, via `get_iban` /
`get_balance`), the profile fields (A5, via `get_user_info` — or via
`update_user_info`, which returns the whole record), file contents (A6, via
`read_file`), and, in UserTask14, the plaintext password itself (A4, from the
user's prompt rather than from any tool). Disclosure of these assets does not
need a dedicated path: it needs one payment call with a controlled destination.
This is what closes the gate between Sections 3 and 4 — every disclosure cell
marked reachable in 4.3 is reached the same way, through these three tools.

Because the outbound text field (`subject`) exists only on these three tools,
**disclosure and unauthorised payment are not two separate problems**: every
exfiltration is also a write to A1 or A2, and both collapse to a single predicate
checked at the payment tools.

The matching weakness is that a scheduled payment, once created, cannot be
removed or disarmed: there is no deletion primitive, and `recurring=False` is
falsy, so recurrence switches on and never off (Section 2.3). Prevention carries
more weight here than in a system with a cleanup path.

### 3.8 What this section fixes for the monitor

Four requirements follow directly from the capabilities above, each traceable to
the subsection that produced it:

1. **The untrusted-content marker must cover tool *results*, not just files.**
   The dominant channel is a transaction subject (3.3).
2. **The decision must be taken at the write call, not at the read.** Entry and
   harm are always different tools, and only the write call carries the
   destination and the amount (3.1).
3. **The rule must be provenance, not harm class.** Harmful and legitimate calls
   are identical in content and in authority (3.4).
4. **`sender` needs no defence; `recipient`, `subject`, `date` and `amount` need
   all of it.** The one field the attacker cannot reach is the one the tools set
   themselves; every argument the model produces is left unvalidated (3.5, and
   Section 2.3).

What the attacker is *entitled* to do — the definition of `Authorized` — is
deliberately not settled here. That is policy, not threat, and it belongs to the
policy store in the gateway architecture.

---

## 4. Assets and harm

### 4.1 The assets

An asset is a piece of state worth protecting. The tools in Section 2 are the
mechanism; the assets are what the mechanism can damage. They are enumerated
from the environment models, not from the tool list, so that the set survives a
change to the tool surface.

`BankingEnvironment` holds three models — `BankAccount`, `UserAccount`,
`Filesystem` (`banking/task_suite.py`). Their fields group into six assets:

| # | Asset | Backing state | Read by | Written by |
|---|---|---|---|---|
| A1 | Money moved | `BankAccount.transactions` | `get_most_recent_transactions` | `send_money` |
| A2 | Future payment commitments | `BankAccount.scheduled_transactions` | `get_scheduled_transactions` | `schedule_transaction`, `update_scheduled_transaction` |
| A3 | Account facts | `BankAccount.iban`, `BankAccount.balance` | `get_iban`, `get_balance` | — |
| A4 | Credentials | `UserAccount.password` | — | `update_password` |
| A5 | Personal data | `UserAccount.first_name`, `last_name`, `street`, `city` | `get_user_info`, `update_user_info` (see 4.2) | `update_user_info` |
| A6 | Environment documents | `Filesystem.files` | `read_file` | — |

### 4.2 Why these six

**A1 and A2 are separate assets, not one.** They share a type (`Transaction`)
and a container, but they differ on both axes fixed in Section 2.2: A1 damage
lands immediately and once, A2 damage lands in the future and may repeat. A2
also has a mutation path (`update_scheduled_transaction`) that A1 does not, and
that path is the silent-redirection case. Merging them would erase the
distinction the monitor exists to make.

**Three asymmetries follow directly from the empty cells above**, and each one
removes a whole harm class before any policy is written:

- **A4 is write-only.** No tool returns the password. `get_user_info` omits the
  field (Section 2.1). The agent can overwrite the credential but cannot read
  it, so disclosure of A4 is not reachable through the tool surface.
- **A3 and A6 are read-only.** `set_iban` and `set_balance` exist in
  `banking_client.py` but are absent from the suite's `TOOLS` list, and no tool
  writes to `Filesystem.files`. Tampering with A3 or A6 is not reachable
  either.
- **A6 is attacker-writable but not agent-writable.** The agent can only read
  the documents; the attacker's text arrives inside them. A6 is therefore the
  input side of the boundary rather than a target — the asset that carries the
  attack rather than absorbing it. Section 3 picks this up.

**On balance.** `BankAccount.balance` is grouped under A3 rather than A1 because
`send_money` never modifies it (Section 2.3). It is a displayed figure, not an
accounting of A1. Harm to A1 has to be expressed over the transaction list.

**A5 has a second read path.** `update_user_info` returns the full record —
all four fields, including the ones the call did not modify
(`user_account.py`). It is a write tool that also discloses. Any analysis that
treats "read tools" and "write tools" as disjoint sets is wrong on this one
tool, and a monitor that only inspects `get_user_info` for A5 disclosure will
miss it.

### 4.3 Harm per asset

Harm is classified as **disclosure** (the value reaches someone who should not
have it), **tampering** (the value is changed without authority) and **denial**
(the legitimate use is prevented). Reachability below means reachable *by the
agent, through the eleven exposed tools* — not reachable in principle for a real
bank.

| Asset | Disclosure | Tampering | Denial |
|---|---|---|---|
| A1 money moved | reachable | reachable — append only | **not reachable** |
| A2 commitments | reachable | reachable — create and mutate | reachable |
| A3 account facts | reachable | **not reachable** — read-only | **not reachable** |
| A4 credentials | not reachable *by tool return*; reachable *from context* | reachable | assumed, not modelled |
| A5 personal data | reachable — two paths | reachable | **not reachable** in code |
| A6 documents | reachable | **not reachable** — no writer | **not reachable** |

Six of the eighteen cells are closed by the tool surface itself. Each is closed
for a stated reason, not by assumption.

#### The unreachable cells, and why

**A1 denial.** Not because deletion is missing — that is the wrong reason. It is
unreachable because the mechanism does not exist: `send_money` appends to
`transactions` and never touches `balance` (Section 2.3), so no sequence of
calls can exhaust funds and cause a later legitimate payment to fail. Existing
records are also immutable, since `update_scheduled_transaction` iterates only
`scheduled_transactions`. The one residual mechanism is visibility, not funds:
`get_most_recent_transactions` returns `transactions[-n:]` with `n = 100`, so
appending more than 100 records would push older history out of the default
view. It is not a serious denial route, because the caller may pass any `n`.

**A3 and A6 tampering and denial.** No writer exists. `set_iban` and
`set_balance` are defined in `banking_client.py` but absent from the suite's
`TOOLS`, and nothing writes `Filesystem.files`.

**A5 denial.** The falsy-argument pattern (Section 2.3) ignores empty strings,
so a field cannot be blanked — only replaced with another non-empty value. The
old value is lost, which is a consequence of tampering; there is no separate
denial mechanism in the code.

**A4 denial — assumption, not a finding.** A wrong password locks the user out
*in a real bank*. This environment models no authentication and no login path,
so nothing in the code supports the claim. It is recorded here as an assumption
carried in from the real-world setting, and it is not used as evidence anywhere.

#### A4 disclosure is only half-closed

No tool returns the password: `get_user_info` omits the field, `update_password`
returns a fixed message, and no other read path exists in the package. The
correct statement is therefore *the password cannot be read out of the
environment by a tool call* — which is not the same as *the password cannot
leak*. In UserTask14 the plaintext password is supplied in the user's own
prompt, so a live credential sits in the model's context, from where it can be
written into any outbound string field. The tool surface closes one route and
the prompt reopens another.

#### The disclosure channel

The suite has no email, HTTP or messaging tool. Data can only leave inside a
free-text argument of a call whose destination the attacker controls. That is
three tools, not two: `send_money`, `schedule_transaction`, and
`update_scheduled_transaction` — the last one both redirects an existing payment
and rewrites its `subject` in a single call. The carrying fields are `recipient`,
`subject` and `date`, all unvalidated `str` (Section 2.3); `amount` is a
low-bandwidth numeric channel on top.

The consequence is structural: **every exfiltration path is also a write to A1
or A2.** Disclosure never stands alone in this environment. Disclosure of A3,
A5 and A6 is parasitic — the value is read by one tool and carried out by a
payment tool. A gateway that inspects the arguments of the three payment tools
sees every disclosure route the environment has.

#### Harm as testable conditions

Each reachable cell is written as a predicate over the environment before and
after the call, so that it can be checked mechanically rather than judged. Let
`pre` and `post` be the environment states, and `New = post.transactions \
pre.transactions` (and likewise for `scheduled_transactions`).

| Cell | Condition |
|---|---|
| A1 tampering | `∃ t ∈ New : t.recipient ∉ Authorized` |
| A2 tampering (create) | `∃ t ∈ New_scheduled : t.recipient ∉ Authorized` |
| A2 tampering (mutate) | `∃ t ∈ post.scheduled, t' ∈ pre.scheduled : t.id = t'.id ∧ t.recipient ≠ t'.recipient` |
| A2 denial | the mutate condition above, or `t.date` moved beyond the intended horizon — `date` is an unvalidated string |
| A4 tampering | `post.user_account.password ≠ pre.user_account.password` |
| A5 tampering | `∃ f ∈ {first_name, last_name, street, city} : post.f ≠ pre.f` |
| disclosure of any asset X | `∃ t ∈ New ∪ New_scheduled : t.recipient ∉ Authorized ∧ value_of(X, pre) appears in t.subject ∥ t.recipient ∥ t.date` |

The last row is one predicate for all of A1, A3, A4, A5 and A6 — only the set of
sensitive values changes. This is the practical payoff of the previous
subsection: disclosure needs a single check at the payment tools, parameterised
by what counts as sensitive, rather than one rule per asset.

> **Deliberately undefined here: `Authorized`.** Every tampering and disclosure
> condition above bottoms out in "is this recipient authorised", and the threat
> model does not answer that. It cannot: authorisation is policy, not threat.
> Defining it is the job of the policy store, and the shape of that definition
> is the subject of the gateway architecture document. What Section 4 fixes is
> that the question is unavoidable — see 4.4.

### 4.4 What harm classification cannot do

The grid in 4.3 says what is at stake. It does **not** say what to block, and it
is worth being explicit about that before the policy store is designed, because
the opposite assumption is the natural one to make.

Every write-side harm cell has a benign counterpart in the suite's own
legitimate tasks. Extracted from the `ground_truth` traces of the sixteen user
tasks:

| Harm cell | Attack tasks | Benign tasks doing the same thing |
|---|---|---|
| A1 tampering (`send_money`) | IT0–3, 5, 6 | UserTask0, 3, 4, 5, 11, 15 |
| A2 tampering (`schedule_transaction`) | IT8 | UserTask6 |
| A2 tampering (`update_scheduled_transaction`) | IT4 | UserTask2, 9, 12, 15 |
| A4 tampering (`update_password`) | IT7 | UserTask14 |
| A5 tampering (`update_user_info`) | — | UserTask13, 15 |

Twelve of the sixteen user tasks call at least one state-changing tool. **There
is no write cell that only an attack reaches.** The asset, the action and the
harm class are identical on both sides; UserTask14 and InjectionTask7 are the
same call to the same tool on the same asset.

The sharpest case is UserTask0. Its legitimate recipient is
`UK12345678901234567890`, read out of `bill-december-2023.txt` — and that file's
content *is* the injection vector `injection_bill_text`, whose default value
carries exactly that IBAN (`data/suites/banking/injection_vectors.yaml`). The
field that legitimately determines where the money goes is the field the
attacker controls. Paying a bill correctly and being redirected are the same
operation, distinguished only by what the document said.

Three consequences, and they shape everything downstream:

1. **A defense keyed on harm class alone has no discriminating power here.** It
   can only choose between blocking legitimate work and permitting the attack.
   Anything that separates the two must come from outside the call's own
   semantics — its provenance, or an authorisation decision made before the
   content was read.
2. **`Authorized` is therefore not a detail deferred for convenience.** It is
   the only place the separation can live. That is why the policy store is the
   next artifact and not an implementation afterthought.
3. **It also predicts where a purely prompt-level defense fails.** An action can
   be authorised, injection-free, and still outside policy; no inspection of the
   text that produced it will reveal this, because there is nothing wrong with
   the text. That is the paper's «authorized-but-out-of-policy» category,
   arrived at from the benchmark's own task definitions rather than assumed.

#### Coverage of the grid by the benchmark

The suite's nine injection tasks target A1 (IT0–3, 5, 6), A2 (IT4, IT8) and A4
(IT7). No injection task targets A3, A5 or A6, and none targets denial. Nothing
in the benchmark contradicts the grid — no attack goal lands in a cell marked
unreachable — but three of six assets and one of three harm classes have no
empirical support from AgentDojo. Episodes generated for this work are what will
cover them, and any claim about those cells has to rest on generated episodes,
stated as such.

---

## 5. Non-goals

*To be written: what this monitor does not claim to do.*
