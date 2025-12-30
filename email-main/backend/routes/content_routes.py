from flask import Flask, request, jsonify, send_file, Blueprint
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itertools import cycle
import threading
from flask_cors import CORS
import google.generativeai as genai
import os
import re
import time
from datetime import datetime
import json
import imaplib
import email
from email.header import decode_header
import requests
from config import app_state  # Import the shared state object
from services.service import (
    generate_email_content,
    create_zoho_lead,
    get_zoho_auth_url,
    get_zoho_tokens,
    refresh_zoho_tokens,
    get_zoho_custom_fields,
    send_bulk_emails,
    check_email_replies,
    save_to_excel,
    mark_email_as_read,
    extract_name_from_email,
    extract_company_from_email,
    extract_phone_number,
    replace_name_placeholders,
    is_valid_phone_number,
    send_bulk_emails_with_templates, 
    is_auto_response,  # Add this import
    ZOHO_ACCESS_TOKEN,
)

content_bp = Blueprint("content", __name__)



def get_zoho_field_mapping(user_id="default_user"):
    """Get a mapping of standard field names to actual Zoho API field names"""
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

@content_bp.route("/update-field-mapping", methods=["POST"])
def update_field_mapping():
    """Update the field mapping for the user"""
    user_id = request.headers.get("X-User-ID", "default_user")
    data = request.json
    field_mapping = data.get("field_mapping", {})
    
    # Initialize user_field_mappings if it doesn't exist
    if not hasattr(app_state, 'user_field_mappings'):
        app_state.user_field_mappings = {}
    
    # Update the mapping for this user
    app_state.user_field_mappings[user_id] = field_mapping
    
    return jsonify({"message": "Field mapping updated successfully", "mapping": field_mapping})    

