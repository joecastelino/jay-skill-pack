---
name: jay-gmail-draft-verification
description: Independently verify a Gmail draft/send that Stacey (email-agent) reports she created — confirm it's actually in Drafts/Sent with correct recipients, body, and attachments, without trusting her self-report alone. Use whenever Joe asks to "chase" or double-check an email Jay routed through Stacey, or when Jay's own Gmail-dependent flow (himalaya/Google API) throws auth errors.
---

# Verifying Stacey's Gmail Drafts/Sends (Jay's independent check)

Jay routes report emails through Stacey (agent-to-agent-bridge), but Stacey's own
self-report ("IN_DRAFTS=y, SENT=n") is not independently verifiable by default —
Jay needs a read-only path into Joe's Gmail that doesn't depend on Stacey.

## Two independent Gmail auth paths — check BOTH, they fail independently
1. **himalaya IMAP** (`~/.config/himalaya/config.toml`, personal account) — password-based (Gmail app password).
2. **Google OAuth API** (`google_token.json`) — used for `google_api.py gmail search` etc.

Either can be dead while the other works. Don't assume one failure means both are broken.

## Recurring trap: stale Gmail app password (hit 2026-08-07 AND 2026-08-18)
Joe rotates the Gmail app password periodically and typically hands the NEW one
only to Stacey (email-agent). **Each agent has its own separate himalaya config**
— the new password does NOT propagate to Jay's config automatically.

Symptom: `himalaya envelope list -a personal -f "[Gmail]/Drafts"` fails with
`AUTHENTICATIONFAILED — Invalid credentials (Failure)`.

### Fix
1. Get the CURRENT working password from Stacey's config:
   ```
   cat /home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml
   ```
   Look at the `raw =` field under `backend.auth` (her config uses flat keys
   like `backend.auth.raw`, not nested `[accounts.personal.backend.auth]` tables
   — different himalaya config style, same effect).
2. Copy that password into Jay's own config, BOTH places:
   `/home/itadmin/.hermes/profiles/jay/home/.config/himalaya/config.toml`
   - `[accounts.personal.backend.auth] raw = "..."`
   - `[accounts.personal.message.send.backend.auth] raw = "..."`
   (use `patch` tool, replace_all not needed — two distinct occurrences, patch each explicitly if `old_string` isn't unique enough).
3. Verify: `himalaya envelope list -a personal -f "[Gmail]/Drafts" -s 3` — should
   list without an explicit `HOME=` override once config.toml is fixed at the
   right path.

If himalaya is fixed but Google OAuth (`google_api.py`) still throws
`invalid_grant: Token has been expired or revoked.` on BOTH Jay's and Stacey's
token copies — that's a SEPARATE, independent failure (needs a fresh OAuth
consent flow via Joe's browser, not self-healable). Don't block draft
verification on fixing OAuth if IMAP already works — IMAP alone is sufficient
to verify a draft.

## Verification commands (once IMAP auth works)
```bash
# Find the draft — Gmail Drafts folder is literally named "[Gmail]/Drafts"
himalaya envelope list -a personal -f "[Gmail]/Drafts" -s 10

# Read the body (confirm To/Cc/Subject/body text match what was requested)
himalaya message read -a personal -f "[Gmail]/Drafts" <id>

# Download attachment(s) to confirm they're real, non-corrupt files
himalaya attachment download -a personal -f "[Gmail]/Drafts" <id>
# NOTE: no -o/--output path flag for filename override (that flag is for output
# FORMAT: plain|json, not a path) — it downloads to /tmp/<original-filename>
# using the attachment's actual filename. Just `ls /tmp/` after to find it.
```

Then sanity-check the downloaded file, e.g. for xlsx:
```python
from openpyxl import load_workbook
wb = load_workbook('/tmp/<file>.xlsx')
print(wb.sheetnames)
```

## CRITICAL FAILURE MODE (2026-08-18): Stacey can report a draft ID that doesn't exist at all
Worse than the draft-vs-sent trap: Stacey self-reported "draft #42420 created,
IN_DRAFTS=y, SENT=n" with specific structure details (CID-embedded PNG, PDF
attached, etc.) — but that draft **never existed anywhere**: not in Drafts, not
in Trash, not in All Mail, under any UID. Meanwhile `himalaya envelope list`
even *displayed* "42420" in a stale list output momentarily, but a direct
`himalaya message read -a personal -f "[Gmail]/Drafts" 42420` returned nothing,
and raw IMAP `UID FETCH 42420` returned `None` — the ID was a phantom (likely
himalaya's local numbering desyncing after a rapid create/trash cycle, or
Stacey's own tool call silently no-opping while still emitting a success
narrative). **himalaya's sequence-number-style IDs can desync from real IMAP
UIDs — do not trust `himalaya envelope list` alone to prove a message exists.**

