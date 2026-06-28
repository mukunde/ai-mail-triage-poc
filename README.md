# Mail Triage POC : triage automatique des mails entrants (ADV / service client)

POC court (n8n + Claude) qui transforme un flux de mails entrants en sorties
qualifiées et routées : **catégorie, champs extraits, résumé, action proposée,
service destinataire**. Cadré comme une preuve de valeur exploitable pour un Lab
IA : objectif clair, données identifiées, résultat évaluable, doc de reprise,
décision Go / No-Go.

> Contexte : exercice de cadrage à l'aveugle (pas d'accès aux vraies données), donc
> un corpus synthétique réaliste sert de Plan B, avec une grille d'évaluation.

## Hypothèse testable

Sur un échantillon de mails entrants, un pipeline LLM peut (1) classer par
intention, (2) extraire les champs clés, (3) produire un résumé et une action
proposée, avec une précision jugée utile par un opérateur et un temps de
traitement faible par mail.

## Architecture (n8n-centré)

```text
Trigger (IMAP / Gmail en prod, Manuel en démo)
        |
Charger les mails  (Code)
        |
Classifier (Claude)  (HTTP -> API Anthropic, sortie JSON structurée)
        |
Parser + router  (Code : parse + table de routage déterministe)
        |
Sortie / route vers le service (ADV, SAV, Commercial, Archivage...)
```

- Le **workflow** est le livrable central : [`workflows/mail-triage.json`](workflows/mail-triage.json).
- Le **prompt** (classification + extraction) est documenté et réutilisé à
  l'identique par le workflow et l'éval : [`prompts/classification.md`](prompts/classification.md).
- Le **routage** est une table déterministe (règles métier traçables) ; le LLM ne
  sert qu'à la compréhension, pas à la décision de routage.

## Lancer

### Option A : exécuter le workflow n8n

```bash
# 1. clé API (jamais commitée)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
# 2. démarrer n8n
docker compose up -d            # http://localhost:5678
```

Puis dans n8n : **Import from File** -> `workflows/mail-triage.json`, ouvrir le
workflow et cliquer **Execute workflow**. Chaque mail ressort classé, extrait,
résumé et routé.

> Le workflow lit la clé via `{{ $env.ANTHROPIC_API_KEY }}`. Le `docker-compose`
> active `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` pour autoriser cet accès dans les
> expressions (sinon n8n le bloque par défaut). Vérifié en exécution réelle sur
> n8n 2.27.

### Option B : mesurer (grille d'évaluation)

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
en charge.

## Décision Go / No-Go

Go si la précision et l'accord opérateur dépassent les cibles sur un échantillon
réel, et si le routage couvre les volumes principaux. Sinon : ajuster la taxonomie
et le prompt, ou cibler d'abord une seule catégorie à fort volume.

## Périmètre

- **Inclus** : classification, extraction, résumé, action proposée, routage proposé.
- **Hors périmètre** : envoi automatique de réponses, écriture dans l'ERP,
  fine-tuning. Une revue humaine reste dans la boucle.

## Limites et prochaines étapes

- Données synthétiques (à l'aveugle) : rejouer sur un corpus réel anonymisé.
- Remplacer le trigger manuel par un vrai trigger **IMAP / Gmail**.
- Brancher la sortie sur l'outil cible (ticket, file ADV) une fois validé.
