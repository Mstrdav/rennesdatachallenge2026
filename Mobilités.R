
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



commune_sf$geometry[2]


# 1. Conversion WKT -> géométrie sf
commune_sf <- commune_sf %>%
  mutate(geometry2 = st_as_sfc(geometry, crs = 4326)) %>%
  st_as_sf()

# 2. Calcul du centre de gravité (centroïde)
commune_sf <- commune_sf %>%
  mutate(centre_gravite = st_centroid(geometry))


# 3. Extraire longitude / latitude
coords <- st_coordinates(commune_sf$centre_gravite)

commune_sf$longitude <- coords[, 1]
commune_sf$latitude  <- coords[, 2]


#################################################################
#################################################################
#################################################################
#################################################################



data_final<-read.csv("carte_termine.csv",sep=",",dec=".")

# Optionnel : forcer numeric pour les coordonnées si nécessai
# -------------------- UI --------------------
ui <- fluidPage(
  titlePanel("Carte des salaires par ville"),
  
  sidebarLayout(
    sidebarPanel(
      radioButtons(
        "type_salaire",
        "Type de salaire",
        choices = c("Théorique" = "pred", "Observé" = "obs"),
        selected = "pred"
      )
    ),
    mainPanel(
      leafletOutput("map", height = 650)
    )
  )
)

# -------------------- SERVER --------------------
server <- function(input, output, session) {
  
  # Reactive pour créer la colonne salaire_affiche
  data_react <- reactive({
    req(data_final)
    
    df <- data_final %>%
      mutate(
        salaire_affiche = if (input$type_salaire == "pred") {
          salaire_pred
        } else {
          Salaire_mensuel
        }
      )
    
    df
  })
  
  # Render Leaflet
  output$map <- renderLeaflet({
    df <- data_react()
    
    # Palette de couleur selon le salaire
    pal <- colorNumeric(
      palette = "viridis",
      domain = df$salaire_affiche
    )
    
    leaflet(df) %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      addCircleMarkers(
        lng = ~longitude,
        lat = ~latitude,
        radius = ~0.005*(salaire_affiche), # taille proportionnelle
        fillColor = ~pal(salaire_affiche),
        fillOpacity = 0.8,
        stroke = FALSE,
        label = ~paste0(city, " : ", round(salaire_affiche, 0), " €")
      ) %>%
      addLegend(
        pal = pal,
        values = ~salaire_affiche,
        title = ifelse(
          input$type_salaire == "pred",
          "Salaire théorique (€)",
          "Salaire observé (€)"
        )
      )
  })
}

# -------------------- Lancer l'app --------------------
shinyApp(ui, server)

