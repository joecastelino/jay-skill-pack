---
name: jay-google-sheets-drive-access
description: Access Joe's Google Sheets and Drive files from Jay's profile — token symlink bootstrap, reading/writing native Sheets, downloading Drive-hosted .xlsx files (like AMG WIP.xlsx) via alt=media, and the xlsx-vs-native-Sheet write limitation. Established 2026-08-02.
---

# Jay → Joe's Google Sheets / Drive Access

## When to use
Joe asks to read or update any Google Sheet or Drive spreadsheet (AMG WIP, Advisor Performance Report, TECH EFF REPORT, recall calendars, etc.), or a report pipeline should push data into a sheet.

## Auth bootstrap (already done, re-do only if broken)
Jay's profile has NO Google token of its own. The FLEET-SHARED token (Joe's account, authorized via Walter/base) lives at `/home/itadmin/.hermes/google_token.json` with scopes: **spreadsheets (read/WRITE)**, drive.readonly, gmail.modify/send, calendar, contacts.readonly, documents.readonly.

Fix applied 2026-08-02:
```bash
ln -sf /home/itadmin/.hermes/google_token.json /home/itadmin/.hermes/profiles/jay/google_token.json
python3 /home/itadmin/.hermes/profiles/jay/skills/productivity/google-workspace/scripts/setup.py --check
# → AUTHENTICATED
```
- Do NOT run a new OAuth flow — reuse the shared token. Stacey has her own at profiles/email-agent/.
- PITFALL: the symlink lives under the jay profile dir (persistent), not `~` (wiped daily). If `--check` ever says NOT_AUTHENTICATED, just re-create the symlink.
- Alt without symlink: prefix commands with `HERMES_HOME=/home/itadmin/.hermes`.

## CLI usage (google-workspace skill wrapper)
```bash
GAPI="python3 /home/itadmin/.hermes/profiles/jay/skills/productivity/google-workspace/scripts/google_api.py"
# Find spreadsheets (Drive query syntax, --raw-query for operators)
$GAPI drive search "name contains 'WIP'" --raw-query --max 10
$GAPI drive search "mimeType='application/vnd.google-apps.spreadsheet'" --raw-query --max 10
# Read / write / append a NATIVE Google Sheet
$GAPI sheets get SHEET_ID "Tab!A1:D10"
$GAPI sheets update SHEET_ID "Tab!A1:B2" --values '[["a","b"],["c","d"]]'
$GAPI sheets append SHEET_ID "Tab!A:C" --values '[["new","row","data"]]'
```

## CRITICAL: .xlsx in Drive ≠ native Google Sheet
Many of Joe's files (incl. AMG WIP.xlsx) are **uploaded .xlsx**, mimeType `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`. The **Sheets API cannot read or write these** — sheets get/update fail. Options:
- **Read**: download the binary via Drive `alt=media`, parse with openpyxl (works, verified):
```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import urllib.request
creds = Credentials.from_authorized_user_file("/home/itadmin/.hermes/google_token.json")
if not creds.valid: creds.refresh(Request())
fid = "FILE_ID"
req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media",
    headers={"Authorization": f"Bearer {creds.token}"})
open("/home/itadmin/amg-wip/out.xlsx","wb").write(urllib.request.urlopen(req).read())
```
- **Write**: either PATCH-upload the whole modified xlsx back (Drive files.update media upload — note token scope is drive.READONLY, so uploads need a scope bump/re-auth), or have Joe convert the file to a native Sheet once (File > Save as Google Sheets) — then full sheets update/append works. State this trade-off to Joe before promising writes to an xlsx.

## Known file IDs (Joe's Drive)
| File | ID | Type |
|---|---|---|
| AMG WIP.xlsx (8 store tabs, monthly fixed-ops tracker) | `1esCOBSklptjeR3We9dKG6rcaDEfii6aJ` | xlsx (read via alt=media) |
| Advisor Performance Report 2026 | `1GkmvTdpJ2KwVe1dQi0CDuyHutUHp2_YHb7kW3nPy4Ak` | native Sheet |
| TECH EFF REPORT 2026 | `1pGZikiOeQXg1qXBdegde2gMimWlULznZWVxJSKS60KI` | native Sheet |
| EOM WIP | `1yKUxOLIQwMV-o8HVEA1KNCyez4BMtkft2xati0HbaM4` | native Sheet |

## AMG WIP.xlsx structure (verified live 2026-08-02)
- 8 tabs: Stevens Creek Toyota, Stevens Creek Volkswagen, Toyota of Fresno (=BT service), Blackstone Body Shop (=BT body), Volkswagen of Clovis, Fresno GM (=BC), Toyota of Lancaster, Alfa Romeo of San Jose. (Fresno-name trap: see AMG WIP memory entry.)
- Row 1 = month datetime headers (one col/month, dated the 26th, Sep2022→current). Find last populated month col by scanning row 1 for datetime. Joe confirmed 2026-08-03: the 26th is cosmetic — each column covers the CALENDAR month (1st→EOM). A "new" month col that is an exact cell-for-cell copy of the prior col = NOT yet filled. Filling method = skill `amg-wip-monthly-column-fill`.
- Col A row labels: Hours Sold (CUSTOMER/TXM/TOYOTA CARE/PREPAID/WARRANTY/PDI/INTERNAL), VEHICLE ATTENDANCE (TOYOTA/OTHERS), WORKSHOP ANALYSIS (TOTAL AVAIL/PROD HOURS/UNAPPLIED), LABOR RATES, WIP ($), ELR by pay type.
- Load with `openpyxl.load_workbook(path, data_only=True)`; read_only=True reports dims as None — use the normal loader.
- Local snapshots: /home/itadmin/amg-wip/ (AMG-WIP.xlsx older copy, AMG-WIP-live.xlsx fresh pull).

## Pitfalls
- Jay's `~` is wiped daily — save downloads under /home/itadmin/, never ~.
- Two different "WIP" workbooks exist: this monthly tracker vs the semi-monthly payroll workbook (skill amg-wip-payroll-vs-rth-analysis). Confirm which one Joe means.
- Never send email or mutate Joe's sheets destructively without showing him first; appends/new-column fills for agreed pipelines are fine.
