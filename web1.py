import os
import streamlit as st
import requests
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import networkx as nx
from typing import Dict, List, Tuple
import time
import contextily as ctx
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# ----------------------------
# CONFIGURATION STREAMLIT + CSS
# ----------------------------

st.set_page_config(
    page_title="Trajets Kinshasa - Version OpenStreetMap",
    layout="wide",
    page_icon="🗺️"
)

st.markdown("""
    <style>
        .main { padding: 2rem; }
        h1, h2, h3 { font-weight: 700 !important; }
        .stButton>button {
            background: linear-gradient(90deg, #0072ff, #00c6ff);
            color: white; padding: 10px 20px; border-radius: 12px; border: none;
        }
        .route-card { padding: 15px; background: #f0f8ff; border: 2px solid #4aa3ff; border-radius: 12px; margin-bottom: 15px; }
        .best-route { border-color: #816bff; background: #fff0f0; }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# SERVICE DE GÉOCODAGE ALTERNATIF
# ----------------------------

class OpenStreetMapService:
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        
    def geocode(self, address: str) -> Tuple[float, float]:
        """Convertit une adresse en coordonnées avec OpenStreetMap"""
        if not address.strip():
            raise ValueError("L'adresse ne peut pas être vide")
            
        # Ajouter Kinshasa si ce n'est pas spécifié
        if "kinshasa" not in address.lower():
            address = f"{address}, Kinshasa, RDC"
            
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "cd"  # RDC
        }
        
        try:
            response = requests.get(self.nominatim_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise Exception(f"Adresse introuvable: '{address}'")
                
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            
            return lat, lon
            
        except requests.RequestException as e:
            raise Exception(f"Erreur réseau: {str(e)}")
    
    def get_routes_demo(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> List[Dict]:
        """Génère des itinéraires de démonstration"""
        # Calculer une route approximative
        lat1, lon1 = start_coords
        lat2, lon2 = end_coords
        
        # Générer quelques points intermédiaires pour simuler un itinéraire
        num_points = 20
        lats = np.linspace(lat1, lat2, num_points)
        lons = np.linspace(lon1, lon2, num_points)
        
        # Ajouter un peu de variation pour simuler des routes différentes
        coords1 = [(lons[i] + 0.001 * np.sin(i*0.5), lats[i] + 0.001 * np.cos(i*0.5)) 
                  for i in range(num_points)]
        coords2 = [(lons[i] - 0.001 * np.sin(i*0.5), lats[i] - 0.001 * np.cos(i*0.5)) 
                  for i in range(num_points)]
        
        routes = [
            {
                "coords": coords1,
                "distance_km": 15.5,
                "duration_min": 45.0,
                "steps": [
                    {"name": "Prendre l'avenue de la Justice", "distance_text": "2 km", "duration_text": "5 min"},
                    {"name": "Tourner à gauche sur le Boulevard du 30 Juin", "distance_text": "8 km", "duration_text": "25 min"},
                    {"name": "Continuer tout droit vers la destination", "distance_text": "5.5 km", "duration_text": "15 min"}
                ],
                "index": 0,
                "start_address": "Point de départ",
                "end_address": "Destination",
                "distance_text": "15.5 km",
                "duration_text": "45 min",
                "is_best": True
            },
            {
                "coords": coords2,
                "distance_km": 17.2,
                "duration_min": 52.0,
                "steps": [
                    {"name": "Prendre l'avenue des Aviateurs", "distance_text": "3 km", "duration_text": "8 min"},
                    {"name": "Tourner à droite sur l'avenue de la Libération", "distance_text": "10 km", "duration_text": "30 min"},
                    {"name": "Prendre la sortie vers la destination", "distance_text": "4.2 km", "duration_text": "14 min"}
                ],
                "index": 1,
                "start_address": "Point de départ",
                "end_address": "Destination",
                "distance_text": "17.2 km",
                "duration_text": "52 min",
                "is_best": False
            }
        ]
        
        return routes

# ----------------------------
# WIDGET CARTE (MapWidget)
# ----------------------------

class MapWidget:
    def __init__(self):
        self.fig = None
        self.ax = None

    def plot_routes(self, routes: List[Dict], route_colors: Dict[int, str] = None):
        """Affiche les itinéraires sur la carte"""
        self.fig = Figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Carte des itinéraires - Kinshasa (OpenStreetMap)", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True, alpha=0.3)

        if not routes:
            return self.fig

        # Couleurs par défaut
        if route_colors is None:
            route_colors = {0: "#816bff", 1: "#4ecdc4", 2: "#d80bf7"}

        # Tracer chaque itinéraire
        for route in routes:
            coords = route.get("coords", [])
            if not coords:
                continue
            
            xs, ys = zip(*coords)
            color = route_colors.get(route.get("index", 0), "#666666")
            linewidth = 4 if route.get("is_best", False) else 2
            alpha = 1.0 if route.get("is_best", False) else 0.7
            
            self.ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=alpha, zorder=10,
                        label=f"{'⭐ ' if route.get('is_best', False) else ''}Itinéraire {route.get('index', 0) + 1}")

        # Marqueurs de départ et arrivée
        if routes and routes[0].get("coords"):
            start_lon, start_lat = routes[0]["coords"][0]
            end_lon, end_lat = routes[0]["coords"][-1]
            
            self.ax.scatter(start_lon, start_lat, c='green', s=200, edgecolors='white', linewidth=2, zorder=11, marker='o', label='Départ')
            self.ax.scatter(end_lon, end_lat, c='red', s=200, edgecolors='white', linewidth=2, zorder=11, marker='s', label='Arrivée')

        # Ajouter le fond de carte OpenStreetMap
        try:
            if routes and routes[0].get("coords"):
                all_lons = [coord[0] for route in routes for coord in route.get("coords", [])]
                all_lats = [coord[1] for route in routes for coord in route.get("coords", [])]
                
                if all_lons and all_lats:
                    margin = 0.01
                    self.ax.set_xlim(min(all_lons) - margin, max(all_lons) + margin)
                    self.ax.set_ylim(min(all_lats) - margin, max(all_lats) + margin)
                    
                    ctx.add_basemap(self.ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik)
        except Exception as e:
            st.warning(f"⚠️ Fond de carte non disponible: {e}")

        self.ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        return self.fig

# ----------------------------
# INTERFACE UTILISATEUR
# ----------------------------

st.title("🗺️ Trajets Kinshasa - Version Démo (OpenStreetMap)")

st.warning("🔧 **Mode démonstration activé** - Utilisation d'OpenStreetMap gratuit")
st.info("💡 Cette version utilise des données de démonstration pour contourner les limites de quota Google Maps")

# Initialisation du service
maps_service = OpenStreetMapService()

col1, col2 = st.columns(2)
with col1:
    start_place = st.text_input("Point de départ (ex: Gombe, Kinshasa)", "Gombe")
with col2:
    end_place = st.text_input("Destination (ex: Lingwala, Kinshasa)", "Lingwala")

launch = st.button("🚗 Générer les itinéraires de démonstration")

if launch:
    if not start_place or not end_place:
        st.error("Veuillez remplir les deux champs.")
        st.stop()

    with st.spinner("Calcul des itinéraires (mode démo)..."):
        try:
            # Géocodage avec OpenStreetMap
            start_coords = maps_service.geocode(start_place)
            end_coords = maps_service.geocode(end_place)
            
            st.success(f"📍 Départ trouvé: {start_coords}")
            st.success(f"🎯 Arrivée trouvée: {end_coords}")

            # Générer des itinéraires de démonstration
            routes = maps_service.get_routes_demo(start_coords, end_coords)
            
            # Afficher les informations
            st.subheader("📊 Itinéraires de démonstration")
            
            for route in routes:
                border_color = "#816bff" if route.get("is_best") else "#4aa3ff"
                bg_color = "#fff0f0" if route.get("is_best") else "#f5f8ff"
                
                st.markdown(f"""
                <div style="padding: 15px; background: {bg_color}; border: 2px solid {border_color}; border-radius: 12px; margin-bottom: 15px;">
                    <h4 style="margin:0; color: {border_color};">
                        {'⭐ Itinéraire Optimal' if route.get('is_best') else f'Itinéraire {route.get(\"index\", 0) + 1}'}
                    </h4>
                    <b>📏 Distance:</b> {route['distance_text']}<br>
                    <b>⏱️ Durée:</b> {route['duration_text']}<br>
                    <b>🚶 Nombre d'étapes:</b> {len(route['steps'])}
                </div>
                """, unsafe_allow_html=True)

            # Afficher la carte
            map_widget = MapWidget()
            route_colors = {0: "#816bff", 1: "#4ecdc4"}
            fig = map_widget.plot_routes(routes, route_colors)
            st.pyplot(fig)

        except Exception as e:
            st.error(f"Erreur: {str(e)}")