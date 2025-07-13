import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np
import matplotlib.pyplot as plt
import joblib

class FraudDetectionAutoencoder:
    def __init__(self, input_dim, encoding_dim=8):
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim
        self.model = self._build_model()
        self.threshold = None
    
    def _build_model(self):
        """Build the autoencoder architecture."""
        # Encoder
        input_layer = Input(shape=(self.input_dim,))
        encoder = Dense(32, activation='relu')(input_layer)
        encoder = Dropout(0.2)(encoder)
        encoder = Dense(16, activation='relu')(encoder)
        encoder = Dense(self.encoding_dim, activation='relu')(encoder)
        
        # Decoder
        decoder = Dense(16, activation='relu')(encoder)
        decoder = Dropout(0.2)(decoder)
        decoder = Dense(32, activation='relu')(decoder)
        decoder = Dense(self.input_dim, activation='sigmoid')(decoder)
        
        # Autoencoder
        autoencoder = Model(inputs=input_layer, outputs=decoder)
        autoencoder.compile(optimizer='adam', loss='mean_squared_error')
        
        return autoencoder
    
    def train(self, X_train, y_train=None, epochs=50, batch_size=32, validation_split=0.1):
        """Train the autoencoder model."""
        print("Training Autoencoder model...")
        
        # Early stopping to prevent overfitting
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        # Train the model
        history = self.model.fit(
            X_train, X_train,  # Autoencoder tries to reconstruct the input
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stopping],
            verbose=1
        )
        
        # Plot training history
        plt.figure(figsize=(10, 6))
        plt.plot(history.history['loss'], label='Training Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Autoencoder Training History')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        # Calculate reconstruction error on training data
        reconstructions = self.model.predict(X_train)
        mse = np.mean(np.power(X_train - reconstructions, 2), axis=1)
        
        # Set threshold for anomaly detection
        if y_train is not None:
            # Find optimal threshold
            best_f1 = 0
            best_threshold = 0
            
            for threshold in np.linspace(min(mse), max(mse), 100):
                y_pred = (mse > threshold).astype(int)
                
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
            # Default threshold based on percentile
            self.threshold = np.percentile(mse, 95)  # 95th percentile
        
        print("Autoencoder model trained successfully")
        return self
    
    def predict(self, X):
        """Predict anomalies."""
        reconstructions = self.model.predict(X)
        mse = np.mean(np.power(X - reconstructions, 2), axis=1)
        return (mse > self.threshold).astype(int)
    
    def predict_proba(self, X):
        """Return anomaly scores normalized to [0, 1]."""
        reconstructions = self.model.predict(X)
        mse = np.mean(np.power(X - reconstructions, 2), axis=1)
        
        # Normalize scores to [0, 1] range where 1 is most anomalous
        min_score = 0
        max_score = self.threshold * 2  # Adjust as needed
        
        # Clip and normalize scores
        clipped_scores = np.clip(mse, min_score, max_score)
        proba = clipped_scores / max_score
        
        return proba
    
    def save_model(self, filepath):
        """Save model to disk."""
        # Save Keras model
        self.model.save(f"{filepath}_keras")
        
        # Save threshold
        joblib.dump({'threshold': self.threshold}, f"{filepath}_threshold.joblib")
        print(f"Model saved to {filepath}")
    
    @classmethod
    def load_model(cls, filepath, input_dim):
        """Load model from disk."""
        # Load Keras model
        keras_model = load_model(f"{filepath}_keras")
        
        # Load threshold
        threshold_data = joblib.load(f"{filepath}_threshold.joblib")
        
        # Create instance
        instance = cls(input_dim=input_dim)
        instance.model = keras_model
        instance.threshold = threshold_data['threshold']
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
    input_dim = X_train.shape[1]
    model = FraudDetectionAutoencoder(input_dim=input_dim)
    model.train(X_train, y_train, epochs=20)
    
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
    model.save_model('autoencoder_model')