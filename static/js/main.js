/**
 * Main JavaScript for BUS TRANSIT AI
 * Handles Map initialization, Autocomplete, Route Finding, Live ETA, and Analytics
 */

// Mobile Navigation
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');
    if(navToggle) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
        });
    }

    // Initialize specific page functionality
    if(document.getElementById('route-map')) initRouteFinder();
    if(document.getElementById('eta-map')) initLiveETA();
    if(document.getElementById('peakChart')) initAnalytics();
});

// ==========================================
// Map Helper Functions
// ==========================================
const MAP_CONFIG = {
    center: [11.0168, 76.9558], // Coimbatore center
    zoom: 13,
    tileLayer: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
};

function initMap(elementId) {
    if(!document.getElementById(elementId)) return null;
    
    const map = L.map(elementId).setView(MAP_CONFIG.center, MAP_CONFIG.zoom);
    L.tileLayer(MAP_CONFIG.tileLayer, {
        attribution: MAP_CONFIG.attribution,
        maxZoom: 19
    }).addTo(map);
    
    return map;
}

// Custom Marker Icons
const createIcon = (color, isDot = false) => {
    const size = isDot ? [12, 12] : [24, 24];
    const html = isDot ? 
        `<div style="background-color:${color};width:100%;height:100%;border-radius:50%;border:2px solid #0a0a0f;"></div>` :
        `<svg viewBox="0 0 24 24" fill="${color}" stroke="#0a0a0f" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="#0a0a0f"/></svg>`;
        
    return L.divIcon({
        className: 'custom-leaflet-icon',
        html: html,
        iconSize: size,
        iconAnchor: isDot ? [6, 6] : [12, 24]
    });
};

const ICONS = {
    source: createIcon('#00ff88'),
    dest: createIcon('#ef4444'),
    stop: createIcon('#00d4ff', true),
    etaOnTime: createIcon('#00ff88', true),
    etaDelayed: createIcon('#f97316', true),
    etaLate: createIcon('#ef4444', true)
};

// ==========================================
// Route Finder Functionality
// ==========================================
function initRouteFinder() {
    const map = initMap('route-map');
    let routeLayer = L.featureGroup().addTo(map);
    let allStops = [];

    // Fetch stops for autocomplete
    fetch('/api/stops')
        .then(res => res.json())
        .then(data => {
            allStops = data;
            setupAutocomplete('source-input', 'source-dropdown', 'source-id', allStops);
            setupAutocomplete('dest-input', 'dest-dropdown', 'dest-id', allStops);
        });

    // Strategy Tabs
    const tabs = document.querySelectorAll('.strategy-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.currentTarget.classList.add('active');
        });
    });

    // Swap Button
    document.getElementById('swap-btn')?.addEventListener('click', () => {
        const srcId = document.getElementById('source-id').value;
        const srcVal = document.getElementById('source-input').value;
        const dstId = document.getElementById('dest-id').value;
        const dstVal = document.getElementById('dest-input').value;

        document.getElementById('source-id').value = dstId;
        document.getElementById('source-input').value = dstVal;
        document.getElementById('dest-id').value = srcId;
        document.getElementById('dest-input').value = srcVal;
    });

    // Find Route
    document.getElementById('find-route-btn')?.addEventListener('click', () => {
        const source = document.getElementById('source-id').value;
        const dest = document.getElementById('dest-id').value;
        const strategy = document.querySelector('.strategy-tab.active').dataset.strategy;

        if(!source || !dest) {
            showError('Please select both source and destination stops from the dropdown.');
            return;
        }

        if(source === dest) {
            showError('Source and destination cannot be the same.');
            return;
        }

        // UI State
        document.getElementById('rf-error').style.display = 'none';
        document.getElementById('rf-results').style.display = 'none';
        document.getElementById('rf-loading').style.display = 'block';
        routeLayer.clearLayers();

        // API Call
        fetch('/api/find-route', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({source, destination: dest, strategy})
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('rf-loading').style.display = 'none';
            
            if(data.error) {
                showError(data.error);
                return;
            }

            displayRouteResults(data, map, routeLayer);
        })
        .catch(err => {
            document.getElementById('rf-loading').style.display = 'none';
            showError('An error occurred while finding the route.');
            console.error(err);
        });
    });
}

function setupAutocomplete(inputId, dropdownId, hiddenId, stopsData) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    const hidden = document.getElementById(hiddenId);

    if(!input) return;

    input.addEventListener('input', () => {
        const val = input.value.toLowerCase();
        dropdown.innerHTML = '';
        
        if(!val) {
            dropdown.classList.remove('show');
            return;
        }

        const matches = stopsData.filter(s => 
            s.name.toLowerCase().includes(val) || 
            s.id.toLowerCase().includes(val)
        ).slice(0, 8);

        if(matches.length > 0) {
            matches.forEach(match => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';
                div.innerHTML = `<strong>${match.name}</strong> <small style="color:#94a3b8;float:right">${match.zone}</small>`;
                div.addEventListener('click', () => {
                    input.value = match.name;
                    hidden.value = match.id;
                    dropdown.classList.remove('show');
                });
                dropdown.appendChild(div);
            });
            dropdown.classList.add('show');
        } else {
            dropdown.classList.remove('show');
        }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if(e.target !== input && e.target !== dropdown) {
            dropdown.classList.remove('show');
        }
    });
}

