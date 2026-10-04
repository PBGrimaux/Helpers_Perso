# Simulateur immobilier CH / FR

Application Streamlit pour simuler un achat immobilier (résidence principale à Genève, locatif en France)
et le comparer au plan actuel d'investissement mensuel en bourse. Elle répond à trois questions :
**combien puis-je acheter**, **combien cela coûte vraiment**, et **que vaut la décision face au portefeuille**.

Référence métier : [`docs/Guide_immobilier_CH_FR.pdf`](docs/Guide_immobilier_CH_FR.pdf) (le chapitre 6 sert de spécification).
Plan de développement et état d'avancement : [`PLAN_APP.md`](PLAN_APP.md).

> Document de compréhension : ne constitue pas un conseil fiscal, juridique ou financier.

## Lancement

Depuis la racine du dépôt (même répertoire de travail que Streamlit Community Cloud) :
```bash
pip install -r simulateur_immobilier/requirements.txt
streamlit run simulateur_immobilier/app.py
cd simulateur_immobilier && pytest          # tests sans réseau
```

Le thème est lu depuis `.streamlit/config.toml` à côté de `app.py` (config au niveau du script, Streamlit ≥ 1.65).

## Structure

```
app.py      point d'entrée, navigation en haut de page
views/      une page par fichier (pas pages/, qui activerait le routage multipage historique)
core/       calculs purs : financement, fiscalité CH / FR, simulation, Monte-Carlo (aucun import de Streamlit)
ui/         thème, composants, formatage des nombres, état de session
config/     hypothèses par défaut et règles fiscales datées (YAML), jamais en dur dans le code
tests/      pytest : valeurs de référence du guide et tests de propriétés
docs/       guide PDF et calc.py d'origine
```

## Conventions

Alignées sur `portfolio_risk_app/` : même thème, template Plotly et composants. Interface en français ;
montants `CHF 1'200'000` et `250 000 €`, décimales à virgule (`2,3 %`).
