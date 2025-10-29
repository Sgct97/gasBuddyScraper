import imaplib
import email

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("scourvilletaylor@gmail.com", "evftbpaoruyooqgb")
mail.select("INBOX")

# Find GasBuddy emails and get their Message-IDs
status, messages = mail.search(None, "(FROM info@aiearlybird.com SUBJECT GasBuddy)")
email_ids = messages[0].split()
print(f"Found {len(email_ids)} GasBuddy emails")
print("=" * 80)

message_ids = []
for email_id in email_ids[-3:]:  # Check last 3
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            msg_id = msg.get("Message-ID", "")
            subject = msg.get("subject", "")
            print(f"\nGasBuddy Email:")
            print(f"  Subject: {subject}")
            print(f"  Message-ID: {msg_id}")
            if msg_id:
                message_ids.append(msg_id)

print("\n" + "=" * 80)
print("Now searching for REPLIES to these emails...")
print("=" * 80)

# Now search ALL emails for ones that reference these Message-IDs
status, all_messages = mail.search(None, "ALL")
all_email_ids = all_messages[0].split()

print(f"Checking {len(all_email_ids[-100:])} recent emails for replies...")

for email_id in all_email_ids[-100:]:  # Check last 100
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            
            in_reply_to = msg.get("In-Reply-To", "")
            references = msg.get("References", "")
            from_addr = msg.get("from", "")
            subject = msg.get("subject", "")
            
            # Check if this email references any of our GasBuddy messages
            for gasbuddy_msg_id in message_ids:
                if gasbuddy_msg_id and (gasbuddy_msg_id in in_reply_to or gasbuddy_msg_id in references):
                    print(f"\n⭐ FOUND REPLY!")
                    print(f"   From: {from_addr}")
                    print(f"   Subject: {subject}")
                    print(f"   In-Reply-To: {in_reply_to[:80]}")
                    
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
                            pass
                    
                    print(f"   Body: {body.strip()[:200]}")

mail.logout()

