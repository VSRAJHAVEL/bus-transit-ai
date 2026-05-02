"""
Transit Graph for BUS TRANSIT AI
Builds and manages the Coimbatore bus network as a NetworkX weighted graph
"""

import json
import networkx as nx
from utils.helpers import haversine_distance


class TransitGraph:
    """Weighted directed graph representing the Coimbatore bus network."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.stops = {}
        self.routes = {}
        self.stop_to_routes = {}  # stop_id -> list of route_ids serving that stop
    
    def load_data(self, stops_path, routes_path):
        """Load stops and routes from JSON files."""
        with open(stops_path, 'r') as f:
            stops_data = json.load(f)
        
        with open(routes_path, 'r') as f:
            routes_data = json.load(f)
        
        # Index stops
        for stop in stops_data['stops']:
            self.stops[stop['id']] = stop
        
        # Index routes
        for route in routes_data['routes']:
            self.routes[route['id']] = route
        
        print(f"[Graph] Loaded {len(self.stops)} stops and {len(self.routes)} routes")
    
    def build_graph(self, predictor=None):
        """Build the network graph from loaded data."""
        self.graph.clear()
        self.stop_to_routes = {}
        
        # Add all stops as nodes
        for stop_id, stop in self.stops.items():
            self.graph.add_node(
                stop_id,
                name=stop['name'],
                lat=stop['lat'],
                lng=stop['lng'],
                zone=stop['zone'],
                type=stop['type']
            )
        
        # Add edges from routes
        for route_id, route in self.routes.items():
            stops = route['stops']
            total_distance = route['distance_km']
            total_time = route['avg_travel_time_minutes']
            n_segments = len(stops) - 1
            
            if n_segments <= 0:
                continue
            
            for i in range(n_segments):
                from_stop = stops[i]
                to_stop = stops[i + 1]
                
                if from_stop not in self.stops or to_stop not in self.stops:
                    continue
                
                # Calculate actual distance between stops
                s1 = self.stops[from_stop]
                s2 = self.stops[to_stop]
                segment_dist = haversine_distance(s1['lat'], s1['lng'], s2['lat'], s2['lng'])
                
                # Estimate segment travel time proportionally
                dist_ratio = segment_dist / max(total_distance, 0.1)
                segment_time = total_time * dist_ratio
                
                # Use ML prediction if available
                if predictor and predictor.is_trained:
                    segment_time = predictor.predict(segment_dist, 1)
                
                # Add/update edge with minimum weight
                edge_key = (from_stop, to_stop)
                if self.graph.has_edge(from_stop, to_stop):
                    existing = self.graph[from_stop][to_stop]
                    if segment_time < existing['weight']:
                        existing['weight'] = segment_time
                    existing['routes'].append(route['route_number'])
                    existing['route_ids'].append(route_id)
                else:
                    self.graph.add_edge(
                        from_stop, to_stop,
                        weight=max(segment_time, 0.5),
                        distance=round(segment_dist, 2),
                        routes=[route['route_number']],
                        route_ids=[route_id]
                    )
                
                # Also add reverse edge (buses go both ways)
                if not self.graph.has_edge(to_stop, from_stop):
                    self.graph.add_edge(
                        to_stop, from_stop,
                        weight=max(segment_time, 0.5),
                        distance=round(segment_dist, 2),
                        routes=[route['route_number']],
                        route_ids=[route_id]
                    )
                else:
                    existing_rev = self.graph[to_stop][from_stop]
                    if route['route_number'] not in existing_rev['routes']:
                        existing_rev['routes'].append(route['route_number'])
                        existing_rev['route_ids'].append(route_id)
                
                # Track which routes serve each stop
                for sid in [from_stop, to_stop]:
                    if sid not in self.stop_to_routes:
                        self.stop_to_routes[sid] = set()
                    self.stop_to_routes[sid].add(route_id)
        
        print(f"[Graph] Built graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def get_stop_info(self, stop_id):
        """Get detailed info about a stop."""
        if stop_id not in self.stops:
            return None
        
        stop = self.stops[stop_id].copy()
        stop['connected_routes'] = list(self.stop_to_routes.get(stop_id, set()))
        stop['connections'] = len(list(self.graph.neighbors(stop_id))) if stop_id in self.graph else 0
        return stop
    
    def get_all_stops(self):
        """Return all stops sorted by name."""
        return sorted(self.stops.values(), key=lambda s: s['name'])
    
    def get_graph_stats(self):
        """Return graph statistics for analytics."""
        if not self.graph.nodes:
            return {}
        
        degrees = dict(self.graph.degree())
        
        return {
            'total_stops': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'total_routes': len(self.routes),
            'avg_connections': round(sum(degrees.values()) / max(len(degrees), 1), 1),
            'most_connected': max(degrees, key=degrees.get) if degrees else None,
            'most_connected_name': self.stops.get(max(degrees, key=degrees.get), {}).get('name', '') if degrees else '',
            'most_connected_count': max(degrees.values()) if degrees else 0
        }
