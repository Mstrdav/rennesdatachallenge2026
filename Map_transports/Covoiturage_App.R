library(shiny)
library(leaflet)
library(sf)
library(dplyr)
library(ggplot2)
library(RColorBrewer)

# --- Configuration & Chargement des données ---

# Coordonnées CHU Pontchaillou
chu_coords <- c(-1.6948973, 48.1189081)
chu_point <- st_sfc(st_point(chu_coords), crs = 4326)

# Paramètres de simulation
avg_speed_kmh <- 50
tortuosity <- 1.3 # Facteur de conversion distance vol d'oiseau -> route
max_stops <- 3 # Max 3 passagers par conducteur

print("[LOG] Démarrage Optimisation")

# Chargement des données
commune_sf <- tryCatch(
  {
    data <- st_read("communes-version-simplifiee.geojson", quiet = TRUE) |>
      st_transform(4326)
    print("[LOG] Données chargées")
    data
  },
  error = function(e) {
    stop("Erreur: 'communes-version-simplifiee.geojson' introuvable.")
  }
)

print("[LOG] Pré-calcul des centroïdes et nettoyage")

# Pré-calcul des centroïdes et nettoyage
commune_sf <- commune_sf |>
  mutate(
    centroide = st_centroid(geometry),
    lon = st_coordinates(centroide)[, 1],
    lat = st_coordinates(centroide)[, 2]
  ) |>
  filter(!is.na(lon) & !is.na(lat))

print("[LOG] Ajout métriques 'Solo' (vectorisé pour éviter problèmes CRS)")

# Ajout métriques "Solo" (vectorisé pour éviter problèmes CRS)
commune_sf$dist_CHU_m <-
  as.numeric(st_distance(commune_sf$centroide, chu_point))
commune_sf$dist_CHU <- (commune_sf$dist_CHU_m / 1000) * tortuosity
commune_sf$time_CHU <- (commune_sf$dist_CHU / avg_speed_kmh) * 60

commune_data <- commune_sf

print("[LOG] Création des noeuds")

# Node 0 sera virtuellement le CHU
nodes <- commune_data |>
  st_drop_geometry() |>
  select(code, nom, lon, lat, dist_CHU, time_CHU) |>
  mutate(id = row_number())

n_nodes <- nrow(nodes)

print("[LOG] Matrice de Distance (Toutes paires)")

# --- Matrice de Distance (Toutes paires) ---
dist_matrix_file <- "mat_dist_time.rds"

if (file.exists(dist_matrix_file)) {
  print(paste(
    "[LOG] Chargement de la matrice de distance depuis",
    dist_matrix_file
  ))
  cache <- readRDS(dist_matrix_file)
  mat_dist_km <- cache$dist_km
  mat_time_min <- cache$time_min
} else {
  print("[LOG] Calcul de la matrice de distance en cours...")
  start_time <- Sys.time()

  # Optimisation : Vectorisation via st_as_sf
  coords_sf <- st_as_sf(nodes, coords = c("lon", "lat"), crs = 4326)

  mat_dist_m <- st_distance(coords_sf)
  mat_dist_km <- (as.numeric(mat_dist_m) / 1000) * tortuosity
  mat_time_min <- (mat_dist_km / avg_speed_kmh) * 60

  end_time <- Sys.time()
  duration <- end_time - start_time
  print(paste("[LOG] Calcul terminé en", round(duration, 2), units(duration)))

  saveRDS(list(dist_km = mat_dist_km, time_min = mat_time_min), dist_matrix_file)
  print(paste("[LOG] Matrice sauvegardée dans", dist_matrix_file))
}

print("[LOG] Interface Utilisateur (UI)")

# --- Interface Utilisateur (UI) ---

ui <- fluidPage(
  titlePanel("\uD83D\uDE97 Covoiturage Optimisé : Algorithme des Économies"),
  sidebarLayout(
    sidebarPanel(
      h4("Paramètres"),
      sliderInput(
        "benefit_factor",
        "Poids 'Bénéfice Écologique' (vs Temps) :",
        min = 0,
        max = 10,
        value = 1.0,
        step = 0.5
      ),
      helpText("Plus la valeur est haute, plus on favorise le regroupement."),
      h5("Légende (Nb Passagers)"),
      tags$ul(
        tags$li(style = "color:#3498db", "0 (Solo)"),
        tags$li(style = "color:#f1c40f", "1 Passager"),
        tags$li(style = "color:#e67e22", "2 Passagers"),
        tags$li(style = "color:#e74c3c", "3 Passagers (Max)")
      ),
      hr(),
      uiOutput("stats_ui")
    ),
    mainPanel(leafletOutput("map", height = "750px"))
  )
)

