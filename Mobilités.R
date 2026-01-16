
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

# 48.1189081,-1.6948973 CHU poncha
# 48.0837382,-1.6556722 CHU sud


# 2. Calcul du centre de gravité (centroïde)
commune_sf <- commune_sf %>%
  mutate(centre_gravite = st_centroid(geometry))


# 3. Extraire longitude / latitude
coords <- st_coordinates(commune_sf$centre_gravite)

commune_sf$longitude <- coords[, 1]
commune_sf$latitude  <- coords[, 2]


#################################################################
#################################################################


data_communes = commune_sf

# UI
ui <- fluidPage(
  titlePanel("Carte interactive des communes de France"),
  
  sidebarLayout(
    sidebarPanel(
      helpText("Carte des communes avec longitude / latitude.")
    ),
    mainPanel(
      leafletOutput("map", height = 650)
    )
  )
)

# Server
server <- function(input, output, session) {
  
  output$map <- renderLeaflet({
    leaflet(data_communes) %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      addCircleMarkers(
        lng = ~longitude,
        lat = ~latitude,
        radius = 5,                    # taille fixe, modifiable
        fillColor = "blue",            # couleur fixe, modifiable
        fillOpacity = 0.7,
        stroke = FALSE,
        label = ~nom                   # affichage du nom au survol
      )
  })
}

# Lancer l'application Shiny
shinyApp(ui, server)



