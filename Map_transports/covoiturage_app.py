
import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os
import time
from scipy.spatial.distance import cdist

# --- Configuration ---
CHU_COORDS = (-1.6948973, 48.1189081) # Lon, Lat
AVG_SPEED_KMH = 50
TORTUOSITY = 1.3
MAX_STOPS = 3
GEOJSON_PATH = "communes-version-simplifiee.geojson"
CACHE_FILE = "mat_dist_time_py.pkl"

st.set_page_config(layout="wide", page_title="Covoiturage Optimisé")

# --- Fonctions Utilitaires ---

@st.cache_data
def load_data():
    if not os.path.exists(GEOJSON_PATH):
        st.error(f"Fichier '{GEOJSON_PATH}' introuvable.")
        return None
    
    # Chargement et projection
    gdf = gpd.read_file(GEOJSON_PATH)
    
    # On s'assure d'être en WGS84 pour l'affichage
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
        
    # Calcul des centroïdes
    gdf['centroid'] = gdf.geometry.centroid
    gdf['lon'] = gdf.centroid.x
    gdf['lat'] = gdf.centroid.y
    gdf = gdf.dropna(subset=['lon', 'lat'])
    
    # Pour les calculs de distance pré-CHU, on projette temporairement en Lambert 93 (France) pour la précision métrique
    # Ou on utilise une approximation Haversine. 
    # Pour reproduire le comportement "st_distance" sur 4326 de R (geodesic), 
    # l'usage d'une projection locale est souvent plus performant en Python que d'itérer du haversine.
    # Rennes est en France => EPSG:2154
    gdf_proj = gdf.to_crs(epsg=2154)
    chu_point = gpd.points_from_xy([CHU_COORDS[0]], [CHU_COORDS[1]], crs="EPSG:4326").to_crs(epsg=2154)[0]
    
    # Distance au CHU
    gdf['dist_CHU_m'] = gdf_proj.centroid.distance(chu_point)
    gdf['dist_CHU'] = (gdf['dist_CHU_m'] / 1000) * TORTUOSITY
    gdf['time_CHU'] = (gdf['dist_CHU'] / AVG_SPEED_KMH) * 60
    
    # Création des noeuds (indices 0 à N-1)
    nodes = gdf[['code', 'nom', 'lon', 'lat', 'dist_CHU', 'time_CHU']].copy().reset_index(drop=True)
    nodes['id'] = nodes.index
    
    return nodes

def compute_distance_matrix(nodes):
    if os.path.exists(CACHE_FILE):
        print(f"[LOG] Chargement de la matrice depuis {CACHE_FILE}")
        return pd.read_pickle(CACHE_FILE)
    
    print("[LOG] Calcul de la matrice de distance en cours...")
    start_time = time.time()
    
    # Projection pour calcul de distance matriciel rapide (Euclidien sur Lambert 93)
    # Re-création de la géométrie projetée pour les noeuds
    nodes_gdf = gpd.GeoDataFrame(
        nodes, 
        geometry=gpd.points_from_xy(nodes.lon, nodes.lat),
        crs="EPSG:4326"
    ).to_crs(epsg=2154)
    
    coords = np.array(list(zip(nodes_gdf.geometry.x, nodes_gdf.geometry.y)))
    
    # cdist calcule la distance euclidienne entre toutes les paires
    mat_dist_m = cdist(coords, coords, metric='euclidean')
    
    mat_dist_km = (mat_dist_m / 1000) * TORTUOSITY
    mat_time_min = (mat_dist_km / AVG_SPEED_KMH) * 60
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"[LOG] Calcul terminé en {duration:.2f} secondes")
    
    result = {'dist_km': mat_dist_km, 'time_min': mat_time_min}
    pd.to_pickle(result, CACHE_FILE)
    print(f"[LOG] Matrice sauvegardée dans {CACHE_FILE}")
    
    return result

# --- Algorithme Clarke-Wright ---

