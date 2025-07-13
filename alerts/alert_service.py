import smtplib
import requests
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("alerts.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FraudAlertService")

class AlertService:
    def __init__(self, config_file='alerts/config.json'):
        """Initialize the alert service with configuration."""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config: {e}")
            # Default configuration
            self.config = {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_email": "",
                    "recipients": []
                },
                "sms": {
                    "enabled": False,
                    "provider": "twilio",
                    "account_sid": "",
                    "auth_token": "",
                    "from_number": "",
                    "to_numbers": []
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "headers": {}
                },
                "alert_thresholds": {
                    "high": 0.8,
                    "medium": 0.6
                }
            }
    
    def send_alert(self, transaction_data, alert_level="high"):
        """Send alerts through configured channels."""
        logger.info(f"Sending {alert_level} alert for transaction {transaction_data.get('transaction_id', 'unknown')}")
        
        # Format the alert message
        alert_message = self._format_alert_message(transaction_data, alert_level)
        
        # Send through each enabled channel
        results = {}
        
        if self.config["email"]["enabled"]:
            results["email"] = self._send_email_alert(alert_message, transaction_data, alert_level)
        
        if self.config["sms"]["enabled"]:
            results["sms"] = self._send_sms_alert(alert_message, transaction_data, alert_level)
        
        if self.config["webhook"]["enabled"]:
            results["webhook"] = self._send_webhook_alert(transaction_data, alert_level)
        
        # Log the results
        for channel, result in results.items():
            if result["success"]:
                logger.info(f"{channel.upper()} alert sent successfully")
            else:
                logger.error(f"{channel.upper()} alert failed: {result['error']}")
        
        return results
    
    def _format_alert_message(self, transaction_data, alert_level):
        """Format the alert message based on transaction data and alert level."""
        fraud_score = transaction_data.get("ensemble", {}).get("fraud_score", 0) * 100
        
        if alert_level == "high":
            subject = "🚨 URGENT: High Risk Fraud Alert"
            severity = "HIGH RISK"
        elif alert_level == "medium":
            subject = "⚠️ Medium Risk Fraud Alert"
            severity = "MEDIUM RISK"
        else:
            subject = "ℹ️ Low Risk Fraud Alert"
            severity = "LOW RISK"
        
        message = f"""
{subject}

Transaction Details:
- ID: {transaction_data.get('transaction_id', 'unknown')}
- Amount: ${transaction_data.get('amount', 0):.2f}
- User ID: {transaction_data.get('user_id', 'unknown')}
- Time: {datetime.fromisoformat(transaction_data.get('timestamp', datetime.now().isoformat())).strftime('%Y-%m-%d %H:%M:%S')}
- Fraud Score: {fraud_score:.2f}%
- Severity: {severity}

This transaction has been flagged by our fraud detection system.
Please review and take appropriate action.
        """
        
        return {
            "subject": subject,
            "body": message
        }
    
    def _send_email_alert(self, alert_message, transaction_data, alert_level):
        """Send an email alert."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["from_email"]
            msg['To'] = ", ".join(self.config["email"]["recipients"])
            msg['Subject'] = alert_message["subject"]
            
            # Add body
            msg.attach(MIMEText(alert_message["body"], 'plain'))
            
            # Connect to server
            server = smtplib.SMTP(self.config["email"]["smtp_server"], self.config["email"]["smtp_port"])
            server.starttls()
            server.login(self.config["email"]["username"], self.config["email"]["password"])
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_sms_alert(self, alert_message, transaction_data, alert_level):
        """Send an SMS alert."""
        try:
            if self.config["sms"]["provider"] == "twilio":
                # Using Twilio
                from twilio.rest import Client
                
                client = Client(self.config["sms"]["account_sid"], self.config["sms"]["auth_token"])
                
                # Create a shorter message for SMS
                sms_body = f"{alert_message['subject']}\nTransaction: {transaction_data.get('transaction_id', 'unknown')}\nAmount: ${transaction_data.get('amount', 0):.2f}\nFraud Score: {transaction_data.get('ensemble', {}).get('fraud_score', 0) * 100:.2f}%"
                
                # Send to all configured numbers
                for to_number in self.config["sms"]["to_numbers"]:
                    client.messages.create(
                        body=sms_body,
                        from_=self.config["sms"]["from_number"],
                        to=to_number
                    )
                
                return {"success": True}
            else:
                return {"success": False, "error": f"Unsupported SMS provider: {self.config['sms']['provider']}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_webhook_alert(self, transaction_data, alert_level):
        """Send a webhook alert."""
        try:
            # Prepare payload
            payload = {
                "alert_level": alert_level,
                "timestamp": datetime.now().isoformat(),
                "transaction": transaction_data
            }
            
            # Send webhook
            response = requests.post(
                self.config["webhook"]["url"],
                headers=self.config["webhook"]["headers"],
                json=payload
            )
            
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            
            return {"success": True, "response": response.json() if response.headers.get('content-type') == 'application/json' else response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_transaction(self, transaction_data):
        """Process a transaction and send alerts if needed."""
        # Get fraud score
        fraud_score = transaction_data.get("ensemble", {}).get("fraud_score", 0)
        
        # Determine alert level based on score
        if fraud_score >= self.config["alert_thresholds"]["high"]:
            return self.send_alert(transaction_data, "high")
        elif fraud_score >= self.config["alert_thresholds"]["medium"]:
            return self.send_alert(transaction_data, "medium")
        else:
            # No alert needed
            logger.info(f"No alert needed for transaction {transaction_data.get('transaction_id', 'unknown')} (score: {fraud_score:.4f})")
            return {"success": True, "message": "No alert needed"}

# Example usage
if __name__ == "__main__":
    # Create a sample transaction
    transaction = {
        "transaction_id": "T-1234567890",
        "user_id": "U-9876",
        "timestamp": datetime.now().isoformat(),
        "amount": 1299.99,
        "ensemble": {
            "is_fraud": True,
            "fraud_score": 0.92
        }
    }
    
    # Initialize alert service
    alert_service = AlertService()
    
    # Process transaction
    result = alert_service.process_transaction(transaction)
    
    print(f"Alert processing result: {result}")