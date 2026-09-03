---
name: brief-writer
description: Rédige un brief structuré puis un fichier Markdown ou Word. À utiliser pour un résumé, un compte-rendu ou une note d'une page.
---

# Brief writer

## When to use
Quand l'utilisateur veut un brief, une note, un compte-rendu ou un document court.

## Preconditions
- Travailler dans le workspace local.
- Pas de réseau obligatoire.

## Steps
1. Lire l'objectif utilisateur.
2. Structurer titre, contexte, points clés, prochaine action.
3. Appeler write_artifact kind=md (et docx si demandé).
4. Ajouter un graphique seulement si des chiffres sont fournis.

## Tools allowed
- write_artifact (md, docx, pptx, chart)
- run_script on scripts/outline.py

## Done when
- Un fichier est produit dans artifacts/ et le chemin est renvoyé.

## On failure
- Renvoyer le plan en texte brut.
