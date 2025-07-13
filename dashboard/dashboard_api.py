from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from dashboard.dashboard_data import DashboardDataService
import os
import json
from datetime import datetime, timedelta
import random

# Create Flask app with correct template folder
app = Flask(__name__, template_folder=os.path.abspath('dashboard/templates'))
app.secret_key = 'fraud_detection_secret_key'

# Initialize data service
data_service = DashboardDataService()

@app.route('/')
def dashboard():
    """Render the dashboard home page."""
    return render_template('dashboard.html')

@app.route('/api/summary')
def get_summary():
    """Get fraud summary data."""
    days = request.args.get('days', default=30, type=int)
    
    try:
        # Get data from service
        summary_data = data_service.get_fraud_summary(days=days)
        
        # Format data for the dashboard
        by_day = []
        for i in range(len(summary_data['dates'])):
            by_day.append({
                'date': summary_data['dates'][i],
                'transactions': summary_data['transaction_counts'][i],
                'fraud_count': summary_data['fraud_counts'][i]
            })
        
        by_country = []
        for country, data in summary_data['countries'].items():
            by_country.append({
                'country': country,
                'transactions': data['total'],
                'fraud_count': data['fraud']
            })
        
        # Get recent fraud transactions
        recent_fraud = []
        transactions = data_service.get_recent_transactions(limit=10, fraud_only=True)
        for tx in transactions['transactions']:
            recent_fraud.append({
                'id': tx['transaction_id'],
                'amount': tx['amount'],
                'timestamp': tx['timestamp'],
                'fraud_score': tx['fraud_score'],
                'details': {
                    'user_id': tx['user_id'],
                    'transaction_type': tx['transaction_type'],
                    'merchant_category': tx['merchant_category'],
                    'country': tx['country'],
                    'device': tx['device'],
                    'isolation_forest_score': tx['isolation_forest_score'],
                    'autoencoder_score': tx['autoencoder_score']
                }
            })
        
        return jsonify({
            'total_transactions': summary_data['total_transactions'],
            'total_fraud': summary_data['fraud_transactions'],
            'fraud_rate': summary_data['fraud_percentage'],
            'fraud_amount': summary_data['fraud_amount'],
            'by_day': by_day,
            'by_country': by_country,
            'recent_fraud': recent_fraud
        })
        
    except Exception as e:
        print(f"Error in get_summary: {e}")
        return jsonify({
            'error': str(e),
            'total_transactions': 0,
            'total_fraud': 0,
            'fraud_rate': 0,
            'fraud_amount': 0,
            'by_day': [],
            'by_country': [],
            'recent_fraud': []
        }), 500

@app.route('/api/performance')
def get_performance():
    """Get model performance data."""
    days = request.args.get('days', default=30, type=int)
    
    try:
        # Get performance data from service
        performance_data = data_service.get_model_performance(days=days)
        
        # Format for the dashboard
        models = {
            'Isolation Forest': {
                'accuracy': performance_data['isolation_forest']['accuracy'],
                'precision': performance_data['isolation_forest']['precision'],
                'recall': performance_data['isolation_forest']['recall'],
                'f1_score': calculate_f1(
                    performance_data['isolation_forest']['precision'],
                    performance_data['isolation_forest']['recall']
                )
            },
            'Autoencoder': {
                'accuracy': performance_data['autoencoder']['accuracy'],
                'precision': performance_data['autoencoder']['precision'],
                'recall': performance_data['autoencoder']['recall'],
                'f1_score': calculate_f1(
                    performance_data['autoencoder']['precision'],
                    performance_data['autoencoder']['recall']
                )
            }
        }
        
        # Calculate overall performance (average of models)
        overall = {
            'accuracy': (performance_data['isolation_forest']['accuracy'] + performance_data['autoencoder']['accuracy']) / 2,
            'precision': (performance_data['isolation_forest']['precision'] + performance_data['autoencoder']['precision']) / 2,
            'recall': (performance_data['isolation_forest']['recall'] + performance_data['autoencoder']['recall']) / 2,
            'f1_score': calculate_f1(
                (performance_data['isolation_forest']['precision'] + performance_data['autoencoder']['precision']) / 2,
                (performance_data['isolation_forest']['recall'] + performance_data['autoencoder']['recall']) / 2
            )
        }
        
        return jsonify({
            'models': models,
            'overall': overall
        })
        
    except Exception as e:
        print(f"Error in get_performance: {e}")
        return jsonify({
            'error': str(e),
            'models': {},
            'overall': {'accuracy': 0, 'precision': 0, 'recall': 0, 'f1_score': 0}
        }), 500

