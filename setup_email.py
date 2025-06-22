#!/usr/bin/env python3
"""
Script to configure Airflow email settings for Gmail SMTP.
Run this script and follow the prompts to set up email notifications.
"""

import os
import re
import getpass

def update_airflow_config():
    """Update Airflow configuration for Gmail SMTP."""
    
    # Airflow config file path
    config_path = "/home/lusitech/airflow/airflow.cfg"
    
    if not os.path.exists(config_path):
        print(f"Error: Airflow config file not found at {config_path}")
        return False
    
    print("🔧 Airflow Email Configuration Setup")
    print("=" * 50)
    print()
    print("To send emails via Gmail, you need:")
    print("1. A Gmail account with 2-factor authentication enabled")
    print("2. An App Password generated for this application")
    print()
    
    # Get Gmail credentials
    gmail_address = input("Enter your Gmail address: ").strip()
    if not gmail_address or '@gmail.com' not in gmail_address:
        print("Error: Please enter a valid Gmail address")
        return False
    
    app_password = getpass.getpass("Enter your Gmail App Password: ").strip()
    if not app_password:
        print("Error: App password is required")
        return False
    
    # Read current config
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Update SMTP settings
    smtp_updates = {
        'smtp_host = smtp.gmail.com': 'smtp_host = smtp.gmail.com',
        'smtp_port = 587': 'smtp_port = 587',
        'smtp_starttls = True': 'smtp_starttls = True',
        'smtp_ssl = False': 'smtp_ssl = False',
        'smtp_mail_from = airflow@example.com': f'smtp_mail_from = {gmail_address}',
        'smtp_user = ': f'smtp_user = {gmail_address}',
        'smtp_password = ': f'smtp_password = {app_password}',
        'smtp_timeout = 30': 'smtp_timeout = 30',
        'smtp_retry_limit = 5': 'smtp_retry_limit = 5'
    }
    
    # Apply updates
    for old_line, new_line in smtp_updates.items():
        if 'smtp_host =' in old_line:
            config_content = re.sub(r'smtp_host = .*', new_line, config_content)
        elif 'smtp_port =' in old_line:
            config_content = re.sub(r'smtp_port = .*', new_line, config_content)
        elif 'smtp_starttls =' in old_line:
            config_content = re.sub(r'smtp_starttls = .*', new_line, config_content)
        elif 'smtp_ssl =' in old_line:
            config_content = re.sub(r'smtp_ssl = .*', new_line, config_content)
        elif 'smtp_mail_from =' in old_line:
            config_content = re.sub(r'smtp_mail_from = .*', new_line, config_content)
        elif 'smtp_user =' in old_line:
            # Add smtp_user if it doesn't exist
            if 'smtp_user =' not in config_content:
                config_content = config_content.replace('[smtp]', '[smtp]\nsmtp_user = ')
            config_content = re.sub(r'smtp_user = .*', new_line, config_content)
        elif 'smtp_password =' in old_line:
            # Add smtp_password if it doesn't exist
            if 'smtp_password =' not in config_content:
                config_content = config_content.replace('smtp_user =', 'smtp_user = \nsmtp_password = ')
            config_content = re.sub(r'smtp_password = .*', new_line, config_content)
        elif 'smtp_timeout =' in old_line:
            config_content = re.sub(r'smtp_timeout = .*', new_line, config_content)
        elif 'smtp_retry_limit =' in old_line:
            config_content = re.sub(r'smtp_retry_limit = .*', new_line, config_content)
    
    # Backup original config
    backup_path = config_path + '.backup'
    with open(backup_path, 'w') as f:
        f.write(config_content)
    
    # Write updated config
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Airflow configuration updated successfully!")
    print(f"📁 Backup saved to: {backup_path}")
    print()
    print("📧 Email Configuration Summary:")
    print(f"   SMTP Host: smtp.gmail.com")
    print(f"   SMTP Port: 587")
    print(f"   From Email: {gmail_address}")
    print(f"   STARTTLS: Enabled")
    print(f"   SSL: Disabled")
    print()
    print("🔄 You'll need to restart Airflow services for changes to take effect:")
    print("   pkill -f airflow")
    print("   airflow webserver --daemon")
    print("   airflow scheduler --daemon")
    
    return True

if __name__ == "__main__":
    update_airflow_config() 