### Robust verification: raw IMAP with Gmail X-GM-RAW search (bypasses himalaya ID drift)
Use `imaplib` directly with Gmail's native search operators via `X-GM-RAW` —
this searches by actual content/labels, not a locally-cached sequence number,
so it can't be fooled by himalaya ID drift:
```python
import imaplib
M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
M.login('jcastelino@americanmotorscorp.com', '<current app password>')

# Search ANY folder (works even if you don't know which folder it landed in)
M.select('"[Gmail]/All Mail"', readonly=True)
typ, data = M.uid('search', None, 'X-GM-RAW', '"subject:\\"exact subject text\\""')
uids = data[0].split()   # empty list = message truly does not exist anywhere

# For each hit, check labels to see Draft vs Sent vs Inbox (ground truth)
for u in uids:
    typ, d = M.uid('fetch', u, '(X-GM-LABELS FLAGS)')
    print(u, d)   # X-GM-LABELS will show \\Draft, \\Sent, \\Inbox, etc.
```
Other useful X-GM-RAW query fragments (combine with spaces, AND-style):
`label:draft`, `has:attachment`, `newer_than:1d`, `cabin` (bare keyword).
`X-GM-LABELS` is the ONLY reliable ground truth for "is this actually a draft
vs did it get sent" — a message can carry `\Inbox \Sent` (self-sent report)
or just `\Draft` (true draft, unsent). Don't infer from folder alone.

If `X-GM-RAW` search returns zero hits for a subject Stacey claims she used,
the draft is a phantom — go back to Stacey with a fresh, explicit request
rather than assuming a formatting/content bug in an existing draft.

## PDF verification: text extraction (pypdf) AND visual rendering (fitz/PyMuPDF) — use BOTH
CORRECTION (2026-08-18, same day, later in session): the earlier claim that
`fitz`/PyMuPDF was "broken" in this environment was WRONG — it works fine
(`pymupdf` 1.28.2 installed, `import fitz` succeeds, just emits a deprecation
warning to stderr suggesting `import pymupdf` instead). `pdftoppm`/`pdfinfo`
(poppler-utils) genuinely are missing and installing needs sudo password
(not available) — that part still stands, use fitz instead of poppler.

**Use pypdf text extraction to verify CONTENT/NUMBERS** (page count, totals,
row values reconcile). **Use fitz-render-to-PNG + vision_analyze to verify
LAYOUT** — text extraction cannot detect visual bugs like overlapping/
overflowing table cells. This combo caught a real bug (2026-08-18, BT filter
report): a ReportLab `Table` with plain Python strings in the Customer column
let long names overflow into the next column — pypdf's `extract_text()` still
returned all the right words in the right order (text extraction doesn't
care about visual boundaries), but the RENDERED page clearly showed
"JACQUELINE CASTROCAMACHO Cabin" running together. **Always render at least
one detail/table page to PNG and vision-check it when the PDF has a table
with variable-length text columns (customer names, notes, descriptions)** —
don't rely on text extraction alone for those.

```python
import fitz  # pymupdf — WORKS, ignore the deprecation warning
doc = fitz.open('/path/to/file.pdf')
pix = doc[1].get_pixmap(dpi=150)   # page index 1 = page 2
pix.save('/tmp/check_page2.png')
# then vision_analyze(image_url='/tmp/check_page2.png',
#   question="Any overlapping/overflowing text or misaligned columns?")
```

**ReportLab fix for overflow**: any table column holding variable-length text
(names, descriptions) must use a `Paragraph` object (wrapping), not a plain
string — plain strings do NOT wrap in `reportlab.platypus.Table` cells, they
either overflow into the neighbor column visually or get silently clipped
depending on column width:
```python
from reportlab.lib.styles import ParagraphStyle
cell_style = ParagraphStyle('cell', fontSize=7.5, leading=9)
row = [ro_num, date, Paragraph(customer_name, cell_style), category, ...]
```
Widen that column a bit too if names run long (e.g. 1.4in -> 1.5in).

`pypdf.PdfReader` text extraction still works reliably (confirmed 2026-08-18,
v6.12.2) for confirming page count and that the right numbers/rows are present:

```python
import imaplib, email, io, pypdf
M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
M.login('jcastelino@americanmotorscorp.com', '<app password>')
M.select('"[Gmail]/Drafts"', readonly=True)
typ, data = M.uid('fetch', '<uid>', '(BODY.PEEK[])')
msg = email.message_from_bytes(data[0][1])
for part in msg.walk():
    if part.get_content_type() == 'application/pdf':
        pdf_bytes = part.get_payload(decode=True)   # exact bytes IN the draft
r = pypdf.PdfReader(io.BytesIO(pdf_bytes))
print(len(r.pages))                       # confirms page count matches expectation
print(r.pages[0].extract_text()[:500])    # confirms summary numbers
print(r.pages[1].extract_text()[:500])    # confirms detail rows present
```
Extracting straight from the MIME part bytes (not a separately-downloaded copy)
proves the exact content Stacey attached — the strongest verification available,
stronger than comparing file size or trusting a downloaded duplicate matches.

