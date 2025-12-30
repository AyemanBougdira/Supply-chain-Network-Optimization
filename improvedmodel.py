from pyomo.environ import value
import pandas as pd
import numpy as np
from pyomo.environ import *
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# =====================================================
# 1. Lecture des données avec validation
# =====================================================


def load_and_validate_data(path=""):
    """Charge et valide toutes les données avec gestion d'erreurs"""
    try:
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

        # Validation basique
        print("✓ Données chargées avec succès")
        print(f"  - Demandes: {len(data['demand'])} lignes")
        print(f"  - Clients: {data['demand']['client'].nunique()}")
        print(f"  - Produits: {data['demand']['product'].nunique()}")
        print(f"  - Périodes: {data['demand']['month'].nunique()}")

        return data
    except FileNotFoundError as e:
        print(f"❌ Erreur: Fichier non trouvé - {e}")
        raise
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        raise

# =====================================================
# 2. Construction du modèle
# =====================================================


def build_model(data):
    """Construit le modèle Pyomo"""
    m = ConcreteModel(name="Supply_Chain_Network")

    # ---------------- Sets ----------------
    m.P = Set(initialize=data['demand']['product'].unique(), doc="Produits")
    m.C = Set(initialize=data['demand']['client'].unique(), doc="Clients")
    m.T = Set(initialize=data['demand']['month'].unique(), doc="Périodes")
    m.F = Set(initialize=[1, 2], doc="Usines")
    m.D = Set(initialize=data['capD']['depot'].tolist(), doc="Dépôts")
    m.W = Set(initialize=data['capW']['warehouse'].tolist(), doc="Entrepôts")

    # ---------------- Parameters ----------------
    m.dem = Param(m.P, m.C, m.T,
                  initialize={(r['product'], r['client'], r['month']): r['demand']
                              for _, r in data['demand'].iterrows()},
                  within=NonNegativeReals, doc="Demande")

    m.capD = Param(m.D, initialize=dict(
        zip(data['capD']['depot'], data['capD']['capacity'])))
    m.capW = Param(m.W, initialize=dict(
        zip(data['capW']['warehouse'], data['capW']['capacity'])))

    m.FD = Param(m.D, initialize=dict(
        zip(data['fixD']['depot'], data['fixD']['fixed_cost'])))
    m.FW = Param(m.W, initialize=dict(
        zip(data['fixW']['warehouse'], data['fixW']['fixed_cost'])))

    m.hD = Param(m.P, initialize=dict(
        zip(data['hold']['product'], data['hold']['holding_depot'])))
    m.hW = Param(m.P, initialize=dict(
        zip(data['hold']['product'], data['hold']['holding_warehouse'])))

    m.cFD = Param(m.F, m.D, initialize={(r['factory'], r['depot']): r['cost']
                                        for _, r in data['cFD'].iterrows()})
    m.cDW = Param(m.D, m.W, initialize={(r['depot'], r['warehouse']): r['cost']
                                        for _, r in data['cDW'].iterrows()})
    m.cWC = Param(m.W, m.C, initialize={(r['warehouse'], r['client']): r['cost']
                                        for _, r in data['cWC'].iterrows()})

    m.ssD = Param(m.P, initialize=dict(
        zip(data['ssD']['product'], data['ssD']['safety_stock'])))
    m.ssW = Param(m.P, initialize=dict(
        zip(data['ssW']['product'], data['ssW']['safety_stock'])))

    m.ID0 = Param(m.P, initialize=dict(
        zip(data['iD']['product'], data['iD']['initial_stock'])))
    m.IW0 = Param(m.P, initialize=dict(
        zip(data['iW']['product'], data['iW']['initial_stock'])))

    # ---------------- Variables ----------------
    m.yD = Var(m.D, within=Binary, doc="Ouverture dépôt")
    m.yW = Var(m.W, within=Binary, doc="Ouverture entrepôt")

    m.q1 = Var(m.P, m.F, m.D, m.T, within=NonNegativeReals,
               doc="Flux usine->dépôt")
    m.q2 = Var(m.P, m.D, m.W, m.T, within=NonNegativeReals,
               doc="Flux dépôt->entrepôt")
    m.q3 = Var(m.P, m.W, m.C, m.T, within=NonNegativeReals,
               doc="Flux entrepôt->client")

    m.ID = Var(m.P, m.D, m.T, within=NonNegativeReals, doc="Stock dépôt")
    m.IW = Var(m.P, m.W, m.T, within=NonNegativeReals, doc="Stock entrepôt")

    # =====================================================
    # 3. Fonction Objectif
    # =====================================================

    def obj_rule(m):

        cost_FD = sum(
            m.cFD[f, d] * m.q1[p, f, d, t]
            for p in m.P for f in m.F for d in m.D for t in m.T
        )

        cost_DW = sum(
            m.cDW[d, w] * m.q2[p, d, w, t]
            for p in m.P for d in m.D for w in m.W for t in m.T
        )

        cost_WC = sum(
            m.cWC[w, c] * m.q3[p, w, c, t]
            for p in m.P for w in m.W for c in m.C for t in m.T
        )

        fixed_costs = (
            sum(m.FD[d] * m.yD[d] for d in m.D)
        + sum(m.FW[w] * m.yW[w] for w in m.W)
        )

        holding_costs = (
            sum(m.hD[p] * m.ID[p, d, t] for p in m.P for d in m.D for t in m.T)
        + sum(m.hW[p] * m.IW[p, w, t] for p in m.P for w in m.W for t in m.T)
        )

        return cost_FD + cost_DW + cost_WC + fixed_costs + holding_costs

    m.OBJ = Objective(rule=obj_rule, sense=minimize)

    # =====================================================
    # 4. Contraintes
    # =====================================================

    # Satisfaction de la demande
    def demand_rule(m, p, c, t):
        return sum(m.q3[p, w, c, t] for w in m.W) == m.dem[p, c, t]
    m.DEM = Constraint(m.P, m.C, m.T, rule=demand_rule)

    # Équilibre stocks dépôts
    def stockD_rule(m, p, d, t):
        if t == 1:
            return m.ID[p, d, t] == m.ID0[p] + sum(m.q1[p, f, d, t] for f in m.F) - sum(m.q2[p, d, w, t] for w in m.W)
        return m.ID[p, d, t] == m.ID[p, d, t-1] + sum(m.q1[p, f, d, t] for f in m.F) - sum(m.q2[p, d, w, t] for w in m.W)
    m.STD = Constraint(m.P, m.D, m.T, rule=stockD_rule)

    # Équilibre stocks entrepôts
    def stockW_rule(m, p, w, t):
        if t == 1:
            return m.IW[p, w, t] == m.IW0[p] + sum(m.q2[p, d, w, t] for d in m.D) - sum(m.q3[p, w, c, t] for c in m.C)
        return m.IW[p, w, t] == m.IW[p, w, t-1] + sum(m.q2[p, d, w, t] for d in m.D) - sum(m.q3[p, w, c, t] for c in m.C)
    m.STW = Constraint(m.P, m.W, m.T, rule=stockW_rule)

    # Capacités
    m.CAPD = Constraint(m.D, m.T,
                        rule=lambda m, d, t: sum(m.q2[p, d, w, t] for p in m.P for w in m.W) <= m.capD[d] * m.yD[d])
    m.CAPW = Constraint(m.W, m.T,
                        rule=lambda m, w, t: sum(m.q3[p, w, c, t] for p in m.P for c in m.C) <= m.capW[w] * m.yW[w])

    # Stocks de sécurité
    m.SSD = Constraint(m.P, m.D, m.T, rule=lambda m, p,
                       d, t: m.ID[p, d, t] >= m.ssD[p])
    m.SSW = Constraint(m.P, m.W, m.T, rule=lambda m, p,
                       w, t: m.IW[p, w, t] >= m.ssW[p])

    print(
        f"\n✓ Modèle construit: {len(m.P)} produits, {len(m.C)} clients, {len(m.T)} périodes")

    return m

