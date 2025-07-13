# Real-Time Fraud Detection System

A comprehensive fraud detection system that uses machine learning models to detect fraudulent transactions in real-time.

## Overview

This system uses anomaly detection techniques to identify potentially fraudulent transactions. It processes transaction data in real-time using Apache Kafka, applies machine learning models to detect anomalies, and sends alerts when suspicious activities are detected.

## Key Features

- **Anomaly Detection**: Uses Isolation Forest and Autoencoder models to detect unusual patterns
- **Real-Time Processing**: Processes transactions as they occur using Apache Kafka
- **Alert System**: Sends notifications via email, SMS, or webhooks when fraud is detected
- **Dashboard**: Visualizes fraud statistics and model performance
- **REST API**: Provides endpoints for fraud detection and batch processing

## System Architecture

![System Architecture](docs/architecture.png)

The system consists of the following components:

1. **Data Preprocessing**: Cleans and transforms transaction data
2. **Machine Learning Models**: Isolation Forest and Autoencoder for anomaly detection
3. **Real-Time Streaming**: Apache Kafka for transaction streaming
4. **API Layer**: Flask API for model integration
5. **Alert System**: Notification service for fraud alerts
6. **Dashboard**: Visualization and reporting

## Tech Stack

- **Python**: Core programming language
- **Scikit-learn**: For Isolation Forest implementation
- **TensorFlow**: For Autoencoder neural network
- **Apache Kafka**: For real-time data streaming
- **Flask**: For API development
- **SQLite**: For storing transaction data
- **Bootstrap & Chart.js**: For dashboard UI

## Installation

### Prerequisites

- Python 3.8+
- Apache Kafka
- pip (Python package manager)

### Setup

1. Clone the repository: