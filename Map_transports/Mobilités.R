
#install.packages('leaflet')
#install.packages('sf')
#install.packages('shiny')
#install.packages("mapsapi")
#install.packages("gtfsrouter")
#install.packages("tidytransit")
#install.packages("stplanr")
#install.packages('googleway')
#install.packages("htmlwidgets")

library(googleway)
library(mapsapi)
library(sf)
library(tidyverse)
library(dplyr)
library(ggplot2)
library(leaflet)
library(shiny)
library(dplyr)
library(stringr)
library(httr)
library(jsonlite)
library(gtfsrouter)
library(tidytransit)
library(stplanr)
library(htmlwidgets)



commune = read.csv('MOBILITE.csv', sep = ';')
View(commune)

commune_sf = read_sf('communes-version-simplifiee.geojson')
view(commune_sf)

commune_sf <- commune_sf |>
  mutate(communes_etudiees = code %in% commune[,1])

# --- Carte avec communes sélectionnées en rouge ---
ggplot(commune_sf) +
  geom_sf(aes(fill = communes_etudiees), color = "lightgrey", size = 0.1) +
  scale_fill_manual(
    values = c("FALSE" = "lightgrey", "TRUE" = "red"),
    name = "Sélection"
  ) +
  ggtitle("Communes où vivent des travailleurs du CHU") +
  theme_minimal()

# Lat Lon des hopitaux
# 48.1189081,-1.6948973 CHU poncha
# 48.0837382,-1.6556722 CHU sud


# Calcul du centre de gravité (centroïde)
commune_sf <- commune_sf %>%
  mutate(centre_gravite = st_centroid(geometry))


# Extraire longitude / latitude
coords <- st_coordinates(commune_sf$centre_gravite)

commune_sf$longitude <- coords[, 1]
commune_sf$latitude  <- coords[, 2]





#################################################################
#################################################################


distance_voiture = read.csv("MOBILITE_results.csv", sep = ";")[,-2]
names(distance_voiture) = c('code', 'Voiture_Pontchaillou_min', 'Voiture_Pontchaillou_km', 'Voiture_HopitalSud_min', 'Voiture_HopitalSud_km')
View(distance_voiture)
View(commune_sf)
dim(commune_voiture) #718 : donc 17 perdues
commune_voiture = merge(distance_voiture, commune_sf, by  = "code")
View(commune_voiture)


for (i in 1:dim(commune_voiture)[1]) {
  commune_voiture$Voiture_min[i] = (commune_voiture$Voiture_HopitalSud_min[i]+ commune_voiture$Voiture_Pontchaillou_min[i])/2
  commune_voiture$Voiture_km[i] = (commune_voiture$Voiture_HopitalSud_km[i]+ commune_voiture$Voiture_Pontchaillou_km[i])/2
}


#################################################################
#################################################################


# --- Paramètres ---
vitesse_velo_kmh <- 15  # vitesse moyenne vélo en km/h

# POINT A et B : c(longitude, latitude)
POINT_A <- st_sfc(st_point(c(-1.6948973, 48.1189081)), crs = 4326)
POINT_B <- st_sfc(st_point(c(-1.6556722, 48.0837382)), crs = 4326)

# --- Fonction pour calculer temps et distance vélo ---
calc_velo <- function(point_depart, point_arrivee, vitesse_kmh = 15) {
  dist_m <- st_distance(st_transform(point_depart, 2154),
                        st_transform(point_arrivee, 2154))
  dist_km <- as.numeric(dist_m) / 1000
  time_min <- (dist_km / vitesse_kmh) * 60
  return(list(time_min = time_min, dist_km = dist_km))
}

# --- Initialiser sf uniquement pour les lignes valides ---
commune_valide <- commune_voiture %>%
  filter(!is.na(longitude) & !is.na(latitude)) %>%
  st_as_sf(coords = c("longitude", "latitude"), crs = 4326)

# --- Calcul des trajets vélo ---
commune_valide <- commune_valide %>%
  rowwise() %>%
  mutate(
    # Trajet vers Point A
    tmp_A = list(calc_velo(geometry, POINT_A, vitesse_velo_kmh)),
    Velo_Pontchaillou_min = tmp_A$time_min,
    Velo_Pontchaillou_km  = tmp_A$dist_km,
    
    # Trajet vers Point B
    tmp_B = list(calc_velo(geometry, POINT_B, vitesse_velo_kmh)),
    Velo_HopitalSud_min = tmp_B$time_min,
    Velo_HopitalSud_km  = tmp_B$dist_km
  ) %>%
  ungroup() %>%
  select(-tmp_A, -tmp_B)

