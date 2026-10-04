# Simulateur immobilier CH / FR : plan de développement

Application Streamlit pour simuler un achat immobilier (résidence principale en Suisse, locatif en France) et le comparer à la stratégie actuelle d'investissement mensuel en bourse.
Document de référence métier : `docs/Guide_immobilier_CH_FR.pdf` (chapitre 6 = spécification).

Mode de travail : une phase à la fois, validation avant de passer à la suivante, corrections appliquées globalement.

---

## 1. Objectifs

L'app répond, pour des paramètres saisis, à trois questions :

1. **Combien puis-je acheter ?** Prix maximal, contrainte active (apport dur, apport total, revenu), cash nécessaire, part LPP mobilisable.
2. **Combien cela coûte vraiment ?** Coût d'usage, flux mensuels et annuels, impôts des deux pays, TRI des fonds propres.
3. **Que vaut la décision face au portefeuille ?** Trajectoires de patrimoine acheteur vs locataire investisseur, point mort, cartes de sensibilité, Monte-Carlo.

Hors périmètre v1 : biens commerciaux, SCI, location courte durée, autres cantons que Genève (prévoir l'extension via config).

---

## 2. Layout et conventions : à aligner sur `Helpers_Perso`

Référence : `portfolio_risk_app/`, seule app Streamlit du dépôt en octobre 2026. Relevé fait en phase 0 :

- [x] **Point d'entrée** : `app.py` avec `st.navigation(pages, position="top")` (navigation en haut, pas de sidebar de pages). Les pages vivent dans `views/`, **pas** `pages/` : ce nom réactiverait le routage multipage historique de Streamlit. `app.py` purge les modules `core/` / `ui/` périmés après un nouveau commit (empreinte des sources + `st.cache_data.clear()`).
- [x] **`.streamlit/config.toml`** au niveau du script (Streamlit ≥ 1.65), dans le dossier de l'app : thème clair façon Apple, accent `#0071E3`, fond secondaire `#F5F5F7`, police Inter, boutons arrondis, palette catégorielle `#2a78d6, #eb6834, #1baf7a, #eda100…`, barre d'outils minimale. Copié à l'identique.
- [x] **Sidebar** : non utilisée pour la navigation. Les inputs sont dans le corps de page (colonnes, expanders, tableaux éditables). On garde ce principe ; les pages de simulation pourront mettre leurs inputs dans `st.sidebar` si le volume le justifie, à trancher en phase 1.
- [x] **Composants partagés** (`ui/`) : `theme.py` (CSS injecté, template Plotly), `components.py` (`page_header` titre + sous-titre, `section` libellé en capitales, `note`, `kpi_row` tuiles `st.metric` sur fond gris arrondi, bouton de téléchargement), `state.py` (schéma de `session_state` avec fabriques par défaut), `cache.py` (wrappers `st.cache_data` autour de `core/`). Ajout ici : `fmt.py`, formatage des nombres sans Streamlit.
- [x] **Graphiques** : Plotly uniquement, template `apple_neutral` défini dans `ui/theme.py`, `displayModeBar: False`, un axe Y par panneau (pas de double axe), couleurs fixes par rôle. Ici : acheteur = bleu, locataire investisseur = orange, bailleur France = vert, neutre = gris.
- [x] **État et cache** : `ui/state.py` initialise `st.session_state` à partir d'un dict `DEFAULTS` ; calculs lourds mis en cache dans `ui/cache.py` (Monte-Carlo en phase 5).
- [x] **Dépendances** : `requirements.txt` propre à l'app (pas de `pyproject`, pas de venv commité), Python 3.12 sur Streamlit Community Cloud. Rien à la racine du dépôt : chaque app est autonome dans son dossier.
- [x] **Style de code** : `from __future__ import annotations`, annotations de types, docstring de module en tête de chaque fichier, commentaires sobres ; tests `pytest` dans `tests/` (`pytest.ini` avec `pythonpath = .`), données synthétiques, pas de réseau. Pas de formatter ni de linter configuré.
- [x] **Langue et nombres** : l'app existante est en anglais. Celle-ci est **en français** (vocabulaire métier : EPL, LMNP, IBGI…). Montants : `CHF 1'200'000` et `250 000 €` (espace fine insécable) ; décimales à virgule comme dans le guide : `2,3 %`, `0,1767` ; graphiques Plotly avec `separators=",'"`.

Conventions retenues : celles ci-dessus. Écarts par rapport au plan initial : dossier `simulateur_immobilier/` (minuscules, comme `portfolio_risk_app/`), pages dans `views/` au lieu de `pages/`, ajout d'une page d'accueil.

---

## 3. Arborescence cible

```
Helpers_Perso/
└── simulateur_immobilier/
    ├── PLAN_APP.md                  # ce document
    ├── README.md                    # lancement, structure, conventions
    ├── app.py                       # point d'entrée, navigation en haut (st.navigation)
    ├── requirements.txt · pytest.ini · .streamlit/config.toml
    ├── views/                       # une page par fichier (pas pages/)
    │   ├── accueil.py
    │   ├── capacite_ch.py
    │   ├── louer_vs_acheter_ch.py
    │   ├── locatif_fr.py
    │   ├── arbitrage.py
    │   └── monte_carlo.py
    ├── core/                        # aucun import streamlit ici
    │   ├── params.py                # dataclasses de paramètres
    │   ├── finance.py               # annuités, TRI, actualisation
    │   ├── financing_ch.py          # fonds propres, EPL, tenue des charges, rangs
    │   ├── financing_fr.py          # prêt, assurance, garantie, HCSF
    │   ├── tax_ch.py                # valeur locative, réforme 2029, fortune, IBGI
    │   ├── tax_fr.py                # micro/réel, LMNP, non-résident, plus-values
    │   ├── cross_border.py          # progressivité CH, répartition des dettes, FX
    │   ├── simulate.py              # moteur mensuel acheteur / locataire / bailleur
    │   └── montecarlo.py
    ├── ui/                          # theme, components, fmt, state (+ charts, cache à venir)
    ├── config/
    │   ├── defaults.yaml            # hypothèses par défaut (celles du guide)
    │   ├── rules_ch_2026.yaml       # règles datées : ASB, IBGI GE, Casatax, réforme 2029
    │   └── rules_fr_2026.yaml       # DMTO, micro-BIC, taux minimum, abattements PV
    ├── tests/
    │   ├── test_skeleton.py         # formatage, core/ sans Streamlit
    │   ├── test_golden.py           # valeurs de référence du guide
    │   └── test_properties.py
    └── docs/
        ├── Guide_immobilier_CH_FR.pdf
        └── calc.py                  # code d'origine du guide, référence à refactorer dans core/
```

Principe : `core/` est du Python pur, testable sans Streamlit. Les règles fiscales datées vivent dans `config/`, jamais en dur dans le code.

---

## 4. Modèle de calcul

Notation et équations : chapitre 6 du guide. Rappel des briques :

- **Capacité CH** : P<sub>max</sub> = min( E<sub>total</sub> / (0,20 + f), E<sub>dur</sub> / (0,10 + f), Y / k ), avec k = 3 · (i<sup>th</sup> · 0,8 + m<sup>th</sup> + 0,1333 / 15)
- **Dette** : D<sub>t+1</sub> = D<sub>t</sub> (1 + i<sub>t</sub>/12) − PMT<sub>t</sub>, tranches à taux fixe et SARON
- **Valeur** : V<sub>t+1</sub> = V<sub>t</sub> (1 + g)<sup>1/12</sup>
- **Portefeuilles** : W<sup>k</sup><sub>t+1</sub> = W<sup>k</sup><sub>t</sub> (1 + r)<sup>1/12</sup> + S<sub>t</sub>/12 + CF<sup>k</sup><sub>t</sub> − min<sub>j</sub> CF<sup>j</sup><sub>t</sub>, k ∈ {B, R}
- **Sortie** : NW<sup>B</sup><sub>H</sub> = W<sup>B</sup><sub>H</sub> + x<sub>H</sub> · [ V<sub>H</sub>(1 − c<sub>s</sub>) − D<sub>H</sub> − T<sup>PV</sup> − EPL ]
- **Progressivité CH** : ΔT<sub>CH</sub> ≈ R<sup>CH</sup> · [ t<sub>marg</sub>(Y) − t<sub>moy</sub>(Y) ]
- **Coût d'usage** : UC = i · D + r · E + m · V + T + F − E[g] · V

Point de départ du code : `docs/calc.py`, utilisé pour produire le guide, à refactorer dans `core/`.

---

## 5. Pages de l'application

| Page | Inputs principaux | Sorties |
|---|---|---|
| Capacité d'achat CH | revenu, apport dur, 3a, LPP, mode EPL, frais, taux théoriques | P<sub>max</sub>, contrainte active, cash requis, structure 1er / 2e rang, charges théoriques |
| Louer vs acheter CH | prix, loyer équivalent, taux, g, r, entretien, fiscalité, horizon | coût d'usage annuel, trajectoires NW<sup>B</sup> / NW<sup>R</sup>, point mort, heatmap (g, r) |
| Locatif France | prix, notaire, loyer, vacance, charges, prêt, régime (nu, LMNP micro / réel) | flux annuels, impôt FR, effet CH, PV à la revente, TRI en EUR et en CHF |
| Arbitrage portefeuille | combinaison des scénarios, allocation actuelle | patrimoine total, concentration, liquidité restante, comparaison au plan bourse |
| Monte-Carlo | lois et corrélations de g, r, i, x | distribution de l'écart de patrimoine, P(achat gagnant), quantiles |

Chaque page : inputs dans le corps de page (convention Helpers_Perso), KPI en tête, graphiques, tableau détaillé téléchargeable (CSV).

---

## 6. Phases

### Phase 0 : cadrage et squelette ✅ (4 octobre 2026, en attente de validation)
- Lire les apps de `Helpers_Perso`, compléter la section 2
- Créer l'arborescence, `README.md`, dépendances, config Streamlit identique aux autres apps
- **Validation** : l'app se lance, page d'accueil vide au bon layout

### Phase 1 : capacité d'achat CH
- `params.py`, `finance.py`, `financing_ch.py`, page 1
- **Validation** (`test_golden.py`), avec P = 1'200'000, f = 5 % :
  cash total 300'000 ; dur min 180'000 ; dette 960'000 ; 2e rang 160'000 ; amortissement 10'667 / an ; charges théoriques 70'667 ; revenu min 212'000 ; k = 0,1767

### Phase 2 : louer vs acheter CH
- `tax_ch.py` (régime jusqu'en 2028 puis réforme 2029, configurable), `simulate.py`, page 2
- **Validation** : coût d'usage année 1 ≈ 31'621 ; point mort ≈ 6 ans ; heatmap à 15 ans identique à la figure 3 du guide (± arrondis)
- Test de propriété : sans frais ni impôt, g = r = i et loyer = coût d'usage ⇒ NW<sup>B</sup> = NW<sup>R</sup>

### Phase 3 : locatif France
- `financing_fr.py`, `tax_fr.py`, page 3
- **Validation** (bien à 250'000 €, hypothèses du guide) : apport 78'000 € ; cash-flow an 1 micro-BIC −8'739 €, réel −7'676 € ; TRI 15 ans micro 2,3 %, réel 2,9 % ; impôt PV réel 6'319 €

### Phase 4 : interactions FR / CH et change
- `cross_border.py` : progressivité, répartition proportionnelle des dettes, conversion EUR/CHF
- TRI en CHF, scénarios de change
- **Validation** : cas simples calculés à la main

### Phase 5 : arbitrage et Monte-Carlo
- Pages 4 et 5, `montecarlo.py` (log-normale pour les prix, Vasicek pour les taux, corrélations paramétrables, seed fixe)
- **Validation** : convergence de la moyenne vers le scénario déterministe quand les volatilités tendent vers 0

### Phase 6 : finitions
- Export d'un rapport PDF (ReportLab, même charte que le guide)
- Sauvegarde / chargement de scénarios (YAML ou JSON)

---

## 7. Points ouverts

- Montants exacts de la déduction primo-acquéreur après 2029 (fédéral et Genève) : paramètre à renseigner
- Traitement d'un bien loué à l'étranger dans la règle de déduction proportionnelle des intérêts (2029)
- Revenu net du bien français retenu par Genève pour le taux (règles suisses, sans amortissement)
- Barèmes ICC / IFD : barème simplifié (taux marginal et moyen en input) en v1, barème complet plus tard ?
- Taux micro-foncier 2026 (30 % retenu) à confirmer

---

## 8. Démarrage dans Claude Code

Depuis `Helpers_Perso/simulateur_immobilier/` :

```
Lis PLAN_APP.md et le guide dans docs/. Commence la phase 0 :
inspecte deux ou trois apps Streamlit de Helpers_Perso, complète la section 2
avec leurs conventions, puis crée le squelette. Arrête-toi pour validation
avant la phase 1.
```
