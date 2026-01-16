**DATA CHALLENGE 2026 - Arkea Asset Management**

## **Description du projet**

Dans un contexte de forte croissance de la gestion passive, de nombreux investisseurs souhaitent aujourd’hui s’exposer aux marchés actions via des indices, tout en intégrant des considérations extra-financières, notamment environnementales, sociales et de gouvernance (ESG).

Cependant, cette demande s’accompagne d’une contrainte forte : **ne pas dégrader significativement la performance financière** par rapport aux indices traditionnels.

Le défi proposé aux étudiants s’inscrit précisément dans cette problématique.

### **Objectif général du projet**

L’objectif du challenge est de concevoir un indice ESG innovant qui :

* conserve une performance aussi proche que possible de l’indice parent,  
* intègre des critères ESG et climatiques exigeants,  
* et limite les coûts implicites liés aux réallocations fréquentes, notamment via une maîtrise du turnover.

---

## **Cadre et contraintes du projet**

### **1\. Construction de l’indice ESG**

Les équipes devront proposer une méthodologie de construction d’un indice ESG reposant notamment sur les principes suivants :

* Exclusion des 30 % (en poids) des entreprises les moins bien notées ESG au sein de chaque secteur, afin de conserver une comparabilité sectorielle avec l’indice parent.  
* Intégration d’un critère climatique, avec une contrainte de trajectoire de température implicite du portefeuille inférieure à 2°C, en cohérence avec les objectifs de l’Accord de Paris.  
* Conservation d’une structure d’indice lisible et justifiable (pondérations, univers d’investissement, règles de sélection).

L’approche retenue devra être clairement expliquée, tant sur le plan financier que méthodologique.

### 

### **2\. Gestion du turnover**

Un enjeu clé du projet réside dans la stabilité de l’indice dans le temps.

Les étudiants devront donc intégrer un mécanisme permettant de :

* Limiter le turnover de l’indice ESG à chaque rebalancement trimestriel,  
* Tout en laissant une flexibilité suffisante pour que l’indice continue de refléter les évolutions ESG des entreprises ainsi que l'évolution de la composition de l’indice parent.

Cette contrainte vise à reproduire des conditions réalistes de gestion indicielle et de la réplicabilité du produit.

---

## **Attendus du challenge**

Les livrables et analyses attendus porteront à la fois sur la performance financière, la cohérence ESG et la qualité méthodologique de la solution proposée.

### **1\. Analyse de la performance**

Les équipes devront présenter :

* L’écart de performance entre l’indice ESG proposé et l’indice parent sur la période de backtest,  
* Une visualisation graphique de l’évolution comparée des performances,  
* Une analyse commentée des phases de sur- ou sous-performance.

### **2\. Tracking Error**

* Le calcul et l’analyse de la Tracking Error (TE) de l’indice ESG par rapport à l’indice parent,  
* Une interprétation de ce niveau de TE au regard des objectifs de gestion passive responsable.

### **3\. Turnover**

* Le niveau de turnover de l’indice ESG, comparé à celui de l’indice parent,  
* Une discussion sur l’impact du mécanisme de limitation du turnover sur la performance et la composition du portefeuille.

### **4\. Innovation de l’approche de sélection**

Les équipes seront évaluées sur :

* Le caractère innovant et pertinent de l’optimiseur,  
* La capacité à concilier contraintes ESG, climatiques et financières,  
* La clarté et la robustesse des règles de construction de l’indice.  
* Le type d’optimiseur ou de méthode de calcul utilisé (optimisation sous contraintes, règles heuristiques, pénalités, etc.),  
* Les choix techniques effectués et leurs implications,  
* Les éventuelles limites de l’approche proposée

---


## **Structure des données fournies**

Le challenge s'appuie sur **5 fichiers de données au format Parquet** situés dans le dossier `data/`. Ces données couvrent **269 entreprises** sur une période de **21 trimestres** (de juin 2021 à décembre 2025).

### 1. `metadata.parquet` - Métadonnées des entreprises

**Structure** : Tableau de 269 lignes (une par entreprise) × plusieurs colonnes descriptives

Ce fichier contient les informations statiques et la couverture temporelle de chaque entreprise :

| Colonne | Description |
|---------|-------------|
| ID | Identifiant unique de l'entreprise |
| `sector` | Secteur d'activité de l'entreprise |
| Date de début/fin | Période de couverture des données disponibles |
| Autres métadonnées | Informations complémentaires sur l'entreprise |

**Utilité** : 
Ce fichier permet d'associer chaque ID à son secteur pour appliquer les exclusions ESG par secteur et de connaître la période de disponibilité des données pour chaque entreprise.

### 2. `itr.parquet` - Température implicite (Implied Temperature Rise)

