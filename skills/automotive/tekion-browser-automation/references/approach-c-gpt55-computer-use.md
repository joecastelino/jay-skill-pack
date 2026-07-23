### Approach C: GPT-5.5 Computer Use (Vision + Playwright)

GPT-5.5 sees screenshots and returns pixel coordinates. Good for simple forms (login/OTP) but **unreliable for multi-level navigation**. Prefer Approach B (Puppeteer + selectors) for full workflows.

**⚠ CRITICAL LIMITATION: Cannot navigate past the Apps Dashboard.** The visual agent gets stuck after login — it can't reliably find "RO" in the left sidebar and transition to the main RO screen with dealer switcher. The tile-based dashboard layout looks too similar to the sidebar, and the model lacks state awareness.

**Where it works:** Login (username → password → OTP) — these are simple sequential forms with distinct visual states. GPT-5.5 tracks these well.

**Where it fails:** Multi-level navigation (Apps → RO → dealer switch → OM → search → edit). The model sees similar screenshots each turn and can't determine what phase it's in, leading to loops.

**How it works:**
1. Playwright takes a screenshot in headless Chrome
2. Screenshot sent to GPT-5.5 via OpenAI Responses API (`input_image`)
3. GPT-5.5 returns a single command: `CLICK:X,Y`, `TYPE:text`, `PRESS:key`, `SCROLL:direction`
4. Playwright executes the command
5. Repeat until task complete or `DONE`

**Key discoveries:**
- The `computer_use_preview` tool is NOT supported by GPT-5.5 — only by a dedicated `computer-use-preview` model (which requires special access)
- The `computer` tool type IS supported by GPT-5.5 but only returns text descriptions, not `computer_call` events
- **Workaround**: Ask GPT-5.5 to respond with machine-parseable format (`CLICK:X,Y`, `TYPE:text`, etc.) and execute with Playwright
- Codex CLI cannot be used for this — it's a coding agent, not a browser driver. Use the OpenAI SDK directly.

**Auth setup:**
- API key with credits on OpenAI platform (not ChatGPT auth — that only supports coding tasks)
- `pip install openai playwright` + `playwright install chromium`
- Use `chromium.launch(headless=True)` — no X server on this headless Linux system

**Script:** `/home/itadmin/tekion-cu.py` — the full computer use agent. Modifiable for any Tekion task.

**Command format reference:**
```
CLICK:1085,432   — click at exact pixel coordinates
TYPE:jcastelino@scvolkswagen.com  — type text
PRESS:Enter      — press a key (Enter, Tab, Escape, Backspace)
SCROLL:down      — scroll down 500px (or SCROLL:up)
WAIT             — wait 2 seconds
OTP              — signal that OTP code is needed (agent auto-fetches via fetch_otp.py)
DONE             — task complete
SCREENSHOT       — re-request visual (no-op, just refreshes screenshot)
```

**Running (IMPORTANT — use -u flag!):**
```bash
# ALWAYS use python3 -u for real-time output with Hermes background processes:
cd /home/itadmin && /home/itadmin/.hermes/hermes-agent/venv/bin/python3 -u tekion-cu.py > /tmp/tekion-cu-run.log 2>&1

# Monitor progress:
tail -f /tmp/tekion-cu-run.log
```
PYTHONUNBUFFERED=1 alone is NOT enough — stdout still buffers when piped. Use `-u` AND redirect to file.

**Must use Puppeteer Chrome, not Playwright's bundled headless shell.** Pass `executable_path` pointing to the Chrome binary at `/home/itadmin/.cache/puppeteer/chrome/linux-148.0.7778.97/chrome-linux64/chrome` with the same launch args as Approach B.

**Rate limiting:** GPT-5.5 returns empty strings when rate-limited (no error exception). Add retry with 3-second cooldown. Add `page.wait_for_timeout(1500)` between steps to avoid hitting limits.

**Previous-action context is essential:** Pass `YOUR PREVIOUS ACTION: {cmd} → {result}` in the prompt so GPT-5.5 knows what it just did and doesn't repeat the same click.

**When to use each approach:**
| Scenario | Approach |
|----------|----------|
| Quick inspection/debugging | A (Built-in browser) |
| High-volume scraping (100s of ROs) | B (Puppeteer scraper) |
| Full opcode update workflows | B (Puppeteer + selectors + direct URLs) |
| Login/OTP only (simple form) | C (GPT-5.5) |
| One-off fixes where selectors break | C (GPT-5.5) — but only for single-page interactions |

**Cost:** ~10K tokens per step with screenshot. A full login flow (10 steps) costs roughly $1 in API credits at GPT-5.5 pricing. Full workflow (>30 steps) not recommended due to navigation failures and rate limiting.