@app.route('/api/alerts')
def get_alerts():
    """Get alert data."""
    days = request.args.get('days', default=30, type=int)
    
    try:
        # Generate some sample alerts based on actual fraud transactions
        fraud_transactions = data_service.get_recent_transactions(limit=50, fraud_only=True)
        
        alerts = []
        alert_types = ['High Risk Transaction', 'Unusual Activity', 'Multiple Failed Attempts', 'New Device Login']
        
        for i, tx in enumerate(fraud_transactions['transactions'][:20]):
            alert = {
                'id': f"A-{i+1:04d}",
                'transaction_id': tx['transaction_id'],
                'timestamp': tx['timestamp'],
                'type': random.choice(alert_types),
                'level': 'high' if tx['fraud_score'] > 0.8 else 'medium' if tx['fraud_score'] > 0.6 else 'low',
                'message': f"Potential fraud detected on transaction {tx['transaction_id']} (Score: {tx['fraud_score']:.2f})",
                'status': random.choice(['new', 'acknowledged', 'resolved']),
                'details': {
                    'amount': tx['amount'],
                    'user_id': tx['user_id'],
                    'country': tx['country'],
                    'device': tx['device'],
                    'fraud_score': tx['fraud_score']
                }
            }
            alerts.append(alert)
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'alerts': alerts,
            'total': len(alerts),
            'new': sum(1 for a in alerts if a['status'] == 'new'),
            'acknowledged': sum(1 for a in alerts if a['status'] == 'acknowledged'),
            'resolved': sum(1 for a in alerts if a['status'] == 'resolved')
        })
        
    except Exception as e:
        print(f"Error in get_alerts: {e}")
        return jsonify({
            'alerts': [],
            'total': 0,
            'new': 0,
            'acknowledged': 0,
            'resolved': 0
        }), 500

@app.route('/api/transaction/<transaction_id>')
def get_transaction_details(transaction_id):
    """Get details for a specific transaction."""
    try:
        # Try to get actual transaction from database
        transactions = data_service.get_recent_transactions(limit=1000)
        transaction = None
        
        for tx in transactions['transactions']:
            if tx['transaction_id'] == transaction_id:
                transaction = tx
                break
        
        if not transaction:
            # Generate sample data if not found
            transaction = {
                'id': transaction_id,
                'user_id': f"U-{random.randint(1000, 9999)}",
                'amount': round(random.uniform(100, 5000), 2),
                'timestamp': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                'transaction_type': random.choice(['purchase', 'withdrawal', 'transfer', 'payment']),
                'merchant_category': random.choice(['retail', 'food', 'travel', 'entertainment', 'other']),
                'country': random.choice(['US', 'CA', 'UK', 'FR', 'DE', 'JP', 'AU']),
                'device': random.choice(['mobile', 'web', 'atm', 'pos']),
                'is_fraud': True,
                'fraud_score': round(random.uniform(0.7, 0.95), 2),
                'isolation_forest_score': round(random.uniform(0.65, 0.9), 2),
                'autoencoder_score': round(random.uniform(0.7, 0.95), 2)
            }
        
        # Add additional fields for the modal
        transaction.update({
            'alert_status': random.choice(['new', 'acknowledged', 'resolved']),
            'alert_channels': random.sample(['email', 'sms', 'push', 'webhook'], k=random.randint(1, 3)),
            'ip_address': f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}",
        })
        
        return jsonify(transaction)
        
    except Exception as e:
        print(f"Error in get_transaction_details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings')
def get_settings():
    """Get system settings."""
    settings = {
        'alert_thresholds': {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        },
        'notification_channels': {
            'email': True,
            'sms': True,
            'webhook': False,
            'push': False
        },
        'model_weights': {
            'isolation_forest': 0.5,
            'autoencoder': 0.5
        },
        'dashboard_refresh_rate': 5,
        'data_retention_days': 90,
        'system_status': {
            'api': 'online',
            'database': 'online',
            'models': 'online',
            'streaming': 'online'
        }
    }
    
    return jsonify(settings)

@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    """Update system settings."""
    try:
        settings = request.get_json()
        # In a real system, this would update the settings in a database
        print(f"Settings updated: {settings}")
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/regenerate-data', methods=['POST'])
def regenerate_data():
    """Regenerate sample data for testing."""
    try:
        count = data_service.generate_sample_data()
        return jsonify({
            'success': True,
            'message': f'Generated {count} sample transactions',
            'count': count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def calculate_f1(precision, recall):
    """Calculate F1 score from precision and recall."""
    if precision + recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('dashboard', exist_ok=True)
    
    print("Starting Fraud Detection Dashboard...")
    print("Dashboard will be available at: http://localhost:5001")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5001)