# =====================================================
# 5. Analyse des résultats
# =====================================================


def analyze_results(m, results):
    """Analyse complète de la solution optimale"""

    print("\n" + "="*70)
    print("                    RÉSULTATS DE L'OPTIMISATION")
    print("="*70)

    # 1. Statut de la solution
    print(f"\n📊 STATUT DE LA SOLUTION")
    print(f"   Statut du solveur: {results.solver.status}")
    print(f"   Condition d'arrêt: {results.solver.termination_condition}")
    print(f"   Temps de calcul: {results.solver.time:.2f} secondes")

    if results.solver.termination_condition != TerminationCondition.optimal:
        print("⚠️  ATTENTION: Solution non-optimale!")
        return None

    # 2. Coût total
    total_cost = value(m.OBJ)
    print(f"\n💰 COÛT TOTAL OPTIMAL: {total_cost:,.2f} MAD")

    # 3. Sites ouverts
    print(f"\n🏢 CONFIGURATION DU RÉSEAU")

    depots_ouverts = [d for d in m.D if value(m.yD[d]) > 0.5]
    depots_fermes = [d for d in m.D if value(m.yD[d]) < 0.5]
    print(
        f"   Dépôts ouverts ({len(depots_ouverts)}/{len(m.D)}): {depots_ouverts}")
    print(
        f"   Dépôts fermés ({len(depots_fermes)}/{len(m.D)}): {depots_fermes}")

    entrepots_ouverts = [w for w in m.W if value(m.yW[w]) > 0.5]
    entrepots_fermes = [w for w in m.W if value(m.yW[w]) < 0.5]
    print(
        f"   Entrepôts ouverts ({len(entrepots_ouverts)}/{len(m.W)}): {entrepots_ouverts[:10]}{'...' if len(entrepots_ouverts) > 10 else ''}")
    print(
        f"   Entrepôts fermés ({len(entrepots_fermes)}/{len(m.W)}): {entrepots_fermes[:10]}{'...' if len(entrepots_fermes) > 10 else ''}")

    # 4. Décomposition des coûts
    print(f"\n📈 DÉCOMPOSITION DES COÛTS")

    # Coûts de transport
    cout_transport_fd = sum(value(m.cFD[f, d] * m.q1[p, f, d, t])
                            for p in m.P for f in m.F for d in m.D for t in m.T)
    cout_transport_dw = sum(value(m.cDW[d, w] * m.q2[p, d, w, t])
                            for p in m.P for d in m.D for w in m.W for t in m.T)
    cout_transport_wc = sum(value(m.cWC[w, c] * m.q3[p, w, c, t])
                            for p in m.P for w in m.W for c in m.C for t in m.T)
    cout_transport_total = cout_transport_fd + cout_transport_dw + cout_transport_wc

    # Coûts fixes
    cout_fixe_depots = sum(value(m.FD[d] * m.yD[d]) for d in m.D)
    cout_fixe_entrepots = sum(value(m.FW[w] * m.yW[w]) for w in m.W)
    cout_fixe_total = cout_fixe_depots + cout_fixe_entrepots

    # Coûts de stockage
    cout_stockage_depots = sum(
        value(m.hD[p] * m.ID[p, d, t]) for p in m.P for d in m.D for t in m.T)
    cout_stockage_entrepots = sum(
        value(m.hW[p] * m.IW[p, w, t]) for p in m.P for w in m.W for t in m.T)
    cout_stockage_total = cout_stockage_depots + cout_stockage_entrepots

    print(
        f"\n   COÛTS DE TRANSPORT ({cout_transport_total/total_cost*100:.1f}%):")
    print(
        f"      - Usine → Dépôt:      {cout_transport_fd:>15,.2f} MAD ({cout_transport_fd/total_cost*100:>5.2f}%)")
    print(
        f"      - Dépôt → Entrepôt:   {cout_transport_dw:>15,.2f} MAD ({cout_transport_dw/total_cost*100:>5.2f}%)")
    print(
        f"      - Entrepôt → Client:  {cout_transport_wc:>15,.2f} MAD ({cout_transport_wc/total_cost*100:>5.2f}%)")
    print(f"      - TOTAL TRANSPORT:    {cout_transport_total:>15,.2f} MAD")

    print(f"\n   COÛTS FIXES ({cout_fixe_total/total_cost*100:.1f}%):")
    print(
        f"      - Dépôts:             {cout_fixe_depots:>15,.2f} MAD ({cout_fixe_depots/total_cost*100:>5.2f}%)")
    print(
        f"      - Entrepôts:          {cout_fixe_entrepots:>15,.2f} MAD ({cout_fixe_entrepots/total_cost*100:>5.2f}%)")
    print(f"      - TOTAL FIXES:        {cout_fixe_total:>15,.2f} MAD")

    print(
        f"\n   COÛTS DE STOCKAGE ({cout_stockage_total/total_cost*100:.1f}%):")
    print(
        f"      - Dépôts:             {cout_stockage_depots:>15,.2f} MAD ({cout_stockage_depots/total_cost*100:>5.2f}%)")
    print(
        f"      - Entrepôts:          {cout_stockage_entrepots:>15,.2f} MAD ({cout_stockage_entrepots/total_cost*100:>5.2f}%)")
    print(f"      - TOTAL STOCKAGE:     {cout_stockage_total:>15,.2f} MAD")

    # 5. Analyse des flux
    print(f"\n📦 ANALYSE DES FLUX")

    flux_total = sum(value(m.q3[p, w, c, t])
                     for p in m.P for w in m.W for c in m.C for t in m.T)
    print(f"   Volume total livré aux clients: {flux_total:,.0f} unités")

    flux_par_periode = {}
    for t in m.T:
        flux_par_periode[t] = sum(value(m.q3[p, w, c, t])
                                  for p in m.P for w in m.W for c in m.C)
    print(
        f"   Flux moyen par mois: {np.mean(list(flux_par_periode.values())):,.0f} unités")
    print(
        f"   Flux maximum: {max(flux_par_periode.values()):,.0f} unités (mois {max(flux_par_periode, key=flux_par_periode.get)})")
    print(
        f"   Flux minimum: {min(flux_par_periode.values()):,.0f} unités (mois {min(flux_par_periode, key=flux_par_periode.get)})")

    # 6. Taux d'utilisation des capacités
    print(f"\n⚙️  TAUX D'UTILISATION DES CAPACITÉS")

    util_depots = {}
    for d in depots_ouverts:
        utilisation = sum(value(m.q2[p, d, w, t])
                          for p in m.P for w in m.W for t in m.T)
        capacite_totale = value(m.capD[d]) * len(m.T)
        util_depots[d] = (utilisation / capacite_totale *
                          100) if capacite_totale > 0 else 0

    if util_depots:
        print(f"   Dépôts:")
        print(
            f"      - Utilisation moyenne: {np.mean(list(util_depots.values())):.1f}%")
        print(
            f"      - Utilisation maximale: {max(util_depots.values()):.1f}% (dépôt {max(util_depots, key=util_depots.get)})")
        print(
            f"      - Utilisation minimale: {min(util_depots.values()):.1f}% (dépôt {min(util_depots, key=util_depots.get)})")

    util_entrepots = {}
    for w in entrepots_ouverts:
        utilisation = sum(value(m.q3[p, w, c, t])
                          for p in m.P for c in m.C for t in m.T)
        capacite_totale = value(m.capW[w]) * len(m.T)
        util_entrepots[w] = (utilisation / capacite_totale *
                             100) if capacite_totale > 0 else 0

    if util_entrepots:
        print(f"   Entrepôts:")
        print(
            f"      - Utilisation moyenne: {np.mean(list(util_entrepots.values())):.1f}%")
        print(
            f"      - Utilisation maximale: {max(util_entrepots.values()):.1f}% (entrepôt {max(util_entrepots, key=util_entrepots.get)})")
        print(
            f"      - Utilisation minimale: {min(util_entrepots.values()):.1f}% (entrepôt {min(util_entrepots, key=util_entrepots.get)})")

    # 7. Analyse des stocks
    print(f"\n📊 ANALYSE DES STOCKS")

    stock_moyen_depots = np.mean([value(m.ID[p, d, t])
                                 for p in m.P for d in depots_ouverts for t in m.T])
    stock_moyen_entrepots = np.mean(
        [value(m.IW[p, w, t]) for p in m.P for w in entrepots_ouverts for t in m.T])

    print(f"   Stock moyen dans les dépôts: {stock_moyen_depots:,.0f} unités")
    print(
        f"   Stock moyen dans les entrepôts: {stock_moyen_entrepots:,.0f} unités")

    print("\n" + "="*70)

    # Retourner un dictionnaire avec tous les résultats
    return {
        'total_cost': total_cost,
        'depots_ouverts': depots_ouverts,
        'entrepots_ouverts': entrepots_ouverts,
        'cout_transport': cout_transport_total,
        'cout_fixe': cout_fixe_total,
        'cout_stockage': cout_stockage_total,
        'flux_par_periode': flux_par_periode,
        'util_depots': util_depots,
        'util_entrepots': util_entrepots
    }

