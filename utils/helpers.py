"""
Utility helpers for BUS TRANSIT AI
"""

import math
from datetime import datetime


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on Earth (in km)."""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def format_duration(minutes):
    """Format minutes into human-readable duration string."""
    if minutes < 1:
        return "< 1 min"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins} min"


def get_time_period(hour=None):
    """Get the time period label for a given hour."""
    if hour is None:
        hour = datetime.now().hour
    
    if 6 <= hour < 10:
        return "morning_peak"
    elif 10 <= hour < 16:
        return "midday"
    elif 16 <= hour < 20:
        return "evening_peak"
    elif 20 <= hour < 23:
        return "night"
    else:
        return "late_night"


def is_peak_hour(hour=None):
    """Check if the given hour is a peak transit hour."""
    if hour is None:
        hour = datetime.now().hour
    return (7 <= hour <= 9) or (17 <= hour <= 19)


def get_congestion_factor(hour=None):
    """Get a congestion multiplier based on time of day."""
    if hour is None:
        hour = datetime.now().hour
    
    congestion_map = {
        "morning_peak": 1.5,
        "midday": 1.0,
        "evening_peak": 1.6,
        "night": 0.8,
        "late_night": 0.6
    }
    period = get_time_period(hour)
    return congestion_map.get(period, 1.0)


def get_weather_factor(weather="clear"):
    """Get a travel time multiplier based on weather conditions."""
    weather_map = {
        "clear": 1.0,
        "cloudy": 1.05,
        "rain": 1.3,
        "heavy_rain": 1.6,
        "fog": 1.2
    }
    return weather_map.get(weather, 1.0)
