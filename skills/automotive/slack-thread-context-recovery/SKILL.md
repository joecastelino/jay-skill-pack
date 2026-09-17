---
name: slack-thread-context-recovery
description: Recover what a context-free Slack message is referring to when the Hermes session that held the thread has already expired (e.g. Joe replies "so does this work now?" days later in an old thread). Reads Jay's own raw session JSON on disk to rebuild the thread's history instead of guessing or asking Joe to repeat himself.
triggers:
  - does this work now
  - any short reply in an old slack thread with no quoted context
  - thread message with no prior messages in the session
  - what were we working on in this thread
  - session expired / context lost
---

# Recovering context for a bare Slack thread message

Joe replies in threads days later with one-liners ("so does this work now?", "this
isn't what I wanted"). New sessions start empty, so the referent is gone. **Do not
guess and do not ask him to repeat** — his own thread history is on disk.

## Recipe

1. **The thread id is in your own system prompt** as `slack:<CHANNEL>:<TS>`.
   `TS` is the epoch (float) of the thread's *parent* message — decode it to know
   when/where the thread started:
   ```python
   import datetime; datetime.datetime.fromtimestamp(1789142143)  # -> 2026-09-11 08:55
   ```
   A TS that's days old = the question is about work from that date.

2. **Find the sessions belonging to that thread** — grep the PROFILE sessions dir
   (not `/home/itadmin/.hermes/sessions/`, which holds other profiles/cron):
   ```python
   import glob, os
   pat = '1789142143'
   for f in glob.glob('/home/itadmin/.hermes/profiles/jay/sessions/*.json*'):
       if pat in open(f, errors='ignore').read():
           print(os.path.getmtime(f), f)
   ```
   Sort by mtime; the newest is likely the CURRENT session (skip it), the rest are
   the thread's earlier sessions. Sibling `.jsonl` files are duplicates.

3. **Read the tail of each older session** — sessions are
   `{"session_id":..., "messages":[{"role":..., "content":...}, ...]}`. Print the
   last ~14 messages with content truncated to ~800 chars, flattening list-content:
   ```python
   d = json.load(open(f)); ms = d['messages']
   for m in ms[-14:]:
       c = m.get('content')
       if isinstance(c, list): c = ' '.join(str(x.get('text', x)) for x in c)
       print('---', m.get('role'), '---'); print((c or '')[:800])
   ```
   Tool-result messages are huge — truncate hard, you only need the narrative.

4. **Find the LAST deliverable + the last thing Joe said** about it, then verify
   that artifact on disk (files persist under `/home/itadmin/<project>/`, unaffected
   by the 3AM profile reset). Answer with the verified state, not a re-summary.

`session_search(query=...)` is the cheaper first pass (it returns LLM summaries with
dates) — run it in parallel with step 1. But its summaries truncate and can miss the
final turns, so fall back to reading the raw session JSON when the answer hinges on
the very last exchange.

## Pitfalls
- Do NOT assume the most recent session is the right one — several threads run in
  parallel (cron, other stores). Match on the **thread id**, not on recency.
- The near-term `session_search` summary may describe a DIFFERENT ticket that merely
  shares a keyword (e.g. a search for `1985592`/"Partially Invoiced" returned three
  unrelated sessions). Confirm the thread TS maps to the session before acting.
- After recovering context, **verify the deliverable still exists and is valid** —
  a week-old claim ("it's in your inbox") is not evidence. Re-check the file and the
  Gmail thread (see `jay-gmail-draft-verification`).
- If two plausible referents remain after recovery, answer the concrete one with
  evidence and add one line: "if 'this' meant something else, tell me what you were
  testing." One line, not a question-only reply.
