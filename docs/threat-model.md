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

> **Status:** Sections 2 and 4 complete, verified against installed source
> 2026-08-14. Sections 1, 3, 5 to be written.

---

## 1. System model

*To be written: who talks to whom, what the gateway sits between, what is inside
and outside the trust boundary.*

### 1.x Why the arguments are the attack surface

A conventional application does not have this problem. A "Pay rent" button is
wired to stored values:

```
user clicks "Pay rent"  →  pay(stored_iban, stored_amount)
```

The IBAN comes from the database. No model decides anything, and no text the
user has received can change where the money goes. The flow is fixed, and a
fixed flow cannot be redirected.

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
stored value: the new amount only exists inside the document. Reading the
document is the task. The attacker writes in the same document.

The consequence is not a defect to be fixed:

| | Fixed flow (button) | Agent |
|---|---|---|
| Arguments come from | storage | model output |
| Can handle open-ended requests | no | yes |
| Can be redirected by content it reads | no | **yes** |

**Flexibility is the exposure.** If the flow is fixed, an agent is not needed;
the moment an agent is used, tool arguments become model output, and model
output is influenced by everything the model has read. This is why the agent is
placed on the untrusted side of the boundary, and why the monitor evaluates the
proposed arguments rather than the text that produced them.

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
  holds 7 transactions in total (`data/suites/banking/environment.yaml`), so the
  default returns the complete history. Asking for "recent" transactions reads
  everything that exists.

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

*To be written: what the attacker can do, what they cannot do, and what they
need in order to reach the agent at all.*

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
