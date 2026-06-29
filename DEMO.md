# Démo end-to-end (pour la vidéo Loom)

Chaîne montrée : génération de mails -> triage (n8n) -> ingestion dans l'assistant
de qualification (sur l'hôte) -> découverte -> opportunités -> artefacts.

## Pré-requis

1. Docker Desktop lancé.
2. `.env` à la racine du POC avec `ANTHROPIC_API_KEY=...` (UTF-8, pas UTF-16).
3. La stack POC up : `docker compose up -d` (lance n8n sur :5678 et GreenMail).
4. L'assistant (sur l'hôte) lancé et **accessible depuis Docker** :
   - Backend : `uv run uvicorn app.main:app --host 0.0.0.0 --reload`
     (le `--host 0.0.0.0` est indispensable : sinon `host.docker.internal:8000`
     depuis le conteneur n8n ne joint pas l'API).
   - Frontend : `npm run dev` (pour montrer les UIs).

## Configuration n8n (une seule fois)

Compte propriétaire au premier lancement (`localhost:5678/setup`), puis créer
**2 credentials** (Credentials -> New). GreenMail a l'auth désactivée, donc
n'importe quel user/mot de passe convient ; l'important est l'hôte/port, et l'hôte
est le **nom de service `greenmail`** (réseau Docker interne), pas `localhost`.

| Credential | Type | Host | Port | SSL/TLS | User / Pass |
| ---------- | ---- | ---- | ---- | ------- | ----------- |
| GreenMail SMTP | SMTP | `greenmail` | `3025` | off | `test` / `test` |
| GreenMail IMAP | IMAP | `greenmail` | `3143` | off | `adv@schmidt.test` / `test` |

Puis **Import from File** des trois workflows de `workflows/` :

- `generate-mails.json` (assigner la credential SMTP au noeud "Envoyer vers GreenMail")
- `mail-triage-imap.json` (assigner la credential IMAP au trigger "Mails entrants (IMAP)")
- `mail-triage.json` (variante standalone, sans IMAP, pour un test rapide)

La clé Anthropic est lue via `{{ $env.ANTHROPIC_API_KEY }}` (déjà passée par le
compose), aucun credential à créer pour ça.

## Dérouler la démo

1. **Activer** le workflow "Triage + ingestion (IMAP -> Alfred)" (toggle Active) :
   le trigger IMAP se met à écouter la boîte.
2. Ouvrir "Generateur de mails de test" -> **Execute workflow** : Claude rédige 6
   mails ADV variés, envoyés dans GreenMail.
3. Au cycle de poll suivant, le triage se déclenche tout seul : il récupère les
   mails, les classe/extrait/route, puis le noeud "Ingestion vers Alfred" crée une
   session de découverte, pousse un signal par mail et lance la détection.
4. La sortie du noeud "Ingestion vers Alfred" montre `sessionId` + les
   `candidates` détectées.
5. Dans l'assistant (UI) : **Découverte** -> ouvrir la session (COMPLETED, avec ses
   opportunités) -> **Promouvoir** une candidate -> **Décision** (score, reco,
   revue humaine) -> **Portfolio** -> **Dossier de reprise** (PRD/TRD/roadmap...).

## Storyboard Loom (fil)

1. Canvas n8n, workflow Générateur : Execute, les noeuds s'allument, Claude écrit.
2. Sortie du noeud d'envoi / GreenMail : les mails partent.
3. Canvas n8n, workflow Triage : le trigger IMAP récupère, chaque mail ressort
   catégorisé / extrait / routé (sortie des noeuds bien lisible).
4. Assistant, Découverte : signaux ingérés, opportunités détectées (transition).
5. Assistant, Décision : promote -> score -> recommandation -> revue humaine.
6. Assistant, Portfolio : l'opportunité se place dans le quadrant.
7. Assistant, Dossier de reprise : génération à la demande, rendu à l'écran.

## Notes

- Réseau : à l'intérieur du réseau Docker, n8n joint GreenMail via `greenmail` ;
  il joint l'assistant (sur l'hôte) via `host.docker.internal`.
- En mode Claude réel, le triage et la génération consomment l'API (quelques
  centimes pour un lot de mails).
- Si plusieurs mails arrivent sur des cycles de poll distincts, plusieurs sessions
  de découverte peuvent être créées ; pour la démo, le lot généré est récupéré en
  une fois.
