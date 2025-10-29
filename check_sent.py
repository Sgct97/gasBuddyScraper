import imaplib
import email

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("scourvilletaylor@gmail.com", "evftbpaoruyooqgb")

# Select Sent Mail folder - need to encode properly
result = mail.select('"[Gmail]/Sent Mail"')
print(f"Select result: {result}")

if result[0] == "OK":
    print("✅ Successfully selected Sent Mail folder")
    
    # Search for emails TO info@aiearlybird.com
    status, messages = mail.search(None, "(TO info@aiearlybird.com)")
    
    if status == "OK" and messages[0]:
        email_ids = messages[0].split()
        print(f"\nFound {len(email_ids)} emails TO info@aiearlybird.com in Sent Mail")
        print("=" * 80)
        
        # Check ALL of them
        for i, email_id in enumerate(email_ids, 1):
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg.get("subject", "")
                    date = msg.get("date", "")
                    
                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except:
                            body = ""
                    
                    body_clean = body.strip()
                    
                    # Show all emails with body content
                    if body_clean:
                        print(f"\n{i}.")
                        print(f"   Date: {date}")
                        print(f"   Subject: {subject[:80]}")
                        print(f"   Body ({len(body_clean)} chars): {body_clean[:500]}")
                        
                        if "ok" in body_clean.lower() and len(body_clean) < 100:
                            print(f"   ⭐⭐⭐ THIS IS THE OK REPLY!")
    else:
        print("No emails found TO info@aiearlybird.com in Sent")
else:
    print("Failed to select Sent Mail folder")

mail.logout()