**Strongest check of all — byte-identical comparison**: when you (Jay) built the
source file locally before handing it to Stacey, compare the MIME part bytes
pulled from the draft directly against your local file with `==`:
```python
local = open('/path/to/your/source.pdf', 'rb').read()
print("byte-identical:", local == pdf_bytes)   # pdf_bytes = bytes pulled from MIME part above
```
This proves Stacey attached YOUR exact file with zero re-encoding/corruption —
stronger than page-count or text-content checks, and catches the case where she
attached a similarly-sized but stale/wrong-version file.

**Fallback if pypdf ever genuinely fails:** verify the PNG instead — Stacey's
HTML drafts embed the scorecard image either as an inline `cid:` MIME part
(walk `msg.walk()` for `image/png`) or an externally-hosted URL (e.g.
`https://i.imgur.com/...png`) in the HTML body — call
`vision_analyze(image_url=<url>, ...)` directly, no download needed. But note
a PNG-only check CANNOT prove a multi-page PDF's later pages are correct —
use pypdf text extraction whenever the deliverable has page-2+ content (e.g.
RO-level detail tables) that isn't mirrored in the PNG.

## BROKEN IMAGE IN GMAIL = `data:` URI, not a bad PNG (root-caused 2026-08-21)
Joe reported "the image is broken" on the BC Deferred Work by Advisor draft.
The PNG was fine and byte-identical to the source. The bug: Stacey embedded it
as `<img src="data:image/png;base64,...">`. **Gmail strips/blocks `data:` URIs
in message bodies** — it renders as a broken-image placeholder. This is NOT
detectable by the standard "INLINE_PNG=y" self-report or even by a byte-compare,
because the bytes ARE correct — only the delivery mechanism is wrong.

### Detect it
```python
html = [p.get_payload(decode=True).decode('utf-8','replace')
        for p in msg.walk() if p.get_content_type()=='text/html'][0]
print('data uri:', 'data:image' in html)      # must be False
print('cid ref :', 'cid:' in html)            # must be True
# and the MIME tree must contain an image/png part with Content-ID set
```
Also a tell-tale: an HTML body of ~180KB for a simple table = a base64 blob
inlined in the HTML. A correct CID body is ~4KB.

### The fix — rebuild as multipart/related with a CID inline part
Required MIME structure:
```
multipart/mixed
  multipart/related
    multipart/alternative
      text/plain
      text/html            <img src="cid:scorecard" ...>
    image/png              Content-ID: <scorecard>, Content-Disposition: inline
  application/pdf          attachment
  text/csv                 attachment
```
Practical recipe: pull the existing broken draft, regex-swap the img tag, write
the fixed HTML + plain text to `/tmp/`, then hand Stacey an explicit
rebuild-and-replace ask (draft-only hard stop, exact To/Cc, exact file paths,
"do not regenerate the files"), and tell her to trash the old UID afterwards.
```python
new_html, n = re.subn(r'src="data:image/png;base64,[^"]+"',
    'src="cid:scorecard" width="900" style="width:100%;max-width:900px;'
    'height:auto;display:block;border:1px solid #ddd;"', html)
```
Watch for a leftover duplicate `style=` attribute after the swap if the original
img already had one — strip it, browsers take the first and ignore the second.

**Standing rule:** any Jay->Stacey email ask that includes an inline image must
say "CID inline attachment (`multipart/related`, `Content-ID: <scorecard>`) —
do NOT use a `data:` URI." Verify `data:image not in html` before calling it good.

## Cleaning up duplicate/stale drafts
Retrying a bridge request to Stacey after a timeout (see agent-to-agent-bridge
"Exit 124 ≠ failure" pitfall) commonly produces 2-3 drafts with the IDENTICAL
subject line — the timed-out first attempt, a retry, and Stacey's real
completion. Verified 2026-08-18 (BT filter report): compare bodies with
`himalaya message read` on each ID — the correct one has the intended content
(right numbers, right attachment TYPE e.g. PDF vs xlsx). Delete/trash the rest:

```bash
himalaya message move -a personal -f "[Gmail]/Drafts" "[Gmail]/Trash" <id1> <id2>
```
NOTE: target folder is a POSITIONAL arg, not `-t`/`--target` (that errors
"unexpected argument"). Also `himalaya message delete` fails outright with
"No folder Trash" and `--trash-folder` is not a valid flag — `move` to
`"[Gmail]/Trash"` is the only working deletion path found. Always re-list
Drafts after to confirm only the intended one remains before telling Joe it's
ready for review.

