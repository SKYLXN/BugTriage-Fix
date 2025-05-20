# BugTriage-Fix

Mémoire: Faire mieux avec moins : Workflows hybrides Humain–IA pour optimiser la documentation et la gestion des bugs dans le développement logiciel.

## Description

BugTriage-Fix utilise GPT-4.1 mini pour analyser les rapports de bugs GitHub et générer des propositions de correctifs. Le système répond automatiquement aux nouvelles issues GitHub, fournit un diagnostic et, lorsque c'est possible, crée une pull request avec un correctif.

## Prérequis

- Python 3.8+
- Un compte Azure OpenAI (ou une clé d'API OpenAI)
- Un compte GitHub et un repository pour les tests
- ngrok (optionnel, pour exposer le webhook à Internet)

## Installation

1. Clonez ce repository:

   ```bash
   git clone https://github.com/votre-username/BugTriage-Fix.git
   cd BugTriage-Fix
   ```

2. Copiez `.env.example` en `.env` et renseignez vos secrets:

   ```bash
   cp .env.example .env
   ```

3. Créez un environnement virtuel et activez-le:

   ```bash
   python -m venv .venv

   # Sur Windows
   .venv\Scripts\activate

   # Sur Linux/MacOS
   source .venv/bin/activate
   ```

4. Installez les dépendances:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Modifiez le fichier `.env` avec vos propres valeurs:

- `ENDPOINT_URL`: URL de votre endpoint Azure OpenAI
- `DEPLOYMENT_NAME`: Nom de votre déploiement de modèle
- `AZURE_OPENAI_API_KEY`: Votre clé API Azure OpenAI
- `GITHUB_WEBHOOK_SECRET`: Secret pour valider les webhooks GitHub
- `GITHUB_TOKEN`: Token d'accès GitHub avec les permissions nécessaires pour créer des PR et commenter les issues

## Utilisation

1. Lancez l'application:

   ```bash
   python -m src.main
   ```

2. L'API sera accessible à `http://localhost:8000`

3. Configuration du webhook GitHub:

   - Allez dans votre repository GitHub > Settings > Webhooks > Add webhook
   - Payload URL: Votre URL (ex: `https://votre-domaine.com/webhooks/github` ou une URL ngrok)
   - Content type: `application/json`
   - Secret: La même valeur que votre `GITHUB_WEBHOOK_SECRET`
   - Sélectionnez "Let me select individual events" > Issues
   - Cochez "Active" et cliquez sur "Add webhook"

4. Pour tester le webhook:

   - Créez une nouvelle issue dans votre repository
   - BugTriage-Fix analysera automatiquement l'issue
   - Si un correctif est possible, il créera une PR et commentera l'issue avec le lien
   - Sinon, il fournira un diagnostic dans un commentaire