def solve_covoiturage(nodes, mat_dist_km, mat_time_min, benefit_factor):
    n_nodes = len(nodes)
    
    # Initialisation : Tout le monde est son propre conducteur
    # Routes est une liste de dicts
    routes = []
    for i in range(n_nodes):
        routes.append({
            'id': i,
            'driver': i,
            'stops': [i], # Liste des indices des noeuds visités
            'load': 0      # 0 passagers (le conducteur ne compte pas dans la "charge" passager selon la logique R originale qui met load=0 init)
                           # R: load=0 init. Stop check: (r_i$load + r_j$load + 1) > max_stops (donc +1 pour le conducteur fusionné ?)
                           # Vérifions la logique R:
                           # routes[[i]]$load init à 0.
                           # Fusion: routes[[r_i]]$load <- r_i$load + r_j$load + 1
                           # Donc load compte le nombre de PASSAGERS récupérés (personnes qui ne conduisent plus).
        })
        
    # --- Calcul des Scores (Savings) ---
    # Logique R: 
    # temp_mat = sweep(mat_time_min, 2, nodes$time_CHU, "+")  => T(i,j) + T(j, CHU)
    # detour_mat = sweep(temp_mat, 1, nodes$time_CHU, "-")    => T(i,j) + T(j, CHU) - T(i, CHU)
    # term1 = nodes$dist_CHU * factor
    # score = term1 - detour
    
    # En numpy :
    # nodes['time_CHU'] shape (N,)
    time_chu = nodes['time_CHU'].values
    dist_chu = nodes['dist_CHU'].values
    
    # Broadcasting pour recréer sweep
    # mat_time_min[i, j]
    # temp_mat[i, j] = mat_time_min[i, j] + time_chu[j]
    temp_mat = mat_time_min + time_chu[None, :] 
    
    # detour_mat[i, j] = temp_mat[i, j] - time_chu[i]
    detour_mat = temp_mat - time_chu[:, None]
    
    # term1[j] = dist_chu[j] * factor. 
    # Dans R: term1_mat = matrix(rep(term1, each=n), nrow=n) => les colonnes sont identiques (valeur de j)
    # term1_mat[i, j] = dist_chu[j] * factor
    term1_mat = (dist_chu * benefit_factor)[None, :]
    
    score_mat = term1_mat - detour_mat
    
    # Diagonale -Inf
    np.fill_diagonal(score_mat, -np.inf)
    
    # Extraction candidats > 0
    # indices where score > 0
    rows, cols = np.where(score_mat > 0)
    scores = score_mat[rows, cols]
    
    candidates = pd.DataFrame({'i': rows, 'j': cols, 'score': scores})
    candidates = candidates.sort_values('score', ascending=False).reset_index(drop=True)
    
    # Mapping Noeud -> Index Route
    node_to_route = list(range(n_nodes))
    route_active = [True] * n_nodes
    
    # Fusion
    for idx, row in candidates.iterrows():
        i = int(row['i'])
        j = int(row['j'])
        
        r_i_idx = node_to_route[i]
        r_j_idx = node_to_route[j]
        
        # Si même route ou inactive
        if r_i_idx == r_j_idx or not route_active[r_i_idx] or not route_active[r_j_idx]:
            continue
            
        r_i = routes[r_i_idx]
        r_j = routes[r_j_idx]
        
        # Check charge max (load i + load j + 1 nouveau passager (le driver j devient passager))
        if (r_i['load'] + r_j['load'] + 1) > MAX_STOPS:
            continue
            
        # Vérification connexion (Fin I -> Début J)
        # R: last_i <- tail(r_i$stops, 1); first_j <- head(r_j$stops, 1)
        last_i = r_i['stops'][-1]
        first_j = r_j['stops'][0]
        
        if i == last_i and j == first_j:
            # Fusion
            # Nouveau stops: stops_i + stops_j
            routes[r_i_idx]['stops'].extend(r_j['stops'])
            routes[r_i_idx]['load'] += r_j['load'] + 1
            
            # Mise à jour index pour tous les membres de J
            for node_idx in r_j['stops']:
                node_to_route[node_idx] = r_i_idx
            
            route_active[r_j_idx] = False
            
    final_routes = [r for idx, r in enumerate(routes) if route_active[idx]]
    return final_routes

# --- Interface ---

st.title("🚗 Covoiturage Optimisé : Algorithme des Économies")

