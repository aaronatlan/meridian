# Meridian — AI Equity Analyst

Prototype fonctionnel. Zero dependance externe (Python stdlib uniquement).

## Lancer le projet

```bash
cd meridian
python3 backend/server.py
```

Ouvrir http://localhost:4000 dans le navigateur.

## Fonctionnalites

- **Analyse de transcripts** : coller du texte, importer via URL, ou uploader un fichier .txt
- **Memo d'investissement** : recommandation BUY/HOLD/SELL, these, metriques, bull/bear case, catalyseurs
- **Scoring detaille** : radar chart sur 5 axes (croissance, rentabilite, momentum, risque, qualite)
- **Dashboard** : filtres par recommandation, recherche par ticker/nom, tri par date/ticker/reco
- **Watchlist** : suivre des tickers et voir leurs dernieres analyses
- **Comparaison** : comparer 2 analyses cote a cote
- **Export** : HTML imprimable avec radar SVG et barres de tendance

## Structure

```
meridian/
├── backend/
│   └── server.py       # API Python (auth, CRUD, AI, export)
├── frontend/
│   └── index.html      # SPA React (CDN)
└── README.md
```

## Stack

- **Backend** : Python 3 (stdlib) — HTTP server, SQLite, JWT maison
- **Frontend** : React 18 via CDN, CSS custom (dark mode finance)
- **AI** : Mock service — swap vers Claude API avec une variable d'environnement
- **DB** : SQLite (cree automatiquement)

## Activer Claude API

```bash
pip install anthropic
export ANTHROPIC_API_KEY='sk-ant-...'
python3 backend/server.py
```

Le serveur detecte automatiquement la cle et passe en mode Claude.

## Port

- `4000` : API + Frontend (tout-en-un)