# --- Fusionner avec les lignes sans coordonnées ---
commune_na <- commune_voiture %>%
  filter(is.na(longitude) | is.na(latitude)) %>%
  mutate(
    Velo_Pontchaillou_min = NA_real_,
    Velo_Pontchaillou_km  = NA_real_,
    Velo_HopitalSud_min   = NA_real_,
    Velo_HopitalSud_km    = NA_real_
  )

# --- Tableau final ---
voiture_velo <- bind_rows(commune_valide %>% st_drop_geometry(), commune_na)

# --- Vérification ---
head(voiture_velo)
dim(voiture_velo)
View(voiture_velo)
voiture_velo = voiture_velo[,c(1,13,14)]

commune_voiture_velo = merge(commune_voiture,voiture_velo, by = 'code')
#commune_voiture_velo = commune_voiture_velo[,-c(14,15)]
View(commune_voiture_velo)
commune_voiture_velo$Velo_Pontchaillou_min = round(commune_voiture_velo$Velo_Pontchaillou_km/15 *60)
commune_voiture_velo$Velo_HopitalSud_min =  round(commune_voiture_velo$Velo_HopitalSud_km/15 *60)
dim(commune_voiture_velo)

#####################################
#####################################
#####################################

commune_voiture_velo2 = commune_voiture_velo


commune_voiture_velo2 <- commune_voiture_velo2 %>%
  mutate(
    Velo_Pontchaillou_min = ifelse(Velo_Pontchaillou_min > 90, NA, Velo_Pontchaillou_min),
    Velo_HopitalSud_min = ifelse(Velo_HopitalSud_min > 90, NA, Velo_HopitalSud_min)
  )


commune_voiture_velo2 <- commune_voiture_velo2 %>%
  mutate(
    Velo_Pontchaillou_min = ifelse(Velo_Pontchaillou_min > 90, NA, Velo_Pontchaillou_min),
    Velo_HopitalSud_min = ifelse(Velo_HopitalSud_min > 90, NA, Velo_HopitalSud_min)
  )

commune_voiture_velo2 <- commune_voiture_velo2 %>%
mutate(
  Voiture_Pontchaillou_min = ifelse(Voiture_Pontchaillou_min > 90, NA, Voiture_Pontchaillou_min),
  Voiture_HopitalSud_min = ifelse(Voiture_HopitalSud_min > 90, NA, Voiture_HopitalSud_min)
)

View(commune_voiture_velo2)


#####################################
#####################################
# VOYAGER EN BUS
#####################################
#####################################



# 1) Charger le GTFS STAR
gtfs_file <- "star_gtfs.zip"  # chemin vers ton fichier GTFS
gtfs_data <- read_gtfs(gtfs_file)

# 2) Extraire les arrêts et transformer en sf
stops_sf <- gtfs_data$stops %>%
  st_as_sf(coords = c("stop_lon", "stop_lat"), crs = 4326)



# ---------------- Fonction améliorée ----------------
calc_bus_time_between <- function(
    lat_depart, lon_depart,
    lat_arrivee, lon_arrivee,
    bus_speed_kmh = 15,
    walk_speed_kmh = 5
) {
  # Créer points départ et arrivée
  depart <- st_sfc(st_point(c(lon_depart, lat_depart)), crs = 4326)
  arrivee <- st_sfc(st_point(c(lon_arrivee, lat_arrivee)), crs = 4326)
  
  # Trouver les arrêts STAR les plus proches
  depart_stop <- stops_sf[st_nearest_feature(depart, stops_sf), ]
  arrivee_stop <- stops_sf[st_nearest_feature(arrivee, stops_sf), ]
  
  # 1️⃣ Temps de marche jusqu'à l'arrêt de départ
  walk_distance_start <- st_distance(depart, depart_stop) # en mètres
  walk_time_start <- as.numeric(walk_distance_start) / 1000 / walk_speed_kmh * 60
  
  # 2️⃣ Temps en bus entre arrêts
  bus_distance <- st_distance(depart_stop, arrivee_stop)
  bus_time <- as.numeric(bus_distance) / 1000 / bus_speed_kmh * 60
  # Durée totale approximative
  duree_total <- walk_time_start + bus_time 
  
  return(round(duree_total, 1))
}


