import requests
import json
import random
import time
from datetime import datetime, timedelta
import numpy as np

def generate_transaction(is_fraud=False):
    """Generate a random transaction."""
    # Transaction types and their probabilities
    transaction_types = ['purchase', 'withdrawal', 'transfer', 'payment']
    
    # Merchant categories
    merchant_categories = ['retail', 'food', 'travel', 'entertainment', 'other']
    
    # Countries
    countries = ['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU']
    unusual_countries = ['RU', 'CN', 'BR', 'NG', 'IN']
    
    # Devices
    devices = ['mobile', 'web', 'atm', 'pos']
    
    # Generate transaction
    transaction_id = f"T-{int(time.time())}-{random.randint(1000, 9999)}"
    user_id = f"U-{random.randint(1000, 9999)}"
    timestamp = datetime.now().isoformat()
    
    # Amount (log-normal distribution)
    amount = np.random.lognormal(mean=4.0, sigma=1.0)
    
    # Transaction type
    transaction_type = random.choice(transaction_types)
    
    # Merchant category (if purchase)
    merchant_category = random.choice(merchant_categories) if transaction_type == 'purchase' else None
    
    # Country
    country = random.choice(countries)
    
    # Device
    device = random.choice(devices)
    
    # If fraud, adjust parameters
    if is_fraud:
        # Larger amount
        amount *= random.uniform(5, 20)
        
        # Unusual country
        country = random.choice(unusual_countries)
        
        # Possibly unknown device
        if random.random() < 0.5:
            device = 'unknown'
    
    # Create transaction
    transaction = {
        'transaction_id': transaction_id,
        'user_id': user_id,
        'timestamp': timestamp,
        'amount': round(amount, 2),
        'transaction_type': transaction_type,
        'merchant_category': merchant_category,
        'country': country,
        'device': device
    }
    
    return transaction

def send_transaction(transaction):
    """Send a transaction to the API."""
    url = 'http://localhost:5000/api/detect'
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=transaction)
        if response.status_code == 200:
            result = response.json()
            fraud_score = result.get('ensemble', {}).get('fraud_score', 0)
            is_fraud = result.get('ensemble', {}).get('is_fraud', False)
            print(f"Transaction {transaction['transaction_id']} - Amount: ${transaction['amount']:.2f}")
            print(f"Fraud Score: {fraud_score:.4f} - Is Fraud: {is_fraud}")
            print("-" * 50)
            return True
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def generate_and_send_transactions(count=20, fraud_ratio=0.2, interval=1.0):
    """Generate and send multiple transactions."""
    print(f"Generating {count} transactions ({fraud_ratio*100:.0f}% fraudulent)...")
    
    success_count = 0
    for i in range(count):
        # Determine if this transaction should be fraudulent
        is_fraud = random.random() < fraud_ratio
        
        # Generate transaction
        transaction = generate_transaction(is_fraud)
        
        # Send transaction
        if send_transaction(transaction):
            success_count += 1
        
        # Wait between transactions
        if i < count - 1:
            time.sleep(interval)
    
    print(f"Successfully sent {success_count}/{count} transactions")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate and send test transactions')
    parser.add_argument('--count', type=int, default=20, help='Number of transactions to generate')
    parser.add_argument('--fraud-ratio', type=float, default=0.2, help='Ratio of fraudulent transactions')
    parser.add_argument('--interval', type=float, default=1.0, help='Interval between transactions (seconds)')
    
    args = parser.parse_args()
    
    generate_and_send_transactions(args.count, args.fraud_ratio, args.interval)