# =====================================================
# 6. Export des résultats
# =====================================================


def export_results(m, output_path="results/"):
    """Exporte les résultats vers des fichiers CSV"""
    import os
    os.makedirs(output_path, exist_ok=True)

    # Sites ouverts
    sites_df = pd.DataFrame({
        'depot': list(m.D),
        'ouvert': [value(m.yD[d]) for d in m.D]
    })
    sites_df.to_csv(output_path + "sites_depots.csv", index=False)

    sites_w_df = pd.DataFrame({
        'warehouse': list(m.W),
        'ouvert': [value(m.yW[w]) for w in m.W]
    })
    sites_w_df.to_csv(output_path + "sites_entrepots.csv", index=False)

    # Flux principaux (> 0)
    flux_q3 = []
    for p in m.P:
        for w in m.W:
            for c in m.C:
                for t in m.T:
                    val = value(m.q3[p, w, c, t])
                    if val > 0.01:
                        flux_q3.append({
                            'product': p, 'warehouse': w, 'client': c,
                            'month': t, 'quantity': val
                        })

    pd.DataFrame(flux_q3).to_csv(
        output_path + "flux_entrepot_client.csv", index=False)

    print(f"\n✓ Résultats exportés dans {output_path}")


    import matplotlib.pyplot as plt

