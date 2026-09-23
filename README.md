# Assistant RAG sur Documents Métier

Application fullstack de chatbot RAG (**Retrieval-Augmented Generation**) permettant d'indexer et d'interroger un corpus de documents métier (documentation interne, règlements, textes réglementaires, procédures) et d'obtenir des réponses précises avec citations systématiques des sources.

---

## 1. Choix techniques & Architecture

### Pipeline RAG & Découpage : LangChain
- **Choix retenu** : Approche modulaire inspirée des conventions **LangChain** (`RecursiveCharacterTextSplitter`) avec gestion hiérarchique par séparateurs sémantiques (`# Titre`, `Article`, `Chapitre`, `\n\n`, `\n`, etc.).
- **Pourquoi par rapport à LlamaIndex** :
  - **Contrôle et modularité** : Permet un découpage granulaire préservant le contexte métier (sections et pages) sans dépendance rigide à un framework boîte-noire.
  - **Compatibilité & légèreté** : Évite les conflits de dépendances et s'intègre naturellement avec SQLAlchemy et l'extension `pgvector`.
  - **Taille & overlap paramétrables** : Configuré par défaut à 800 caractères avec un overlap de 120 caractères.

### Génération & Modèles LLM : Google Gemini, OpenAI & Anthropic
- **Choix retenu** : Architecture multi-fournisseur configurable via la variable d'environnement `LLM_PROVIDER` (`gemini`, `openai` ou `anthropic`).
- **Google Gemini** : Prise en charge de `gemini-1.5-flash` (ou `gemini-2.0-flash`) avec embeddings vectoriels `models/text-embedding-004`.
- **OpenAI** : Prise en charge de `gpt-4o-mini` (ou `gpt-4o`) avec embeddings vectoriels `text-embedding-3-small` (1536 dimensions).
- **Anthropic** : Prise en charge de `claude-3-5-sonnet-20241022`.
- **Mode hors ligne / Fallback de test** : Si aucune clé API externe n'est configurée, un synthétiseur local extrait fidèlement les passages clés et applique la citation des sources, permettant des tests et démonstrations immédiats sans frais d'API.

### Stockage Vectoriel : PostgreSQL + pgvector
- Extension native `pgvector` sur PostgreSQL pour les embeddings (`vector(1536)`).
- Distance cosinus (`<=>`) pour le ranking de similarité sémantique.
- Initialisation automatique de l'extension et des tables au démarrage de FastAPI.

### Évaluation de la qualité & Audit
- Module d'évaluation calculant trois métriques transparentes pour chaque réponse :
  - **Fidélité (Faithfulness)** : Taux d'alignement des faits de la réponse avec les extraits de documents.
  - **Pertinence (Relevance)** : Alignement entre la question de l'utilisateur et la réponse produite.
  - **Utilisation du contexte (Context Usage)** : Proportion des extraits récupérés effectivement exploités.
- Journalisation structurée dans `audit.log` (horodatage, question, réponse, sources et scores).

---

## 2. Structure du Projet

```
RAG-Assisant/
├── backend/
│   ├── db/
│   │   └── pgvector_client.py    # Connexion PostgreSQL + extension pgvector + sessions
│   ├── models/
│   │   └── document.py           # Modèles SQLAlchemy (DocumentModel, ChunkModel, MessageModel)
│   ├── routers/
│   │   ├── documents_router.py   # Routes POST/GET/DELETE /api/documents
│   │   └── chat_router.py        # Routes POST /api/chat et GET /api/chat/history
│   ├── schemas/
│   │   └── chat_schema.py        # Schémas Pydantic (validation, sérialisation)
│   ├── services/
│   │   ├── ingestion_service.py  # Extraction (PDF, DOCX, TXT), chunking, embeddings
│   │   ├── retrieval_service.py  # Recherche vectorielle pgvector
│   │   ├── generation_service.py # Prompt et génération LLM (OpenAI / Anthropic)
│   │   └── evaluation_service.py # Métriques de qualité et journal d'audit
│   ├── tests/                    # Tests unitaires et d'intégration pytest
│   ├── main.py                   # Application FastAPI, CORS, gestion d'erreurs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx    # Fenêtre de chat, saisie, indicateur de chargement
│   │   │   ├── MessageBubble.tsx # Bulles messages utilisateur et assistant
│   │   │   ├── SourceCitation.tsx# Accordéon et badges des sources citées
│   │   │   └── DocumentUpload.tsx# Glisser-déposer, validation format/taille, liste docs
│   │   ├── hooks/
│   │   │   └── useChat.ts        # Hook principal (scroll auto, état, actions)
│   │   ├── services/
│   │   │   └── ChatService.ts    # Client HTTP vers l'API FastAPI
│   │   ├── types/
│   │   │   └── index.ts          # Interfaces TypeScript
│   │   ├── App.tsx               # Composant racine et mise en page
│   │   ├── App.css               # Styles modernes et responsive
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── doc/                          # Spécifications fonctionnelles et techniques
├── docs/gemini/                  # Miroir de configuration
├── docker-compose.yml            # PostgreSQL 16 + pgvector prêt à l'emploi
└── README.md
```

