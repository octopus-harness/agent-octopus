# 🐙 Agent Octopus

> **Stop copy-pasting prompts. Build a 10x throughput personal AI operating system.**

Agent Octopus is a forkable, extensible multi-agent CLI framework built on **[Pydantic AI](https://github.com/pydantic/pydantic-ai)**, the **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)**, and the **`octo-com` (`com`)** command framework.

It is designed to solve a fundamental problem in LLM productivity: **prompt rot and context explosion**. Instead of keeping massive prompts in sticky notes or dumping 15+ MCP servers with hundreds of tool schemas into a single bloated LLM context window, Agent Octopus divides workflows into **deterministic, versioned runbooks** organized by **category**, executing them through **isolated specialist agents** that boot only the exact MCP servers they need on demand.

```
+------------------------------------------------------------------------------------------------------+
|                                          OCTO INTERACTIVE CLI                                        |
|  - Renders category-grouped command tables                                                           |
|  - Tab / $ popup completion with category badges & arg previews                                      |
|  - Shortcut execution by index ("4 Zeus") or direct name ("$$god_find Zeus")                         |
+------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+------------------------------------------------------------------------------------------------------+
|                                     ORCHESTRATOR AGENT (Pydantic AI)                                 |
|  1. Parses user intent & category routing                                                            |
|  2. Fetches interpolated runbook via `com get <cmd>`                                                 |
|  3. Injects recent cross-specialist shared ledger                                                    |
|  4. Hands off execution via `delegate_to_specialist`                                                 |
+------------------------------------------------------------------------------------------------------+
                                                   |
         +-----------------------------------------+-----------------------------------------+
         |                                         |                                         |
         v                                         v                                         v
+-----------------------+               +-----------------------+               +-----------------------+
|    RESEARCH & NOTES   |               | CONTENT & PRODUCTIVITY|               |       LEADS CRM       |
|       Specialist      |               |       Specialist      |               |       Specialist      |
|  (noteking, memorable)|               |    (doer, devbook)    |               |      (ninja-crm)      |
+-----------------------+               +-----------------------+               +-----------------------+
         |                                         |                                         |
         v                                         v                                         v
+-----------------------+               +-----------------------+               +-----------------------+
|  NoteKing & Memorable |               |    Doer & Devbook     |               |    Ninja CRM Tools    |
|      MCP Servers      |               |      MCP Servers      |               |      MCP Server       |
+-----------------------+               +-----------------------+               +-----------------------+
```

---

## ⚡ Core Philosophy: Why 10x Throughput?

1. **Deterministic Runbooks over Copy-Pasted Prompts**: Workflows are defined in version-controlled Markdown files managed by `com` (`octo-com`). Steps are explicit, reliable, and testable.
2. **Variable Interpolation**: IDs, project keys, and template hashes live in `~/.config/octo-com/vars.yml` (e.g. `{{content_ideas_list_id}}`, `{{research_project_id}}`), preventing manual ID lookups.
3. **Category-to-Specialist Isolation**: Tools are strictly sandboxed. The `research_notes` specialist only sees `noteking` and `memorable` tools; the `leads_crm` specialist only connects to `ninja-crm`. This prevents hallucinated tool calls and keeps token counts lean.
4. **On-Demand MCP Lifecycles**: MCP server processes are booted via `AsyncExitStack` only during specialist execution and cleaned up immediately when the task finishes.
5. **Cross-Specialist Shared Ledger**: Specialists can build on work produced by prior turns in the same session without polluting subsequent agent contexts (e.g. `$$leads_get` -> `$$leads_in_progress` -> `$$leads_merge`).
6. **Interactive Human-in-the-Loop Prompts**: Specialists can pause mid-runbook and invoke `ask_user_interactive` (`question` tool) with Rich-formatted tables for confirmation or user input before executing mutations.

---

## 🛠️ The `octo-com` (`com`) Framework Integration

`agent-octopus` integrates natively with the `com` command runner.

### How `com` Works
`com` stores Markdown runbooks inside a commands directory (configured via `com config set-dir` or `$OCTO_COMMANDS_DIR`). Each `.md` command begins with a strict 4-line header:

```markdown
Usage: $$content_prompt
Args: -
Description: Pull todos from `content-ideas`, pick one, and draft an article prompt.
Category: content

Tool use is allowed for this command.

1. Use `doer` MCP to locate the todo list with id {{content_ideas_list_id}} and fetch its current todo items.
2. Present the fetched items as a numbered list and ask the user which single item to work on. Use the `question` tool if available.
3. Once the user selects an item, produce a ready-to-use **article prompt** for that idea (Title + 3 to 6 section outline).
4. Retrieve the prompt template from Devbook MCP (id {{article_generation_prompt_template_id}}), replace `{article title}` and `{article bullet points}`. DO NOT MODIFY THE PROMPT IN DEVBOOK MCP. Return the merged content.
```

### Essential `com` CLI Commands

| Command | Purpose |
|---|---|
| `com` / `com tui` | Launch the interactive Ratatui terminal studio for browsing and testing commands |
| `com list [--category <cat>]` | List registered commands with category, arguments, and descriptions |
| `com get <name> [--raw]` | Print interpolated markdown runbook (`--raw` displays raw `{{variable}}` templates) |
| `com add <name> --category <cat>` | Create a new `.md` runbook with the required 4-line header |
| `com edit <name>` | Open the command definition in your default `$EDITOR` |
| `com rm <name>` | Remove a command definition |
| `com vars [show\|edit]` | View or edit global template variables stored in `~/.config/octo-com/vars.yml` |
| `com config [show\|set-dir]` | Display active directory or configure persistent command root |

---

## 🤖 Built-in Specialists, Categories & MCP Ecosystem

Agent Octopus comes pre-configured with **12 Specialists** handling **15 distinct MCP servers** configured in `mcp_config.json`:

| Specialist Agent | Category | Default Commands | MCP Servers Glued | Primary Capabilities |
|---|---|---|---|---|
| **`research_notes`** | `research`, `general` | `$$add_research`, `$$readable_summary`, `$$god_save_research` | `noteking`, `memorable` | Summarizes research in the user's voice, queries architectural guidelines and vector memories in Memorable, manages Markdown notes and projects in NoteKing. |
| **`content_productivity`** | `content` | `$$content_prompt` | `doer`, `devbook` | Manages developer checklist backlogs in Doer, selects content ideas, retrieves prompt templates with `{{variable}}` substitution from Devbook, merges outputs. |
| **`leads_crm`** | `crm` | `$$leads_get`, `$$leads_in_progress`, `$$leads_merge` | `ninja-crm` | Full-cycle sales execution: queries coaching/recruiting leads, advances lead statuses, drafts outreach, and merges leads against outreach templates in Ninja CRM. |
| **`mythology_knowledge`** | `mythology` | `$$god_find`, `$$god_save_research` | `syncretica`, `wikidata` | Cross-cultural deity lookups and 1024-dim `pgvector` manifold queries in Syncretica; local Wikidata Truthy knowledge grounding and entity disambiguation via QLever. |
| **`astronomer`** | `science` | Domain requests | `astronomer` | Computational research platform for comparative astrophysics, cosmic structures, star systems, celestial body manifolds, and pgvector clustering. |
| **`biologist`** | `science` | Domain requests | `biologist` | Computational research platform for comparative biology, ecology, organismal taxonomy, biomes, species manifolds, and evolutionary convergence inquiries. |
| **`chemist`** | `science` | Domain requests | `chemist` | Computational research platform for comparative chemistry, molecular structures, functional group manifolds, and synthesis report generation. |
| **`physicist`** | `science` | Domain requests | `physicist` | Computational research platform for comparative particle physics, subatomic particles, quantum state manifolds, and quantum cluster synthesis monographs. |
| **`statesman`** | `governance` | Domain requests | `statesman` | Computational research platform for comparative geopolitics, statecraft, urban power centers, cross-continental catalogs, and pgvector cosine distance manifolds. |
| **`book_rhino`** | `creative` | Domain requests | `book-rhino` | AI-assisted novel architecture, worldbuilding, character taxonomies, Sidekiq asynchronous AI generation pipelines, and compiled Markdown manuscript generation. |
| **`macronx`** | `osint` | Domain requests | `macronx` | Personal Open-Source Intelligence (OSINT) intake and analysis pipeline: raw signal ingestion, multimodal attachments (IMINT/audio), inbox triage, and Executive Intelligence Briefs (EIB). |
| **`evox`** | `music` | Domain requests | `evox` | Structured Song AST compiler and PDF songbook generation engine with aligned chords, multi-column lyrics, and automated Table of Contents. |

---

## 🏗️ How to Fork & Customize Your Machine

Customizing Agent Octopus to orchestrate your own workflows follows a clear 3-pillar pattern:

### Step 1: Author a `com` Runbook & Assign a Category
Create a new command using the `com` CLI:

```bash
com add github_triage --category dev --args "[repo]" --desc "Triage open issues and draft replies"
```

Edit the generated command file (or use `com edit github_triage`):

```markdown
Usage: $$github_triage `[repo]`
Args: `[repo]`
Description: Triage open issues and draft replies
Category: dev

Tool use is allowed for this command.

1. Fetch open issues from repository `{{default_repo}}` using the github MCP server.
2. Filter for issues labeled "needs-triage".
3. Use the `question` tool to ask which issue to address.
4. Draft a response following guidelines from memorable memory id {{dev_guidelines_id}}.
```

Add your variables to `~/.config/octo-com/vars.yml` via `com vars edit`:
```yaml
default_repo: "my-org/my-project"
dev_guidelines_id: 12
```

### Step 2: Register Your MCP Server in `mcp_config.json`
Add your server's transport definition in `mcp_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

### Step 3: Wire the Specialist & Category Routing
1. **Define the specialist identifier** in `src/agent_octopus/models.py`:
   ```python
   SpecialistName = Literal[
       "research_notes",
       "content_productivity",
       "leads_crm",
       "dev_triage",  # <-- Your new specialist
       # ...
   ]
   ```

2. **Create the specialist module** in `src/agent_octopus/specialists/<name>.py`:
   ```python
   from agent_octopus.specialists.base import SpecialistDefinition

   SPECIALIST = SpecialistDefinition(
       name="dev_triage",
       description="Specialist in repository triage and issue drafting.",
       mcp_servers=["github", "memorable"],
       system_prompt=(
           "You are the Dev Triage Specialist Agent. Follow the $$github_triage runbook strictly. "
           "Use the `question` tool when selecting issues or requesting clarification."
       ),
   )
   ```

3. **Register the specialist** in `src/agent_octopus/specialists/__init__.py`:
   ```python
   from .dev_triage import SPECIALIST as dev_triage_specialist
   # Add to SPECIALISTS dict
   ```

3. **Update orchestrator routing** in `src/agent_octopus/orchestrator.py`:
   Add your command-to-specialist mapping in `ORCHESTRATOR_SYSTEM_PROMPT`:
   ```text
   * $$github_triage -> dev_triage
   ```

Now run `octo`: your new category `DEV` will render with unified styling, `$$github_triage` will autocomplete with badges, and selecting it boots only `github` and `memorable`!

---

## 🚀 Quickstart

### Prerequisites
- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (recommended Python package manager)
- [Node.js](https://nodejs.org/) (required to run stdio MCP servers)
- `com` binary installed and available on your `$PATH`
- An OpenAI-compatible LLM endpoint (e.g. Ollama, vLLM, or OpenAI)

### Installation

```bash
# Clone your fork
git clone https://github.com/<your-username>/agent-octopus.git
cd agent-octopus

# Sync virtualenv and dependencies
uv sync

# Configure environment variables
cp .env.example .env
```

Edit `.env` to configure your LLM endpoint and paths:
```env
OLLAMA_API_BASE=http://localhost:11434/v1
OLLAMA_MODEL=Qwen3.6-35B-A3B-NVFP4
OLLAMA_API_KEY=ollama
MCP_CONFIG_PATH=mcp_config.json
COM_BIN=com
LOGFIRE_TOKEN=
```

---

## 💻 Usage

### Interactive REPL Mode
Start the interactive terminal UI:
```bash
uv run octo
```

When started, Octopus prints a structured, grouped table of all commands registered in `com`:
- Type `$` or press `Tab` to see interactive auto-completions with category badges and argument descriptions.
- Type a command index directly (e.g., `4` or `4 Zeus`) to immediately trigger that command with arguments.
- Or simply chat in natural language: the orchestrator will identify the correct specialist and delegate automatically.

### Single-Shot Command Execution
Execute a single runbook or query directly from the shell:
```bash
uv run octo -c "$$content_prompt"
uv run octo -c "$$god_find Apollo"
```

### Runtime Flag Overrides
```bash
uv run octo --model gpt-4o --api-base https://api.openai.com/v1
uv run octo --mcp-config /path/to/custom_mcp.json
uv run octo --logfire-console  # View live Pydantic AI OpenTelemetry spans in terminal
```

---

## 🔍 Observability with Pydantic Logfire

Agent Octopus includes native telemetry via **[Pydantic Logfire](https://pydantic.dev/logfire)**:
- All orchestrator decisions, specialist tool calls, and LLM completions are instrumented.
- Add `LOGFIRE_TOKEN` in `.env` to stream traces directly to the Logfire cloud dashboard.
- Pass `--logfire-console` to view formatted trace spans directly in your console.

---

## 🧪 Testing

Run unit tests via `pytest`:
```bash
uv run pytest
```

---

## 📄 License

MIT
