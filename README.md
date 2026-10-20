# PostePlan IA

PoC fonctionnel d’un générateur de business plans pour le Groupe La Poste.
Executive MBA Epitech P2026 — module SI et big data — projet #2 (valorisation de l’innovation).

Ce n’est **pas** un produit fini. C’est une chaîne réelle, allégée :

saisie ou sélection d’un projet → lecture / écriture MySQL → score de pertinence 0–100 → génération d’un business plan, de scénarios et d’une note Codir → export texte.

## Mise en ligne (Render — gratuit)

1. Poussez le dossier `bp-laposte` sur un dépôt GitHub (public ou privé).
2. Sur [render.com](https://render.com) : New → Blueprint → connectez le dépôt. Le fichier `render.yaml` crée le service web gratuit.
3. Dans Environment, ajoutez `XAI_API_KEY` (votre clé xAI). Ne la mettez pas dans le dépôt.
4. Une fois déployé, l’URL est `https://posteplan-ia.onrender.com` (ou le nom que vous choisissez).

Le plan free s’endort après 15 minutes d’inactivité (premier chargement ~30 s). La base SQLite est recréée à chaque redémarrage : les 8 projets d’exemple reviennent, les imports Excel et versions ne persistent pas. Pour une base persistante, un disque Render (payant) ou un MySQL externe est nécessaire — à valider avant.

```bash
cd bp-laposte
chmod +x start.sh
./start.sh
```

Puis ouvrir [http://127.0.0.1:8080](http://127.0.0.1:8080).

Dépendances : Python 3.10+, Flask, PyMySQL. MariaDB / MySQL si disponible ; sinon la base bascule automatiquement sur SQLite (`data/laposte_bp.sqlite`) avec le même schéma.

Si le portefeuille est vide, supprimez le fichier `data/laposte_bp.sqlite` et relancez l’application : les 8 projets d’exemple seront recréés automatiquement.

Pour brancher un LLM (Grok ou Claude). En `auto`, Grok est pris s’il y a une clé xAI, sinon Claude :

```bash
# Grok (xAI)
export XAI_API_KEY=xai-…
export XAI_MODEL=grok-4.6          # optionnel
export LLM_PROVIDER=grok           # ou auto

# Claude (Anthropic) — alternative
export ANTHROPIC_API_KEY=sk-ant-…
export ANTHROPIC_MODEL=claude-sonnet-4-6
export LLM_PROVIDER=claude

./start.sh
```

Sans clé, le moteur de repli assemble des livrables structurés **uniquement** à partir des données MySQL. Aucun montant n’est inventé. Les prompts métier sont les mêmes pour les deux moteurs (`prompts/prompts_metier.md`).

## Ce qui est démontrable

| Flux | Endpoint |
|---|---|
| Santé + moteur | `GET /api/health` |
| Portefeuille | `GET /api/projets` |
| Dossier complet (score, finances, risques) | `GET /api/projets/<id>` |
| Création réelle en base | `POST /api/projets` |
| Recalcul du score | `GET /api/projets/<id>/score` |
| Génération unitaire | `POST /api/projets/<id>/generer` `{"type":"analyse\|business_plan\|scenarios\|note_codir"}` |
| Enchaînement de démo | `POST /api/projets/<id>/dossier` |
| Dialogue d’ajustement | `POST /api/projets/<id>/chat` |
| Export note Codir | `GET /api/projets/<id>/export.txt` |

## Base MySQL

8 tables : `porteurs`, `projets`, `hypotheses_financieres`, `parametres_strategiques`, `risques`, `opportunites`, `scenarios`, `generations`.

8 projets fictifs mais ancrés La Poste :

1. Mobilité interne augmentée (RH)
2. Facteo Assist (digital / Courrier)
3. OptiLast last-mile (logistique)
4. Appli Unique Client 2.0 (Numérique)
5. Maison de services France Poste (territorial)
6. Flotte douce 2030 (RSE)
7. SereniPoste seniors (Banque / innovation)
8. InnovLab valorisation des PoC (innovation)

Jeu associé : 24 lignes d’hypothèses financières (3 ans × 8), 24 scénarios, catalogue de 10 risques types + 10 risques projet, opportunités, 8 porteurs.

Schéma : `sql/schema.sql`. Données : `sql/seed.sql`.

## Score de pertinence

Six dimensions obligatoires du cahier des charges.

| Dimension | Poids | Sens |
|---|---|---|
| Rentabilité | 25 % | ROI, délai de retour, CA an 3 / investissement |
| Alignement stratégique | 20 % | Priorité Groupe + impact branches |
| Maîtrise des risques | 15 % | Inverse des risques technique / humain / réglementaire |
| Impact opérationnel | 15 % | Impact branches − complexité |
| Impact social / environnemental | 15 % | Mission + RSE |
| Faisabilité technique | 10 % | Maturité technique + maturité porteur − complexité |

Seuils d’aide à la décision : ≥ 75 GO prioritaire · 60–74 GO sous conditions · 45–59 réviser · < 45 NO-GO ou report.

Implémentation : `scoring.py`. Le score est explicable (chaque barre de l’interface montre la note et le poids).

## Prompts

Voir `prompts/prompts_metier.md`.

Cinq prompts métier + un prompt de dialogue. Le score n’est pas saisi : l’IA note les dimensions qualitatives, le moteur pondère le 0–100. Contrat commun : JSON strict, interdiction d’inférer un chiffre financier absent, style Codir.

Chaque modification (utilisateur ou IA) crée un snapshot dans la table `versions`. Dans le dossier, le panneau **Historique des versions** permet de restaurer n’importe quelle version antérieure. Les générations IA (BP, note, etc.) restent historisées dans `generations`.

Import Excel : bouton sur le portefeuille. Téléchargez le modèle (`/api/import/modele.xlsx`), remplissez les colonnes, puis importez. Les codes déjà présents sont ignorés.

Graphiques : jauge circulaire pour le score (cartes et en-tête), barres colorées pour les 6 dimensions, mini-histogrammes pour les finances et les scénarios.

## Périmètre volontairement hors scope

Visualisations radar avancées, import Excel, multi-tenant, authentification SSO, hébergement production. Ces items étaient optionnels dans le brief.

## Soutenance — fil de démo recommandé (8 minutes)

1. Saisir un projet (informations clés seulement — aucune note).
2. L’IA évalue les dimensions ; l’outil affiche le score 0–100.
3. « Lancer le parcours Codir » : BP, scénarios, note.
4. Télécharger la synthèse `.txt`.
5. Comparer deux dossiers du portefeuille (ex. OptiLast vs InnovLab).
6. Dialogue d’ajustement, puis recalcul du score IA.

## Architecture

```
Frontend HTML/CSS/JS  →  Flask (app.py)
                           ├─ scoring.py
                           ├─ ai_service.py  (Claude ou fallback)
                           └─ db.py          (MariaDB, repli SQLite)
```
