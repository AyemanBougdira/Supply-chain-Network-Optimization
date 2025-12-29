import pandas as pd
from pyomo.environ import *

# =====================================================
# 1. Lecture des données
# =====================================================

path = ""

demand_df = pd.read_csv(path+"demand_pct.csv")
capD = pd.read_csv(path+"capacity_depots.csv")
capW = pd.read_csv(path+"capacity_warehouses.csv")
fixD = pd.read_csv(path+"fixed_cost_depots.csv")
fixW = pd.read_csv(path+"fixed_cost_warehouses.csv")
hold = pd.read_csv(path+"holding_costs.csv")

cFD = pd.read_csv(path+"transport_factory_depot.csv")
cDW = pd.read_csv(path+"transport_depot_warehouse.csv")
cWC = pd.read_csv(path+"transport_warehouse_client.csv")

ssD = pd.read_csv(path+"safety_stock_depots.csv")
ssW = pd.read_csv(path+"safety_stock_warehouses.csv")
iD = pd.read_csv(path+"initial_stock_depots.csv")
iW = pd.read_csv(path+"initial_stock_warehouses.csv")

# =====================================================
# 2. Modèle
# =====================================================

m = ConcreteModel()

# ---------------- Sets ----------------
m.P = Set(initialize=demand_df['product'].unique())
m.C = Set(initialize=demand_df['client'].unique())
m.T = Set(initialize=demand_df['month'].unique())
m.F = Set(initialize=[1, 2])
m.D = Set(initialize=capD['depot'].tolist())
m.W = Set(initialize=capW['warehouse'].tolist())

# ---------------- Parameters ----------------
# CORRECTION 1: 'demand_df' remplacé par 'demand'
m.dem = Param(m.P, m.C, m.T,
              initialize={(r['product'], r['client'], r['month'])
                           : r['demand'] for _, r in demand_df.iterrows()},
              within=NonNegativeReals)

m.capD = Param(m.D, initialize=dict(zip(capD['depot'], capD['capacity'])))
m.capW = Param(m.W, initialize=dict(zip(capW['warehouse'], capW['capacity'])))

m.FD = Param(m.D, initialize=dict(zip(fixD['depot'], fixD['fixed_cost'])))
m.FW = Param(m.W, initialize=dict(zip(fixW['warehouse'], fixW['fixed_cost'])))

m.hD = Param(m.P, initialize=dict(zip(hold['product'], hold['holding_depot'])))
m.hW = Param(m.P, initialize=dict(
    zip(hold['product'], hold['holding_warehouse'])))

m.cFD = Param(m.F, m.D, initialize={
              (r['factory'], r['depot']): r['cost'] for _, r in cFD.iterrows()})
m.cDW = Param(m.D, m.W, initialize={
              (r['depot'], r['warehouse']): r['cost'] for _, r in cDW.iterrows()})
m.cWC = Param(m.W, m.C, initialize={
              (r['warehouse'], r['client']): r['cost'] for _, r in cWC.iterrows()})

m.ssD = Param(m.P, initialize=dict(zip(ssD['product'], ssD['safety_stock'])))
m.ssW = Param(m.P, initialize=dict(zip(ssW['product'], ssW['safety_stock'])))

m.ID0 = Param(m.P, initialize=dict(zip(iD['product'], iD['initial_stock'])))
m.IW0 = Param(m.P, initialize=dict(zip(iW['product'], iW['initial_stock'])))

# ---------------- Variables ----------------
m.yD = Var(m.D, within=Binary)
m.yW = Var(m.W, within=Binary)

m.q1 = Var(m.P, m.F, m.D, m.T, within=NonNegativeReals)
m.q2 = Var(m.P, m.D, m.W, m.T, within=NonNegativeReals)
m.q3 = Var(m.P, m.W, m.C, m.T, within=NonNegativeReals)

m.ID = Var(m.P, m.D, m.T, within=NonNegativeReals)
m.IW = Var(m.P, m.W, m.T, within=NonNegativeReals)

# =====================================================
# 3. Fonction Objectif
# =====================================================


def obj_rule(m):
    return sum(
        m.cFD[f, d] * m.q1[p, f, d, t]
        + m.cDW[d, w] * m.q2[p, d, w, t]
        + m.cWC[w, c] * m.q3[p, w, c, t]
        for p in m.P for f in m.F for d in m.D
        for w in m.W for c in m.C for t in m.T
    ) \
        + sum(m.FD[d] * m.yD[d] for d in m.D) \
        + sum(m.FW[w] * m.yW[w] for w in m.W) \
        + sum(m.hD[p] * m.ID[p, d, t] for p in m.P for d in m.D for t in m.T) \
        + sum(m.hW[p] * m.IW[p, w, t] for p in m.P for w in m.W for t in m.T)


m.OBJ = Objective(rule=obj_rule, sense=minimize)

# =====================================================
# 4. Contraintes
# =====================================================

# --- Demande ---
# CORRECTION 2: 'demand_df_rule' renommé en 'demand_rule'


def demand_rule(m, p, c, t):
    return sum(m.q3[p, w, c, t] for w in m.W) == m.dem[p, c, t]


m.DEM = Constraint(m.P, m.C, m.T, rule=demand_rule)

# --- Stock dépôts ---


def stockD_rule(m, p, d, t):
    if t == 1:
        return m.ID[p, d, t] == m.ID0[p] \
            + sum(m.q1[p, f, d, t] for f in m.F) \
            - sum(m.q2[p, d, w, t] for w in m.W)
    return m.ID[p, d, t] == m.ID[p, d, t-1] \
        + sum(m.q1[p, f, d, t] for f in m.F) \
        - sum(m.q2[p, d, w, t] for w in m.W)


m.STD = Constraint(m.P, m.D, m.T, rule=stockD_rule)

# --- Stock entrepôts ---


def stockW_rule(m, p, w, t):
    if t == 1:
        return m.IW[p, w, t] == m.IW0[p] \
            + sum(m.q2[p, d, w, t] for d in m.D) \
            - sum(m.q3[p, w, c, t] for c in m.C)
    return m.IW[p, w, t] == m.IW[p, w, t-1] \
        + sum(m.q2[p, d, w, t] for d in m.D) \
        - sum(m.q3[p, w, c, t] for c in m.C)


m.STW = Constraint(m.P, m.W, m.T, rule=stockW_rule)

# --- Capacités ---
m.CAPD = Constraint(m.D, m.T,
                    rule=lambda m, d, t: sum(m.q2[p, d, w, t] for p in m.P for w in m.W) <= m.capD[d] * m.yD[d])

m.CAPW = Constraint(m.W, m.T,
                    rule=lambda m, w, t: sum(m.q3[p, w, c, t] for p in m.P for c in m.C) <= m.capW[w] * m.yW[w])

# --- Stocks de sécurité ---
m.SSD = Constraint(m.P, m.D, m.T, rule=lambda m, p,
                   d, t: m.ID[p, d, t] >= m.ssD[p])
m.SSW = Constraint(m.P, m.W, m.T, rule=lambda m, p,
                   w, t: m.IW[p, w, t] >= m.ssW[p])

# =====================================================
# 5. Résolution
# =====================================================

solver = SolverFactory("glpk")  # ou gurobi, cplex
results = solver.solve(m, tee=True)

# Affichage des résultats
print("\n" + "="*50)
print("RÉSULTATS DE L'OPTIMISATION")
print("="*50)
print(f"Statut: {results.solver.status}")
print(f"Condition: {results.solver.termination_condition}")
print(f"Valeur optimale: {value(m.OBJ):,.2f}")
print("="*50)
