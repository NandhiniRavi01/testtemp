import re
import email
from email.header import decode_header
from datetime import datetime
import pandas as pd
import os

def extract_phone_number(text):
    """Extract valid phone number from email body text"""
    if not text:
        return ""
    
    # More specific phone patterns with validation
    phone_patterns = [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',                    # US: 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',                    # US: (123) 456-7890
        r'\b\d{3}[-.\s]?\d{4}[-.\s]?\d{4}\b',                    # International: 123-4567-8901
        r'\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # With country code
        r'\b\d{10}\b',                                           # Just 10 digits
        r'\b\d{4}[-.\s]?\d{3}[-.\s]?\d{3}\b',                    # 11 digits with formatting
        r'\b\d{3}[-.\s]?\d{4}\b'                                 # 7 digits (local)
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Clean the phone number
            clean_number = re.sub(r'[^\d+]', '', match)
            
            # Validate phone number length and format
            if len(clean_number) >= 7:  # Minimum valid phone number length
                # Remove country code if it's just +1 (US) for simplicity
                if clean_number.startswith('+1') and len(clean_number) == 12:
                    clean_number = clean_number[2:]  # Remove +1
                
                # Format the number nicely
                if len(clean_number) == 10:
                    return f"({clean_number[:3]}) {clean_number[3:6]}-{clean_number[6:]}"
                elif len(clean_number) == 7:
                    return f"{clean_number[:3]}-{clean_number[3:]}"
                else:
                    return clean_number
    
    return ""

def is_valid_phone_number(phone):
    """Validate if a string is a valid phone number"""
    if not phone:
        return False
    
    # Remove all non-digit characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Check if it's just random numbers (like years)
    if clean_phone.isdigit():
        # Avoid storing years or short numbers that look like years
        if len(clean_phone) <= 4:
            return False
        
        # Check if it looks like a year (1900-2099)
        if len(clean_phone) == 4 and clean_phone.isdigit():
            year = int(clean_phone)
            if 1900 <= year <= 2099:
                return False
    
    # Valid phone number should have at least 7 digits
    digit_count = len(re.sub(r'[^\d]', '', phone))
    if digit_count < 7:
        return False
    
    # Additional validation patterns
    valid_patterns = [
        r'^\+?[\d\s\-\(\)]{10,}$',  # International format
        r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$',  # US format
        r'^\d{7,15}$'  # Plain digits
    ]
    
    for pattern in valid_patterns:
        if re.match(pattern, phone):
            return True
    
    return False    

def extract_name_from_email(email_address):
    """Extract a name from an email address - handle various formats"""
    if not email_address:
        return "", ""
    
    # Try to extract name from "Name <email@example.com>" format
    name_match = re.match(r'^"?([^"<]+)"?\s*<', email_address)
    if name_match:
        full_name = name_match.group(1).strip()
        name_parts = full_name.split()
        if len(name_parts) >= 2:
            return name_parts[0], " ".join(name_parts[1:])
        elif len(name_parts) == 1:
            return name_parts[0], ""
    
    # Try to extract from email username (before @)
    email_only_match = re.search(r'([^@]+)@', email_address)
    if email_only_match:
        username = email_only_match.group(1)
        
        # Remove numbers and special characters, replace with spaces
        clean_name = re.sub(r'[^a-zA-Z]+', ' ', username).title().strip()
        
        # Handle common separators
        for separator in ['.', '_', '-']:
            if separator in clean_name:
                parts = clean_name.split(separator)
                if len(parts) >= 2:
                    return parts[0], " ".join(parts[1:])
        
        # If no separators found, try to split camelCase
        if re.search(r'[a-z][A-Z]', clean_name):
            parts = re.findall(r'[A-Z][a-z]*', clean_name)
            if len(parts) >= 2:
                return parts[0], " ".join(parts[1:])
        
        name_parts = clean_name.split()
        if len(name_parts) >= 2:
            return name_parts[0], " ".join(name_parts[1:])
        elif len(name_parts) == 1:
            return name_parts[0], ""
    
    return "", ""

def extract_company_from_email(email_address):
    """Extract company name from email domain"""
    if not email_address:
        return "Unknown Company"
    
    domain_match = re.search(r'@([a-zA-Z0-9.-]+)', email_address)
    if domain_match:
        domain = domain_match.group(1)
        company_name = re.sub(r'\.[a-z]{2,3}$', '', domain)
        return company_name.title()
    
    return "Unknown Company"

def replace_name_placeholders(text, name):
    """Replace any placeholder that refers to a name."""
    placeholder_map = {
        "{{name}}": name,
        "{name}": name,
        "[Candidate Name]": name,
        "[Client Name]": name,
        "[Name]": name,
        "[client name]": name
    }
    for placeholder, value in placeholder_map.items():
        text = text.replace(placeholder, value)

    # Dynamic catch-all like [something name]
    text = re.sub(r"\[(.*?name.*?)\]", name, text, flags=re.IGNORECASE)

    return text

def save_to_excel(data):
    """Save reply data to Excel file with comprehensive lead information"""
    filename = "email_replies.xlsx"
    
    try:
        if os.path.exists(filename):
            df = pd.read_excel(filename)
        else:
            df = pd.DataFrame(columns=[
                "timestamp", "sender_email", "recipient_email", 
                "subject", "body", "first_name", "last_name",
                "company", "phone", "converted_to_lead", "zoho_lead_id"
            ])
        
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(filename, index=False)
        return True
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return False

def is_auto_response(email_data):
    """Check if an email is an auto-response"""
    body = email_data.get("body", "").lower()
    subject = email_data.get("subject", "").lower()
    
    # Common auto-response indicators
    auto_response_indicators = [
        "out of office", "ooo", "vacation", "away from my email",
        "auto-reply", "autoreply", "automatic reply",
        "this is an automated response", "no-reply",
        "do not reply to this email", "delivery receipt",
        "read receipt", "acknowledgement", "confirmation of receipt"
    ]
    
    # Check if any indicator appears in subject or body
    for indicator in auto_response_indicators:
        if indicator in subject or indicator in body:
            return True
    
    # Check for short messages typical of auto-responses
    if len(body.split()) < 20 and any(phrase in body for phrase in ["thank you", "received", "confirm"]):
        return True
        
    return False

def save_sent_email(data):
    """Save sent email data to a separate Excel file"""
    filename = "sent_emails.xlsx"
    
    try:
        if os.path.exists(filename):
            df = pd.read_excel(filename)
        else:
            df = pd.DataFrame(columns=[
                "timestamp", "sender_email", "recipient_email", 
                "subject", "body", "first_name", "last_name",
                "company", "phone"
            ])
        
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(filename, index=False)
        return True
    except Exception as e:
        print(f"Error saving sent email to Excel: {e}")
        return False
    
    # Add to helpers.py

def extract_zoho_field_info(fields_data):
    """Extract field information in a more usable format"""
    field_info = []
    for field in fields_data.get('fields', []):
        field_info.append({
            "api_name": field.get('api_name'),
            "field_label": field.get('field_label'),
            "data_type": field.get('data_type'),
            "mandatory": field.get('mandatory', False),
            "length": field.get('length'),
            "custom_field": field.get('custom_field', False)
        })
    return field_info
