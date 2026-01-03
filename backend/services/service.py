import os, re, smtplib, imaplib, email, json, requests, pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from itertools import cycle
import google.generativeai as genai
from datetime import datetime
from config import app_state
import time
from itertools import cycle
from utils.helpers import (
    extract_name_from_email,
    extract_phone_number,
    extract_company_from_email,
    save_to_excel,
    save_sent_email,
    replace_name_placeholders,
    is_auto_response,
    is_valid_phone_number
)

# Import shared config - ONLY import what you need
from config import (
    ZOHO_CLIENT_ID,
    ZOHO_CLIENT_SECRET,
    ZOHO_REDIRECT_URI,
    ZOHO_API_DOMAIN,
    ZOHO_ACCESS_TOKEN,
    ZOHO_REFRESH_TOKEN,
    app_state  # Import the shared state object
)

# Zoho API functions
def get_zoho_auth_url(user_id="default_user", base_url=None):
    """Generate Zoho OAuth authorization URL with proper scopes using user credentials"""
    user_creds = app_state.user_zoho_credentials.get(user_id)
    
    if not user_creds:
        print(f"No credentials found for user: {user_id}")
        return None
    
    # Use provided base URL or default to user's redirect_uri
    if base_url and user_creds.get('redirect_uri'):
        # Extract path from existing redirect_uri and combine with new base URL
        from urllib.parse import urlparse
        existing_uri = user_creds['redirect_uri']
        path = urlparse(existing_uri).path
        redirect_uri = base_url + path
    else:
        redirect_uri = user_creds.get('redirect_uri', '')
    
    scopes = [
        "ZohoCRM.modules.ALL",
        "ZohoCRM.settings.ALL",
        "ZohoCRM.users.READ"
    ]
    scope_param = ",".join(scopes)
    
    # Include user_id as state parameter
    auth_url = f"https://accounts.zoho.in/oauth/v2/auth?scope={scope_param}&client_id={user_creds['client_id']}&response_type=code&access_type=offline&redirect_uri={redirect_uri}&state={user_id}"
    
    print(f"Generated auth URL for user: {user_id}")
    print(f"Redirect URI: {redirect_uri}")
    
    return auth_url

def get_zoho_tokens(auth_code, user_id="default_user"):
    """Exchange authorization code for access and refresh tokens using user credentials"""
    user_creds = app_state.user_zoho_credentials.get(user_id)
    if not user_creds:
        print(f"[Zoho Tokens] No user credentials found for {user_id}")
        return False

    token_url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        'grant_type': 'authorization_code',
        'client_id': user_creds['client_id'],
        'client_secret': user_creds['client_secret'],
        'redirect_uri': user_creds['redirect_uri'],
        'code': auth_code
    }

    try:
        response = requests.post(token_url, data=data)
        # 🔥 Debug line: print Zoho's actual response
        print(f"Zoho token response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')

            if not access_token:
                print("No access_token in response")
                return False

            # ✅ Save tokens into user credentials
            user_creds['access_token'] = access_token
            if refresh_token:
                user_creds['refresh_token'] = refresh_token
            app_state.user_zoho_credentials[user_id] = user_creds

            # ✅ Update global access token
            global ZOHO_ACCESS_TOKEN
            ZOHO_ACCESS_TOKEN = access_token

            app_state.zoho_status = {
                "connected": True,
                "message": "Zoho CRM connected successfully!"
            }

            print(f"[Zoho Tokens] Tokens stored for {user_id}")
            return True
        else:
            print(f"[Zoho Tokens] Failed to get token: {response.status_code}")
            return False

    except Exception as e:
        print(f"Exception getting tokens: {e}")
        return False


def refresh_zoho_tokens(user_id="default_user"):
    """Refresh Zoho access token using refresh token with user credentials"""
    user_creds = app_state.user_zoho_credentials.get(user_id)
    
    if not user_creds or not user_creds.get('refresh_token'):
        app_state.zoho_status = {"connected": False, "message": "No refresh token available. Please reconnect to Zoho CRM."}
        return False
        
    token_url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        'grant_type': 'refresh_token',
        'client_id': user_creds['client_id'],
        'client_secret': user_creds['client_secret'],
        'refresh_token': user_creds['refresh_token']
    }
    
    try:
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            user_creds['access_token'] = tokens.get('access_token')
            # Update the global access token
            global ZOHO_ACCESS_TOKEN
            ZOHO_ACCESS_TOKEN = user_creds['access_token']
            app_state.zoho_status = {"connected": True, "message": "Zoho CRM reconnected successfully!"}
            return True
        else:
            print(f"Error refreshing tokens: {response.status_code} - {response.text}")
            app_state.zoho_status = {"connected": False, "message": f"Token refresh failed: {response.text}"}
            return False
    except Exception as e:
        print(f"Exception refreshing tokens: {e}")
        app_state.zoho_status = {"connected": False, "message": f"Token refresh error: {e}"}
        return False
    
