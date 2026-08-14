---
name: hermes-agent-provider-switch
description: Diagnose why an AMG agent (Walter II, Don, Ralph, Stacey, etc.) is dead/unresponsive on an LLM-billing error, and switch it from OpenRouter to the ChatGPT-Team Codex OAuth provider. Use when an agent boots but can't reply, an ask-agent ping returns an HTTP 402 (out of credits) or 400 (unsupported model), or OpenRouter credits are exhausted. Covers the read_file API-key-masking landmine and how to discover the account's valid Codex model names.
triggers:
  - agent is down
  - agent not responding
  - walter is dead
  - out of credits
  - HTTP 402
  - openrouter out of credits
  - switch agent to openai
  - switch provider to codex
  - is walter up
---

# Hermes Agent Provider Switch (OpenRouter → Codex OAuth)

When an AMG agent (Walter II / base, or any profile: don-ready, ralph, email-agent,
autumn, etc.) **boots fine but can't reply**, it's almost always an LLM billing/model
error, NOT a crash. The fleet historically shares ONE OpenRouter key, so when that
balance dries up, multiple agents die at once.

## Step 0.5 — Identify WHICH profile is actually behind the user-facing bot (shared-token trap)
Don't assume the bot name shown in the chat UI (e.g. "Walter II") maps to the profile you
think. Multiple agent profiles can end up configured with the same platform bot
credential — only one process can hold a live connection at a time, so whichever
profile's gateway started first/last is the one actually serving that chat, regardless of
the bot's display name. To identify the real owner: compare each profile's configured
platform bot identifier for duplicates, list the running gateway processes per profile to
see which one is actually alive, and check that profile's state file for a "connected"
platform status. If you try to start the profile you *think* owns the bot and get an
error that the token is already in use by another PID, that PID belongs to the REAL
owner — go fix that profile, not the one you assumed. (Real case 2026-08-13: Joe's
"Walter II" Telegram chat was actually being served by the unrelated `number5` profile,
which had a duplicate/squatted bot token; the base Walter service was disabled and not
running at all.)

## Step 0 — Diagnose with a ping (don't guess)
```sh
timeout 100 ~/bin/ask-agent walter "Jay here, quick ping — are you up?"
```
Read the error in the output box:
- **HTTP 402 "requires more credits"** → OpenRouter balance exhausted. Switch to Codex (below).
- **HTTP 400 "model not supported … ChatGPT account"** → already on Codex but wrong model name (see Step 4).
- Process spins up tools/skills then errors = brain is reachable, only the API call failed.

## Step 1 — Confirm OpenRouter balance + auto-refill
Query OpenRouter's own balance endpoints (`GET /api/v1/credits` and `GET /api/v1/key`)
using the key already in `config.yaml`, via an authenticated request:
- `/credits` → `total_credits` vs `total_usage`; remaining = the difference. If remaining is
  a few dollars, a single big-model turn (65k max_tokens) won't fit → 402.
- `/key` → if `limit: null` / `limit_remaining: null`, there is **no auto-refill on the key**.
  Auto-refill is an ACCOUNT-level billing toggle, not visible/settable via this key
  (`is_management_key: false`). Tell Joe to check https://openrouter.ai/settings/credits.

