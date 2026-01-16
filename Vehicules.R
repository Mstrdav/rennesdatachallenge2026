
library(sf)
library(tidyverse)
library(dplyr)
library(ggplot2)
library(leaflet)
library(shiny)
library(dplyr)
library(stringr)

readLines("VEHICULES.csv")
vehicule = read.csv("VEHICULES.csv", sep = ";")
View(vehicule)

'''
Les moyens de transport
Le fichier de données VEHICULES.xlsx liste des moyens de transport utilisés.
Aucune liste officielle de facteurs d’émission n’est disponible pour les moyens
de transport, mais un système officiel est proposé à partir du poids du véhicule
(formule dans le fichier).
Un travail avec des modèles d’IA est il possible afin d’estimer le poids et la
catégorie de voiture (citadines, berlines, SUV, monospaces, utilitaires, poids
                      lourds, véhicules spéciaux) des véhicules mentionnés dans le fichier, et d’en
déduire les facteurs d’émission associés.
'''

