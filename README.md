# Procedural OS Studio

Application de chat pour créer, éditer et exécuter des **agents-skills** selon
[agentskills.io](https://agentskills.io/home) / le proto procedural-OS.

Aucune dépendance Google (pas d’ADK, pas de Gemini, pas de Google Cloud).

Repo : https://github.com/Ulml/procedural-os-studio

## Ce que fait l’UI

Colonne gauche : liste d’agents. L’utilisateur peut en créer à tout moment.

À la création :

- une seule zone de **langage naturel non formaté** pour L2 (instructions) et L3 (scripts)
- un **exemple d’entrée** : prompt, fichier ou HTTP
- un **résultat final associé** : prompt, fichier ou HTTP
- l’app **compile et formate** une skill valide (`SKILL.md` + `scripts/` + `examples/`)

Sur une skill existante :

- onglet **Instruction** : édition L2 et L3
- zone de chat : les demandes du type « corrige / ajoute / change… » partent dans l’onglet **Mémoire**
- chaque item Mémoire a une **case à cocher**
- **Intégrer la sélection** reformate `SKILL.md`
- **Intégrer et commit GitHub** pousse les fichiers de la skill sur ce dépôt

## Runner agnostique

`app/engine/runner.py` :

- prend **toutes** ses procédures dans `agents/<slug>/SKILL.md` et les fichiers L3
- parle à **n’importe quel LLM** OpenAI-compatible (`LLM_BASE_URL`)
- sans LLM : mode hors-ligne (scripts + artefacts quand même)
- sandbox locale (`python` / `bash` / `node`, timeout, env filtré)
- artefacts : **md, docx, xlsx, pptx**, graphiques matplotlib, images locales
- `http_fetch` pour les exemples HTTP / APIs
- `call_mcp` vers les serveurs listés dans `MCP_SERVERS`
- cron : `agents/<slug>/cron.json` (`{"enabled": true, "cron": "0 9 * * 1-5", "goal": "..."}`)

Arborescence d’un agent (spec Agent Skills) :

```
agents/mon-agent/
  SKILL.md           # L1 frontmatter + L2 body
  scripts/           # L3 exécutable
  references/
  assets/
  examples/          # paire input / output
  cron.json          # optionnel
```

## Lancer

```bash
cd procedural-os-studio
python3 app/server.py
# http://127.0.0.1:8787
```

Option LLM local :

```bash
ollama pull llama3.1
export LLM_BASE_URL=http://127.0.0.1:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=llama3.1
```

Commit GitHub depuis l’onglet Mémoire :

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_OWNER=Ulml
export GITHUB_REPO=procedural-os-studio
export GITHUB_BRANCH=main
```

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/api/agents` | liste L1 |
| POST | `/api/agents` | compile NL → skill |
| GET | `/api/agents/{slug}` | L2 + fichiers |
| POST | `/api/agents/{slug}/instruction` | sauver L2/L3 |
| POST | `/api/agents/{slug}/chat` | run ou mémoire |
| GET | `/api/agents/{slug}/memory` | items cochables |
| POST | `/api/agents/{slug}/memory/apply` | reformate + option `push_github` |
