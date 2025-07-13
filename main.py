import os
import sys
import threading
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fraud_detection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FraudDetectionSystem")

# Add modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from data_preprocessing import load_and_preprocess_data
from models.isolation_forest import FraudDetectionIsolationForest
from models.autoencoder import FraudDetectionAutoencoder
from streaming.kafka_producer import TransactionProducer
from streaming.kafka_consumer import TransactionConsumer
from alerts.alert_service import AlertService
from dashboard.dashboard_data import DashboardDataService

class FraudDetectionSystem:
    def __init__(self):
        self.data_path = 'data/transactions.csv'
        self.models_path = 'models'
        self.isolation_forest_path = os.path.join(self.models_path, 'isolation_forest_model.joblib')
        self.autoencoder_path = os.path.join(self.models_path, 'autoencoder_model')
        self.scaler_path = os.path.join(self.models_path, 'scaler.joblib')
        
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('models', exist_ok=True)
        os.makedirs('dashboard', exist_ok=True)
        os.makedirs('dashboard/templates', exist_ok=True)
        
        # Initialize components
        self.alert_service = AlertService()
        self.dashboard_data = DashboardDataService()
        
        # Flags
        self.is_training = False
        self.is_streaming = False
        
        logger.info("Fraud Detection System initialized")
    
    def train_models(self, data_path=None):
        """Train the fraud detection models."""
        if self.is_training:
            logger.warning("Training is already in progress")
            return False
        
        self.is_training = True
        logger.info("Starting model training")
        
        try:
            # Use provided data path or default
            if data_path is None:
                data_path = self.data_path
            
            # Load and preprocess data
            logger.info(f"Loading data from {data_path}")
            X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data(data_path)
            
            # Save scaler
            import joblib
            joblib.dump(scaler, self.scaler_path)
            logger.info(f"Scaler saved to {self.scaler_path}")
            
            # Train Isolation Forest
            logger.info("Training Isolation Forest model")
            isolation_forest = FraudDetectionIsolationForest()
            isolation_forest.train(X_train, y_train)
            isolation_forest.save_model(self.isolation_forest_path)
            
            # Evaluate Isolation Forest
            y_pred_if = isolation_forest.predict(X_test)
            accuracy_if = (y_pred_if == y_test).mean()
            logger.info(f"Isolation Forest accuracy: {accuracy_if:.4f}")
            
            # Train Autoencoder
            logger.info("Training Autoencoder model")
            input_dim = X_train.shape[1]
            autoencoder = FraudDetectionAutoencoder(input_dim=input_dim)
            autoencoder.train(X_train, y_train, epochs=20)
            autoencoder.save_model(self.autoencoder_path)
            
            # Evaluate Autoencoder
            y_pred_ae = autoencoder.predict(X_test)
            accuracy_ae = (y_pred_ae == y_test).mean()
            logger.info(f"Autoencoder accuracy: {accuracy_ae:.4f}")
            
            logger.info("Model training completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error during model training: {e}")
            return False
        
        finally:
            self.is_training = False
    
    def start_streaming(self, bootstrap_servers=['localhost:9092'], topic='transactions'):
        """Start the Kafka streaming process."""
        if self.is_streaming:
            logger.warning("Streaming is already in progress")
            return False
        
        # Check if models exist
        if not os.path.exists(self.isolation_forest_path) or not os.path.exists(f"{self.autoencoder_path}_keras"):
            logger.error("Models not found. Please train the models first.")
            return False
        
        self.is_streaming = True
        logger.info("Starting streaming process")
        
        # Start consumer in a separate thread
        def consumer_thread():
            try:
                consumer = TransactionConsumer(
                    bootstrap_servers=bootstrap_servers,
                    topic=topic,
                    isolation_forest_path=self.isolation_forest_path,
                    autoencoder_path=self.autoencoder_path,
                    scaler_path=self.scaler_path
                )
                
                logger.info("Consumer started. Processing transactions...")
                
                for message in consumer.consumer:
                    if not self.is_streaming:
                        break
                    
                    transaction = message.value
                    
                    # Detect fraud
                    result = consumer.detect_fraud(transaction)
                    
                    # Store transaction in dashboard database
                    self.dashboard_data.store_transaction(result)
                    
                    # Process alerts if fraud detected
                    if result.get('ensemble', {}).get('is_fraud', False):
                        alert_result = self.alert_service.process_transaction(result)
                        
                        logger.info(f"Fraud detected in transaction {result['transaction_id']} - Score: {result.get('ensemble', {}).get('fraud_score', 0):.4f}")
                    else:
                        logger.debug(f"Transaction {result['transaction_id']} processed - No fraud detected")
            
            except Exception as e:
                logger.error(f"Error in consumer thread: {e}")
            
            finally:
                logger.info("Consumer thread stopped")
        
        # Start the consumer thread
        self.consumer_thread = threading.Thread(target=consumer_thread)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        
        logger.info("Streaming process started")
        return True
    
    def stop_streaming(self):
        """Stop the Kafka streaming process."""
        if not self.is_streaming:
            logger.warning("Streaming is not running")
            return False
        
        logger.info("Stopping streaming process")
        self.is_streaming = False
        
        # Wait for consumer thread to stop
        if hasattr(self, 'consumer_thread') and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=5)
        
        logger.info("Streaming process stopped")
        return True
    
    def simulate_transactions(self, count=100, interval=1.0):
        """Simulate transactions for testing."""
        logger.info(f"Simulating {count} transactions")
        
        producer = TransactionProducer()
        producer.simulate_transactions(count=count, interval=interval)
        
        logger.info("Transaction simulation completed")
        return True
    
    def generate_sample_data(self, num_samples=1000):
        """Generate sample data for training."""
        logger.info(f"Generating {num_samples} sample transactions for training")
        
        import numpy as np
        import pandas as pd
        
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
        df.to_csv(self.data_path, index=False)
        
        logger.info(f"Sample data generated and saved to {self.data_path}")
        return True
    
    def run_flask_app(self):
        """Run the Flask API."""
        logger.info("Starting Flask API")
        
        from app import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    
    def run_dashboard(self):
        """Run the dashboard."""
        logger.info("Starting Dashboard")
        
        # Generate sample data for dashboard if needed
        if not os.path.exists('dashboard/dashboard.db'):
            from fix_dashboard import generate_sample_data
            generate_sample_data()
        
        # Import and run dashboard API
        from dashboard.dashboard_api import app as dashboard_app
        dashboard_app.run(debug=False, host='0.0.0.0', port=5001)

if __name__ == "__main__":
    # Create and run the fraud detection system
    system = FraudDetectionSystem()
    
    # Generate sample data if needed
    if not os.path.exists('data/transactions.csv'):
        system.generate_sample_data()
    
    # Train models if needed
    if not os.path.exists('models/isolation_forest_model.joblib') or not os.path.exists('models/autoencoder_model_keras'):
        system.train_models()
    
    # Start streaming in a separate thread
    streaming_thread = threading.Thread(target=system.start_streaming)
    streaming_thread.daemon = True
    streaming_thread.start()
    
    # Start Flask API in a separate thread
    api_thread = threading.Thread(target=system.run_flask_app)
    api_thread.daemon = True
    api_thread.start()
    
    # Start Dashboard in a separate thread
    dashboard_thread = threading.Thread(target=system.run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    # Simulate some transactions
    time.sleep(5)  # Wait for everything to start
    system.simulate_transactions(count=50, interval=0.5)
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Fraud Detection System")
        system.stop_streaming()
