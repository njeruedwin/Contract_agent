import json
from pathlib import Path
import uuid
from typing import Any, Callable, Set
from dotenv import load_dotenv
import os
import smtplib, ssl
from email.message import EmailMessage

# Load variables from .env file
load_dotenv()

# Access the variables
username = os.getenv("SMTP_USERNAME")
password = os.getenv("SMTP_PASSWORD")
port = os.getenv("PORT")

# Create a function to submit a send_risk_assessment_email
def send_risk_assessment_email(file: str):
     port = 587
     smtp_server = "smtp.zeptomail.com"
     username=username
     password =password
     message = "Test email sent successfully."
     #attach file
     script_dir = Path(__file__).parent  # Get the directory of the script
     file_path = script_dir / file

     # Send email
     msg = EmailMessage()
     msg['Subject'] = "Test Email"
     msg['From'] = "noreply@tsavo.ke"
     msg['To'] = "edwin.njeru@tsavo.ke"
     msg.set_content(message)
     
     
     with open(f"{file_path}", "rb") as f:
          file_data = f.read()
          file_name = f.name
          msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file)
     try:
          if port == 465:
               context = ssl.create_default_context()
               with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
          elif port == 587:
               with smtplib.SMTP(smtp_server, port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
          else:
               print ("use 465 / 587 as port value")
               exit()
          return 'Email sent successfully.'
     except Exception as e:
            return e