function showError(msg) {
    const errEl = document.getElementById('rf-error');
    if(errEl) {
        errEl.textContent = msg;
        errEl.style.display = 'block';
    }
}

function displayRouteResults(data, map, routeLayer) {
    // 1. Update Map
    const coords = data.coordinates;
    
    // Draw polyline
    const line = L.polyline(coords, {
        color: '#00ff88',
        weight: 4,
        opacity: 0.8,
        dashArray: '10, 10',
        lineCap: 'round'
    }).addTo(routeLayer);

    // Add markers
    data.stops.forEach((stop, idx) => {
        let icon = ICONS.stop;
        if(idx === 0) icon = ICONS.source;
        if(idx === data.stops.length - 1) icon = ICONS.dest;

        L.marker([stop.lat, stop.lng], {icon: icon})
         .bindPopup(`<b>${stop.name}</b><br>Arr: ${stop.arrival_time_str}`)
         .addTo(routeLayer);
    });

    map.fitBounds(routeLayer.getBounds(), {padding: [50, 50]});

    // 2. Update UI
    document.getElementById('rf-results').style.display = 'block';
    document.getElementById('results-algo').textContent = data.algorithm;
    
    // Stats
    document.getElementById('results-stats').innerHTML = `
        <div class="result-stat">
            <div class="result-stat-value">${data.total_time_str}</div>
            <div class="result-stat-label">Estimated Time</div>
        </div>
        <div class="result-stat">
            <div class="result-stat-value">${data.total_distance_km}</div>
            <div class="result-stat-label">Distance (km)</div>
        </div>
        <div class="result-stat">
            <div class="result-stat-value">${data.transfers}</div>
            <div class="result-stat-label">Transfers</div>
        </div>
    `;

    // Bus info
    let busHtml = `Take <strong>Bus ${data.recommended_bus}</strong>`;
    if(data.transfers > 0) {
        busHtml += ` with ${data.transfers} transfer(s).`;
    } else if (data.direct_buses.length > 1) {
        busHtml += ` or ${data.direct_buses.slice(1,4).join(', ')}.`;
    }
    document.getElementById('results-bus').innerHTML = busHtml;

    // Timeline
    let timelineHtml = '';
    data.stops.forEach((stop, idx) => {
        let cls = 'timeline-stop';
        if(idx === 0) cls += ' first';
        if(idx === data.stops.length - 1) cls += ' last';
        
        let meta = `<div class="timeline-time">${stop.arrival_time_str}</div>`;
        
        // Add segment info if not last stop
        if(idx < data.stops.length - 1) {
            const seg = data.segments[idx];
            meta += `<div class="timeline-bus">Bus ${seg.buses.join(', ')} • ${seg.time_min}m</div>`;
        }

        timelineHtml += `
            <div class="${cls}">
                <div class="timeline-name">${stop.name}</div>
                ${meta}
            </div>
        `;
    });
    document.getElementById('results-timeline').innerHTML = timelineHtml;
}

// ==========================================
// Live ETA Functionality
// ==========================================
function initLiveETA() {
    if(!document.getElementById('eta-map')) return;
    
    const map = initMap('eta-map');
    let etaLayer = L.featureGroup().addTo(map);

    const routeItems = document.querySelectorAll('.route-item');
    
    routeItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // UI Selection
            routeItems.forEach(r => r.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            const routeId = e.currentTarget.dataset.routeId;
            fetchETA(routeId, map, etaLayer);
        });
    });
}

