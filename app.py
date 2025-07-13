from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
import pandas as pd
import os
import json
from datetime import datetime

# Import models
from models.isolation_forest import FraudDetectionIsolationForest
from models.autoencoder import FraudDetectionAutoencoder

app = Flask(__name__)

# Load models
isolation_forest = None
autoencoder = None
scaler = None

def load_models():
    global isolation_forest, autoencoder, scaler
    
    # Load Isolation Forest
    if os.path.exists('models/isolation_forest_model.joblib'):
        isolation_forest = FraudDetectionIsolationForest.load_model('models/isolation_forest_model.joblib')
    
    # Load scaler
    if os.path.exists('models/scaler.joblib'):
        scaler = joblib.load('models/scaler.joblib')
    
    # Load Autoencoder
    if os.path.exists('models/autoencoder_model_keras') and scaler is not None:
        # Get input dimension from scaler
        sample_data = np.zeros((1, len(scaler.mean_)))
        input_dim = scaler.transform(sample_data).shape[1]
        # Load autoencoder
        autoencoder = FraudDetectionAutoencoder.load_model('models/autoencoder_model', input_dim)

# Load models at startup instead of waiting for first request
load_models()

def preprocess_transaction(transaction):
    """Preprocess a transaction for model input."""
    # Extract features
    features = {}
    
    # Numeric features
    features['amount'] = transaction.get('amount', 0)
    
    # Categorical features (one-hot encoded)
    # Transaction type
    for t_type in ['purchase', 'withdrawal', 'transfer', 'payment']:
        features[f'type_{t_type}'] = 1 if transaction.get('transaction_type') == t_type else 0
    
    # Merchant category (if applicable)
    merchant_cat = transaction.get('merchant_category')
    if merchant_cat:
        for category in ['retail', 'food', 'travel', 'entertainment', 'other']:
            features[f'merchant_{category}'] = 1 if merchant_cat == category else 0
    else:
        for category in ['retail', 'food', 'travel', 'entertainment', 'other']:
            features[f'merchant_{category}'] = 0
    
    # Country
    countries = ['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU', 'RU', 'CN', 'BR', 'NG', 'IN']
    for country in countries:
        features[f'country_{country}'] = 1 if transaction.get('country') == country else 0
    
    # Device
    devices = ['mobile', 'web', 'atm', 'pos', 'unknown']
    for device in devices:
        features[f'device_{device}'] = 1 if transaction.get('device') == device else 0
    
    # Time features
    if 'timestamp' in transaction:
        try:
            dt = datetime.fromisoformat(transaction['timestamp'])
            features['hour'] = dt.hour / 24.0  # Normalize to [0, 1]
            features['day_of_week'] = dt.weekday() / 6.0  # Normalize to [0, 1]
            features['month'] = (dt.month - 1) / 11.0  # Normalize to [0, 1]
        except (ValueError, TypeError):
            features['hour'] = 0
            features['day_of_week'] = 0
            features['month'] = 0
    
    # Convert to DataFrame
    df = pd.DataFrame([features])
    
    # Scale features if scaler is available
    if scaler:
        X = scaler.transform(df)
    else:
        X = df.values
    
    return X

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/detect', methods=['GET', 'POST'])
def detect_fraud():
    """API endpoint to detect fraud in a transaction."""
    if request.method == 'GET':
        return jsonify({
            'message': 'Fraud detection API is running. Send a POST request with transaction data to detect fraud.',
            'example': {
                'transaction_id': 'T-12345',
                'user_id': 'U-789',
                'amount': 1299.99,
                'transaction_type': 'purchase',
                'merchant_category': 'electronics',
                'country': 'US',
                'device': 'mobile',
                'timestamp': '2023-06-15T14:30:45'
            }
        })
    
    if request.is_json:
        transaction = request.get_json()
    else:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    # Validate transaction
    required_fields = ['amount', 'transaction_type']
    for field in required_fields:
        if field not in transaction:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Preprocess transaction
    X = preprocess_transaction(transaction)
    
    results = {
        'transaction_id': transaction.get('transaction_id', 'unknown'),
        'amount': transaction.get('amount', 0),
        'timestamp': transaction.get('timestamp', datetime.now().isoformat()),
        'user_id': transaction.get('user_id', 'unknown'),
        'models': {}
    }
    
    # Isolation Forest prediction
    if isolation_forest:
        is_fraud_if = bool(isolation_forest.predict(X)[0])
        fraud_score_if = float(isolation_forest.predict_proba(X)[0])
        
        results['models']['isolation_forest'] = {
            'is_fraud': is_fraud_if,
            'fraud_score': fraud_score_if
        }
    
    # Autoencoder prediction
    if autoencoder:
        is_fraud_ae = bool(autoencoder.predict(X)[0])
        fraud_score_ae = float(autoencoder.predict_proba(X)[0])
        
        results['models']['autoencoder'] = {
            'is_fraud': is_fraud_ae,
            'fraud_score': fraud_score_ae
        }
    
    # Ensemble decision (if both models are available)
    if isolation_forest and autoencoder:
        # Average of both scores
        avg_score = (results['models']['isolation_forest']['fraud_score'] + 
                     results['models']['autoencoder']['fraud_score']) / 2
        
        # Fraud if either model predicts fraud with high confidence
        is_fraud = (results['models']['isolation_forest']['is_fraud'] and 
                    results['models']['isolation_forest']['fraud_score'] > 0.7) or \
                   (results['models']['autoencoder']['is_fraud'] and 
                    results['models']['autoencoder']['fraud_score'] > 0.7)
        
        results['ensemble'] = {
            'is_fraud': is_fraud,
            'fraud_score': avg_score
        }
    
    # If fraud is detected, trigger alert
    if results.get('ensemble', {}).get('is_fraud', False):
        # In a real system, this would call the alert service
        results['alert'] = {
            'status': 'triggered',
            'message': f"Potential fraud detected for transaction {results['transaction_id']}"
        }
    
    # Store the transaction in the dashboard database
    try:
        from dashboard.dashboard_data import DashboardDataService
        dashboard_data = DashboardDataService()
        dashboard_data.store_transaction(results)
    except Exception as e:
        print(f"Error storing transaction in dashboard: {e}")
    
    return jsonify(results)

