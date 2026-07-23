---
name: install-agent-bridge-into-peer
description: >
  Make ANOTHER AMG agent (e.g. Autumn, Don, Ralph) able to message Jay/peers
  DIRECTLY from their own sessions — not just be reachable BY Jay. Installs the
  ask-agent bridge helper + a MEMORY.md entry into the target agent's profile so
  the capability is discoverable in their real chats. Use when Joe says "set up
  a pipeline between <agent> and Jay" or "<agent> needs to talk to you".
triggers:
  - set up a pipeline with another agent
  - agent needs to talk to me
  - install bridge into another agent
trigger: agent pipeline, autumn talk to jay, bridge another agent, peer agent communication
---

# Install the Agent Bridge INTO a Peer Agent's Profile

The `agent-to-agent-bridge` skill lets JAY call other agents. But that only
makes Jay able to reach THEM. To make a peer agent (Autumn, Don, etc.) able to
reach Jay/others FROM THEIR OWN sessions with Joe, you must install the bridge
into the PEER's profile. This is a different, one-directional-each-way thing.

## The core lesson (why a passing handshake test LIES)

When Jay runs `ask-agent autumn "test the bridge: run ask-agent jay ..."`, it
works — but ONLY because Jay literally handed over the command. In the peer's
REAL sessions with Joe, nobody hands them that command, and most peer agents'
SOUL.md/persona says nothing about co-located agents. So they default to "I'd
have to EMAIL a person named Jay" and ask Joe to relay. The capability must be
**discoverable in their always-on context**, not buried in a skill they'd have
to know to load. → Put it in their `MEMORY.md` (injected every turn).

## Steps (proven 2026-06-17, target = autumn)

REAL home = `/home/itadmin`. Profiles live at `/home/itadmin/.hermes/profiles/<name>`.
Jay's bridge helper is profile-agnostic (hardcodes `REAL=/home/itadmin`), so the
SAME script works copied into any peer.

1. **Copy the helper into the peer's bin:**
   ```sh
   P=/home/itadmin/.hermes/profiles/<peer>
   mkdir -p $P/home/bin
   cp /home/itadmin/.hermes/profiles/jay/home/bin/ask-agent $P/home/bin/ask-agent
   chmod +x $P/home/bin/ask-agent
   ```

2. **Fix the PATH gotcha** — peer profiles often have EMPTY/no `.bashrc` PATH
   export, so the bare `ask-agent` won't resolve. Append:
   ```sh
   RC=$P/home/.bashrc; touch "$RC"
   grep -q 'HOME/bin' "$RC" || printf '\n# AMG agent bridge\nexport PATH="$HOME/bin:$PATH"\n' >> "$RC"
   ```
   Belt-and-suspenders; ALSO write the memory entry to use the FULL path so it
   works regardless of PATH.

3. **Write the capability into the peer's MEMORY.md** (the critical step). File:
   `$P/memories/MEMORY.md`. Prepend a section that states plainly: the other AMG
   agents are NOT people you email — they run on THIS machine; reach them with
   `~/bin/ask-agent <agent> "msg"` (full path fallback
   `/home/itadmin/.hermes/profiles/<peer>/home/bin/ask-agent`); list who's
   reachable (jay=Tekion/DMS data, walter=chief, ralph=recalls, don-ready=used
   cars, stacey=email, jeff=amazon, solo=pilot, dori); WARN each call is a FRESH
   one-shot session with NO memory of prior msgs → put ALL context in the single
   message; give a concrete ready-to-run example for their use case.

4. **Optionally install the `agent-to-agent-bridge` SKILL too** (copy
   `jay/skills/automotive/agent-to-agent-bridge/SKILL.md` into the peer's skills
   dir) — but MEMORY.md is what actually makes it work; the skill is backup.

## Verify the RIGHT way (no cheating)

Do NOT hand them the command. Talk to them like Joe would, zero hints:
```sh
timeout 200 ~/bin/ask-agent <peer> "It's Joe. Quick: is Jay reachable? Ping him
with a one-line hello and tell me exactly what he says back."
```
If they figure out the command themselves from memory and return Jay's reply,
the bridge is genuinely live. (Proven: this worked for Autumn after the memory
edit; before it, she punted to "give me Jay's email".)

## Pitfalls
- **Bridge calls TIME OUT for heavy tasks (exit 124).** When the peer asks Jay
  for a full Tekion SCRAPE, it nests a third cold agent + a slow scrape and
  blows the ~180s ask-agent timeout. The lightweight ping works instantly; a
  scrape-on-demand often times out. → For data the peer needs repeatedly,
  prefer a SCHEDULED FILE DROP (Jay writes JSON+CSV to a shared path on a cron;
  peer just reads the file instantly) over live scrape-on-demand. More reliable,
  no timeout, always-fresh-enough.
- Peer agents may run a non-frontier model (Autumn = DeepSeek v4-pro) — keep the
  memory instructions explicit and example-driven, don't assume inference.
- Each profile has its OWN memory char limit (default 2200). A big MEMORY.md
  entry may need trimming or a limit bump in that profile's config.yaml.
- Some peer data (declined services, customer lists) is PII — get Joe's explicit
  green-light before wiring a pipeline that hands customer contact info around.
