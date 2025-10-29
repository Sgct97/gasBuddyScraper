import imaplib
import email

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("scourvilletaylor@gmail.com", "evftbpaoruyooqgb")
mail.select("INBOX")

# Find emails FROM info@aiearlybird.com about GasBuddy
status, messages = mail.search(None, "(FROM info@aiearlybird.com SUBJECT GasBuddy)")
email_ids = messages[0].split()
print(f"Found {len(email_ids)} GasBuddy emails from info@aiearlybird.com")
print("=" * 80)

# Check the LAST 5 (most recent)
for i, email_id in enumerate(email_ids[-5:], 1):
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject = str(msg.get("subject", ""))
            from_addr = str(msg.get("from", ""))
            
            print(f"\n{i}. Email ID: {email_id}")
            print(f"   From: {from_addr}")
            print(f"   Subject: {subject}")
            
            # Parse ALL parts (this includes threaded replies in Gmail)
            print(f"   Multipart: {msg.is_multipart()}")
            
            part_count = 0
            for part in msg.walk():
                content_type = part.get_content_type()
                part_count += 1
                
                print(f"   Part {part_count}: {content_type}")
                
                if content_type in ["text/plain", "text/html"]:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            payload_str = payload.decode("utf-8", errors="ignore")
                            payload_clean = payload_str.strip()
                            
                            print(f"      Length: {len(payload_clean)} chars")
                            print(f"      Preview: {payload_clean[:300]}")
                            
                            # Check if this looks like a short reply with OK
                            if "ok" in payload_clean.lower() and len(payload_clean) < 100:
                                print(f"      ⭐ POSSIBLE OK REPLY!")
                    except Exception as e:
                        print(f"      Error: {e}")

mail.logout()

