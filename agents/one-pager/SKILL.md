---
name: one-pager
description: Quand on me donne un titre, ecris un rapport markdown d une page. Script python bienvenu.
---

# one pager

## When to use
Quand on me donne un titre, ecris un rapport markdown d une page. Script python bienvenu.

## Preconditions
- Local workspace only unless an HTTP example is provided.
- Follow the input/output pair stored in `examples/`.

## Steps
Quand on me donne un titre, ecris un rapport markdown d une page. Script python bienvenu.

## Input / output example
- Input (prompt): Rapport Q3
- Output (file): artifacts/one-pager.md

## Tools allowed
- list_skills, load_skill, run_script, write_artifact, http_fetch, call_mcp
- Generate md / docx / xlsx / pptx when the user asks for a document

## Done when
- The output matches the kind requested in the example or by the user.

## On failure
- Stop after two attempts and keep the trace.