## Step 2 — Verify the Codex OAuth credential is ALIVE
Hermes manages `openai-codex` OAuth in **`~/.hermes/auth.json`** (the base instance),
NOT `~/.codex/auth.json`. (For a profile agent, check that profile's auth.json.)
Decode `providers["openai-codex"].tokens`:
```sh
python3 - <<'PY'
import json,base64,datetime
d=json.load(open("/home/itadmin/.hermes/auth.json"))
print("providers:", list(d.get("providers",{}).keys()), "active:", d.get("active_provider"))
tok=d["providers"]["openai-codex"]["tokens"]
def dec(t):
    p=t.split(".")[1]; p+="="*(-len(p)%4); return json.loads(base64.urlsafe_b64decode(p))
c=dec(tok["access_token"]); now=datetime.datetime.utcnow().timestamp()
print("access exp:", datetime.datetime.utcfromtimestamp(c["exp"]).isoformat(),
      "VALID" if c["exp"]>now else "EXPIRED")
ic=dec(tok["id_token"]).get("https://api.openai.com/auth",{})
print("plan:", ic.get("chatgpt_plan_type"), "until", ic.get("chatgpt_subscription_active_until"))
PY
```
Hermes auto-refreshes the access_token on boot (recent `last_refresh`), so an expired
access_token is fine IF the refresh_token still works and the plan is active. Confirm
`chatgpt_plan_type` (e.g. `team`) and a future subscription end date.

## Step 3 — Discover the account's VALID Codex models (CRITICAL — don't guess)
ChatGPT-account Codex does NOT accept `gpt-5-codex` / `gpt-5-pro` / arbitrary names.
Query the account's real allowed list with the helper Hermes ships:
```sh
cd /home/itadmin/.hermes/hermes-agent
venv/bin/python - <<'PY'
import json
tok=json.load(open("/home/itadmin/.hermes/auth.json"))["providers"]["openai-codex"]["tokens"]["access_token"]
from hermes_cli.codex_models import get_codex_model_ids
print(get_codex_model_ids(access_token=tok))
PY
```
Pick the top model from the returned list (observed 2026-06-20: `gpt-5.5`, `gpt-5.4`,
`gpt-5.4-mini` — note: plain version names, NOT `-codex` suffixed).

## Step 4 — Edit config.yaml (BACK UP FIRST; watch the key-masking trap)
**Save a dated backup copy of the config file before making any edit.**
Then set the `model:` block to:
```yaml
model:
  default: gpt-5.5                                   # from Step 3
  provider: openai-codex
  base_url: https://chatgpt.com/backend-api/codex
providers:
  openai-codex:
    base_url: https://chatgpt.com/backend-api/codex
  openrouter:
    api_key: <REAL KEY — keep it untouched!>
    base_url: https://openrouter.ai/api/v1
fallback_providers:
- openrouter            # keep OpenRouter as emergency fallback once topped up
```

### ⚠️ THE LANDMINE: `read_file` and the `patch` tool MASK API keys
`read_file` displays the OpenRouter key masked (e.g. `sk-or-...XXXX`) even though the real
73-char key is on disk. If you build a `patch` old_string/new_string from that masked view,
the fuzzy matcher WRITES THE MASK BACK, destroying the real key and breaking the fallback.
AVOID the file-edit tools for any block containing the key. Edit with raw Python string
replacement on the `model:` block ONLY (leaves the key bytes untouched). If you already
clobbered it, recover the real key from the `.bak` file (raw Python read, no masking) and
write it back. Always finish by comparing the set of keys in the new file vs the backup to
confirm they match — and note there's usually a SECOND OpenRouter key in the summarizer/aux
block (~line 119) that must survive too.

## Step 5 — Verify with a real ping
```sh
timeout 150 ~/bin/ask-agent walter "Jay here, post-switch check — reply one short line."
```
A clean one-line reply = done. Billing on Codex is `subscription_included` (flat ChatGPT
Team seat), so no per-token OpenRouter cost.

## Step 0.5 — Identify WHICH profile is actually behind the user-facing bot (shared-token trap)
Don't assume the bot name shown in the chat UI (e.g. "Walter II") maps to the profile you
think. Multiple agent profiles can end up configured with the same platform bot
credential — only one process can hold a live connection at a time, so whichever
profile's gateway started first/last is the one actually serving that chat, regardless of
the bot's display name. To identify the real owner: compare each profile's configured
platform bot identifier for duplicates, list the running gateway processes per profile to
see which one is actually alive, and check that profile's state file for a "connected"
platform status. If you try to start the profile you *think* owns the bot and get an
error that the token is already in use by another PID, that PID belongs to the REAL
owner — go fix that profile, not the one you assumed. (Real case 2026-08-13: Joe's
"Walter II" Telegram chat was actually being served by the unrelated `number5` profile,
which had a duplicate/squatted bot token; the base Walter service was disabled and not
running at all.)

## Resolution note (2026-08-13 real case, current live state)
After finding `number5` squatting Walter's Telegram token, Joe's final call was NOT to
fix number5 in place — it was **disable number5 entirely** (`systemctl --user disable
--now hermes-gateway-number5.service`) and bring up the **real base Walter** service
instead (it already had valid Codex OAuth credentials — no provider switch was actually
needed once the real profile could hold the token). Only after stopping number5 could
Walter's gateway successfully bind the shared Telegram token (previously got "token
already in use" conflict). Lesson: when two profiles share one platform bot token, the
fix may be "stop the impostor and start the real one" rather than "repair the impostor's
provider" — confirm with the user which profile *should* own the bot before spending
time fixing the wrong one's credentials. Standing state: number5 stays disabled until
Joe says otherwise; it needs its own dedicated bot token before it can safely run
alongside Walter again.

## Alternative fix: switch a broken-Codex profile straight to Anthropic (no OAuth needed)
If Codex OAuth is missing entirely for a profile (no `openai-codex` entry in its auth
store at all — not just expired) and you don't want to run the interactive OAuth login
flow, pointing that profile's `model:`/`providers:` block at Anthropic API-key auth
instead is faster and needs no browser/OTP step, provided the profile already has a
working `ANTHROPIC_API_KEY` in its environment. Sanity-check that the key is valid with
one small test call to the provider's API before touching config — a successful response
confirms the key works and saves a wasted round-trip if it's dead. Edit only the
`model:`/`providers:` block; leave every other provider block (especially the fallback
`openrouter` block with its API key) completely untouched, then diff the pre-edit backup
against the new file to confirm nothing else moved. This path is lower-risk than the
OpenRouter-key-masking landmine below since the Anthropic block has no secret to mask,
but stay disciplined about not letting your edit boundary drift into the masked
`openrouter.api_key` line sitting right below it. NOTE: this is only the right fix when
the profile in question is the one that's SUPPOSED to own the user-facing bot — if it
turns out to be an impostor squatting another profile's token (see Step 0.5), the right
fix is usually to disable the impostor and start the real owner, not reconfigure the
impostor's provider (real case below).

## Verifying the fix actually took (don't trust startup logs alone)
Right after restarting the gateway, the agent log often shows a startup-time "fallback
activated" line pointing at the emergency fallback model. This is usually a
transient/turn-scoped auxiliary call (e.g. auto-detect for background summarization)
timing out on a cold connection — NOT the main chat path failing. Fallback activation is
per-turn and self-heals on the next request, so don't panic-diagnose off that one line.
The real proof is a live ping through the agent-to-agent bridge that comes back naming
the new model by name — that's confirmed-fixed; a generic/empty reply is not enough.

## Pitfalls recap
- Agent "down" is usually billing/model, not a crash — always ping to read the actual HTTP code.
- Codex OAuth lives in `~/.hermes/auth.json` (Hermes-managed), not `~/.codex/auth.json`.
- ChatGPT-account Codex rejects `gpt-5-codex`/`gpt-5-pro` — ALWAYS pull the allowed list via
  `get_codex_model_ids()`; the names are version-only (`gpt-5.5`).
- `read_file`/`patch` mask the API key — never round-trip the key through them; use raw Python IO.
- The whole fleet may share one OpenRouter key — if Walter died on 402, Don/Ralph/Stacey likely
  did too. Offer to apply the same switch to the others.
