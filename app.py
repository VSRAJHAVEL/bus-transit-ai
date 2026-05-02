"""
BUS TRANSIT AI - Route Optimization System
Coimbatore City Bus Network (TNSTC) | 2024

Flask web application with ensemble ML and graph algorithms
for optimal route prediction and live ETAs.
"""

from flask import Flask, render_template, request, jsonify
from config import Config
from models.ml_predictor import ETAPredictor
from models.transit_graph import TransitGraph
from models.route_optimizer import RouteOptimizer
from datetime import datetime
import random
import json


# ──────────────────────────────────────────────
#  Initialize Flask App
# ──────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

# ──────────────────────────────────────────────
#  Initialize AI Components
# ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("  BUS TRANSIT AI — Coimbatore Route Optimization System")
print("  TNSTC City Bus Network | 2024")
print("=" * 60)

# 1. ML Predictor
predictor = ETAPredictor(
    model_path=Config.ML_MODEL_PATH,
    scaler_path=Config.SCALER_PATH
)
if not predictor.load_model():
    predictor.generate_training_data(Config.TRAFFIC_FILE)
    predictor.train(Config.TRAFFIC_FILE)

# 2. Transit Graph
transit_graph = TransitGraph()
transit_graph.load_data(Config.STOPS_FILE, Config.ROUTES_FILE)
transit_graph.build_graph(predictor)

# 3. Route Optimizer
optimizer = RouteOptimizer(transit_graph)

print("\n[OK] All systems initialized. Server ready.\n")


# ──────────────────────────────────────────────
#  Page Routes
# ──────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page."""
    stats = transit_graph.get_graph_stats()
    return render_template('index.html', stats=stats)


@app.route('/route-finder')
def route_finder():
    """Route optimization page."""
    stops = transit_graph.get_all_stops()
    return render_template('route_finder.html', stops=stops)


@app.route('/live-eta')
def live_eta():
    """Live ETA dashboard."""
    routes = sorted(transit_graph.routes.values(), key=lambda r: r['route_number'])
    return render_template('live_eta.html', routes=routes)


@app.route('/analytics')
def analytics():
    """Analytics dashboard."""
    stats = transit_graph.get_graph_stats()
    model_info = predictor.get_model_info()
    return render_template('analytics.html', stats=stats, model_info=model_info)


@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')


# ──────────────────────────────────────────────
#  API Endpoints
# ──────────────────────────────────────────────

@app.route('/api/stops', methods=['GET'])
def api_stops():
    """Return all stops for autocomplete."""
    stops = transit_graph.get_all_stops()
    return jsonify(stops)


@app.route('/api/find-route', methods=['POST'])
def api_find_route():
    """Find optimal route between two stops."""
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    strategy = data.get('strategy', 'fastest')
    
    if not source or not destination:
        return jsonify({"error": "Please provide source and destination stops."}), 400
    
    result = optimizer.find_optimal_route(source, destination, strategy)
    
    if 'error' in result:
        return jsonify(result), 404
    
    return jsonify(result)


@app.route('/api/route-alternatives', methods=['POST'])
def api_route_alternatives():
    """Get multiple route alternatives."""
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not destination:
        return jsonify({"error": "Please provide source and destination stops."}), 400
    
    alternatives = optimizer.get_route_alternatives(source, destination)
    return jsonify({"alternatives": alternatives})


@app.route('/api/eta', methods=['POST'])
def api_eta():
    """Get live ETA for a specific route."""
    data = request.get_json()
    route_id = data.get('route_id')
    
    if not route_id:
        return jsonify({"error": "Please provide a route_id."}), 400
    
    result = optimizer.get_eta_for_route(route_id, predictor)
    
    if 'error' in result:
        return jsonify(result), 404
    
    return jsonify(result)


@app.route('/api/analytics-data', methods=['GET'])
def api_analytics_data():
    """Return analytics data for charts."""
    stats = transit_graph.get_graph_stats()
    model_info = predictor.get_model_info()
    
    # Generate route efficiency data
    route_efficiency = []
    for route_id, route in transit_graph.routes.items():
        stops_count = len(route['stops'])
        distance = route['distance_km']
        time = route['avg_travel_time_minutes']
        speed = (distance / time * 60) if time > 0 else 0
        
        route_efficiency.append({
            'route_number': route['route_number'],
            'name': route['name'],
            'stops': stops_count,
            'distance_km': distance,
            'avg_time_min': time,
            'avg_speed_kmh': round(speed, 1),
            'frequency_min': route.get('frequency_minutes', 15),
            'operator': route.get('operator', 'TNSTC'),
            'type': route.get('type', 'town_bus')
        })
    
    # Peak vs off-peak data
    peak_data = {
        'labels': ['6AM', '7AM', '8AM', '9AM', '10AM', '11AM', '12PM', 
                   '1PM', '2PM', '3PM', '4PM', '5PM', '6PM', '7PM', '8PM', '9PM'],
        'avg_delay': [2, 5, 8, 7, 3, 2, 2, 3, 2, 3, 4, 7, 9, 8, 5, 3],
        'passenger_load': [30, 65, 90, 85, 50, 40, 45, 55, 45, 50, 60, 80, 95, 85, 60, 35]
    }
    
    # Stop connectivity ranking
    stop_ranking = []
    degrees = dict(transit_graph.graph.degree())
    for stop_id, degree in sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:15]:
        stop_info = transit_graph.stops.get(stop_id, {})
        routes_serving = len(transit_graph.stop_to_routes.get(stop_id, set()))
        stop_ranking.append({
            'id': stop_id,
            'name': stop_info.get('name', stop_id),
            'connections': degree,
            'routes_served': routes_serving,
            'type': stop_info.get('type', 'regular')
        })
    
    return jsonify({
        'graph_stats': stats,
        'model_info': model_info,
        'route_efficiency': route_efficiency,
        'peak_data': peak_data,
        'stop_ranking': stop_ranking
    })


# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
