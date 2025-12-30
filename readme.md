# Supply Chain Network Optimization (MILP)

Fait par: 
- Ayeman BOUGDIRA
- Ranya KSSIM
- Mohammed OUTAABOUT
- Aya El Kouach

## 🧑‍💻Utiliser l'application
Exécuter les commandes suivantes au terminal

"""
git clone https://github.com/AyemanBougdira/Supply-chain-Network-Optimization.git
cd Supply-chain-Network-Optimization
pip install -r requirements.txt
conda install -c conda-forge glpk  
"""

Lancer l'application et modifier les données:

"""
streamlit run app.py
"""

Déclancher l'optimisation en cliquant sur "LANCER L'OPTMISATION"

## 📦 Description du Projet

Ce projet porte sur la **conception et l’optimisation d’un réseau logistique multi-échelons** à l’aide d’un **modèle de Programmation Linéaire en Nombres Entiers Mixtes (MILP)**.

Le réseau étudié comporte **quatre niveaux** :
- Usines
- Dépôts
- Entrepôts
- Clients

Le modèle est :
- **multi-produits**
- **multi-périodes (12 mois)**
- intégrant des **décisions stratégiques** (ouverture des sites),
- des **décisions tactiques** (flux),
- et des **décisions opérationnelles** (gestion des stocks).

L’objectif est de **minimiser le coût total** comprenant :
- les coûts de transport,
- les coûts fixes de location,
- les coûts de stockage,
tout en satisfaisant la demande et en respectant les contraintes de capacité et de stock de sécurité.

---

## 🎯 Objectifs

- Concevoir un modèle MILP réaliste pour un réseau logistique
- Implémenter le modèle avec **Pyomo**
- Résoudre un problème de grande dimension avec un solveur open-source (**GLPK**)
- Analyser en détail le processus de résolution (Simplexe, Branch-and-Bound)
- Valider la solution optimale et évaluer les performances computationnelles

---

## 🧮 Modèle Mathématique

**Type de modèle** : MILP  
**Horizon de planification** : 12 mois  
**Dimensions principales** :
- 2 usines
- 3 dépôts
- 20 entrepôts
- 209 clients
- 3 produits

**Décisions clés** :
- Ouverture/fermeture des dépôts et entrepôts
- Flux de produits entre chaque niveau
- Niveaux de stock par période

---

## 🗂️ Structure du Répertoire

```text
.
├── data/
│   ├── demand_pct.csv
│   ├── capacity_depots.csv
│   ├── capacity_warehouses.csv
│   ├── fixed_cost_depots.csv
│   ├── fixed_cost_warehouses.csv
│   ├── holding_costs.csv
│   ├── transport_factory_depot.csv
│   ├── transport_depot_warehouse.csv
│   ├── transport_warehouse_client.csv
│   ├── safety_stock_depots.csv
│   ├── safety_stock_warehouses.csv
│   ├── initial_stock_depots.csv
│   └── initial_stock_warehouses.csv
│
├── model/
│   ├── model.py
|   |── solve_model.py
│
├── results/
│   ├── solution_summary.txt
│   
│
├── README.md
└── requirements.txt
