#!/usr/bin/env python3
"""
Test script for the fraud detection dashboard.
This script will generate sample data and test the API endpoints.
"""

import requests
import json
from dashboard.dashboard_data import DashboardDataService

def test_dashboard():
    """Test the dashboard functionality."""
    print("Testing Fraud Detection Dashboard...")
    
    # Initialize data service
    data_service = DashboardDataService()
    
    # Generate sample data
    print("\n1. Generating sample data...")
    count = data_service.generate_sample_data(num_days=30, transactions_per_day=100)
    print(f"Generated {count} sample transactions")
    
    # Test data retrieval
    print("\n2. Testing data retrieval...")
    summary = data_service.get_fraud_summary(days=30)
    print(f"Total transactions: {summary['total_transactions']}")
    print(f"Fraud transactions: {summary['fraud_transactions']}")
    print(f"Fraud rate: {summary['fraud_percentage']:.2%}")
    print(f"Fraud amount: ${summary['fraud_amount']:,.2f}")
    
    # Test performance metrics
    print("\n3. Testing performance metrics...")
    performance = data_service.get_model_performance(days=30)
    print(f"Isolation Forest accuracy: {performance['isolation_forest']['accuracy']:.2%}")
    print(f"Autoencoder accuracy: {performance['autoencoder']['accuracy']:.2%}")
    print(f"Ensemble accuracy: {performance['ensemble']['accuracy']:.2%}")
    
    # Test recent transactions
    print("\n4. Testing recent transactions...")
    recent = data_service.get_recent_transactions(limit=5, fraud_only=True)
    print(f"Found {len(recent['transactions'])} recent fraud transactions")
    
    for tx in recent['transactions'][:3]:
        print(f"  - {tx['transaction_id']}: ${tx['amount']:.2f} (Score: {tx['fraud_score']:.2f})")
    
    print("\n✅ Dashboard data test completed successfully!")
    print("\nTo view the dashboard:")
    print("1. Run: python dashboard/dashboard_api.py")
    print("2. Open: http://localhost:5001")

def test_api_endpoints():
    """Test API endpoints if the server is running."""
    base_url = "http://localhost:5001"
    
    endpoints = [
        "/api/summary",
        "/api/performance", 
        "/api/alerts",
        "/api/settings"
    ]
    
    print("\n5. Testing API endpoints...")
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ {endpoint}: OK")
            else:
                print(f"  ❌ {endpoint}: HTTP {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"  ⚠️  {endpoint}: Server not running")

if __name__ == "__main__":
    test_dashboard()
    test_api_endpoints()