def get_zoho_field_mapping(user_id="default_user"):
    """Get a mapping of standard field names to actual Zoho API field names"""
    global ZOHO_ACCESS_TOKEN
    
    user_creds = app_state.user_zoho_credentials.get(user_id)
    if not user_creds or not user_creds.get('access_token'):
        return None
    
    access_token = user_creds['access_token']
    url = f"{ZOHO_API_DOMAIN}/crm/v2/settings/fields"
    params = {"module": "Leads"}
    
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            fields_data = response.json()
            
            # Create a mapping of common field names to actual API names
            field_mapping = {}
            
            # Standard field mappings that we'll try to match
            standard_fields = {
                'First_Name': ['First_Name', 'First Name', 'FirstName', 'First_Name'],
                'Last_Name': ['Last_Name', 'Last Name', 'LastName', 'Last_Name'],
                'Email': ['Email', 'Email_ID', 'EmailID', 'Email_Address'],
                'Phone': ['Phone', 'Phone_Number', 'Mobile', 'Phone_No', 'PhoneNumber'],
                'Company': ['Company', 'Company_Name', 'Account_Name', 'Organization'],
                'Lead_Source': ['Lead_Source', 'Source', 'LeadSource'],
                'Description': ['Description', 'Message', 'Body', 'Notes']
            }
            
            # Find the best matches for each standard field
            for standard_field, possible_names in standard_fields.items():
                for field in fields_data.get('fields', []):
                    api_name = field.get('api_name', '')
                    field_label = field.get('field_label', '')
                    
                    # Check if this field matches any of our possible names
                    if (api_name in possible_names or 
                        field_label in possible_names or
                        any(name.lower() in api_name.lower() for name in possible_names) or
                        any(name.lower() in field_label.lower() for name in possible_names)):
                        
                        field_mapping[standard_field] = api_name
                        break
            
            # Store the mapping for this user
            if 'user_field_mappings' not in app_state.__dict__:
                app_state.user_field_mappings = {}
            app_state.user_field_mappings[user_id] = field_mapping
            
            return field_mapping
        else:
            print(f"Error getting fields: {response.text}")
            return None
    except Exception as e:
        print(f"Exception getting field mapping: {e}")
        return None

def create_zoho_lead_with_mapping(lead_data, user_id="default_user"):
    """Create a lead using the field mapping for this user"""
    # Get or create field mapping
    if (not hasattr(app_state, 'user_field_mappings') or 
        user_id not in app_state.user_field_mappings):
        field_mapping = get_zoho_field_mapping(user_id)
    else:
        field_mapping = app_state.user_field_mappings.get(user_id, {})
    
    # If we couldn't get a mapping, use default field names
    if not field_mapping:
        field_mapping = {
            'First_Name': 'First_Name',
            'Last_Name': 'Last_Name',
            'Email': 'Email',
            'Phone': 'Phone',
            'Company': 'Company',
            'Lead_Source': 'Lead_Source',
            'Description': 'Description'
        }
    
    # Prepare data using the field mapping
    first_name = lead_data.get("first_name", "").strip()
    last_name = lead_data.get("last_name", "").strip()
    
    if not last_name:
        last_name = "Unknown"
    
    mapped_data = {}
    if first_name and 'First_Name' in field_mapping:
        mapped_data[field_mapping['First_Name']] = first_name
    if last_name and 'Last_Name' in field_mapping:
        mapped_data[field_mapping['Last_Name']] = last_name
    if lead_data.get("email") and 'Email' in field_mapping:
        mapped_data[field_mapping['Email']] = lead_data.get("email")
    
    # Only add phone if it's a valid phone number
    phone_number = lead_data.get("phone", "")
    if phone_number and is_valid_phone_number(phone_number) and 'Phone' in field_mapping:
        mapped_data[field_mapping['Phone']] = phone_number
    
    if lead_data.get("company") and 'Company' in field_mapping:
        mapped_data[field_mapping['Company']] = lead_data.get("company")
    if 'Lead_Source' in field_mapping:
        mapped_data[field_mapping['Lead_Source']] = "Email Reply"
    if lead_data.get("body") and 'Description' in field_mapping:
        mapped_data[field_mapping['Description']] = lead_data.get("body", "No message content")[:32000]
    
    # Create the lead with mapped data
    return create_zoho_lead_with_data(mapped_data, user_id)

