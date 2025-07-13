from kafka import KafkaProducer
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class TransactionProducer:
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='transactions'):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.topic = topic
    
    def generate_transaction(self):
        """Generate a synthetic transaction."""
        # Transaction amount (log-normal distribution)
        amount = np.random.lognormal(mean=4.0, sigma=1.0)
        
        # Transaction type
        transaction_types = ['purchase', 'withdrawal', 'transfer', 'payment']
        transaction_type = np.random.choice(transaction_types, p=[0.6, 0.2, 0.15, 0.05])
        
        # Merchant category (if purchase)
        merchant_categories = ['retail', 'food', 'travel', 'entertainment', 'other']
        merchant_category = np.random.choice(merchant_categories) if transaction_type == 'purchase' else None
        
        # Location
        countries = ['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU']
        country = np.random.choice(countries, p=[0.7, 0.1, 0.05, 0.05, 0.05, 0.03, 0.02])
        
        # User ID
        user_id = np.random.randint(1000, 9999)
        
        # Device info
        devices = ['mobile', 'web', 'atm', 'pos']
        device = np.random.choice(devices, p=[0.5, 0.3, 0.1, 0.1])
        
        # IP address (simplified)
        ip_address = f"{np.random.randint(1, 255)}.{np.random.randint(1, 255)}.{np.random.randint(1, 255)}.{np.random.randint(1, 255)}"
        
        # Timestamp
        timestamp = datetime.now().isoformat()
        
        # Create transaction
        transaction = {
            'transaction_id': f"T-{int(time.time())}-{np.random.randint(1000, 9999)}",
            'user_id': user_id,
            'timestamp': timestamp,
            'amount': round(amount, 2),
            'transaction_type': transaction_type,
            'merchant_category': merchant_category,
            'country': country,
            'device': device,
            'ip_address': ip_address
        }
        
        # Occasionally generate fraudulent transactions (5% chance)
        is_fraud = np.random.random() < 0.05
        
        if is_fraud:
            # Modify transaction to make it fraudulent
            # For example: unusual amount, different country, etc.
            fraud_modifications = np.random.choice(['amount', 'country', 'device'], 
                                                 size=np.random.randint(1, 3), 
                                                 replace=False)
            
            if 'amount' in fraud_modifications:
                # Much larger amount
                transaction['amount'] = round(transaction['amount'] * np.random.uniform(5, 20), 2)
            
            if 'country' in fraud_modifications:
                # Different country from usual
                unusual_countries = ['RU', 'CN', 'BR', 'NG', 'IN']
                transaction['country'] = np.random.choice(unusual_countries)
            
            if 'device' in fraud_modifications:
                # Unusual device
                transaction['device'] = 'unknown'
        
        # Add fraud label for testing purposes
        transaction['is_fraud'] = int(is_fraud)
        
        return transaction
    
    def send_transaction(self, transaction=None):
        """Send a transaction to Kafka topic."""
        if transaction is None:
            transaction = self.generate_transaction()
        
        self.producer.send(self.topic, transaction)
        return transaction
    
    def simulate_transactions(self, count=100, interval=1.0):
        """Simulate a stream of transactions."""
        print(f"Simulating {count} transactions at {interval}s intervals...")
        
        for i in range(count):
            transaction = self.send_transaction()
            print(f"Sent transaction {i+1}/{count}: {transaction['transaction_id']} - Amount: ${transaction['amount']:.2f} - Fraud: {bool(transaction['is_fraud'])}")
            time.sleep(interval)
        
        self.producer.flush()
        print("Transaction simulation completed")

# Example usage
if __name__ == "__main__":
    producer = TransactionProducer()
    producer.simulate_transactions(count=20, interval=0.5)