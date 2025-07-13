import os
import sys
import time
import subprocess
import threading
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

print("Step 1: Creating necessary directories...")
# Ensure all directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs('dashboard', exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('dashboard/templates', exist_ok=True)

print("Step 2: Generating synthetic data for training...")
# Generate synthetic data for training
def generate_training_data(num_samples=10000):
    # Generate features
    n_features = 10
    X = np.random.randn(num_samples, n_features)
    
    # Generate target (5% fraud)
    y = np.zeros(num_samples)
    fraud_indices = np.random.choice(num_samples, size=int(0.05 * num_samples), replace=False)
    y[fraud_indices] = 1
    
    # Create DataFrame
    features = [f'feature_{i}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=features)
    df['is_fraud'] = y
    
    # Add timestamp
    dates = pd.date_range('2023-01-01', periods=num_samples)
    df['timestamp'] = np.random.choice(dates, num_samples)
    
    # Save to CSV
    df.to_csv('data/transactions.csv', index=False)
    print(f"Generated {num_samples} training samples and saved to data/transactions.csv")

generate_training_data()

print("Step 3: Training models...")
# Import and train models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_preprocessing import load_and_preprocess_data
from models.isolation_forest import FraudDetectionIsolationForest
from models.autoencoder import FraudDetectionAutoencoder

# Train models
try:
    # Load and preprocess data
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data('data/transactions.csv')
    
    # Save scaler
    import joblib
    joblib.dump(scaler, 'models/scaler.joblib')
    
    # Train Isolation Forest
    isolation_forest = FraudDetectionIsolationForest()
    isolation_forest.train(X_train, y_train)
    isolation_forest.save_model('models/isolation_forest_model.joblib')
    
    # Train Autoencoder
    input_dim = X_train.shape[1]
    autoencoder = FraudDetectionAutoencoder(input_dim=input_dim)
    autoencoder.train(X_train, y_train, epochs=5)  # Reduced epochs for faster training
    autoencoder.save_model('models/autoencoder_model')
    
    print("Models trained successfully!")
except Exception as e:
    print(f"Error during model training: {e}")
    sys.exit(1)

print("Step 4: Generating dashboard sample data...")
# Generate dashboard sample data
from dashboard.dashboard_data import DashboardDataService
dashboard_data = DashboardDataService()
dashboard_data.generate_sample_data(num_days=30, transactions_per_day=20)

print("Step 5: Starting the system...")
# Start Flask API in a separate process
api_process = subprocess.Popen([sys.executable, 'app.py'])
print("API server started on http://localhost:5000")

# Wait a moment to ensure API is up
time.sleep(2)

# Start Dashboard in a separate process
dashboard_process = subprocess.Popen([sys.executable, 'dashboard/dashboard_api.py'])
print("Dashboard started on http://localhost:5001")

# Wait a moment to ensure dashboard is up
time.sleep(2)

print("Step 6: Generating test transactions...")
# Generate and send some test transactions
def generate_transaction(is_fraud=False):
    """Generate a random transaction."""
    # Transaction types and their probabilities
    transaction_types = ['purchase', 'withdrawal', 'transfer', 'payment']
    
    # Merchant categories
    merchant_categories = ['retail', 'food', 'travel', 'entertainment', 'other']
    
    # Countries
    countries = ['US', 'CA', 'UK', 'FR', 'DE', 'entertainment', 'other']
    
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
    transaction_type = np.random.choice(transaction_types)
    
    # Merchant category (if purchase)
    merchant_category = np.random.choice(merchant_categories) if transaction_type == 'purchase' else None
    
    # Country
    country = np.random.choice(countries)
    
    # Device
    device = np.random.choice(devices)
    
    # If fraud, adjust parameters
    if is_fraud:
        # Larger amount
        amount *= np.random.uniform(5, 20)
        
        # Unusual country
        country = np.random.choice(unusual_countries)
        
        # Possibly unknown device
        if np.random.random() < 0.5:
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

# Generate and send 20 transactions (5 fraudulent)
import random
import requests

for i in range(20):
    # 25% chance of fraud
    is_fraud = random.random() < 0.25
    transaction = generate_transaction(is_fraud)
    
    try:
        response = requests.post(
            'http://localhost:5000/api/detect',
            json=transaction,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            fraud_score = result.get('ensemble', {}).get('fraud_score', 0)
            is_fraud_detected = result.get('ensemble', {}).get('is_fraud', False)
            print(f"Transaction {i+1}/20: {'⚠️ FRAUD' if is_fraud_detected else '✓ SAFE'} - Score: {fraud_score:.4f}")
        else:
            print(f"Transaction {i+1}/20: Error {response.status_code}")
    except Exception as e:
        print(f"Transaction {i+1}/20: Exception - {str(e)}")
    
    # Small delay between transactions
    time.sleep(0.5)

print("\nSystem is now running!")
print("- API: http://localhost:5000")
print("- Dashboard: http://localhost:5001")
print("\nTest the API with:")
print("""
curl -X POST http://localhost:5000/api/detect \\
  -H "Content-Type: application/json" \\
  -d '{
    "transaction_id": "T-12345",
    "user_id": "U-789",
    "amount": 1299.99,
    "transaction_type": "purchase",
    "merchant_category": "electronics",
    "country": "US",
    "device": "mobile",
    "timestamp": "2023-06-15T14:30:45"
  }'
""")

print("\nPress Ctrl+C to stop the system...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping the system...")
    api_process.terminate()
    dashboard_process.terminate()
    print("System stopped.")