def create_zoho_lead_with_data(mapped_data, user_id="default_user"):
    """Create a lead with the provided mapped data"""
    global ZOHO_ACCESS_TOKEN
    
    user_creds = app_state.user_zoho_credentials.get(user_id)
    if not user_creds or not user_creds.get('access_token'):
        app_state.zoho_status = {"connected": False, "message": "Not connected to Zoho CRM"}
        return False
    
    access_token = user_creds['access_token']
    ZOHO_ACCESS_TOKEN = access_token

    url = f"{ZOHO_API_DOMAIN}/crm/v2/Leads"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }

    data = {"data": [mapped_data]}

    print(f"Creating lead with mapped data: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Zoho API Response: {response.status_code} - {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            return result['data'][0]['details']['id']
        elif response.status_code == 401:
            # Token expired, try to refresh
            print("Token expired, attempting to refresh...")
            if refresh_zoho_tokens(user_id):
                # Get the new access token
                new_access_token = app_state.user_zoho_credentials[user_id].get('access_token')
                headers['Authorization'] = f'Zoho-oauthtoken {new_access_token}'
                ZOHO_ACCESS_TOKEN = new_access_token
                
                # Retry the request
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 201:
                    result = response.json()
                    return result['data'][0]['details']['id']
                else:
                    print(f"Retry failed: {response.status_code} - {response.text}")
                    return False
            else:
                print("Token refresh failed")
                return False
        else:
            print(f"API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception creating lead: {e}")
        return False

# Replace the existing create_zoho_lead function in service.py
def create_zoho_lead(lead_data, user_id="default_user"):
    """Create a lead in Zoho CRM with field mapping"""
    return create_zoho_lead_with_mapping(lead_data, user_id)

def generate_email_content(prompt):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"""
        Create professional email content based on this specific user request: {prompt}
        
        IMPORTANT: 
        - Use ONLY plain text format
        - Do NOT use any markdown formatting like **bold**, *italic*, or any special characters
        - Make the content relevant and tailored to the user's specific request
        
        Please provide the response in this exact format:
        
        SUBJECT: [email subject here]
        SENDER_NAME: [sender name here]
        BODY: [email body here]
        """)

        lines = response.text.strip().split('\n')
        result = {"subject": "", "body": "", "sender_name": ""}
        body_lines = []
        is_body = False

        for line in lines:
            if line.startswith("SUBJECT:"):
                result["subject"] = line.replace("SUBJECT:", "").strip()
            elif line.startswith("SENDER_NAME:"):
                result["sender_name"] = line.replace("SENDER_NAME:", "").strip()
            elif line.startswith("BODY:"):
                is_body = True
                body_lines.append(line.replace("BODY:", "").strip())
            elif is_body:
                body_lines.append(line.strip())

        result["body"] = "\n".join(body_lines).strip()
        
        # Clean any remaining markdown formatting from all fields
        result["subject"] = clean_markdown(result["subject"])
        result["sender_name"] = clean_markdown(result["sender_name"])
        result["body"] = clean_markdown(result["body"])
        
        return result

    except Exception as e:
        return {"error": str(e)}

