"""
ML Predictor for BUS TRANSIT AI
Ensemble model: Random Forest + Gradient Boosting for travel time prediction
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import random
from datetime import datetime


class ETAPredictor:
    """Ensemble ML model for predicting bus travel times."""
    
    def __init__(self, model_path=None, scaler_path=None):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.metrics = {}
    
    def generate_training_data(self, output_path=None, n_samples=5000):
        """Generate synthetic but realistic training data for Coimbatore bus transit."""
        np.random.seed(42)
        
        data = []
        for _ in range(n_samples):
            hour = np.random.randint(5, 23)
            day_of_week = np.random.randint(0, 7)  # 0=Monday
            is_weekend = 1 if day_of_week >= 5 else 0
            is_peak = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
            
            # Route characteristics
            stop_count = np.random.randint(3, 15)
            distance_km = round(np.random.uniform(2, 30), 1)
            
            # Weather: 0=clear, 1=cloudy, 2=rain, 3=heavy_rain, 4=fog
            weather = np.random.choice([0, 1, 2, 3, 4], p=[0.45, 0.25, 0.15, 0.05, 0.10])
            
            # Congestion index (0-1)
            base_congestion = 0.3
            if is_peak:
                base_congestion += np.random.uniform(0.2, 0.5)
            if is_weekend:
                base_congestion -= 0.1
            if weather >= 2:
                base_congestion += 0.15
            congestion = min(max(base_congestion + np.random.normal(0, 0.1), 0), 1)
            
            # Passenger load factor (0-1)
            passenger_load = min(max(
                0.4 + (0.3 if is_peak else 0) + np.random.normal(0, 0.15), 0), 1)
            
            # Calculate travel time based on realistic factors
            base_time = (distance_km / 22) * 60  # ~22 km/h avg city bus speed
            stop_delay = stop_count * np.random.uniform(0.5, 1.5)  # time at each stop
            congestion_delay = base_time * congestion * 0.6
            weather_delay = base_time * (weather * 0.08)
            
            actual_time = base_time + stop_delay + congestion_delay + weather_delay
            actual_time += np.random.normal(0, actual_time * 0.08)  # noise
            actual_time = max(actual_time, distance_km * 1.5)  # minimum bound
            
            data.append({
                'hour_of_day': hour,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'is_peak_hour': is_peak,
                'stop_count': stop_count,
                'distance_km': distance_km,
                'weather': weather,
                'congestion_index': round(congestion, 3),
                'passenger_load': round(passenger_load, 3),
                'actual_travel_time_minutes': round(actual_time, 1)
            })
        
        df = pd.DataFrame(data)
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"[ML] Generated {n_samples} training samples -> {output_path}")
        
        return df
    
    def train(self, data_path=None, data_df=None):
        """Train the ensemble model."""
        if data_df is not None:
            df = data_df
        elif data_path and os.path.exists(data_path):
            df = pd.read_csv(data_path)
        else:
            print("[ML] No training data found. Generating synthetic data...")
            df = self.generate_training_data(data_path)
        
        feature_cols = [
            'hour_of_day', 'day_of_week', 'is_weekend', 'is_peak_hour',
            'stop_count', 'distance_km', 'weather', 'congestion_index', 'passenger_load'
        ]
        
        X = df[feature_cols].values
        y = df['actual_travel_time_minutes'].values
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Build ensemble
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        gb = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )
        
        self.model = VotingRegressor(
            estimators=[('rf', rf), ('gb', gb)],
            n_jobs=-1
        )
        
        print("[ML] Training ensemble model (Random Forest + Gradient Boosting)...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        self.metrics = {
            'mae': round(mean_absolute_error(y_test, y_pred), 2),
            'r2_score': round(r2_score(y_test, y_pred), 4),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'features': feature_cols
        }
        
        print(f"[ML] Model trained — MAE: {self.metrics['mae']} min | R²: {self.metrics['r2_score']}")
        
        # Save model
        if self.model_path:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            print(f"[ML] Model saved to {self.model_path}")
        
        self.is_trained = True
        return self.metrics
    
    def load_model(self):
        """Load a previously trained model."""
        if self.model_path and os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.is_trained = True
            print("[ML] Loaded pre-trained model.")
            return True
        return False
    
    def predict(self, distance_km, stop_count, hour=None, day=None, weather=0):
        """Predict travel time for a route segment."""
        if not self.is_trained:
            # Fallback to simple estimation
            return self._simple_estimate(distance_km, stop_count)
        
        now = datetime.now()
        if hour is None:
            hour = now.hour
        if day is None:
            day = now.weekday()
        
        is_weekend = 1 if day >= 5 else 0
        is_peak = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
        
        # Estimate congestion from time
        congestion = 0.3 + (0.35 if is_peak else 0) - (0.1 if is_weekend else 0)
        congestion = min(max(congestion + random.uniform(-0.05, 0.05), 0), 1)
        
        # Estimate passenger load
        passenger_load = 0.4 + (0.3 if is_peak else 0) + random.uniform(-0.1, 0.1)
        passenger_load = min(max(passenger_load, 0), 1)
        
        features = np.array([[
            hour, day, is_weekend, is_peak,
            stop_count, distance_km, weather,
            congestion, passenger_load
        ]])
        
        features_scaled = self.scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]
        
        return max(round(prediction, 1), 1.0)
    
    def _simple_estimate(self, distance_km, stop_count):
        """Simple fallback ETA estimation."""
        base_time = (distance_km / 20) * 60  # 20 km/h avg
        stop_delay = stop_count * 1.0
        return round(base_time + stop_delay, 1)
    
    def get_model_info(self):
        """Return model information for the analytics page."""
        return {
            'model_type': 'Ensemble (VotingRegressor)',
            'estimators': ['Random Forest (100 trees)', 'Gradient Boosting (150 trees)'],
            'metrics': self.metrics,
            'is_trained': self.is_trained
        }
