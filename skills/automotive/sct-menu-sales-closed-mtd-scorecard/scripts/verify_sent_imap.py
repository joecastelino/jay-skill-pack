"""Direct-IMAP verification that a report email actually went out (\\Sent label + real attachment part).
Usage: python verify_sent_imap.py <since DD-Mon-YYYY> <subject fragment 1> [<fragment 2> ...]
Example: python verify_sent_imap.py 18-Sep-2026 "Closed MTD" "9/18/26"
Prints UID, X-GM-LABELS (need \\Sent — \\Draft alone means NOT sent), decoded subject/to/date,
RFC822.SIZE and the raw BODYSTRUCTURE (look for ("ATTACHMENT" ("FILENAME" "...pdf"))).
A live copy also lives at /home/itadmin/tekion-reports/verify_sent_imap.py.
"""
import re, sys, imaplib
from email import message_from_bytes
from email.header import decode_header, make_header

since = sys.argv[1]
frags = sys.argv[2:]
cfg = open("/home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml").read()
pw = re.search(r'raw\s*=\s*"([^"]+)"', cfg).group(1).replace(" ", "")
EMAIL = "jcastelino@americanmotorscorp.com"
m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
m.login(EMAIL, pw)
m.select('"[Gmail]/All Mail"', readonly=True)
typ, data = m.search(None, "SINCE", since)

def dec(v):
    try: return str(make_header(decode_header(v or "")))
    except Exception: return v or ""

hits = 0
for uid in data[0].split()[-60:]:
    typ, d = m.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE TO)] X-GM-LABELS)")
    hdr = b""; labels = b""
    for el in d:
        if isinstance(el, tuple):
            if b"X-GM-LABELS" in el[0]: labels = el[0]
            hdr += el[1]
        elif isinstance(el, bytes) and b"X-GM-LABELS" in el:
            labels = el
    msg = message_from_bytes(hdr)
    # Subject with em-dash arrives RFC2047-encoded (=?utf-8?...) — MUST decode before matching
    h = f"Subject: {dec(msg['Subject'])} | To: {dec(msg['To'])} | Date: {msg['Date']}"
    if all(f in h for f in frags):
        hits += 1
        lab = re.search(rb"X-GM-LABELS \(([^)]*)\)", labels)
        print("UID", uid.decode(), "| labels:", lab.group(1).decode() if lab else labels)
        print("  ", h)
        typ, bs = m.fetch(uid, "(RFC822.SIZE BODYSTRUCTURE)")
        s = b"".join(x if isinstance(x, bytes) else x[0] + x[1] for x in bs).decode("utf-8", "ignore")
        print("   RFC822.SIZE:", re.search(r"RFC822.SIZE (\d+)", s).group(1))
        print("   BODYSTRUCTURE:", s[:900])
        if "ATTACHMENT" not in s.upper():
            print("   !! NO ATTACHMENT DISPOSITION — markup-only?")
        print("---")
print("hits:", hits)
m.logout()