**Structure** : Matrice 21 dates (index) × 269 IDs (colonnes)

| Date (index) | ID_001 | ID_002 | ID_003 | ... | ID_269 |
|--------------|--------|--------|--------|-----|--------|
| 2021-06-30 | 2.45 | 3.12 | 1.89 | ... | 2.67 |
| 2021-09-30 | 2.48 | 3.08 | 1.92 | ... | 2.65 |
| ... | ... | ... | ... | ... | ... |
| 2025-12-31 | 2.35 | 2.98 | 1.85 | ... | 2.58 |

**Interprétation** : Une valeur ITR de 2°C indique que l'entreprise est alignée avec l'objectif de l'Accord de Paris. Des valeurs plus élevées signalent un moins bon alignement climatique.

**Utilité** : 
Ce fichier est crucial pour imposer la contrainte climat (ITR du portefeuille < 2°C) en calculant la moyenne pondérée des ITR des entreprises sélectionnées.

### 3. `price.parquet` - Prix des titres

**Structure** : Matrice 21 dates (index) × 269 IDs (colonnes)

| Date (index) | ID_001 | ID_002 | ID_003 | ... | ID_269 |
|--------------|--------|--------|--------|-----|--------|
| 2021-06-30 | 0.0125 | 0.0089 | 0.0234 | ... | 0.0156 |
| 2021-09-30 | 0.0128 | 0.0091 | 0.0229 | ... | 0.0159 |
| ... | ... | ... | ... | ... | ... |
| 2025-12-31 | 0.0142 | 0.0095 | 0.0251 | ... | 0.0168 |

**Utilité** :
1. Calculer les **rendements** de chaque titre et du portefeuille
2. Évaluer la **performance** de l'indice ESG vs l'indice parent
3. Déterminer les **pondérations** après dérive (avant rebalancement)
4. Calculer la **Tracking Error**

### 4. `esg_score.parquet` - Scores ESG

**Structure** : Matrice 21 dates (index) × 269 IDs (colonnes)

| Date (index) | ID_001 | ID_002 | ID_003 | ... | ID_269 |
|--------------|--------|--------|--------|-----|--------|
| 2021-06-30 | 14.5 | 8.2 | 17.3 | ... | 12.6 |
| 2021-09-30 | 14.8 | 8.1 | 17.5 | ... | 12.9 |
| ... | ... | ... | ... | ... | ... |
| 2025-12-31 | 15.2 | 8.5 | 17.8 | ... | 13.2 |

**Interprétation** : Les scores sont sur une échelle de 0 à 20, où **20 représente la meilleure note ESG**. Les scores peuvent évoluer dans le temps, reflétant l'amélioration ou la détérioration des pratiques ESG des entreprises.

**Utilité** :
- Appliquer l'**exclusion des 30% les moins bien notés par secteur**
- Classer les entreprises au sein de chaque secteur
- Suivre l'évolution des pratiques ESG dans le temps

### 5. `universe.parquet` - Poids de l'indice parent

**Structure** : Matrice 21 dates (index) × 269 IDs (colonnes)

| Date (index) | ID_001 | ID_002 | ID_003 | ... | ID_269 |
|--------------|--------|--------|--------|-----|--------|
| 2021-06-30 | 0.0125 | 0.0089 | 0.0000 | ... | 0.0156 |
| 2021-09-30 | 0.0128 | 0.0091 | 0.0045 | ... | 0.0159 |
| ... | ... | ... | ... | ... | ... |
| 2025-12-31 | 0.0142 | 0.0000 | 0.0087 | ... | 0.0168 |

**Interprétation** :
- Chaque valeur représente le **poids de l'entreprise dans l'indice parent** à cette date
- Les poids sont compris entre **0 et 1**, et leur **somme à chaque date = 1** (100% de l'indice)
- Un `NaN` signifie que l'entreprise n'est **pas présente** dans l'indice parent à cette date (radiation, acquisition, critères d'éligibilité non remplis...)
- Un poids non nul indique que l'entreprise fait partie de l'indice parent, avec une pondération proportionnelle à sa capitalisation boursière (pour un indice cap-weighted)

**Utilité** :
1. L'**univers investissable** à chaque date (entreprises avec poids > 0)
2. La **structure de pondération de référence** de l'indice parent
3. Les **entrées/sorties** de l'univers parent au fil du temps
4. La **base de comparaison** pour calculer la Tracking Error et évaluer les écarts de pondération de l'indice ESG

### 6. Conclusion des données

**Points clés** :
- Les **269 IDs sont communs** à tous les fichiers
- Les **21 dates** sont identiques (rebalancements trimestriels)
- Période d'analyse : **2021-06-30 à 2025-12-31** (4.5 années)
- Format **Parquet** : lecture rapide et efficace en Python (pandas, polars)

