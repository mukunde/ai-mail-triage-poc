"""Offline evaluation harness for the mail-triage POC.

Runs the same classification/extraction the n8n workflow performs, against the
synthetic corpus, and measures it against the ground-truth labels: category
accuracy, extraction completeness, average confidence and time per mail.

Uses Claude when ANTHROPIC_API_KEY is set; otherwise falls back to a keyword
baseline so the harness still runs with no key (Plan B, working blind). Stdlib
only (urllib + json), no dependencies.

Usage:
    python eval/eval.py            # auto: Claude if key set, else baseline
    python eval/eval.py --baseline # force the keyword baseline
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (
    "Tu es l'assistant de triage du service client / ADV d'un vendeur de cuisines. "
    "On te donne un mail entrant. Classe-le dans EXACTEMENT une de ces categories: "
    "demande_devis, relance_devis, reclamation, demande_information, suivi_commande, "
    "annulation, spam, autre. Extrais les champs cles s'ils sont presents (order_ref, "
    "quote_ref, budget, contact), sinon null, n'invente rien. Resume en une phrase et "
    "propose une action concrete. Reponds UNIQUEMENT par un objet JSON {category, "
    "fields:{order_ref,quote_ref,budget,contact}, summary, proposed_action, confidence}. "
    "confidence entre 0 et 1."
)


def classify_claude(content: str, key: str) -> dict:
    body = json.dumps(
        {
            "model": "claude-opus-4-8",
            "max_tokens": 512,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": content}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    text = data["content"][0]["text"]
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def classify_baseline(mail: dict) -> dict:
    """Deterministic keyword baseline, used when no API key is available."""
    text = f"{mail['subject']} {mail['body']}".lower()
    if any(w in text for w in ["-30%", "offre", "newsletter", "catalogue pro", "profitez"]):
        category = "spam"
    elif "relance" in text:
        category = "relance_devis"
    elif "annul" in text or "report" in text:
        category = "annulation"
    elif any(w in text for w in ["casse", "fendue", "probleme", "inacceptable", "coulisse"]):
        category = "reclamation"
    elif "devis" in text or "chiffrer" in text:
        category = "demande_devis"
    elif any(w in text for w in ["ou en est", "livraison", "commande regl"]):
        category = "suivi_commande"
    elif any(w in text for w in ["delais", "materiaux", "proposez-vous", "question"]):
        category = "demande_information"
    else:
        category = "autre"
    fields = {
        "order_ref": (re.search(r"CDE-\d+", mail["body"]) or [None])[0]
        if re.search(r"CDE-\d+", mail["body"])
        else None,
        "quote_ref": (re.search(r"devis\s*n?\s*(\d{4,})", text) or [None, None])[1]
        if re.search(r"devis\s*n?\s*(\d{4,})", text)
        else None,
        "budget": (re.search(r"(\d{4,5})\s*euros", text) or [None, None])[1]
        if re.search(r"(\d{4,5})\s*euros", text)
        else None,
        "contact": mail["from"],
    }
    return {"category": category, "fields": fields, "summary": "", "proposed_action": "", "confidence": 0.5}


def main() -> int:
    mails = json.loads((ROOT / "data" / "sample_mails.json").read_text("utf-8"))
    labels = json.loads((ROOT / "eval" / "labels.json").read_text("utf-8"))
    key = os.environ.get("ANTHROPIC_API_KEY")
    use_claude = bool(key) and "--baseline" not in sys.argv
    print(f"Engine: {'Claude (claude-opus-4-8)' if use_claude else 'keyword baseline'}\n")

    correct = 0
    field_hits = field_total = 0
    confidences: list[float] = []
    durations: list[float] = []

    for m in mails:
        content = f"Sujet: {m['subject']}\n\n{m['body']}"
        start = time.perf_counter()
        try:
            pred = classify_claude(content, key) if use_claude else classify_baseline(m)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  {m['id']}: ERROR {exc}")
            continue
        durations.append(time.perf_counter() - start)

        expected = labels[m["id"]]
        ok = pred.get("category") == expected["category"]
        correct += ok
        confidences.append(float(pred.get("confidence") or 0))

        # Extraction completeness: every labelled expected field must be found.
        for fname, fval in expected.get("fields", {}).items():
            field_total += 1
            got = str((pred.get("fields") or {}).get(fname) or "")
            if fval in got:
                field_hits += 1

        mark = "OK " if ok else "XX "
        print(f"  {mark}{m['id']}: pred={pred.get('category'):<18} exp={expected['category']}")

    n = len(mails)
    print("\n--- Results ---")
    print(f"Category accuracy   : {correct}/{n} = {correct / n:.0%}")
    if field_total:
        print(f"Extraction complete : {field_hits}/{field_total} = {field_hits / field_total:.0%}")
    if confidences:
        print(f"Avg confidence      : {sum(confidences) / len(confidences):.2f}")
    if durations:
        print(f"Avg time / mail     : {sum(durations) / len(durations) * 1000:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
