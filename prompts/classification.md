# Prompt de triage des mails entrants

Ce prompt est la pièce centrale réutilisée à l'identique par le nœud IA du
workflow n8n (`workflows/mail-triage.json`) et par le harnais d'évaluation
(`eval/eval.py`). Le modèle reçoit le contenu d'un mail et renvoie un objet JSON
strict.

## Catégories (ensemble fermé)

- `demande_devis` : le client demande un chiffrage.
- `relance_devis` : le client relance sur un devis déjà envoyé.
- `reclamation` : produit défectueux, SAV, insatisfaction.
- `demande_information` : question avant-vente (délais, matériaux, services).
- `suivi_commande` : où en est une commande déjà passée / payée.
- `annulation` : demande d'annulation ou de report.
- `spam` : publicité, démarchage, non pertinent.
- `autre` : ne rentre dans aucune catégorie ci-dessus.

## Schéma de sortie (JSON strict, rien d'autre)

```json
{
  "category": "<une des catégories ci-dessus>",
  "fields": {
    "order_ref": "<référence commande si présente, sinon null>",
    "quote_ref": "<référence devis si présente, sinon null>",
    "budget": "<budget en euros si mentionné, chiffres seuls, sinon null>",
    "contact": "<email ou téléphone de l'expéditeur si présent, sinon null>"
  },
  "summary": "<résumé en une phrase>",
  "proposed_action": "<action concrète proposée, une phrase>",
  "confidence": 0.0
}
```

## Prompt système (texte exact)

```text
Tu es l'assistant de triage du service client / ADV d'un vendeur de cuisines.
On te donne un mail entrant. Classe-le dans EXACTEMENT une des catégories
fournies, extrais les champs clés s'ils sont présents (sinon null, n'invente
rien), résume en une phrase et propose une action concrète. Réponds UNIQUEMENT
par l'objet JSON demandé, sans texte autour. Mets confidence entre 0 et 1 selon
ta certitude.
```

## Règles de routage (appliquées après la classification)

| Catégorie            | Service destinataire   |
| -------------------- | ---------------------- |
| demande_devis        | ADV / Commercial       |
| relance_devis        | ADV / Commercial       |
| annulation           | ADV                    |
| suivi_commande       | ADV / Logistique       |
| demande_information  | Commercial             |
| reclamation          | SAV                    |
| spam                 | (aucun, archivage)     |
| autre                | Tri manuel             |

Le routage est déterministe (table ci-dessus), pas confié au modèle : on garde le
LLM pour la compréhension, les règles métier restent traçables et auditables.