---

## **Q&A**

### 1. Indice « parent »
L’**indice parent** (ou *parent index*) est l’indice de référence « classique » (ex. MSCI World, STOXX Europe 600, S&P 500, etc.). L’objectif de l’indice ESG est de rester **proche** de cet indice en performance et en exposition (secteurs, pays, styles…), tout en intégrant des contraintes ESG/climat.

### 2. Note ESG : définition
Une **note ESG** est un score (ici de 0 à 20) qui résume l’évaluation d’une entreprise sur :

- **E – Environnement** : émissions, énergie, eau, pollution, stratégie climat, etc.
- **S – Social** : conditions de travail, santé/sécurité, diversité, chaîne d’approvisionnement, droits humains…
- **G – Gouvernance** : indépendance du conseil, rémunération, éthique, contrôles internes, structure actionnariale…

**À retenir**
- Les scores peuvent différer selon les fournisseurs (méthodologies, données, pondérations).
- Les notes ESG sont souvent utilisées comme proxy de risques extra-financiers(controverses, réglementation, réputation) et/ou de qualité de pratiques.

### 3. Exclusion « 30% en poids des moins bien notés ESG, par secteur »
On cherche à conserver une comparabilité sectorielle avec l’indice parent.

**Principe**
1. On partitionne l’univers par secteur.
2. Dans chaque secteur, on classe les entreprises selon leur score ESG.
3. On exclut les entreprises représentant les 30% les moins bien notées en poids dans ce secteur.

**Pourquoi “en poids” ?**
- On raisonne en **poids d’indice** (poids dans l'indice parent parent), pas en nombre d’entreprises.
- Quelques grandes capitalisations mal notées peuvent suffire à atteindre 30% de poids.

**Pourquoi “par secteur” ?**
- Pour éviter un portefeuille biaisé vers des secteurs structurellement mieux notés (ex. Tech) et sous-pondéré sur d’autres (ex. Énergie).

### 4. Turnover : définition

Le **turnover** mesure l’ampleur des **réallocations** entre deux dates de rebalancement (ici trimestrielles). C’est un proxy des **coûts implicites** : bid-ask, impact de marché, slippage, taxes éventuelles, etc.

**Formule standard (one-way turnover)**
\[
\text{Turnover}_t = \frac{1}{2}\sum_{i} \left| w_{i,t}^{\text{après}} - w_{i,t}^{\text{avant}} \right|
\]
- \(w_{i,t}^{\text{avant}}\) : poids du titre \(i\) juste **avant** rebalancement (après performance du trimestre)
- \(w_{i,t}^{\text{après}}\) : poids cible **après** rebalancement
- Le facteur \(1/2\) évite de compter deux fois (une vente finance un achat).

**Exemple**
- Si vous vendez 5% sur A et achetez 5% sur B, le turnover est ~5% (pas 10%).

### 5. Tracking Error (TE) : définition

La **Tracking Error** mesure l’écart de comportement de l’indice ESG vis-à-vis du parent, via la volatilité des rendements actifs.

**Définition** : écart-type des rendements \(r^{\text{ESG}} - r^{\text{Parent}}\), annualisé.
\[
\text{TE}_{\text{ann}} = \sqrt{K}\; \sigma\left(r_{t}^{\text{ESG}} - r_{t}^{\text{Parent}}\right)
\]
- \(K\) : facteur d’annualisation (ex. 252 si daily, 12 si mensuel, 4 si trimestriel)

**Interprétation**
- TE faible → indice ESG **très proche** du parent (profil « passif »)
- TE élevée → indice ESG prend des paris plus visibles (secteurs, styles, facteurs)

### 6. Contrainte climat « température implicite < 2°C »
La **température implicite** (souvent *Implied Temperature Rise*, ITR) est un indicateur qui traduit l’alignement d’une entreprise/portefeuille avec une trajectoire de réchauffement.

**Intuition**
- Une entreprise alignée « Paris-aligned » aura une température plus basse.
- Une entreprise très exposée / peu alignée aura une température plus élevée.

**Agrégation portefeuille**
\[
\text{ITR}_{\text{port}} = \sum_i w_i \cdot \text{ITR}_i
\]
Contrainte :
\[
\text{ITR}_{\text{port}} < 2^\circ C
\]

Certains secteurs ont des ITR structurellement plus élevés, ce qui peut créer une tension avec la comparabilité sectorielle.

### 7. Rebalancement trimestriel
Un **rebalancement trimestriel** signifie qu’à des dates fixées (ex. fin mars/juin/sept/déc), on met à jour :
- l’univers (entrées/sorties du parent),
- les scores ESG,
- les métriques climat,
- la composition et les poids de l’indice ESG.

Entre deux rebalancements, les poids **dérivent** avec la performance des titres.