import seaborn as sns

# Configuration du style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def plot_cost_breakdown(analysis):
    """Graphique en camembert de la décomposition des coûts"""

    fig, ax = plt.subplots(1, 1, figsize=(10, 7))

    costs = [
        analysis['cout_transport'],
        analysis['cout_fixe'],
        analysis['cout_stockage']
    ]
    labels = ['Transport', 'Coûts Fixes', 'Stockage']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    explode = (0.05, 0.05, 0.05)

    wedges, texts, autotexts = ax.pie(
        costs,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        explode=explode,
        textprops={'fontsize': 12, 'weight': 'bold'}
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)

    ax.set_title('Répartition des Coûts Totaux',
                 fontsize=16, weight='bold', pad=20)

    # Légende avec valeurs
    legend_labels = [f'{labels[i]}: {costs[i]:,.0f} MAD ({costs[i]/sum(costs)*100:.1f}%)'
                     for i in range(len(labels))]
    ax.legend(legend_labels, loc='upper left',
              bbox_to_anchor=(1, 1), fontsize=10)

    plt.tight_layout()
    plt.savefig('cost_breakdown.png', dpi=300, bbox_inches='tight')
    print("✓ Graphique sauvegardé: cost_breakdown.png")
    # plt.show()


def plot_flux_evolution(analysis):
    """Graphique de l'évolution des flux mensuels"""

    fig, ax = plt.subplots(figsize=(12, 6))

    mois = sorted(analysis['flux_par_periode'].keys())
    flux = [analysis['flux_par_periode'][m] for m in mois]

    ax.plot(mois, flux, marker='o', linewidth=2.5, markersize=8,
            color='#3498db', label='Flux mensuel')
    ax.fill_between(mois, flux, alpha=0.3, color='#3498db')

    # Ligne de tendance
    z = np.polyfit(mois, flux, 1)
    p = np.poly1d(z)
    ax.plot(mois, p(mois), "--", linewidth=2, color='#e74c3c',
            label=f'Tendance (pente: {z[0]:,.0f})')

    # Moyenne
    flux_moyen = np.mean(flux)
    ax.axhline(y=flux_moyen, color='#2ecc71', linestyle='--', linewidth=2,
               label=f'Moyenne: {flux_moyen:,.0f} unités')

    ax.set_xlabel('Mois', fontsize=12, weight='bold')
    ax.set_ylabel('Flux Total (unités)', fontsize=12, weight='bold')
    ax.set_title('Évolution des Flux Mensuels',
                 fontsize=14, weight='bold', pad=15)
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('flux_evolution.png', dpi=300, bbox_inches='tight')
    print("✓ Graphique sauvegardé: flux_evolution.png")
    # plt.show()


