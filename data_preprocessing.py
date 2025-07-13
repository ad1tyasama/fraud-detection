import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

def load_and_preprocess_data(file_path):
    """Load and preprocess transaction data."""
    print("Loading and preprocessing data...")
    
    # Load data
    df = pd.read_csv(file_path)
    
    # Basic preprocessing
    # Handle missing values
    df = df.fillna(0)
    
    # Convert categorical features
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype('category').cat.codes
    
    # Feature engineering
    # Add time-based features if timestamp exists
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        # Drop the timestamp column to avoid the dtype error
        df = df.drop('timestamp', axis=1)
    
    # Separate features and target
    X = df.drop(['is_fraud'], axis=1) if 'is_fraud' in df.columns else df
    y = df['is_fraud'] if 'is_fraud' in df.columns else None
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"Data preprocessed. Shape: {X_scaled.shape}")
    
    if y is not None:
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        return X_train, X_test, y_train, y_test, scaler
    else:
        return X_scaled, scaler

# Example usage with synthetic data
if __name__ == "__main__":
    # Create synthetic data for demonstration
    n_samples = 1000
    n_features = 10
    
    # Generate random features
    X = np.random.randn(n_samples, n_features)
    
    # Generate target (5% fraud)
    y = np.zeros(n_samples)
    fraud_indices = np.random.choice(n_samples, size=int(0.05 * n_samples), replace=False)
    y[fraud_indices] = 1
    
    # Create DataFrame
    features = [f'feature_{i}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=features)
    df['is_fraud'] = y
    
    # Add timestamp
    dates = pd.date_range('2023-01-01', periods=n_samples)
    df['timestamp'] = np.random.choice(dates, n_samples)
    
    # Save to CSV
    df.to_csv('synthetic_transactions.csv', index=False)
    
    # Preprocess
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data('synthetic_transactions.csv')
    
    print(f"Training data shape: {X_train.shape}")
    print(f"Testing data shape: {X_test.shape}")
    print(f"Fraud ratio: {y_test.mean():.2%}")