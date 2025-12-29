import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pyomo.environ import value

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
    plt.show()


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
    plt.show()


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
    plt.show()


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
    plt.show()


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
