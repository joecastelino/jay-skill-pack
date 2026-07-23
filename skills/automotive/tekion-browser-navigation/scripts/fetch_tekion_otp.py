#!/usr/bin/env python3
"""Fetch the latest Tekion-Login OTP from Gmail All Mail via IMAP."""

import imaplib
import email
import re
import sys
import time
from datetime import datetime

def get_otp(user="jcastelino@americanmotorscorp.com", password="<GMAIL_APP_PASSWORD>", timeout=40):
    """
    Poll for the 6-digit OTP from the most recent Tekion-Login email.
    
    Uses SINCE date filter to avoid scanning 130+ old OTP emails.
    Polls up to `timeout` seconds for a fresh OTP to arrive.
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(user, password)
    
    today = datetime.utcnow().strftime("%d-%b-%Y")
    
    for attempt in range(timeout // 5):
        mail.select('"[Gmail]/All Mail"')
        status, messages = mail.search(
            None, 
            f'(SUBJECT "Tekion-Login OTP" SINCE "{today}")'
        )
        ids = messages[0].split()
        
        if ids:
            # Get most recent
            mid = ids[-1]
            status, data = mail.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            
            # OTP is typically in text/html part, not text/plain
            for part in msg.walk():
                ct = part.get_content_type()
                payload = part.get_payload(decode=True)
                if ct in ("text/plain", "text/html") and payload:
                    body = payload.decode(errors="ignore")
                    codes = re.findall(r'\b(\d{6})\b', body)
                    if codes:
                        mail.logout()
                        return codes[0]  # first 6-digit match
            
            # If we got here, the latest email had no OTP code
            # (shouldn't happen — maybe it wasn't fully delivered yet)
            pass
        
        time.sleep(5)
    
    mail.logout()
    return None

if __name__ == "__main__":
    otp = get_otp()
    if otp:
        print(otp)
    else:
        print("NO_OTP_FOUND — click 'Resend' on Tekion and retry", file=sys.stderr)
        sys.exit(1)