def plot_capacity_utilization(analysis):
    """Graphique des taux d'utilisation des capacités"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Dépôts
    if analysis['util_depots']:
        depots = list(analysis['util_depots'].keys())
        util_d = list(analysis['util_depots'].values())

        colors_d = ['#2ecc71' if u > 80 else '#f39c12' if u > 50 else '#e74c3c'
                    for u in util_d]

        ax1.barh(depots, util_d, color=colors_d,
                 edgecolor='black', linewidth=1.2)
        ax1.axvline(x=80, color='red', linestyle='--',
                    linewidth=2, label='Seuil critique (80%)')
        ax1.set_xlabel('Taux d\'utilisation (%)', fontsize=11, weight='bold')
        ax1.set_ylabel('Dépôt', fontsize=11, weight='bold')
        ax1.set_title('Utilisation des Dépôts', fontsize=13, weight='bold')
        ax1.legend()
        ax1.grid(axis='x', alpha=0.3)

    # Entrepôts (top 15)
    if analysis['util_entrepots']:
        entrepots_sorted = sorted(analysis['util_entrepots'].items(),
                                  key=lambda x: x[1], reverse=True)[:15]
        entrepots = [e[0] for e in entrepots_sorted]
        util_w = [e[1] for e in entrepots_sorted]

        colors_w = ['#2ecc71' if u > 80 else '#f39c12' if u > 50 else '#e74c3c'
                    for u in util_w]

        ax2.barh(entrepots, util_w, color=colors_w,
                 edgecolor='black', linewidth=1.2)
        ax2.axvline(x=80, color='red', linestyle='--',
                    linewidth=2, label='Seuil critique (80%)')
        ax2.set_xlabel('Taux d\'utilisation (%)', fontsize=11, weight='bold')
        ax2.set_ylabel('Entrepôt', fontsize=11, weight='bold')
        ax2.set_title('Top 15 Entrepôts (Utilisation)',
                      fontsize=13, weight='bold')
        ax2.legend()
        ax2.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig('capacity_utilization.png', dpi=300, bbox_inches='tight')
    print("✓ Graphique sauvegardé: capacity_utilization.png")
    # plt.show()


def plot_stock_evolution(m, depots_ouverts, entrepots_ouverts_sample):
    """Évolution des stocks au cours du temps"""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Stocks dépôts
    for d in depots_ouverts[:3]:  # Top 3 dépôts
        for p in list(m.P)[:2]:  # 2 premiers produits
            mois = sorted(m.T)
            stocks = [value(m.ID[p, d, t]) for t in mois]
            ax1.plot(mois, stocks, marker='o',
                     label=f'Dépôt {d} - Produit {p}', linewidth=2)

    ax1.set_xlabel('Mois', fontsize=11, weight='bold')
    ax1.set_ylabel('Stock (unités)', fontsize=11, weight='bold')
    ax1.set_title('Évolution des Stocks dans les Dépôts',
                  fontsize=13, weight='bold')
    ax1.legend(fontsize=9, loc='best')
    ax1.grid(True, alpha=0.3)

    # Stocks entrepôts
    for w in entrepots_ouverts_sample[:3]:  # Top 3 entrepôts
        for p in list(m.P)[:2]:
            mois = sorted(m.T)
            stocks = [value(m.IW[p, w, t]) for t in mois]
            ax2.plot(mois, stocks, marker='s',
                     label=f'Entrepôt {w} - Produit {p}', linewidth=2)

    ax2.set_xlabel('Mois', fontsize=11, weight='bold')
    ax2.set_ylabel('Stock (unités)', fontsize=11, weight='bold')
    ax2.set_title('Évolution des Stocks dans les Entrepôts',
                  fontsize=13, weight='bold')
    ax2.legend(fontsize=9, loc='best')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('stock_evolution.png', dpi=300, bbox_inches='tight')
    print("✓ Graphique sauvegardé: stock_evolution.png")
    # plt.show()


def generate_all_visualizations(m, analysis):
    """Génère toutes les visualisations"""

    print("\n" + "="*50)
    print("GÉNÉRATION DES VISUALISATIONS")
    print("="*50 + "\n")

    plot_cost_breakdown(analysis)
    plot_flux_evolution(analysis)
    plot_capacity_utilization(analysis)

    # Pour l'évolution des stocks, on a besoin du modèle
    entrepots_sample = analysis['entrepots_ouverts'][:5]
    plot_stock_evolution(m, analysis['depots_ouverts'], entrepots_sample)

    print("\n✅ Toutes les visualisations ont été générées!")

# Utilisation après résolution:
# generate_all_visualizations(model, analysis)

# =====================================================
# 7. Fonction principale
# =====================================================


def main():
    """Fonction principale avec visualisations intégrées"""

    print("="*70)
    print("    OPTIMISATION DU RÉSEAU LOGISTIQUE - SUPPLY CHAIN NETWORK")
    print("="*70)
    print(f"Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Chargement des données
    print("📁 Étape 1/5: Chargement des données...")
    data = load_and_validate_data(path="Data/")

    # Construction du modèle
    print("\n🔧 Étape 2/5: Construction du modèle...")
    m = build_model(data)

    # Résolution
    print("\n⚡ Étape 3/5: Résolution du problème MILP...")
    print("   (Ceci peut prendre plusieurs minutes...)\n")

    # solver = SolverFactory("glpk")
    solver = SolverFactory("glpk")
    results = solver.solve(m, tee=True)

    # Analyse des résultats
    print("\n📊 Étape 4/5: Analyse des résultats...")
    analysis = analyze_results(m, results)

    # NOUVEAU: Génération des visualisations
    print("\n📈 Étape 5/5: Génération des visualisations...")
    try:
        generate_all_visualizations(m, analysis)
    except Exception as e:
        print(f"⚠️ Erreur lors de la génération des graphiques: {e}")
        print("   Les résultats numériques restent disponibles.")

    # Export (optionnel)
    # export_results(m, output_path="results/")

    print(
        f"\n✅ Optimisation terminée: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return m, results, analysis

# =====================================================
# Exécution
# =====================================================



if __name__ == "__main__":
    model, results, analysis = main()