@content_bp.route("/zoho-generate-professional-reply", methods=["POST"])
def zoho_generate_professional_reply():
    """Generate a single professional AI reply for a received email"""
    data = request.json
    original_email = data.get("original_email")
    
    if not original_email:
        return jsonify({"error": "Missing email content"}), 400
    
    try:
        # Use Gemini to generate a professional reply
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        Write a professional email reply to this message. 
        Make it concise, polite, and business-appropriate.
        Write only one reply in plain text format.
        
        Email to reply to: {original_email}
        
        Professional reply:
        """
        
        response = model.generate_content(prompt)
        
        # Get the response and clean it
        reply_text = response.text.strip()
        
        # Simple cleaning - remove any markdown formatting
        reply_text = re.sub(r'\*\*(.*?)\*\*', r'\1', reply_text)  # Remove bold
        reply_text = re.sub(r'\*(.*?)\*', r'\1', reply_text)  # Remove italic
        
        return jsonify({"reply": reply_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/generate-content", methods=["POST"])
def generate_content():
    data = request.json
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    content = generate_email_content(prompt)

    if "error" in content:
        return jsonify({"error": content["error"]}), 500

    # Use app_state instead of global email_content
    app_state.email_content = content

    return jsonify(content)

@content_bp.route("/get-content", methods=["GET"])
def get_content():
    # Use app_state instead of global email_content
    return jsonify(app_state.email_content)

@content_bp.route("/update-content", methods=["POST"])
def update_content():
    data = request.json

    if "subject" in data:
        app_state.email_content["subject"] = data["subject"]
    if "body" in data:
        app_state.email_content["body"] = data["body"]
    if "sender_name" in data:
        app_state.email_content["sender_name"] = data["sender_name"]

    return jsonify({"message": "Content updated successfully", "content": app_state.email_content})

@content_bp.route("/upload-templates", methods=["POST"])
def upload_templates():
    """Upload Excel file with email templates for different positions"""
    file = request.files["file"]
    
    if not file:
        return jsonify({"error": "No file provided"}), 400

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # Validate required columns
        required_columns = ['position', 'subject', 'body']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({"error": f"Missing required columns: {', '.join(missing_columns)}"}), 400

        # Store templates in app_state
        templates = {}
        template_details = []
        
        for _, row in df.iterrows():
            position = str(row['position']).strip().lower()
            template_data = {
                'subject': str(row['subject']),
                'body': str(row['body']),
                'sender_name': str(row.get('sender_name', ''))  # Keep empty if not provided
            }
            templates[position] = template_data
            
            # Store template details for frontend display
            template_details.append({
                'position': position,
                'subject': template_data['subject'],
                'body': template_data['body'],
                'sender_name': template_data['sender_name']
            })

        app_state.email_templates = templates
        app_state.default_template = templates.get('general', templates.get('default', next(iter(templates.values())) if templates else None))
        app_state.template_details = template_details  # Store for frontend access

        return jsonify({
            "message": f"Successfully loaded {len(templates)} templates",
            "positions": list(templates.keys()),
            "templates": template_details,  # Send template details to frontend
            "templates_with_sender_names": [pos for pos, template in templates.items() if template.get('sender_name')]
        })

    except Exception as e:
        return jsonify({"error": f"Error processing template file: {str(e)}"}), 500

@content_bp.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    batch_size = int(request.form.get("batch_size", 250))

    # Get template-related data
    use_templates = request.form.get("use_templates", "false").lower() == "true"
    position_column = request.form.get("position_column", "position")
    
    sender_emails = request.form.getlist("sender_emails[]")
    sender_passwords = request.form.getlist("sender_passwords[]")
    sender_names = request.form.getlist("sender_names[]")  # Get sender names

    print(f"Received {len(sender_emails)} sender accounts")
    print(f"Sender emails: {sender_emails}")
    print(f"Sender names: {sender_names}")

    if not sender_emails or not sender_passwords:
        return jsonify({"error": "No sender accounts provided!"}), 400

    if len(sender_emails) != len(sender_passwords):
        return jsonify({"error": "Mismatch between number of emails and passwords!"}), 400

    # Create sender accounts with names
    sender_accounts = []
    for i in range(len(sender_emails)):
        sender_name = sender_names[i] if i < len(sender_names) else ""
        sender_accounts.append({
            'email': sender_emails[i],
            'password': sender_passwords[i],
            'sender_name': sender_name
        })

    print(f"Created sender accounts: {sender_accounts}")

    # Read file
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 400

    # Enhanced email column detection
    possible_email_cols = ['email', 'Email', 'EMAIL', 'email_id', 'Email ID', 'EMAIL_ID', 
                          'email_address', 'Email Address', 'EMAIL_ADDRESS', 'recipient_email',
                          'Recipient Email', 'RECIPIENT_EMAIL', 'mail', 'Mail', 'MAIL', 'Validated Emails',
                          'e-mail', 'E-mail', 'E-MAIL', 'contact_email', 'Contact Email']
    
    # Enhanced name column detection
    possible_name_cols = ['name', 'Name', 'NAME', 'full_name', 'Full Name', 'FULL_NAME',
                         'first_name', 'First Name', 'FIRST_NAME', 'last_name', 'Last Name',
                         'LAST_NAME', 'contact_name', 'Contact Name', 'CONTACT_NAME',
                         'candidate_name', 'Candidate Name', 'CANDIDATE_NAME']
    
    # Position column detection
    possible_position_cols = ['position', 'Position', 'POSITION', 'job_title', 'Job Title', 
                             'JOB_TITLE', 'role', 'Role', 'ROLE', 'title', 'Title', 'TITLE']

    email_col = None
    name_col = None
    position_col = None

    # Find email column
    for col in df.columns:
        col_lower = col.lower().strip()
        for possible in possible_email_cols:
            if col_lower == possible.lower():
                email_col = col
                break
        if email_col:
            break

    if not email_col:
        for col in df.columns:
            sample_values = df[col].dropna().head(5)
            if len(sample_values) > 0 and any('@' in str(val) for val in sample_values):
                email_col = col
                break

    if not email_col:
        return jsonify({"error": "No email column found in the uploaded file!"}), 400

    # Find name column
    for col in df.columns:
        col_lower = col.lower().strip()
        for possible in possible_name_cols:
            if col_lower == possible.lower():
                name_col = col
                break
        if name_col:
            break

    # Find position column if using templates
    if use_templates:
        for col in df.columns:
            col_lower = col.lower().strip()
            for possible in possible_position_cols:
                if col_lower == possible.lower():
                    position_col = col
                    break
            if position_col:
                break
        
        if not position_col:
            return jsonify({"error": "No position column found for template matching! Please check your file or change the position column name."}), 400

    recipients = []
    for _, row in df.iterrows():
        email_value = row[email_col]
        if pd.isna(email_value) or not isinstance(email_value, str):
            continue
            
        # Split multiple emails using comma, semicolon, or space
        email_list = []
        if email_value:
            # First split by semicolon, then by comma, then by space
            for separator in [';', ',', ' ']:
                if separator in email_value:
                    # Split and clean each email
                    split_emails = [email.strip() for email in email_value.split(separator) if email.strip()]
                    email_list.extend(split_emails)
                    break
            else:
                # No separators found, treat as single email
                email_list = [email_value.strip()]
        
        # Filter valid emails and remove duplicates
        valid_emails = []
        seen_emails = set()
        for email_str in email_list:
            if email_str and '@' in email_str and email_str not in seen_emails:
                valid_emails.append(email_str)
                seen_emails.add(email_str)
        
        if not valid_emails:
            continue
            
        name_value = ""
        if name_col and name_col in df.columns and not pd.isna(row[name_col]):
            name_value = str(row[name_col])
        
        position_value = ""
        if use_templates and position_col and position_col in df.columns and not pd.isna(row[position_col]):
            position_value = str(row[position_col]).strip().lower()
        
        # Create a recipient entry for each valid email
        for email_str in valid_emails:
            # Extract name from email if name column is empty
            final_name = name_value
            if not final_name:
                final_name = extract_name_from_email(email_str)[0] or ""
            
            recipients.append({
                "email": email_str,
                "name": final_name,
                "position": position_value
            })

    if len(recipients) == 0:
        return jsonify({"error": "No valid email addresses found in the uploaded file!"}), 400

    print(f"Found {len(recipients)} valid recipients after splitting multiple emails")

    # Determine email content source
    if use_templates:
        # Check if templates are loaded
        if not hasattr(app_state, 'email_templates') or not app_state.email_templates:
            return jsonify({"error": "No email templates loaded! Please upload template file first."}), 400
        
        # Use template-based content
        template_data = {
            'templates': app_state.email_templates,
            'default_template': app_state.default_template
        }
        print("Starting template-based email sending...")
        threading.Thread(
            target=send_bulk_emails_with_templates,
            args=(recipients, batch_size, sender_accounts, template_data)
        ).start()
    else:
        # Use regular email content
        template_data = None
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        sender_name = request.form.get("sender_name", "")
        
        # Validate regular email content
        if not subject or not body or not sender_name:
            return jsonify({"error": "Email content is incomplete! Please generate or enter subject, body, and sender name."}), 400

        print("Starting regular email sending...")
        threading.Thread(
            target=send_bulk_emails,
            args=(recipients, batch_size, sender_accounts, subject, body, sender_name)
        ).start()

    return jsonify({"message": f"Started sending {len(recipients)} personalized emails."})

@content_bp.route("/preview", methods=["POST"])
def preview_file():
    file = request.files["file"]

    if file.filename.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    preview_data = df.head(5).to_dict(orient="records")
    columns = df.columns.tolist()

    return jsonify({"columns": columns, "data": preview_data})

@content_bp.route("/progress", methods=["GET"])
def get_progress():
    # Use app_state instead of global progress
    return jsonify(app_state.progress)

@content_bp.route("/zoho-auth", methods=["GET"])
def zoho_auth():
    """Initiate Zoho OAuth authentication with user credentials"""
    user_id = request.headers.get("X-User-ID", "default_user")
    
    try:
        # Get the current domain for redirect URI
        if request.headers.get('X-Forwarded-Proto') == 'https':  # AWS load balancer
            base_url = f"https://{request.headers.get('Host')}"
        else:
            base_url = request.url_root.rstrip('/')
        
        print(f"Generating auth URL for user: {user_id}")
        print(f"Base URL: {base_url}")
        
        # Check if user credentials exist
        user_creds = app_state.user_zoho_credentials.get(user_id)
        if not user_creds:
            return jsonify({"error": "User credentials not found. Please set up Zoho credentials first."}), 400
        
        auth_url = get_zoho_auth_url(user_id, base_url)
        if not auth_url:
            return jsonify({"error": "Failed to generate authentication URL"}), 400
            
        app_state.zoho_status = {"connected": False, "message": "Authentication initiated"}
        return jsonify({"auth_url": auth_url})
    except Exception as e:
        print(f"Exception in zoho_auth: {e}")
        return jsonify({"error": str(e)}), 500

    
# Add to content_routes.py

@content_bp.route("/save-zoho-credentials", methods=["POST"])
def save_zoho_credentials():
    """Save user's Zoho CRM credentials"""
    data = request.json
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    redirect_uri = data.get("redirect_uri")
    
    if not all([client_id, client_secret, redirect_uri]):
        return jsonify({"error": "Missing required credentials"}), 400
    
    # In a real app, you'd have user authentication and store credentials per user
    # For simplicity, we'll use a session or simple user identifier
    user_id = request.headers.get("X-User-ID", "default_user")  # Simple user identification
    
    # Store credentials in app state
    app_state.user_zoho_credentials[user_id] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "access_token": None,
        "refresh_token": None
    }
    
    return jsonify({"message": "Zoho credentials saved successfully"})    