function fetchETA(routeId, map, etaLayer) {
    document.getElementById('eta-empty').style.display = 'none';
    document.getElementById('eta-stops').innerHTML = '<div class="loading-spinner" style="margin-top:40px"></div>';
    document.getElementById('eta-stops').style.display = 'block';

    fetch('/api/eta', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({route_id: routeId})
    })
    .then(res => res.json())
    .then(data => {
        if(data.error) {
            document.getElementById('eta-stops').innerHTML = `<p style="color:red">${data.error}</p>`;
            return;
        }

        // Update Header
        document.getElementById('eta-route-header').style.display = 'flex';
        document.getElementById('eta-map-wrap').style.display = 'block';
        
        // Tell Leaflet the container size changed from 0 to visible
        setTimeout(() => map.invalidateSize(), 10);
        
        const badge = document.getElementById('eta-badge');
        badge.textContent = data.route_number;
        badge.style.color = data.color;
        
        document.getElementById('eta-route-name').textContent = data.route_name;
        document.getElementById('eta-route-detail').textContent = `${data.operator} • ${data.stops.length} Stops`;

        // Draw Map
        etaLayer.clearLayers();
        const coords = data.stops.map(s => [s.lat, s.lng]);
        
        L.polyline(coords, {color: data.color, weight: 4}).addTo(etaLayer);
        
        // Draw Stops & Timeline
        let timelineHtml = '';
        
        data.stops.forEach((stop, idx) => {
            // Map marker
            let iconType = ICONS.etaOnTime;
            if(stop.status === 'delayed') iconType = ICONS.etaDelayed;
            if(stop.status === 'late') iconType = ICONS.etaLate;
            
            L.marker([stop.lat, stop.lng], {icon: iconType})
             .bindPopup(`<b>${stop.stop_name}</b><br>ETA: ${stop.eta_str}`)
             .addTo(etaLayer);
             
            // Timeline HTML
            timelineHtml += `
                <div class="eta-stop ${stop.status}">
                    <div class="eta-time-box">
                        <div class="eta-mins ${stop.status}">${stop.eta_str}</div>
                        <div class="eta-schedule">Sched: ${stop.scheduled_minutes}m</div>
                    </div>
                    <div class="eta-stop-name">${stop.stop_name}</div>
                    <div class="eta-delay-text ${stop.status}">${stop.delay_minutes > 0 ? '+'+stop.delay_minutes+' min delay' : 'On Time'}</div>
                </div>
            `;
        });
        
        document.getElementById('eta-stops').innerHTML = timelineHtml;
        setTimeout(() => {
            if(etaLayer.getBounds().isValid()) {
                map.fitBounds(etaLayer.getBounds(), {padding: [30, 30]});
            }
        }, 100);
    })
    .catch(err => {
        console.error(err);
        document.getElementById('eta-stops').innerHTML = `<p>Error loading ETA data.</p>`;
    });
}

// ==========================================
// Analytics Dashboard Functionality
// ==========================================
function initAnalytics() {
    if(!document.getElementById('peakChart')) return;
    
    // Global Chart.js Defaults
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    fetch('/api/analytics-data')
        .then(res => res.json())
        .then(data => {
            renderPeakChart(data.peak_data);
            renderStopsChart(data.stop_ranking);
            renderEfficiencyChart(data.route_efficiency);
            renderRouteTable(data.route_efficiency);
        });
}

function renderPeakChart(data) {
    const ctx = document.getElementById('peakChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Avg Delay (min)',
                    data: data.avg_delay,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Passenger Load (%)',
                    data: data.passenger_load,
                    borderColor: '#00d4ff',
                    borderDash: [5, 5],
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { type: 'linear', position: 'left', grid: {color: 'rgba(255,255,255,0.05)'} },
                y1: { type: 'linear', position: 'right', grid: {display: false} }
            }
        }
    });
}

function renderStopsChart(stopsData) {
    const ctx = document.getElementById('stopsChart').getContext('2d');
    const labels = stopsData.map(s => s.name.substring(0,15) + (s.name.length>15?'...':''));
    const data = stopsData.map(s => s.connections);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Direct Connections',
                data: data,
                backgroundColor: 'rgba(168, 85, 247, 0.5)',
                borderColor: '#a855f7',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: {color: 'rgba(255,255,255,0.05)'} },
                x: { ticks: {maxRotation: 45, minRotation: 45} }
            }
        }
    });
}

function renderEfficiencyChart(routesData) {
    const ctx = document.getElementById('efficiencyChart').getContext('2d');
    
    // Sort by speed
    const sorted = [...routesData].sort((a,b) => b.avg_speed_kmh - a.avg_speed_kmh).slice(0, 15);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(r => 'R' + r.route_number),
            datasets: [{
                label: 'Avg Speed (km/h)',
                data: sorted.map(r => r.avg_speed_kmh),
                backgroundColor: 'rgba(0, 255, 136, 0.5)',
                borderColor: '#00ff88',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: {color: 'rgba(255,255,255,0.05)'} }
            }
        }
    });
}

function renderRouteTable(routesData) {
    const tbody = document.getElementById('route-table-body');
    if(!tbody) return;
    
    let html = '';
    routesData.forEach(r => {
        let speedColor = r.avg_speed_kmh > 20 ? '#00ff88' : (r.avg_speed_kmh > 15 ? '#00d4ff' : '#f97316');
        html += `
            <tr>
                <td><strong>${r.route_number}</strong></td>
                <td>${r.name}</td>
                <td>${r.operator}</td>
                <td><span class="tech-chip">${r.type.replace('_', ' ')}</span></td>
                <td>${r.stops}</td>
                <td>${r.distance_km} km</td>
                <td>${r.avg_time_min} min</td>
                <td style="color:${speedColor}">${r.avg_speed_kmh} km/h</td>
                <td>${r.frequency_min} min</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}
