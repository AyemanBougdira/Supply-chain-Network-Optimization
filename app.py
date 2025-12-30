import streamlit as st
import pandas as pd
import numpy as np
import os
from pyomo.environ import *
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

from improvedmodel import build_model
from improvedmodel import analyze_results
from improvedmodel import generate_all_visualizations

# =====================================================
# 1. LOGIQUE DU MODÈLE (VOTRE CODE PYOMO)
# =====================================================


def load_and_validate_data(path=""):
    data = {
        'demand': pd.read_csv(path+"demand_pct.csv"),
        'capD': pd.read_csv(path+"capacity_depots.csv"),
        'capW': pd.read_csv(path+"capacity_warehouses.csv"),
        'fixD': pd.read_csv(path+"fixed_cost_depots.csv"),
        'fixW': pd.read_csv(path+"fixed_cost_warehouses.csv"),
        'hold': pd.read_csv(path+"holding_costs.csv"),
        'cFD': pd.read_csv(path+"transport_factory_depot.csv"),
        'cDW': pd.read_csv(path+"transport_depot_warehouse.csv"),
        'cWC': pd.read_csv(path+"transport_warehouse_client.csv"),
        'ssD': pd.read_csv(path+"safety_stock_depots.csv"),
        'ssW': pd.read_csv(path+"safety_stock_warehouses.csv"),
        'iD': pd.read_csv(path+"initial_stock_depots.csv"),
        'iW': pd.read_csv(path+"initial_stock_warehouses.csv")
    }
    return data




# def analyze_results_dict(m, results):
#     total_cost = value(m.OBJ)
#     depots_ouverts = [d for d in m.D if value(m.yD[d]) > 0.5]
#     entrepots_ouverts = [w for w in m.W if value(m.yW[w]) > 0.5]
#     return {'total_cost': total_cost, 'depots_ouverts': depots_ouverts, 'entrepots_ouverts': entrepots_ouverts}

# =====================================================
# 2. INTERFACE STREAMLIT
# =====================================================


st.set_page_config(page_title="Supply Chain Optimizer", layout="wide")
st.title("🚚 Optimisation Supply Chain")

files_config = {
    "Demande": "demand_pct.csv", "Capacité Dépôts": "capacity_depots.csv",
    "Capacité Entrepôts": "capacity_warehouses.csv", "Coûts Fixes Dépôts": "fixed_cost_depots.csv",
    "Coûts Fixes Entrepôts": "fixed_cost_warehouses.csv", "Coûts Stockage": "holding_costs.csv",
    "Transport Usine-Dépôt": "transport_factory_depot.csv", "Transport Dépôt-Entrepôt": "transport_depot_warehouse.csv",
    "Transport Entrepôt-Client": "transport_warehouse_client.csv", "Stock Sécurité Dépôts": "safety_stock_depots.csv",
    "Stock Sécurité Entrepôts": "safety_stock_warehouses.csv", "Stock Initial Dépôts": "initial_stock_depots.csv",
    "Stock Initial Entrepôts": "initial_stock_warehouses.csv"
}

tab1, tab2 = st.tabs(["📊 Données d'Entrée", "🚀 Optimisation"])

with tab1:
    st.subheader("Visualisation et Edition")
    for label, filename in files_config.items():
        with st.expander(f"📄 {label} ({filename})"):
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                edited_df = st.data_editor(
                    df, key=f"ed_{filename}", hide_index=True)
                if st.button(f"Sauvegarder {label}", key=f"btn_{filename}"):
                    edited_df.to_csv(filename, index=False)
                    st.success("Sauvegardé !")
            else:
                st.error(f"Fichier {filename} non trouvé.")

with tab2:
    if st.button("▶️ LANCER L'OPTIMISATION"):
        with st.spinner("Calcul en cours avec GLPK..."):
            try:
                data = load_and_validate_data()
                model = build_model(data)
                # solver = SolverFactory("glpk")
                solver = SolverFactory("cbc")
                results = solver.solve(model)

                analysis = analyze_results(model, results)

                st.balloons()
                st.success("Optimisation Réussie !")

                c1, c2, c3 = st.columns(3)
                c1.metric("Coût Total", f"{analysis['total_cost']:,.0f} MAD")
                c2.metric(
                    "Dépôts", f"{len(analysis['depots_ouverts'])} Ouverts")
                c3.metric(
                    "Entrepôts", f"{len(analysis['entrepots_ouverts'])} Ouverts")
                
                d1, d2 = st.columns(2)
                with d1:
                    st.image("cost_breakdown.png")
                    st.image("flux_evolution.png")
                with d2:
                    st.image("stock_evolution.png")
                    st.image("capacity_utilization.png")

            except Exception as e:
                st.error(f"Erreur : {e}")