@content_bp.route("/zoho-callback", methods=["GET"])
def zoho_callback():
    """Handle Zoho OAuth callback"""
    try:
        auth_code = request.args.get('code')
        user_id = request.args.get('state', 'default_user')  # Pass user ID as state parameter
        
        if not auth_code:
            return jsonify({"error": "No authorization code provided"}), 400
        
        print(f"Zoho callback received for user: {user_id}")
        print(f"Auth code: {auth_code}")
        
        # Check if user credentials exist
        user_creds = app_state.user_zoho_credentials.get(user_id)
        if not user_creds:
            return jsonify({"error": "No Zoho credentials found for user. Please save credentials first."}), 400
        
        success = get_zoho_tokens(auth_code, user_id)
        if success:
            # Verify tokens were stored
            updated_creds = app_state.user_zoho_credentials.get(user_id)
            if updated_creds and updated_creds.get('access_token'):
                print(f"Successfully stored tokens for user: {user_id}")
                print(f"Access token: {updated_creds['access_token'][:50]}...")
                if updated_creds.get('refresh_token'):
                    print(f"Refresh token: {updated_creds['refresh_token'][:50]}...")
                return jsonify({"message": "Zoho CRM connected successfully!"})
            else:
                print("Tokens not stored properly")
                return jsonify({"error": "Failed to store authentication tokens"}), 500
        else:
            return jsonify({"error": "Failed to get access token"}), 500
    except Exception as e:
        print(f"Exception in zoho_callback: {e}")
        return jsonify({"error": str(e)}), 500