def clean_markdown(text):
    """Remove all markdown formatting from text"""
    if not text:
        return text
    
    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Remove italic: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Remove strikethrough: ~~text~~
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # Remove code blocks: `text` or ```text```
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```.*?\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
    
    # Remove headers: # Header, ## Header, etc.
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove links: [text](url)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove blockquotes: > text
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    
    # Remove lists: - item, * item, 1. item
    text = re.sub(r'^[\s]*[-*•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s*', '', text, flags=re.MULTILINE)
    
    return text.strip()

def send_bulk_emails_with_templates(recipients, batch_size, sender_accounts, template_data=None):
    """Send bulk emails with position-based templates"""
    # Use app_state instead of global progress
    app_state.progress["total"] = len(recipients)
    app_state.progress["sent"] = 0
    app_state.progress["status"] = "running"

    sender_cycle = cycle(sender_accounts)
    start = 0

    while start < len(recipients):
        batch = recipients[start:start + batch_size]
        sender_email, password = next(sender_cycle)

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)

                for recipient in batch:
                    name = recipient.get("name", "") or extract_name_from_email(recipient["email"])[0] or "there"
                    
                    # Get the appropriate template
                    if template_data and template_data['templates']:
                        position = recipient.get("position", "").lower()
                        template = template_data['templates'].get(position, template_data['default_template'])
                        
                        if template:
                            subject = template['subject']
                            body = template['body']
                            sender_name = template.get('sender_name', app_state.email_content.get('sender_name', ''))
                        else:
                            # Fallback to default email content
                            subject = app_state.email_content.get("subject", "")
                            body = app_state.email_content.get("body", "")
                            sender_name = app_state.email_content.get("sender_name", "")
                    else:
                        # Use regular email content
                        subject = app_state.email_content.get("subject", "")
                        body = app_state.email_content.get("body", "")
                        sender_name = app_state.email_content.get("sender_name", "")

                    # Personalize content
                    personalized_body = replace_name_placeholders(body, name)
                    personalized_subject = replace_name_placeholders(subject, name)

                    msg = MIMEMultipart()
                    msg['From'] = f"{sender_name} <{sender_email}>"
                    msg['To'] = recipient["email"]
                    msg['Subject'] = personalized_subject
                    msg.attach(MIMEText(personalized_body, 'plain'))
                    server.send_message(msg)

                    # Extract first and last name from the name
                    first_name, last_name = extract_name_from_email(recipient["email"])
                    
                    # Save sent email to separate file
                    save_sent_email({
                        "timestamp": datetime.now().isoformat(),
                        "sender_email": sender_email,
                        "recipient_email": recipient["email"],
                        "subject": personalized_subject,
                        "body": personalized_body,
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": extract_company_from_email(recipient["email"]),
                        "phone": "",
                        "position": recipient.get("position", ""),
                        "template_used": recipient.get("position", "default") if template_data else "standard"
                    })

                    app_state.progress["sent"] += 1
        except Exception as e:
            app_state.progress["status"] = f"error: {e}"
            return

        start += batch_size

    app_state.progress["status"] = "completed"

def send_bulk_emails(recipients, batch_size, sender_accounts, subject, body, sender_name):
    """Original function for sending bulk emails without templates"""
    # Use app_state instead of global progress
    app_state.progress["total"] = len(recipients)
    app_state.progress["sent"] = 0
    app_state.progress["status"] = "running"

    sender_cycle = cycle(sender_accounts)
    start = 0

    while start < len(recipients):
        batch = recipients[start:start + batch_size]
        # FIX: Get the full account object instead of just email and password
        sender_account = next(sender_cycle)
        sender_email = sender_account['email']
        password = sender_account['password']
        account_sender_name = sender_account.get('sender_name', '')

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)

                for recipient in batch:
                    name = recipient.get("name", "") or extract_name_from_email(recipient["email"])[0] or "there"

                    personalized_body = replace_name_placeholders(body, name)
                    personalized_subject = replace_name_placeholders(subject, name)

                    msg = MIMEMultipart()
                    # Use account sender name if available, otherwise use the provided sender_name
                    display_sender_name = account_sender_name or sender_name
                    msg['From'] = f"{display_sender_name} <{sender_email}>"
                    msg['To'] = recipient["email"]
                    msg['Subject'] = personalized_subject
                    msg.attach(MIMEText(personalized_body, 'plain'))
                    
                    try:
                        server.send_message(msg)
                        print(f"Sent email to {recipient['email']}")
                    except Exception as e:
                        print(f"Failed to send email to {recipient['email']}: {e}")
                        app_state.progress["sent"] += 1
                        continue

                    # Extract first and last name from the name
                    first_name, last_name = extract_name_from_email(recipient["email"])
                    
                    # Save sent email to separate file
                    save_sent_email({
                        "timestamp": datetime.now().isoformat(),
                        "sender_email": sender_email,
                        "sender_name": display_sender_name,  # Include sender name in tracking
                        "recipient_email": recipient["email"],
                        "subject": personalized_subject,
                        "body": personalized_body,
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": extract_company_from_email(recipient["email"]),
                        "phone": ""
                    })

                    app_state.progress["sent"] += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                    
        except smtplib.SMTPAuthenticationError as e:
            app_state.progress["status"] = f"error: SMTP Authentication failed for {sender_email}: {e}"
            return
        except smtplib.SMTPException as e:
            app_state.progress["status"] = f"error: SMTP error for {sender_email}: {e}"
            return
        except Exception as e:
            app_state.progress["status"] = f"error: {e}"
            return

        start += batch_size

    app_state.progress["status"] = "completed"
    print("Email sending completed successfully!")

def send_bulk_emails_with_templates(recipients, batch_size, sender_accounts, template_data=None):
    """Send bulk emails with position-based templates"""
    # Use app_state instead of global progress
    app_state.progress["total"] = len(recipients)
    app_state.progress["sent"] = 0
    app_state.progress["status"] = "running"

    sender_cycle = cycle(sender_accounts)
    start = 0

    while start < len(recipients):
        batch = recipients[start:start + batch_size]
        sender_account = next(sender_cycle)  # Now get the full account object
        sender_email = sender_account['email']
        password = sender_account['password']
        account_sender_name = sender_account.get('sender_name', '')

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)

                for recipient in batch:
                    name = recipient.get("name", "") or extract_name_from_email(recipient["email"])[0] or "there"
                    
                    # Get the appropriate template
                    if template_data and template_data['templates']:
                        position = recipient.get("position", "").lower()
                        template = template_data['templates'].get(position, template_data['default_template'])
                        
                        if template:
                            subject = template['subject']
                            body = template['body']
                            # Priority: 1. Account sender name, 2. Template sender name, 3. Extract from email
                            if account_sender_name:
                                sender_name = account_sender_name
                            elif template.get('sender_name'):
                                sender_name = template['sender_name']
                            else:
                                # Extract name from sender email as fallback
                                sender_name, _ = extract_name_from_email(sender_email)
                                if not sender_name:
                                    sender_name = sender_email.split('@')[0].replace('.', ' ').title()
                        else:
                            # Fallback to default email content
                            subject = app_state.email_content.get("subject", "")
                            body = app_state.email_content.get("body", "")
                            sender_name = account_sender_name or app_state.email_content.get("sender_name", "")
                    else:
                        # Use regular email content
                        subject = app_state.email_content.get("subject", "")
                        body = app_state.email_content.get("body", "")
                        sender_name = account_sender_name or app_state.email_content.get("sender_name", "")

                    # Personalize content
                    personalized_body = replace_name_placeholders(body, name)
                    personalized_subject = replace_name_placeholders(subject, name)

                    msg = MIMEMultipart()
                    msg['From'] = f"{sender_name} <{sender_email}>"
                    msg['To'] = recipient["email"]
                    msg['Subject'] = personalized_subject
                    msg.attach(MIMEText(personalized_body, 'plain'))
                    
                    try:
                        server.send_message(msg)
                        print(f"Sent email from {sender_name} to {recipient['email']}")
                    except Exception as e:
                        print(f"Failed to send email to {recipient['email']}: {e}")
                        app_state.progress["sent"] += 1
                        continue

                    # Extract first and last name from the recipient
                    first_name, last_name = extract_name_from_email(recipient["email"])
                    
                    # Save sent email to separate file
                    save_sent_email({
                        "timestamp": datetime.now().isoformat(),
                        "sender_email": sender_email,
                        "sender_name": sender_name,
                        "recipient_email": recipient["email"],
                        "subject": personalized_subject,
                        "body": personalized_body,
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": extract_company_from_email(recipient["email"]),
                        "phone": "",
                        "position": recipient.get("position", ""),
                        "template_used": recipient.get("position", "default") if template_data else "standard"
                    })

                    app_state.progress["sent"] += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                    
        except smtplib.SMTPAuthenticationError as e:
            app_state.progress["status"] = f"error: SMTP Authentication failed for {sender_email}: {e}"
            return
        except smtplib.SMTPException as e:
            app_state.progress["status"] = f"error: SMTP error for {sender_email}: {e}"
            return
        except Exception as e:
            app_state.progress["status"] = f"error: {e}"
            return

        start += batch_size

    app_state.progress["status"] = "completed"
    print("Email sending completed successfully!")

def check_email_replies(sender_email, sender_password):
    """Check for UNREAD replies in the sender's inbox using IMAP"""
    replies = []
    
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        
        # Search for UNREAD emails only
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()
        
        # Get all unread emails
        for num in email_ids:
            status, data = mail.fetch(num, "(RFC822)")
            
            if status != "OK":
                continue
                
            msg = email.message_from_bytes(data[0][1])
            
            # Decode subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            
            # Check if this is a reply (subject starts with "Re:") or related to our campaign
            is_reply = subject.lower().startswith("re:")
            
            # Check if this is a bounce message (common indicators)
            is_bounce = any(indicator in subject.lower() for indicator in [
                "delivery failure", "undeliverable", "returned mail", 
                "delivery status", "failure notice", "mailer-daemon"
            ])
            
            # Check if this is an auto-response (common indicators)
            is_auto_response = any(indicator in subject.lower() or 
                                  any(indicator in msg.get("Auto-Submitted", "").lower() or 
                                      indicator in msg.get("X-Auto-Response-Suppress", "").lower() 
                                      for indicator in ["auto", "automatic", "out of office", "ooo", "vacation"])
                                  for indicator in ["auto-reply", "autoreply", "automatic reply", "out of office", "vacation"])
            
            # Only process replies that aren't bounces and aren't auto-responses
            if (is_reply or "your campaign subject terms" in subject.lower()) and not is_bounce and not is_auto_response:
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                
                # Get from address
                from_header = msg["From"]
                
                # Extract just the email address if it's in format "Name <email@example.com>"
                email_match = re.search(r'<(.+?)>', from_header)
                if email_match:
                    from_email = email_match.group(1)
                    from_name = from_header.split('<')[0].strip()
                else:
                    from_email = from_header
                    from_name = ""
                
                # Extract first and last name from the from header
                first_name, last_name = extract_name_from_email(from_header)
                
                # Extract phone number from body
                phone = extract_phone_number(body)
                
                # Extract company from email domain
                company = extract_company_from_email(from_email)
                
                replies.append({
                    "id": num.decode(),
                    "from": from_email,
                    "from_name": from_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "subject": subject,
                    "body": body,
                    "date": msg["Date"],
                    "phone": phone,
                    "company": company
                })
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"Error checking emails: {e}")
    
    return replies

def mark_email_as_read(sender_email, sender_password, email_id):
    """Mark an email as read"""
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(sender_email, sender_password)
        mail.select("inbox")
        
        # Mark email as read
        mail.store(email_id, '+FLAGS', '\\Seen')
        
        mail.close()
        mail.logout()
        return True
    except Exception as e:
        print(f"Error marking email as read: {e}")
        return False

def get_zoho_custom_fields(user_id="default_user"):
    """Get the actual API names of custom fields in Zoho CRM"""
    user_creds = app_state.user_zoho_credentials.get(user_id)
    
    if not user_creds or not user_creds.get('access_token'):
        # Try to refresh tokens if we have a refresh token
        if user_creds and user_creds.get('refresh_token'):
            print(f"Attempting to refresh tokens for user: {user_id}")
            if refresh_zoho_tokens(user_id):
                # Get updated credentials after refresh
                user_creds = app_state.user_zoho_credentials.get(user_id)
                if user_creds and user_creds.get('access_token'):
                    print("Token refresh successful")
                else:
                    print("Token refresh failed - no access token after refresh")
                    return None
            else:
                print("Token refresh failed")
                return None
        else:
            print(f"No access token or refresh token for user: {user_id}")
            return None
    
    access_token = user_creds['access_token']
    url = f"{ZOHO_API_DOMAIN}/crm/v2/settings/fields"
    params = {"module": "Leads"}
    
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Making fields request with token for user: {user_id}")
        response = requests.get(url, headers=headers, params=params)
        print(f"Zoho fields API response: {response.status_code}")
        
        if response.status_code == 200:
            fields_data = response.json()
            print(f"Successfully retrieved {len(fields_data.get('fields', []))} fields")
            return fields_data
        elif response.status_code == 401:
            # Token expired, try to refresh
            print("Token expired in get_zoho_custom_fields, attempting to refresh...")
            if refresh_zoho_tokens(user_id):
                # Get the new access token and retry
                user_creds = app_state.user_zoho_credentials.get(user_id)
                if user_creds and user_creds.get('access_token'):
                    headers['Authorization'] = f'Zoho-oauthtoken {user_creds["access_token"]}'
                    
                    response = requests.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        fields_data = response.json()
                        print(f"Retry successful - retrieved {len(fields_data.get('fields', []))} fields")
                        return fields_data
                    else:
                        print(f"Retry failed: {response.status_code} - {response.text}")
                        return None
                else:
                    print("No access token after refresh")
                    return None
            else:
                print("Token refresh failed in get_zoho_custom_fields")
                return None
        else:
            print(f"Error getting fields: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception getting fields: {e}")
        return None
