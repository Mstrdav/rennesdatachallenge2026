
#install.packages('leaflet')
#install.packages('sf')
#install.packages('shiny')

library(sf)
library(tidyverse)
library(dplyr)
library(ggplot2)
library(leaflet)
library(shiny)
library(dplyr)
library(stringr)

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


data_communes = commune_sf


# UI
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

# Server
server <- function(input, output, session) {
  
  output$map <- renderLeaflet({
    df_filtre <- commune_sf %>% filter(communes_etudiees == TRUE)
    
    leaflet(df_filtre) %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      addCircleMarkers(
        lng = ~longitude,
        lat = ~latitude,
        radius = 5,
        fillColor = "blue",
        fillOpacity = 0.7,
        stroke = FALSE,
        label = ~nom
      )
  })
}

# Lancer l'app
shinyApp(ui, server)