@content_bp.route("/zoho-status", methods=["GET"])
def get_zoho_status():
    """Get Zoho CRM connection status"""
    # Use app_state instead of global zoho_status
    # Check if token is still valid
    if app_state.zoho_status["connected"] and ZOHO_ACCESS_TOKEN:
        # Simple check - if we have an access token, consider it connected
        pass
    return jsonify(app_state.zoho_status)

@content_bp.route("/zoho-check-replies", methods=["POST"])
def zoho_check_replies():
    """Check unread replies and create leads in Zoho CRM"""
    data = request.json
    sender_email = data.get("sender_email")
    sender_password = data.get("sender_password")

    if not sender_email or not sender_password:
        return jsonify({"error": "Missing sender email or password"}), 400

    try:
        # Get user ID from request
        user_id = request.headers.get("X-User-ID", "default_user")
        
        # 1. Fetch replies from Gmail IMAP (excluding auto-responses)
        replies = check_email_replies(sender_email, sender_password)

        created_leads = []
        for reply in replies:
            # Only process if this is a genuine reply (not an auto-response)
            if not is_auto_response(reply):
                # Extract phone number and validate it
                phone = extract_phone_number(reply.get("body", ""))
                if not is_valid_phone_number(phone):
                    phone = ""  # Don't include invalid phone numbers
                
                lead_data = {
                    "email": reply.get("from"),
                    "first_name": reply.get("first_name", ""),
                    "last_name": reply.get("last_name", ""),
                    "company": reply.get("company", "From Email Reply"),
                    "phone": phone,  # This will be empty if invalid
                    "body": reply.get("body", "")
                }

                # 2. Create lead in Zoho CRM - pass user_id
                lead_id = create_zoho_lead(lead_data, user_id)
                if lead_id:
                    reply["zoho_lead_id"] = lead_id
                    reply["converted_to_lead"] = True
                    created_leads.append(lead_id)
                else:
                    reply["converted_to_lead"] = False

                # 3. Save reply details to Excel
                save_to_excel({
                    "timestamp": datetime.now().isoformat(),
                    "sender_email": reply.get("from"),
                    "recipient_email": sender_email,
                    "subject": reply.get("subject"),
                    "body": reply.get("body"),
                    "first_name": reply.get("first_name", ""),
                    "last_name": reply.get("last_name", ""),
                    "company": reply.get("company", ""),
                    "phone": phone,  # Save the validated phone (or empty)
                    "converted_to_lead": reply.get("converted_to_lead", False),
                    "zoho_lead_id": reply.get("zoho_lead_id", "")
                })

        return jsonify({
            "message": f"Found {len(replies)} replies. "
                       f"Created {len(created_leads)} leads in Zoho CRM.",
            "replies": replies
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/zoho-generate-reply", methods=["POST"])
def zoho_generate_reply():
    """Generate an AI reply for a received email"""
    data = request.json
    original_email = data.get("original_email")
    reply_content = data.get("reply_content")
    
    if not original_email or not reply_content:
        return jsonify({"error": "Missing email or content"}), 400
    
    try:
        # Use Gemini to generate a reply
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        Generate a professional reply to this email:
        
        Original email content: {original_email}
        
        Context for reply: {reply_content}
        
        Please provide a polite, professional response that addresses the sender's message.
        Keep it concise and appropriate for a business context.
        """
        
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/zoho-send-reply", methods=["POST"])
def zoho_send_reply():
    """Send a reply and store in Zoho CRM"""
    data = request.json
    sender_email = data.get("sender_email")
    sender_password = data.get("sender_password")
    recipient_email = data.get("recipient_email")
    subject = data.get("subject")
    body = data.get("body")
    email_id = data.get("email_id")
    lead_data = data.get("lead_data", {})
    
    if not all([sender_email, sender_password, recipient_email, subject, body]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
        
        # Mark email as read if email_id is provided
        if email_id:
            mark_email_as_read(sender_email, sender_password, email_id)
        
        # Extract name from email - handle single names
        first_name, last_name = extract_name_from_email(recipient_email)
        
        # Use any additional lead data provided
        company = lead_data.get("company", extract_company_from_email(recipient_email))
        phone = lead_data.get("phone", extract_phone_number(body))
        
        # Store in Zoho CRM if connected
        zoho_success = False
        zoho_lead_id = None
        
        # Use app_state instead of global zoho_status
        if app_state.zoho_status["connected"]:
            # Create lead in Zoho CRM
            zoho_lead_id = create_zoho_lead({
                "email": recipient_email,
                "first_name": first_name,
                "last_name": last_name,
                "body": body,
                "phone": phone,
                "company": company
            })
            zoho_success = bool(zoho_lead_id)
        
        # Save to Excel file
        excel_success = save_to_excel({
            "timestamp": datetime.now().isoformat(),
            "sender_email": sender_email,
            "recipient_email": recipient_email,
            "subject": subject,
            "body": body,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "phone": phone,
            "converted_to_lead": zoho_success,
            "zoho_lead_id": zoho_lead_id or "N/A"
        })
        
        return jsonify({
            "message": "Reply sent successfully",
            "zoho_saved": zoho_success,
            "zoho_lead_id": zoho_lead_id,
            "excel_saved": excel_success
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/download-replies", methods=["GET"])
def download_replies():
    """Download the Excel file with all captured replies"""
    filename = "email_replies.xlsx"
    
    if not os.path.exists(filename):
        return jsonify({"error": "No replies data available"}), 404
    
    try:
        return send_file(
            filename,
            as_attachment=True,
            download_name=f"email_replies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/zoho-fields", methods=["GET"])
def zoho_fields():
    """Get Zoho CRM field information"""
    user_id = request.headers.get("X-User-ID", "default_user")
    print(f"Getting Zoho fields for user: {user_id}")
    
    # Check if user has credentials
    user_creds = app_state.user_zoho_credentials.get(user_id)
    if not user_creds:
        return jsonify({"error": "No Zoho credentials found for user"}), 400
    
    fields = get_zoho_custom_fields(user_id)
    if fields:
        return jsonify(fields)
    else:
        return jsonify({"error": "Failed to get field information. Please check your Zoho connection."}), 500