---

## 3. Prérequis

- **Python** : 3.10 ou supérieur (testé et compatible Python 3.14)
- **Node.js** : 18+ (avec npm)
- **Base de données** : PostgreSQL 15+ avec extension `pgvector` (ou Docker)

---

## 4. Guide d'Installation et Lancement

### Étape 1 : Démarrer PostgreSQL avec pgvector

Avec Docker (recommandé) :
```bash
docker compose up -d
```
Cela lance une instance PostgreSQL 16 avec l'extension `pgvector` préinstallée sur le port `5432` (utilisateur: `postgres`, mot de passe: `postgres`, base: `rag_assistant`).

### Étape 2 : Configurer et démarrer le Backend

1. Créer et activer l'environnement virtuel :
```bash
cd backend
python -m venv .venv

# Sous Windows (PowerShell) :
.\.venv\Scripts\Activate.ps1
# Sous Linux / macOS :
source .venv/bin/activate
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
Copiez le fichier exemple :
```bash
cp .env.example .env
```
Éditez le fichier `.env` pour y renseigner vos clés API :
```ini
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag_assistant

# Fournisseur LLM ('gemini', 'openai' ou 'anthropic')
LLM_PROVIDER=gemini

# Si Google Gemini :
GEMINI_API_KEY=votre-cle-api-gemini
GEMINI_MODEL=gemini-1.5-flash

# Si OpenAI :
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
# EMBEDDING_MODEL=text-embedding-3-small

# Si Anthropic :
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

4. Lancer le backend (commande officielle `GEMINI.md`) :
```bash
cd backend
uvicorn main:app --reload
```
Le backend sera accessible sur `http://localhost:8000`.  
La documentation Swagger interactive est disponible sur `http://localhost:8000/docs`.

---

### Étape 3 : Configurer et démarrer le Frontend

1. Installer les dépendances Node.js :
```bash
cd frontend
npm install
```

2. Lancer le frontend (commande officielle `GEMINI.md`) :
```bash
cd frontend
npm run dev
```
L'application web React est accessible sur `http://localhost:5173`.

---

## 5. Exécution des Tests

### Tests Backend (pytest)
La suite de tests couvre l'ensemble des modules backend : découpage/chunking, recherche vectorielle, génération avec mocks LLM, validation des entrées (formats non supportés, taille > 10 Mo, question vide), métriques d'évaluation et routes HTTP :
```bash
cd backend
pytest -v
```
*(Résultat : 23 tests passés avec succès)*

### Tests Frontend (Jest + React Testing Library)
La suite teste les composants UI (`ChatWindow`, `MessageBubble`, `SourceCitation`, `DocumentUpload`), le service API (`ChatService`) et le hook personnalisé (`useChat`) :
```bash
cd frontend
npm test
```
*(Résultat : 14 tests passés avec succès)*

Pour vérifier la compilation TypeScript et le build de production :
```bash
cd frontend
npm run build
```

---

## 6. Récapitulatif des Endpoints API

| Méthode | Route | Description | Validation / Statuts |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/documents` | Uploader et indexer un nouveau document | Fichier requis, PDF/DOCX/TXT, max 10 Mo -> `201` ou `400` |
| `GET` | `/api/documents` | Liste de tous les documents indexés | Ordonné par date d'upload -> `200` |
| `DELETE` | `/api/documents/{id}` | Supprimer un document et ses chunks | `200` ou `404` si non trouvé |
| `POST` | `/api/chat` | Poser une question et obtenir la réponse sourcée | Question non vide -> `200` ou `400` |
| `GET` | `/api/chat/history` | Récupérer l'historique complet des échanges | Ordonné chronologiquement -> `200` |
| `GET` | `/health` | Vérification de santé du service | -> `200` |

---

## 7. Fonctionnalités Clés Implémentées

- **Glisser-déposer de documents** avec validation instantanée (formats PDF, DOCX, TXT et limite 10 Mo).
- **Chunking hiérarchique intelligent** respectant les sections, articles et paragraphes des textes réglementaires.
- **Citations interactives des sources** : chaque réponse d'assistant détaille le nom du document, la section ou page d'origine, et un extrait déroulable.
- **Scroll automatique** vers les derniers messages grâce à `useRef`.
- **Indicateurs d'état** clairs (traitement, indexation, erreurs d'upload ou de génération).
- **Audit et métriques RAG** (fidélité, pertinence, utilisation du contexte) enregistrés automatiquement.
