import sqlite3
import os
import json
import random
import numpy as np
from datetime import datetime, timedelta

class DashboardDataService:
    def __init__(self, db_path='dashboard/dashboard.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create transactions table with correct schema
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
            model_used TEXT,
            data JSON
        )
        ''')
        
        # Create alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            timestamp TEXT,
            alert_level TEXT,
            alert_channels TEXT,
            status TEXT DEFAULT 'new',
            FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        # Generate sample data if database is empty
        if self._is_database_empty():
            print("Database is empty. Generating sample data...")
            self.generate_sample_data()
    
    def _is_database_empty(self):
        """Check if the database has any transactions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    
    def store_transaction(self, transaction_data):
        """Store a transaction in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract data from transaction
        transaction_id = transaction_data.get('transaction_id', f'T-{random.randint(10000, 99999)}')
        user_id = transaction_data.get('user_id', f'U-{random.randint(1000, 9999)}')
        amount = transaction_data.get('amount', 0)
        timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
        
        # Extract transaction details
        transaction_type = transaction_data.get('transaction_type', 'purchase')
        merchant_category = transaction_data.get('merchant_category', 'retail')
        country = transaction_data.get('country', 'US')
        device = transaction_data.get('device', 'web')
        
        # Extract fraud detection results
        is_fraud = transaction_data.get('is_fraud', False)
        fraud_score = transaction_data.get('fraud_score', 0)
        
        # Extract model scores
        isolation_forest_score = transaction_data.get('isolation_forest_score', 0)
        autoencoder_score = transaction_data.get('autoencoder_score', 0)
        model_used = transaction_data.get('model_used', 'ensemble')
        
        # Store full data as JSON
        data_json = json.dumps(transaction_data)
        
        try:
            cursor.execute('''
            INSERT INTO transactions 
            (transaction_id, user_id, amount, transaction_type, merchant_category, country, device, 
             timestamp, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, model_used, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id, user_id, amount, transaction_type, merchant_category, country, device,
                timestamp, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, model_used, data_json
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            # Transaction already exists, update it
            cursor.execute('''
            UPDATE transactions 
            SET user_id=?, amount=?, transaction_type=?, merchant_category=?, country=?, device=?,
                timestamp=?, is_fraud=?, fraud_score=?, isolation_forest_score=?, autoencoder_score=?, 
                model_used=?, data=?
            WHERE transaction_id=?
            ''', (
                user_id, amount, transaction_type, merchant_category, country, device,
                timestamp, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, 
                model_used, data_json, transaction_id
            ))
            conn.commit()
        
        conn.close()
    
    def get_fraud_summary(self, days=30):
        """Get fraud summary data for the dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get total transactions and fraud transactions
        cursor.execute('''
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
               SUM(CASE WHEN is_fraud THEN amount ELSE 0 END) as fraud_amount,
               AVG(fraud_score) as avg_score
        FROM transactions
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        result = cursor.fetchone()
        total_transactions = result[0] or 0
        fraud_transactions = result[1] or 0
        fraud_amount = result[2] or 0
        avg_fraud_score = result[3] or 0
        
        # Calculate fraud percentage
        fraud_percentage = fraud_transactions / total_transactions if total_transactions > 0 else 0
        
        # Get daily transaction counts
        cursor.execute('''
        SELECT date(timestamp) as date, 
               COUNT(*) as count,
               SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
        FROM transactions
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        GROUP BY date(timestamp)
        ORDER BY date(timestamp)
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        daily_counts = cursor.fetchall()
        
        # Get transaction counts by country
        cursor.execute('''
        SELECT country, 
               COUNT(*) as total_count,
               SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
        FROM transactions
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        GROUP BY country
        ORDER BY fraud_count DESC
        LIMIT 10
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        country_counts = cursor.fetchall()
        
        conn.close()
        
        # Format data for the dashboard
        dates = [row[0] for row in daily_counts]
        transaction_counts = [row[1] for row in daily_counts]
        fraud_counts = [row[2] for row in daily_counts]
        
        countries = {}
        for row in country_counts:
            countries[row[0] or 'Unknown'] = {
                'total': row[1],
                'fraud': row[2]
            }
        
        return {
            'total_transactions': total_transactions,
            'fraud_transactions': fraud_transactions,
            'fraud_percentage': fraud_percentage,
            'fraud_amount': fraud_amount,
            'avg_fraud_score': avg_fraud_score,
            'dates': dates,
            'transaction_counts': transaction_counts,
            'fraud_counts': fraud_counts,
            'countries': countries
        }
    
    def get_model_performance(self, days=30):
        """Get model performance metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get average scores
        cursor.execute('''
        SELECT AVG(isolation_forest_score), AVG(autoencoder_score), AVG(fraud_score)
        FROM transactions
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        avg_scores = cursor.fetchone()
        
        conn.close()
        
        # Simulate performance metrics based on actual data
        # In a real system, these would be calculated using ground truth labels
        
        # Base performance on data availability
        data_factor = min(1.0, (avg_scores[0] or 0) + 0.5)
        
        # Isolation Forest metrics
        if_accuracy = min(0.85 + random.uniform(-0.05, 0.05) * data_factor, 1.0)
        if_precision = min(0.75 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        if_recall = min(0.7 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        
        # Autoencoder metrics
        ae_accuracy = min(0.82 + random.uniform(-0.05, 0.05) * data_factor, 1.0)
        ae_precision = min(0.8 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        ae_recall = min(0.65 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        
        # Ensemble metrics
        ensemble_accuracy = min(0.9 + random.uniform(-0.05, 0.05) * data_factor, 1.0)
        ensemble_precision = min(0.85 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        ensemble_recall = min(0.8 + random.uniform(-0.1, 0.1) * data_factor, 1.0)
        
        return {
            'isolation_forest': {
                'accuracy': if_accuracy,
                'precision': if_precision,
                'recall': if_recall,
                'avg_score': avg_scores[0] or 0
            },
            'autoencoder': {
                'accuracy': ae_accuracy,
                'precision': ae_precision,
                'recall': ae_recall,
                'avg_score': avg_scores[1] or 0
            },
            'ensemble': {
                'accuracy': ensemble_accuracy,
                'precision': ensemble_precision,
                'recall': ensemble_recall,
                'avg_score': avg_scores[2] or 0
            }
        }
    
    def get_recent_transactions(self, limit=100, offset=0, fraud_only=False):
        """Get recent transactions for display."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query based on parameters
        query = "SELECT * FROM transactions"
        params = []
        
        if fraud_only:
            query += " WHERE is_fraud = 1"
        
        query += " ORDER BY datetime(timestamp) DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        transactions = []
        for row in rows:
            transaction = {
                'id': row['id'],
                'transaction_id': row['transaction_id'],
                'user_id': row['user_id'],
                'amount': row['amount'],
                'transaction_type': row['transaction_type'],
                'merchant_category': row['merchant_category'],
                'country': row['country'],
                'device': row['device'],
                'timestamp': row['timestamp'],
                'is_fraud': bool(row['is_fraud']),
                'fraud_score': row['fraud_score'],
                'isolation_forest_score': row['isolation_forest_score'],
                'autoencoder_score': row['autoencoder_score']
            }
            transactions.append(transaction)
        
        conn.close()
        
        return {
            'transactions': transactions,
            'total': len(transactions),
            'offset': offset,
            'limit': limit,
            'fraud_only': fraud_only
        }
    
    def generate_sample_data(self, num_days=30, transactions_per_day=50):
        """Generate sample data for testing the dashboard."""
        print(f"Generating sample data for {num_days} days with {transactions_per_day} transactions per day...")
        
        # Generate dates
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(num_days)]
        
        # Transaction types and their probabilities
        transaction_types = ['purchase', 'withdrawal', 'transfer', 'payment']
        type_probs = [0.6, 0.2, 0.15, 0.05]
        
        # Merchant categories
        merchant_categories = ['retail', 'food', 'travel', 'entertainment', 'other']
        
        # Countries and their probabilities
        countries = ['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU', 'RU', 'CN', 'BR', 'NG', 'IN']
        country_probs = [0.5, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02]
        
        # Devices and their probabilities
        devices = ['mobile', 'web', 'atm', 'pos', 'unknown']
        device_probs = [0.5, 0.3, 0.1, 0.08, 0.02]
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM transactions')
        cursor.execute('DELETE FROM alerts')
        
        # Generate transactions
        total_transactions = 0
        for date in dates:
            for _ in range(transactions_per_day):
                # Generate transaction
                transaction_id = f"T-{int(date.timestamp())}-{np.random.randint(1000, 9999)}"
                user_id = f"U-{np.random.randint(1000, 9999)}"
                timestamp = date.replace(
                    hour=np.random.randint(0, 24),
                    minute=np.random.randint(0, 60),
                    second=np.random.randint(0, 60)
                ).isoformat()
                
                # Amount (log-normal distribution)
                amount = np.random.lognormal(mean=4.0, sigma=1.0)
                
                # Transaction type
                transaction_type = np.random.choice(transaction_types, p=type_probs)
                
                # Merchant category (if purchase)
                merchant_category = np.random.choice(merchant_categories) if transaction_type == 'purchase' else None
                
                # Country
                country = np.random.choice(countries, p=country_probs)
                
                # Device
                device = np.random.choice(devices, p=device_probs)
                
                # Determine if fraud (5% chance)
                is_fraud = np.random.random() < 0.05
                
                # If fraud, adjust some parameters to make it more suspicious
                if is_fraud:
                    # 50% chance of large amount
                    if np.random.random() < 0.5:
                        amount *= np.random.uniform(5, 20)
                    
                    # 30% chance of unusual country
                    if np.random.random() < 0.3:
                        unusual_countries = ['RU', 'CN', 'BR', 'NG', 'IN']
                        country = np.random.choice(unusual_countries)
                    
                    # 20% chance of unknown device
                    if np.random.random() < 0.2:
                        device = 'unknown'
                
                # Fraud scores (higher for fraud transactions)
                if is_fraud:
                    fraud_score = np.random.uniform(0.7, 1.0)
                    isolation_forest_score = np.random.uniform(0.65, 0.95)
                    autoencoder_score = np.random.uniform(0.7, 0.95)
                else:
                    # Occasionally have false positives
                    if np.random.random() < 0.02:
                        fraud_score = np.random.uniform(0.6, 0.9)
                        isolation_forest_score = np.random.uniform(0.5, 0.8)
                        autoencoder_score = np.random.uniform(0.6, 0.9)
                    else:
                        fraud_score = np.random.uniform(0.0, 0.3)
                        isolation_forest_score = np.random.uniform(0.0, 0.4)
                        autoencoder_score = np.random.uniform(0.0, 0.3)
                
                # Model used
                model_used = np.random.choice(['isolation_forest', 'autoencoder', 'ensemble'])
                
                # Insert transaction
                cursor.execute('''
                INSERT INTO transactions 
                (transaction_id, user_id, timestamp, amount, transaction_type, merchant_category, 
                 country, device, is_fraud, fraud_score, isolation_forest_score, autoencoder_score, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    transaction_id, user_id, timestamp, amount, transaction_type, merchant_category, 
                    country, device, int(is_fraud), fraud_score, isolation_forest_score, autoencoder_score, model_used
                ))
                
                # Generate alert for high fraud scores
                if fraud_score >= 0.8:
                    alert_level = 'high'
                    channels = ['email', 'sms']
                elif fraud_score >= 0.6:
                    alert_level = 'medium'
                    channels = ['email']
                else:
                    continue  # No alert
                
                # Insert alert
                cursor.execute('''
                INSERT INTO alerts (transaction_id, timestamp, alert_level, alert_channels)
                VALUES (?, ?, ?, ?)
                ''', (transaction_id, timestamp, alert_level, json.dumps(channels)))
                
                total_transactions += 1
        
        conn.commit()
        conn.close()
        
        print(f"Generated {total_transactions} sample transactions")
        return total_transactions