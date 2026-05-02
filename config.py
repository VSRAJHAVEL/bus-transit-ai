"""
Configuration for BUS TRANSIT AI - Route Optimization System
Coimbatore City Bus Network (TNSTC)
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bus-transit-ai-coimbatore-2024')
    DEBUG = True
    
    # Data paths
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    STOPS_FILE = os.path.join(DATA_DIR, 'coimbatore_stops.json')
    ROUTES_FILE = os.path.join(DATA_DIR, 'coimbatore_routes.json')
    TRAFFIC_FILE = os.path.join(DATA_DIR, 'traffic_data.csv')
    
    # Model paths
    MODEL_DIR = os.path.join(BASE_DIR, 'trained_models')
    ML_MODEL_PATH = os.path.join(MODEL_DIR, 'eta_ensemble_model.pkl')
    SCALER_PATH = os.path.join(MODEL_DIR, 'feature_scaler.pkl')
    
    # App settings
    APP_NAME = "BUS TRANSIT AI"
    APP_SUBTITLE = "Coimbatore Route Optimization System"
    CITY = "Coimbatore"
    OPERATOR = "TNSTC (Tamil Nadu State Transport Corporation)"
    YEAR = 2024
    
    # Map center (Coimbatore)
    MAP_CENTER_LAT = 11.0168
    MAP_CENTER_LNG = 76.9558
    MAP_ZOOM = 13