server <- function(input, output, session) {
  # Calcul Réactif: Algorithme Clarke-Wright
  routes_reactive <- reactive({
    factor <- input$benefit_factor

    withProgress(message = "Optimisation en cours...", value = 0, {
      # Initialisation: Tout le monde est conducteur
      routes <- lapply(1:n_nodes, function(i) {
        list(
          id = i,
          driver = i,
          stops = c(i),
          load = 0
        )
      })

      incProgress(0.1, detail = "Initialisation...")
      print("--- [LOG] Démarrage Optimisation ---")
      print("--- [LOG] Calcul Matrices ---")

      # 1. Matrice Détour D[i,j] = Time(i->j) + Time(j->CHU) - Time(i->CHU)
      # sweep additionne colonnes / soustrait lignes efficacement
      temp_mat <- sweep(mat_time_min, 2, nodes$time_CHU, "+")
      detour_mat <- sweep(temp_mat, 1, nodes$time_CHU, "-")

      # 2. Score = (Facteur * Dist(j->CHU)) - Détour
      term1 <- nodes$dist_CHU * factor
      term1_mat <- matrix(rep(term1, each = n_nodes), nrow = n_nodes)

      score_mat <- term1_mat - detour_mat
      diag(score_mat) <- -Inf # Diagonale ignorée

      incProgress(0.2, detail = "Tri candidats...")
      print("--- [LOG] Matrices calculées. Extraction... ---")

      # 3. Extraction Candidats > 0
      indices <- which(score_mat > 0, arr.ind = TRUE)

      if (nrow(indices) > 0) {
        candidates <- data.frame(
          i = indices[, 1],
          j = indices[, 2],
          score = score_mat[indices]
        ) |>
          arrange(desc(score))
        print(paste("--- [LOG] Paires candidates:", nrow(candidates)))
      } else {
        candidates <- data.frame()
        print("--- [LOG] Aucun candidat positif ---")
      }

      incProgress(0.1, detail = "Fusion trajets...")
      print("--- [LOG] Fusion (Greedy Step) ---")

      # Cartographie Noeud -> Route
      node_to_route <- 1:n_nodes
      route_active <- rep(TRUE, n_nodes)

      # Fusion Itérative
      if (nrow(candidates) > 0) {
        for (k in seq_len(nrow(candidates))) {
          i <- candidates$i[k]
          j <- candidates$j[k]

          r_i_idx <- node_to_route[i]
          r_j_idx <- node_to_route[j]

          # Si même route ou inactive, on passe
          if (r_i_idx == r_j_idx ||
            !route_active[r_i_idx] ||
            !route_active[r_j_idx]) {
            next
          }

          r_i <- routes[[r_i_idx]]
          r_j <- routes[[r_j_idx]]

          # Contrainte Max Passagers
          if ((r_i$load + r_j$load + 1) > max_stops) {
            next
          }

          # Vérification connexion (Fin I -> Début J)
          last_i <- tail(r_i$stops, 1)
          first_j <- head(r_j$stops, 1)

          if (i == last_i && j == first_j) {
            # Fusion Valide
            routes[[r_i_idx]]$stops <- c(r_i$stops, r_j$stops)
            routes[[r_i_idx]]$load <- r_i$load + r_j$load + 1

            # Mise à jour index
            for (node in r_j$stops) {
              node_to_route[node] <- r_i_idx
            }
            route_active[r_j_idx] <- FALSE
          }
        }
      }

      incProgress(0.3, detail = "Finalisation...")

      final_routes <- routes[route_active]
      nb_solos <- sum(sapply(final_routes, function(r) {
        length(r$stops) == 1
      }))
      nb_carpools <- length(final_routes) - nb_solos

      return(list(
        routes = final_routes,
        nb_solos = nb_solos,
        nb_carpools = nb_carpools
      ))
    })
  })

  output$stats_ui <- renderUI({
    res <- routes_reactive()

    # Calcul km réels
    total_km_initial <- sum(nodes$dist_CHU)
    total_km_final <- 0

    for (r in res$routes) {
      path <- r$stops
      if (length(path) == 1) {
        total_km_final <- total_km_final + nodes$dist_CHU[path[1]]
      } else {
        d_driven <- 0
        for (k in 1:(length(path) - 1)) {
          d_driven <- d_driven + mat_dist_km[path[k], path[k + 1]]
        }
        # Dernier stop -> CHU
        d_driven <- d_driven + nodes$dist_CHU[path[length(path)]]
        total_km_final <- total_km_final + d_driven
      }
    }

    saved <- total_km_initial - total_km_final

    tagList(
      p(strong("Trajets Covoiturés : "), res$nb_carpools),
      p(strong("Conducteurs Solo : "), res$nb_solos),
      p(strong("Km Économisés : "), round(saved, 1), " km")
    )
  })

  output$map <- renderLeaflet({
    res <- routes_reactive()

    m <- leaflet() |>
      addProviderTiles(providers$CartoDB.Positron) |>
      addMarkers(
        lng = chu_coords[1],
        lat = chu_coords[2],
        popup = "CHU Rennes",
        icon = makeIcon(
          iconUrl = "https://cdn-icons-png.flaticon.com/512/3063/3063176.png",
          iconWidth = 35,
          iconHeight = 35
        )
      )

    pal_cols <- c("#3498db", "#f1c40f", "#e67e22", "#e74c3c")

    for (r in res$routes) {
      load <- min(r$load, 3)
      col <- pal_cols[load + 1]

      path_ids <- r$stops
      lats <- c(nodes$lat[path_ids], chu_coords[2])
      lons <- c(nodes$lon[path_ids], chu_coords[1])

      m <- m |>
        addPolylines(
          lng = lons,
          lat = lats,
          color = col,
          weight = if (load > 0) {
            4
          } else {
            2
          },
          opacity = 0.8,
          popup = paste("Passagers:", load)
        )

      driver_node <- nodes[path_ids[1], ]
      m <- m |>
        addCircleMarkers(
          lng = driver_node$lon,
          lat = driver_node$lat,
          radius = 5,
          color = col,
          fillOpacity = 1,
          popup = paste("<b>Conducteur</b>:", driver_node$nom)
        )

      if (length(path_ids) > 1) {
        passengers <- path_ids[-1]
        for (pid in passengers) {
          p_node <- nodes[pid, ]
          m <- m |>
            addCircleMarkers(
              lng = p_node$lon,
              lat = p_node$lat,
              radius = 3,
              color = "black",
              fillColor = "white",
              fillOpacity = 1,
              weight = 1,
              popup = paste("Passager:", p_node$nom)
            )
        }
      }
    }
    m
  })
}

shinyApp(ui, server)
