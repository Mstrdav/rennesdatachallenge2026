
#install.packages('sf')
library(sf)
library(tidyverse)
library(dplyr)
library(ggplot2)


commune = read.csv('MOBILITE.csv', sep = ';')
View(commune)


commune_sf = read_sf('communes-version-simplifiee.geojson')



commune_sf <- commune_sf |>
  mutate(communes_etudiees = code %in% commune[,1])


# Afficher un résumé des données
print(commune_sf)
plot(st_geometry(commune_sf), col = "lightblue", border = "grey")


# --- 2. Visualisation avec ggplot2 ---
ggplot(commune_sf) +
  geom_sf(fill = "darkgrey", color = "darkgrey", size = 0.1) +
  ggtitle("Carte des communes de France") +
  theme_minimal()


# --- 3. Carte avec communes sélectionnées en rouge ---
ggplot(commune_sf) +
  geom_sf(aes(fill = communes_etudiees), color = "lightgrey", size = 0.1) +
  scale_fill_manual(
    values = c("FALSE" = "lightgrey", "TRUE" = "red"),
    name = "Sélection"
  ) +
  ggtitle("Communes où vivent des travailleurs du CHU") +
  theme_minimal()