commune_voiture_velo2$Bus_Pontchaillou <- mapply(
  calc_bus_time_between,
  lat_depart = commune_voiture_velo2$latitude,
  lon_depart = commune_voiture_velo2$longitude,
  lat_arrivee = 48.1189081,
  lon_arrivee = -1.6948973
)

commune_voiture_velo2$Bus_HopitalSud <- mapply(
  calc_bus_time_between,
  lat_depart = commune_voiture_velo2$latitude,
  lon_depart = commune_voiture_velo2$longitude,
  lat_arrivee = 48.0837382,
  lon_arrivee = -1.6556722
)


# Lat Lon des hopitaux
# 48.1189081,-1.6948973 CHU poncha
# 48.0837382,-1.6556722 CHU sud



commune_voiture_velo2 <- commune_voiture_velo2 %>%
  mutate(
    Bus_Pontchaillou = ifelse(Bus_Pontchaillou > 90, NA, Bus_Pontchaillou),
    Bus_HopitalSud = ifelse(Bus_HopitalSud > 90, NA, Bus_HopitalSud)
  )

View(commune_voiture_velo2)


Transports_Voit_Velo_Bus = commune_voiture_velo2[,-c(7,9)]

#write.table(Transports_Voit_Velo_Bus, "Transports_Voit_Velo_Bus.csv", sep = ";", dec  = ".")
#readLines("Transports_Voit_Velo_Bus.csv")

commune_voiture_velo3 = read.csv2( "Transports_Voit_Velo_Bus.csv",  
  header = TRUE,                  
  sep = ";",                     
  dec = ".",                       
  quote = "\"",                    
  stringsAsFactors = FALSE         
)

View(commune_voiture_velo3)



#####################################
#####################################
# VOYAGER EN TRAIN
#####################################
#####################################



#####################################
# AFFICHAGE DE LA CARTE
#####################################
  
# ---------------- UI ----------------
ui <- fluidPage(
  titlePanel("Carte interactive des communes étudiées"),
  
  sidebarLayout(
    sidebarPanel(
      helpText("Affichage uniquement des communes étudiées (communes_etudiees == TRUE).")
    ),
    mainPanel(
      leafletOutput("map", height = 650)
    )
  )
)

# ---------------- SERVER ----------------
server <- function(input, output, session) {
  
  output$map <- renderLeaflet({
    
    # Filtrer les communes étudiées
    df_filtre <- commune_voiture_velo3 %>% filter(communes_etudiees == TRUE)
    
    # Construire le label HTML pour le tooltip
    labels <- lapply(1:nrow(df_filtre), function(i) {
      row <- df_filtre[i, ]
      
      # Condition temps voiture > 60 ou NA
      if (is.na(row$Voiture_Pontchaillou_min) | is.na(row$Voiture_HopitalSud_min) |
          row$Voiture_Pontchaillou_min > 60 | row$Voiture_HopitalSud_min > 60) {
        
        label <- paste0(
          "<b>", row$nom, "</b><br/>",
          "Voiture temps moyen (min) : ", round(row$Voiture_min, 1), "<br/>",
          "Voiture distance moyenne (km) : ", round(row$Voiture_km, 1)
        )
        
      } else {
        # Affichage détaillé, sans les NA
        label <- paste0(
          "<b>", row$nom, "</b><br/>",
          if (!is.na(row$Voiture_Pontchaillou_km)) paste0("Distance Pontchaillou (km) : ", row$Voiture_Pontchaillou_km, "<br/>") else "",
          if (!is.na(row$Voiture_HopitalSud_km)) paste0("Distance Hopital Sud (km) : ", row$Voiture_HopitalSud_km, "<br/>") else "",
          if (!is.na(row$Voiture_Pontchaillou_min)) paste0("Voiture Pontchaillou (min) : ", row$Voiture_Pontchaillou_min, "<br/>") else "",
          if (!is.na(row$Voiture_HopitalSud_min)) paste0("Voiture Hopital Sud (min) : ", row$Voiture_HopitalSud_min, "<br/>") else "",
          if (!is.na(row$Velo_Pontchaillou_min)) paste0("Velo Pontchaillou (min) : ", row$Velo_Pontchaillou_min, "<br/>") else "",
          if (!is.na(row$Velo_HopitalSud_min)) paste0("Velo Hopital Sud (min) : ", row$Velo_HopitalSud_min, "<br/>") else "",
          if (!is.na(row$Bus_Pontchaillou)) paste0("Bus Pontchaillou (min) : ", row$Bus_Pontchaillou, "<br/>") else "",
          if (!is.na(row$Bus_HopitalSud)) paste0("Bus Hopital Sud (min) : ", row$Bus_HopitalSud, "<br/>") else ""
        )
      }
      
      HTML(label)
    })
    
    # Carte Leaflet
    leaflet(df_filtre) %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      addCircleMarkers(
        lng = ~longitude,
        lat = ~latitude,
        radius = 10,
        fillColor = "blue",
        fillOpacity = 0.7,
        stroke = FALSE,
        label = labels
      )
  })
}

  
  
  
  # ---------------- Lancer l'application Shiny ----------------
