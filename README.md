# Mail Triage POC : triage automatique des mails entrants (ADV / service client)

POC court (n8n + Claude) qui transforme un flux de mails entrants en sorties
qualifiées et routées : **catégorie, champs extraits, résumé, action proposée,
service destinataire**. Les besoins clients extraits alimentent ensuite un
**assistant de qualification** qui en fait émerger des opportunités IA, jusqu'au
dossier de reprise. Cadré comme une preuve de valeur exploitable pour un Lab IA :
objectif clair, données identifiées, résultat évaluable, doc de reprise, décision
Go / No-Go.

> 🎥 **Démo vidéo (bout en bout)** : du workflow n8n à l'agent IA de
> qualification des cas d'usage,
> [voir la démo sur Loom](https://www.loom.com/share/f655345c29024669ac4d07ba077a6989).

> Contexte : exercice de cadrage à l'aveugle (pas d'accès aux vraies données), donc
> un corpus synthétique réaliste sert de Plan B, avec une grille d'évaluation.

## Hypothèse testable

Sur un échantillon de mails entrants, un pipeline LLM peut (1) classer par
intention, (2) extraire les champs clés, (3) produire un résumé et une action
proposée, avec une précision jugée utile par un opérateur et un temps de
traitement faible par mail.

## L'idée : valoriser les frictions, pas seulement trier

Les mails entrants expriment chaque jour des frictions réelles (demandes
répétées, réclamations, relances). Au lieu de simplement les trier, la chaîne les
**valorise** : les besoins extraits sont poussés comme signaux vers un assistant
de qualification, qui détecte des opportunités d'automatisation ou de produit IA,
les fait scorer par un humain et génère un dossier de reprise. Le tri règle le
flux ; la qualification exploite le gisement.

## Architecture

### Workflow de triage (le livrable central)

```text
Trigger (IMAP en démo, IMAP / Gmail en prod)
        |
Préparer le contenu du mail  (Code)
        |
Analyser le mail (IA)  (HTTP -> API Anthropic, sortie JSON structurée)
        |
Classer et router  (Code : parse + table de routage déterministe)
        |
Transmettre à l'assistant de qualification  (Code -> API de l'assistant)
```

- Le **prompt** (classification + extraction) est documenté et réutilisé à
  l'identique par le workflow et l'éval : [`prompts/classification.md`](prompts/classification.md).
- Le **routage** est une table déterministe (règles métier traçables) ; le LLM ne
  sert qu'à la compréhension, pas à la décision de routage.
- La **revue humaine** reste dans la boucle : l'assistant impose une validation
  humaine avant toute décision.

### Chaîne de démo complète (3 workflows)

| Workflow | Rôle |
| -------- | ---- |
| [`workflows/generate-mails.json`](workflows/generate-mails.json) | Génère un lot de mails clients réalistes (Claude) et les dépose dans une boîte de test GreenMail |
| [`workflows/mail-triage-imap.json`](workflows/mail-triage-imap.json) | Trigger IMAP : trie chaque mail reçu, extrait, route, puis pousse les signaux vers l'assistant de qualification |
| [`workflows/mail-triage.json`](workflows/mail-triage.json) | Variante autonome (exemples embarqués, sans IMAP) pour un test rapide |

```text
Générateur (Claude) --> GreenMail (SMTP/IMAP local) --> Triage (n8n + Claude)
                                                              |
                                            signaux (besoins clients extraits)
                                                              |
                        Assistant de qualification : découverte -> opportunités
                        -> score (humain) -> revue Go / No-Go -> dossier de reprise
```

Le pas-à-pas complet (credentials n8n, ordre d'exécution, storyboard de la
vidéo) est dans [`DEMO.md`](DEMO.md).

## Lancer

### Option A : démo bout en bout (n8n + GreenMail + assistant)

```bash
# 1. clé API (jamais commitée), en UTF-8
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
# 2. démarrer n8n + GreenMail
docker compose up -d            # n8n: http://localhost:5678
```

Puis suivre [`DEMO.md`](DEMO.md) : importer les workflows, créer les deux
credentials GreenMail, activer le triage, exécuter le générateur. L'assistant de
qualification tourne sur l'hôte et doit être joignable depuis Docker
(`host.docker.internal`).

### Option B : workflow autonome (sans boîte mail)

Dans n8n : **Import from File** -> `workflows/mail-triage.json`, ouvrir le
workflow et cliquer **Execute workflow**. Chaque mail d'exemple ressort classé,
extrait, résumé et routé.

> Les workflows lisent la clé via `{{ $env.ANTHROPIC_API_KEY }}`. Le
> `docker-compose` active `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` pour autoriser cet
> accès dans les expressions (sinon n8n le bloque par défaut). Vérifié en
> exécution réelle sur n8n 2.27.

### Option C : mesurer (grille d'évaluation)

```bash
python eval/eval.py             # Claude si ANTHROPIC_API_KEY est défini, sinon baseline
python eval/eval.py --baseline  # force la baseline mots-clés (sans clé)
```

L'éval compare les sorties au fichier de vérité [`eval/labels.json`](eval/labels.json)
et reporte : précision de catégorie, complétude d'extraction, confiance moyenne,
temps par mail.

## Critères de succès

| Métrique                 | Cible indicative          |
| ------------------------ | ------------------------- |
| Précision de catégorie   | >= 90 % sur le jeu étiqueté |
| Complétude d'extraction  | >= 90 % des champs attendus |
| Temps par mail           | < 3 s                     |
| Accord opérateur         | jugé utile sur un échantillon réel |

## ROI (illustratif)

`volume mensuel de mails x temps de tri manuel economise par mail`. Exemple : 3000
mails/mois x 30 s gagnees = ~25 h/mois reallouees, hors reduction du delai de prise
en charge. S'y ajoute la valeur amont : chaque friction récurrente détectée est
une opportunité d'automatisation qualifiée au lieu d'un irritant invisible.

## Décision Go / No-Go

Go si la précision et l'accord opérateur dépassent les cibles sur un échantillon
réel, et si le routage couvre les volumes principaux. Sinon : ajuster la taxonomie
et le prompt, ou cibler d'abord une seule catégorie à fort volume.

## Périmètre

- **Inclus** : classification, extraction, résumé, action proposée, routage
  proposé, transmission des signaux à l'assistant de qualification.
- **Hors périmètre** : envoi automatique de réponses, écriture dans l'ERP,
  fine-tuning. Une revue humaine reste dans la boucle.

## Stack

n8n (orchestration low-code), Claude / API Anthropic (classification, extraction,
génération du corpus), GreenMail (boîte mail de test SMTP/IMAP), Python stdlib
(harnais d'évaluation). L'assistant de qualification aval : FastAPI, LangGraph,
Next.js.

## Limites et prochaines étapes

- Données synthétiques (à l'aveugle) : rejouer sur un corpus réel anonymisé.
- Remplacer GreenMail par un vrai trigger **IMAP / Gmail** en production.
- Brancher la sortie sur l'outil cible (ticket, file ADV) une fois validé.

## Licence

[MIT](LICENSE)