@app.route('/api/batch-detect', methods=['GET', 'POST'])
def batch_detect_fraud():
    """API endpoint to detect fraud in a batch of transactions."""
    if request.method == 'GET':
        return jsonify({
            'message': 'Batch fraud detection API is running. Send a POST request with an array of transactions.',
            'example': [
                {
                    'transaction_id': 'T-12345',
                    'amount': 1299.99,
                    'transaction_type': 'purchase'
                },
                {
                    'transaction_id': 'T-12346',
                    'amount': 9999.99,
                    'transaction_type': 'withdrawal'
                }
            ]
        })
    
    if request.is_json:
        transactions = request.get_json()
    else:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    if not isinstance(transactions, list):
        return jsonify({'error': 'Request must be a list of transactions'}), 400
    
    results = []
    for transaction in transactions:
        # Preprocess transaction
        X = preprocess_transaction(transaction)
        
        result = {
            'transaction_id': transaction.get('transaction_id', 'unknown'),
            'amount': transaction.get('amount', 0),
            'timestamp': transaction.get('timestamp', datetime.now().isoformat()),
            'user_id': transaction.get('user_id', 'unknown'),
            'models': {}
        }
        
        # Isolation Forest prediction
        if isolation_forest:
            is_fraud_if = bool(isolation_forest.predict(X)[0])
            fraud_score_if = float(isolation_forest.predict_proba(X)[0])
            
            result['models']['isolation_forest'] = {
                'is_fraud': is_fraud_if,
                'fraud_score': fraud_score_if
            }
        
        # Autoencoder prediction
        if autoencoder:
            is_fraud_ae = bool(autoencoder.predict(X)[0])
            fraud_score_ae = float(autoencoder.predict_proba(X)[0])
            
            result['models']['autoencoder'] = {
                'is_fraud': is_fraud_ae,
                'fraud_score': fraud_score_ae
            }
        
        # Ensemble decision
        if isolation_forest and autoencoder:
            avg_score = (result['models']['isolation_forest']['fraud_score'] + 
                         result['models']['autoencoder']['fraud_score']) / 2
            
            is_fraud = (result['models']['isolation_forest']['is_fraud'] and 
                        result['models']['isolation_forest']['fraud_score'] > 0.7) or \
                       (result['models']['autoencoder']['is_fraud'] and 
                        result['models']['autoencoder']['fraud_score'] > 0.7)
            
            result['ensemble'] = {
                'is_fraud': is_fraud,
                'fraud_score': avg_score
            }
        
        # Store the transaction in the dashboard database
        try:
            from dashboard.dashboard_data import DashboardDataService
            dashboard_data = DashboardDataService()
            dashboard_data.store_transaction(result)
        except Exception as e:
            print(f"Error storing transaction in dashboard: {e}")
        
        results.append(result)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)