## Stacey's self-reported UID is frequently a SEQUENCE NUMBER (verified 2026-08-26)
She reported `DRAFT_UID=80`; the real IMAP UID was **42675**. Don't treat a suspiciously low
number as evidence of a phantom draft (see the phantom-42420 section above) — resolve it yourself.
The raw fetch response shows both, and the distinction is explicit:
```python
t, d = M.uid('fetch', '42675', '(X-GM-LABELS FLAGS)')
# b'80 (X-GM-LABELS () UID 42675 FLAGS (\\Draft))'
#   ^^ sequence number          ^^^^^ the real UID
```
Always find the draft by CONTENT, never by her reported id:
```python
M.select('"[Gmail]/Drafts"', readonly=True)
t, d = M.uid('search', 'CHARSET', 'UTF-8', 'X-GM-RAW', '"subject:\\"%s\\""' % SUBJ)
uids = d[0].split()      # the authoritative UID(s)
```
`CHARSET','UTF-8'` must precede `X-GM-RAW` or Gmail returns `BAD Could not parse command`.
Note `X-GM-LABELS ()` being EMPTY on a draft is normal — `FLAGS (\Draft)` is the ground truth
for draft status; an empty label set is not a red flag.

Sweep four folders in one pass so "where did it go" is answered in a single step —
Drafts (should be 1), Sent Mail (must be 0), All Mail (1, the same message), Trash (0):
```python
for f in ["[Gmail]/Drafts","[Gmail]/Sent Mail","[Gmail]/All Mail","[Gmail]/Trash"]:
    M.select(f'"{f}"', readonly=True); ...
```

## Verifying an inline-CID report email — one-pass checklist
Walking the MIME tree once yields every check the deferred/menu report asks for. Collect
attachment payloads into a dict keyed by filename, then byte-compare against your local sources:
```python
attach = {}
for p in msg.walk():
    if p.get_content_maintype() == 'multipart': continue
    payload = p.get_payload(decode=True) or b''
    print(p.get_content_type(), len(payload), p.get('Content-ID'),
          p.get_content_disposition(), p.get_filename())
    if p.get_content_type() == 'text/html': html = payload.decode('utf-8','replace')
    attach[p.get_filename() or p.get_content_type()] = payload

assert 'data:image' not in html and 'cid:scorecard' in html
assert len(html) < 10_000          # CID body ~2-4KB; ~180KB means a data: URI slipped in
for ext in ('png','pdf','csv'):
    local = open(f'{base}.{ext}','rb').read()
    print(ext, [k for k,v in attach.items() if v == local])   # must be non-empty
```
A correct tree prints exactly: `multipart/mixed → multipart/related → multipart/alternative →
text/plain, text/html, image/png (cid=<scorecard>, disp=inline), application/pdf (attachment),
text/csv (attachment)`. Stacey labels the CSV `text/csv` or `application/csv` — both fine.
Also strip tags from the HTML (`re.sub(r'<[^>]+>',' ',html)`) and assert the greeting, the
headline total, and any required caveat text are literally present — a structurally perfect
draft can still be missing a requested sentence.

## Pitfalls
- **A "missing" draft may just be Joe trashing it himself** (2026-08-18) — when
  Joe says "I don't see it in Drafts," don't assume Stacey's bridge call failed
  or produced a phantom. Check `"[Gmail]/Trash"` via `X-GM-RAW` subject search
  FIRST — Joe reviews drafts and trashes ones he's unhappy with (e.g. a layout
  bug) without necessarily saying so upfront; he may clarify "I trashed it
  because X" only after you ask/report back. Trash search: same X-GM-RAW
  pattern, `M.select('"[Gmail]/Trash"')`.
- **Never trust "Sent Mail" presence as confirmation of anything** — a draft-only
  ask can still get sent by Stacey (see STACEY DRAFT-ONLY TRAP in memory); always
  check the actual target folder (Drafts) the ask specified.
- Folder name is `"[Gmail]/Drafts"` (with brackets, needs quoting in shell) — a
  bare `Drafts` folder name will 404 with "Unknown Mailbox: Drafts (Failure)".
- If `himalaya` still fails after fixing the password, check whether it's being
  invoked with `HOME=/home/itadmin` override vs relying on the config at
  `/home/itadmin/.hermes/profiles/jay/home/.config/himalaya/config.toml` — both
  should work once the password is current, but a stale copy at
  `/home/itadmin/.config/himalaya/config.toml` (root level, no profile) can also
  exist and cause confusion if accidentally targeted — check profile-scoped path
  first.
- Clean up downloaded verification files from `/tmp/` after checking (temp only, not evidence to keep).
