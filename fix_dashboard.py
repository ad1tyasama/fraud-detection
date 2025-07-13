import os
import sqlite3
import json
import random
from datetime import datetime, timedelta

def ensure_directory_structure():
    """Ensure all necessary directories exist."""
    os.makedirs('dashboard', exist_ok=True)
    os.makedirs('dashboard/templates', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    os.makedirs('data', exist_ok=True)

def generate_sample_data():
    """Generate sample data for the dashboard."""
    # Create database connection
    conn = sqlite3.connect('dashboard/dashboard.db')
    cursor = conn.cursor()
    
    # Create transactions table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE,
        user_id TEXT,
        amount REAL,
        transaction_type TEXT,
        merchant_category TEXT,
        country TEXT,
        device TEXT,
        timestamp TEXT,
        is_fraud BOOLEAN,
        fraud_score REAL,
        isolation_forest_score REAL,
        autoencoder_score REAL,
        data JSON
    )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM transactions')
    
    # Generate sample transactions
    countries = ['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU', 'RU', 'CN', 'BR']
    transaction_types = ['purchase', 'withdrawal', 'transfer', 'payment']
    merchant_categories = ['retail', 'food', 'travel', 'entertainment', 'other']
    devices = ['mobile', 'web', 'atm', 'pos', 'unknown']
    
    # Generate transactions for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Generate 500 transactions
    for i in range(500):
        # Random date within the range
        days_ago = random.randint(0, 30)
        tx_date = end_date - timedelta(days=days_ago)
        timestamp = tx_date.isoformat()
        
        # Transaction details
        transaction_id = f"T-{i+1:05d}"
        user_id = f"U-{random.randint(1000, 9999)}"
        amount = round(random.uniform(10, 1000), 2)
        transaction_type = random.choice(transaction_types)
        merchant_category = random.choice(merchant_categories) if transaction_type == 'purchase' else None
        country = random.choice(countries)
        device = random.choice(devices)
        
        # Fraud determination (5% chance)
        is_fraud = random.random() < 0.05
        
        # Fraud scores
        if is_fraud:
            isolation_forest_score = round(random.uniform(0.7, 0.95), 2)
            autoencoder_score = round(random.uniform(0.65, 0.9), 2)
            fraud_score = round((isolation_forest_score + autoencoder_score) / 2, 2)
        else:
            isolation_forest_score = round(random.uniform(0.05, 0.3), 2)
            autoencoder_score = round(random.uniform(0.1, 0.35), 2)
            fraud_score = round((isolation_forest_score + autoencoder_score) / 2, 2)
        
        # Transaction data as JSON
        data = {
            'transaction_id': transaction_id,
            'user_id': user_id,
            'amount': amount,
            'transaction_type': transaction_type,
            'merchant_category': merchant_category,
            'country': country,
            'device': device,
            'timestamp': timestamp,
            'models': {
                'isolation_forest': {
                    'is_fraud': isolation_forest_score > 0.6,
                    'fraud_score': isolation_forest_score
                },
                'autoencoder': {
                    'is_fraud': autoencoder_score > 0.6,
                    'fraud_score': autoencoder_score
                }
            },
            'ensemble': {
                'is_fraud': is_fraud,
                'fraud_score': fraud_score
            }
        }
        
        data_json = json.dumps(data)
        
        # Insert into database
        cursor.execute('''
        INSERT INTO transactions 
        (transaction_id, user_id, amount, transaction_type, merchant_category, country, device, 
         timestamp, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id, user_id, amount, transaction_type, merchant_category, country, device,
            timestamp, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, data_json
        ))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Generated 500 sample transactions in dashboard/dashboard.db")

if __name__ == "__main__":
    print("Fixing dashboard...")
    ensure_directory_structure()
    generate_sample_data()
    print("Dashboard fixed! You can now run the dashboard with 'python -m dashboard.dashboard_api'")

