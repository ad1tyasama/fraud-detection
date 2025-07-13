from sklearn.ensemble import IsolationForest
import joblib
import numpy as np
import matplotlib.pyplot as plt

class FraudDetectionIsolationForest:
    def __init__(self, contamination=0.05, random_state=42):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples='auto'
        )
        self.threshold = None
    
    def train(self, X_train, y_train=None):
        """Train the Isolation Forest model."""
        print("Training Isolation Forest model...")
        self.model.fit(X_train)
        
        # Get anomaly scores
        scores = self.model.decision_function(X_train)
        
        # Set threshold if we have labels
        if y_train is not None:
            # Plot score distribution
            plt.figure(figsize=(10, 6))
            plt.hist(scores, bins=50, alpha=0.5)
            plt.title('Anomaly Score Distribution')
            plt.xlabel('Anomaly Score')
            plt.ylabel('Count')
            
            # Find optimal threshold
            best_f1 = 0
            best_threshold = 0
            
            for threshold in np.linspace(min(scores), max(scores), 100):
                y_pred = (scores < threshold).astype(int)
                
                # Calculate F1 score
                tp = np.sum((y_train == 1) & (y_pred == 1))
                fp = np.sum((y_train == 0) & (y_pred == 1))
                fn = np.sum((y_train == 1) & (y_pred == 0))
                
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
            
            self.threshold = best_threshold
            print(f"Optimal threshold: {self.threshold:.4f}, F1 Score: {best_f1:.4f}")
        else:
            # Default threshold based on contamination
            self.threshold = np.percentile(scores, 100 * self.model.contamination)
        
        print("Isolation Forest model trained successfully")
        return self
    
    def predict(self, X):
        """Predict anomalies."""
        scores = self.model.decision_function(X)
        return (scores < self.threshold).astype(int)
    
    def predict_proba(self, X):
        """Return anomaly scores normalized to [0, 1]."""
        scores = self.model.decision_function(X)
        # Convert to probability-like values (higher value = more likely to be fraud)
        # Normalize scores to [0, 1] range where 1 is most anomalous
        min_score = self.threshold - 0.5  # Adjust as needed
        max_score = self.threshold + 0.5  # Adjust as needed
        
        # Clip and invert scores (lower scores are more anomalous in Isolation Forest)
        clipped_scores = np.clip(scores, min_score, max_score)
        proba = 1 - ((clipped_scores - min_score) / (max_score - min_score))
        
        return proba
    
    def save_model(self, filepath):
        """Save model to disk."""
        model_data = {
            'model': self.model,
            'threshold': self.threshold
        }
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    @classmethod
    def load_model(cls, filepath):
        """Load model from disk."""
        model_data = joblib.load(filepath)
        instance = cls()
        instance.model = model_data['model']
        instance.threshold = model_data['threshold']
        print(f"Model loaded from {filepath}")
        return instance

# Example usage
if __name__ == "__main__":
    import sys
    sys.path.append('..')
    from data_preprocessing import load_and_preprocess_data
    
    # Load and preprocess data
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data('../synthetic_transactions.csv')
    
    # Train model
    model = FraudDetectionIsolationForest(contamination=0.05)
    model.train(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    tp = np.sum((y_test == 1) & (y_pred == 1))
    fp = np.sum((y_test == 0) & (y_pred == 1))
    fn = np.sum((y_test == 1) & (y_pred == 0))
    tn = np.sum((y_test == 0) & (y_pred == 0))
    
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
    # Save model
    model.save_model('isolation_forest_model.joblib')