from kafka import KafkaConsumer
import json
import numpy as np
import pandas as pd
import joblib
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.isolation_forest import FraudDetectionIsolationForest
from models.autoencoder import FraudDetectionAutoencoder

class TransactionConsumer:
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='transactions',
                 isolation_forest_path=None, autoencoder_path=None, scaler_path=None):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='fraud-detection-group'
        )
        
        # Load models if paths are provided
        self.isolation_forest = None
        self.autoencoder = None
        self.scaler = None
        
        if isolation_forest_path:
            self.isolation_forest = FraudDetectionIsolationForest.load_model(isolation_forest_path)
        
        if autoencoder_path and scaler_path:
            # Load scaler first to get input dimensions
            self.scaler = joblib.load(scaler_path)
            # Get input dimension from scaler
            sample_data = np.zeros((1, len(self.scaler.mean_)))
            input_dim = self.scaler.transform(sample_data).shape[1]
            # Load autoencoder
            self.autoencoder = FraudDetectionAutoencoder.load_model(autoencoder_path, input_dim)
    
    def preprocess_transaction(self, transaction):
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
        if self.scaler:
            X = self.scaler.transform(df)
        else:
            X = df.values
        
        return X
    
    def detect_fraud(self, transaction):
        """Detect if a transaction is fraudulent using loaded models."""
        # Preprocess transaction
        X = self.preprocess_transaction(transaction)
        
        results = {
            'transaction_id': transaction.get('transaction_id', 'unknown'),
            'amount': transaction.get('amount', 0),
            'timestamp': transaction.get('timestamp', datetime.now().isoformat()),
            'user_id': transaction.get('user_id', 'unknown'),
            'models': {}
        }
        
        # Isolation Forest prediction
        if self.isolation_forest:
            is_fraud_if = bool(self.isolation_forest.predict(X)[0])
            fraud_score_if = float(self.isolation_forest.predict_proba(X)[0])
            
            results['models']['isolation_forest'] = {
                'is_fraud': is_fraud_if,
                'fraud_score': fraud_score_if
            }
        
        # Autoencoder prediction
        if self.autoencoder:
            is_fraud_ae = bool(self.autoencoder.predict(X)[0])
            fraud_score_ae = float(self.autoencoder.predict_proba(X)[0])
            
            results['models']['autoencoder'] = {
                'is_fraud': is_fraud_ae,
                'fraud_score': fraud_score_ae
            }
        
        # Ensemble decision (if both models are available)
        if self.isolation_forest and self.autoencoder:
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
        
        # Add ground truth if available (for testing)
        if 'is_fraud' in transaction:
            results['actual_fraud'] = bool(transaction['is_fraud'])
        
        return results
    
    def process_transactions(self, max_count=None):
        """Process incoming transactions from Kafka stream."""
        print("Starting to consume transactions...")
        count = 0
        
        for message in self.consumer:
            transaction = message.value
            
            # Detect fraud
            result = self.detect_fraud(transaction)
            
            # Print result
            is_fraud = result.get('ensemble', {}).get('is_fraud', False)
            fraud_score = result.get('ensemble', {}).get('fraud_score', 0)
            
            if is_fraud:
                print(f"⚠️ FRAUD ALERT! Transaction {result['transaction_id']} - Score: {fraud_score:.4f}")
                print(f"   Amount: ${result['amount']:.2f}, User: {result['user_id']}")
                
                # Here you would trigger alerts (SMS, email, etc.)
                # self.send_alert(result)
            else:
                print(f"✓ Transaction {result['transaction_id']} - Score: {fraud_score:.4f}")
            
            # For testing: compare with actual fraud label
            if 'actual_fraud' in result:
                if result['actual_fraud'] == is_fraud:
                    print(f"   Correct prediction! Actual: {result['actual_fraud']}")
                else:
                    print(f"   Incorrect prediction! Actual: {result['actual_fraud']}")
            
            count += 1
            if max_count and count >= max_count:
                break
        
        print(f"Processed {count} transactions")

# Example usage
if __name__ == "__main__":
    consumer = TransactionConsumer(
        isolation_forest_path='../models/isolation_forest_model.joblib',
        autoencoder_path='../models/autoencoder_model',
        scaler_path='../models/scaler.joblib'
    )
    consumer.process_transactions(max_count=20)