map = shinyApp(ui, server)
map



make_leaflet_map <- function() {
  
  df_filtre <- commune_voiture_velo3 %>%
    filter(communes_etudiees == TRUE)
  
  labels <- lapply(1:nrow(df_filtre), function(i) {
    row <- df_filtre[i, ]
    
    if (is.na(row$Voiture_Pontchaillou_min) | is.na(row$Voiture_HopitalSud_min) |
        row$Voiture_Pontchaillou_min > 60 | row$Voiture_HopitalSud_min > 60) {
      
      label <- paste0(
        "<b>", row$nom, "</b><br/>",
        "Voiture temps moyen (min) : ", round(row$Voiture_min, 1), "<br/>",
        "Voiture distance moyenne (km) : ", round(row$Voiture_km, 1)
      )
      
    } else {
      label <- paste0(
        "<b>", row$nom, "</b><br/>",
        if (!is.na(row$Voiture_Pontchaillou_km)) paste0("Distance Pontchaillou (km) : ", row$Voiture_Pontchaillou_km, "<br/>") else "",
        if (!is.na(row$Voiture_HopitalSud_km)) paste0("Distance Hopital Sud (km) : ", row$Voiture_HopitalSud_km, "<br/>") else "",
        if (!is.na(row$Voiture_Pontchaillou_min)) paste0("Voiture Pontchaillou (min) : ", row$Voiture_Pontchaillou_min, "<br/>") else "",
        if (!is.na(row$Voiture_HopitalSud_min)) paste0("Voiture Hopital Sud (min) : ", row$Voiture_HopitalSud_min, "<br/>") else "",
        if (!is.na(row$Velo_Pontchaillou_min)) paste0("Velo Pontchaillou (min) : ", row$Velo_Pontchaillou_min, "<br/>") else "",
        if (!is.na(row$Velo_HopitalSud_min)) paste0("Velo Hopital Sud (min) : ", row$Velo_HopitalSud_min, "<br/>") else "",
        if (!is.na(row$Bus_Pontchaillou)) paste0("Bus Pontchaillou (min) : ", row$Bus_Pontchaillou, "<br/>") else "",
        if (!is.na(row$Bus_HopitalSud)) paste0("Bus Hopital Sud (min) : ", row$Bus_HopitalSud, "<br/>") else ""
      )
    }
    
    htmltools::HTML(label)
  })
  
  leaflet(df_filtre) %>%
    addProviderTiles(providers$CartoDB.Positron) %>%
    addCircleMarkers(
      lng = ~longitude,
      lat = ~latitude,
      radius = 5,
      fillColor = "blue",
      fillOpacity = 0.7,
      stroke = FALSE,
      label = labels
    )
}


ui <- fluidPage(
  titlePanel("Carte interactive des communes étudiées"),
  leafletOutput("map", height = 650)
)

server <- function(input, output, session) {
  output$map <- renderLeaflet({
    make_leaflet_map()
  })
}

shinyApp(ui, server)


map_leaflet <- make_leaflet_map()

saveWidget(
  map_leaflet,
  file = "carte_communes.html",
  selfcontained = FALSE
)





