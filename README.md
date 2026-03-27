# 🛢️ Petroleum Data API

API REST sécurisée pour la gestion des données pétrolières et la visualisation des résultats de puits.

**Stack :** FastAPI · PostgreSQL · SQLAlchemy · JWT · Python 3.12

---

## 📁 Structure du Projet

```
petroleum_api/
├── app/
│   ├── main.py                  # Point d'entrée FastAPI
│   ├── core/
│   │   └── config.py            # Configuration (pydantic-settings)
│   ├── database/
│   │   └── session.py           # Moteur SQLAlchemy, session, init_db
│   ├── models/
│   │   ├── user.py              # Modèle User (rôles Admin/User)
│   │   ├── well.py              # Modèle Well (puits pétrolier)
│   │   ├── petrophysical_file.py # Fichiers LAS/CSV + CurveData
│   │   ├── analysis_result.py   # Résultats d'analyse
│   │   └── audit_log.py         # Journal des actions
│   ├── schemas/
│   │   ├── user.py              # Pydantic: User, Token, Login
│   │   ├── well.py              # Pydantic: Well CRUD + filtres
│   │   ├── petrophysical.py     # Pydantic: fichiers, courbes
│   │   └── analysis.py          # Pydantic: résultats
│   ├── routes/
│   │   ├── auth.py              # POST /auth/register, /login, /refresh
│   │   ├── users.py             # GET/PATCH /users (admin)
│   │   ├── wells.py             # CRUD /wells
│   │   ├── files.py             # Upload /wells/{id}/files
│   │   ├── curves.py            # GET /wells/{id}/curves
│   │   └── results.py           # CRUD /wells/{id}/results
│   ├── services/
│   │   ├── file_processor.py    # Parsing LAS/CSV → CurveData
│   │   └── audit.py             # Logging des actions
│   └── auth/
│       └── jwt.py               # JWT: création, vérification, dépendances
├── tests/
│   └── test_api.py              # Tests d'intégration pytest
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🚀 Démarrage Rapide

### 1. Configuration
```bash
cp .env.example .env
# Éditez .env avec vos paramètres (DATABASE_URL, SECRET_KEY)
```

### 2. Avec Docker (recommandé)
```bash
docker-compose up -d
# API disponible sur http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### 3. Développement local
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Démarrer PostgreSQL, puis :
uvicorn app.main:app --reload --port 8000
```

---

## 🔑 Authentification

Toutes les routes (sauf `/health` et `/auth/register`) requièrent un token JWT.

```bash
# 1. Inscription
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user1","password":"Secret123"}'

# 2. Connexion → récupère access_token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Secret123"}'

# 3. Utilisation
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/v1/wells/
```

---

## 📡 Endpoints Principaux

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/auth/register` | Inscription |
| `POST` | `/api/v1/auth/login` | Connexion → JWT |
| `GET` | `/api/v1/auth/me` | Profil utilisateur |
| `GET` | `/api/v1/wells/` | Liste des puits (filtres, pagination) |
| `POST` | `/api/v1/wells/` | Créer un puits |
| `GET` | `/api/v1/wells/map` | Puits avec coordonnées (carte) |
| `PUT` | `/api/v1/wells/{id}` | Modifier un puits |
| `DELETE` | `/api/v1/wells/{id}` | Supprimer un puits |
| `POST` | `/api/v1/wells/{id}/files/` | Uploader LAS/CSV |
| `GET` | `/api/v1/wells/{id}/files/` | Lister les fichiers |
| `DELETE` | `/api/v1/wells/{id}/files/{fid}` | Supprimer un fichier |
| `GET` | `/api/v1/wells/{id}/curves/available` | Courbes disponibles |
| `GET` | `/api/v1/wells/{id}/curves/{curve}` | Données d'une courbe |
| `GET` | `/api/v1/wells/{id}/curves/?curves=GR,RHOB` | Multi-courbes |
| `POST` | `/api/v1/wells/{id}/results/` | Ajouter un résultat |
| `GET` | `/api/v1/wells/{id}/results/` | Lister les résultats |

---

## 📊 Modèle de Données

```
users ─────────┐
               │ owner_id
wells ─────────┴──────────────────────────┐
  │                                        │
  ├── petrophysical_files ─────── curve_data (partitionné par well_id)
  │       └── [LAS metadata + status]     └── [curve_name, depth_m, value]
  │
  └── analysis_results
          └── [porosity, Sw, permeability, result_data JSON]

audit_logs ── [toutes les actions utilisateur]
```

---

## 🧪 Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=html
```

---

## ⚙️ Variables d'Environnement Clés

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL PostgreSQL | `postgresql://...` |
| `SECRET_KEY` | Clé JWT (min 32 chars) | **À changer !** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée du token | `60` |
| `MAX_FILE_SIZE_MB` | Taille max upload | `100` |
| `UPLOAD_DIR` | Répertoire fichiers | `./uploads` |

---

## 🔒 Sécurité

- Mots de passe hashés avec **bcrypt**
- Tokens JWT avec expiration configurable
- Contrôle d'accès par **rôle** (Admin / User)
- Les utilisateurs ne voient que **leurs propres données**
- **Audit log** de toutes les actions sensibles
- Validation stricte côté serveur (Pydantic v2)
- Soft delete pour la traçabilité