with st.sidebar:
    st.header("Paramètres")
    benefit_factor = st.slider(
        "Poids 'Bénéfice Écologique' (vs Temps)", 
        min_value=0.0, max_value=10.0, value=1.0, step=0.5
    )
    st.info("Plus la valeur est haute, plus on favorise le regroupement.")
    
    st.markdown("""
    **Légende (Nb Passagers)**
    * <span style="color:#3498db">0 (Solo)</span>
    * <span style="color:#f1c40f">1 Passager</span>
    * <span style="color:#e67e22">2 Passagers</span>
    * <span style="color:#e74c3c">3 Passagers (Max)</span>
    """, unsafe_allow_html=True)
    
    stats_container = st.container()

# Chargement
nodes = load_data()

if nodes is not None:
    # Matrice
    mat_cache = compute_distance_matrix(nodes)
    mat_dist_km = mat_cache['dist_km']
    mat_time_min = mat_cache['time_min']
    
    # Optimisation
    with st.spinner("Optimisation en cours..."):
        final_routes = solve_covoiturage(nodes, mat_dist_km, mat_time_min, benefit_factor)
    
    # Stats
    nb_solos = sum(1 for r in final_routes if len(r['stops']) == 1)
    nb_carpools = len(final_routes) - nb_solos
    
    total_km_initial = nodes['dist_CHU'].sum()
    total_km_final = 0
    
    for r in final_routes:
        path = r['stops']
        if len(path) == 1:
            total_km_final += nodes.loc[path[0], 'dist_CHU']
        else:
            d_driven = 0
            for k in range(len(path) - 1):
                # dist entre path[k] et path[k+1]
                # mat_dist_km est un np.array, indexé par [i, j]
                d_driven += mat_dist_km[path[k], path[k+1]]
            
            # Dernier stop -> CHU
            d_driven += nodes.loc[path[-1], 'dist_CHU']
            total_km_final += d_driven
            
    saved_km = total_km_initial - total_km_final
    
    with stats_container:
        st.markdown("---")
        st.metric("Trajets Covoiturés", nb_carpools)
        st.metric("Conducteurs Solo", nb_solos)
        st.metric("Km Économisés", f"{saved_km:.1f} km")

    # Carte
    m = folium.Map(location=[CHU_COORDS[1], CHU_COORDS[0]], zoom_start=10, tiles='CartoDB positron')
    
    # Marker CHU
    icon_url = "https://cdn-icons-png.flaticon.com/512/3063/3063176.png"
    icon = folium.CustomIcon(icon_url, icon_size=(35, 35))
    folium.Marker(
        [CHU_COORDS[1], CHU_COORDS[0]], 
        popup="CHU Rennes", 
        icon=icon
    ).add_to(m)
    
    colors = ["#3498db", "#f1c40f", "#e67e22", "#e74c3c"]
    
    for r in final_routes:
        load = min(r['load'], 3)
        col = colors[load]
        
        path_ids = r['stops']
        
        # Coordonnées pour la ligne: [stop1, stop2, ..., stopN, CHU]
        route_coords = []
        for pid in path_ids:
            route_coords.append([nodes.loc[pid, 'lat'], nodes.loc[pid, 'lon']])
        route_coords.append([CHU_COORDS[1], CHU_COORDS[0]])
        
        weight = 4 if load > 0 else 2
        opacity = 0.8
        
        folium.PolyLine(
            route_coords, color=col, weight=weight, opacity=opacity, 
            popup=f"Passagers: {load}"
        ).add_to(m)
        
        # Conducteur (Premier noeud)
        driver_node = nodes.loc[path_ids[0]]
        folium.CircleMarker(
            location=[driver_node.lat, driver_node.lon],
            radius=5,
            color=col,
            fill=True,
            fill_opacity=1,
            popup=f"<b>Conducteur</b>: {driver_node['nom']}"
        ).add_to(m)
        
        # Passagers
        if len(path_ids) > 1:
            for pid in path_ids[1:]:
                p_node = nodes.loc[pid]
                folium.CircleMarker(
                    location=[p_node.lat, p_node.lon],
                    radius=3,
                    color="black",
                    fill=True,
                    fill_color="white",
                    fill_opacity=1,
                    weight=1,
                    popup=f"Passager: {p_node['nom']}"
                ).add_to(m)

    st_folium(m, height=750, width="100%")
