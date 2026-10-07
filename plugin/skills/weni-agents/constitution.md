<!--
  SYNC IMPACT REPORT
  ==================
  Version change: 1.4.0 → 1.5.0
  Modified principles:
    - III. Response Type Discipline → restricted to TextResponse and FinalResponse only;
      legacy types (AttachmentResponse, QuickReplyResponse, ListMessageResponse,
      CTAMessageResponse, OrderDetailsResponse, LocationResponse) marked as unsupported
  Added sections:
    - Agent Evaluation (weni eval init/run, agent_evaluation.yml structure, test writing patterns)
    - Weni Retail Setup API / VTEX Proxy (store-url, account-identifier, vtex-account, proxy)
  Changed sections:
    - Weni Flows API Integration → expanded Available API Endpoints with full
      query-parameter and body-field payloads for every endpoint from the API Explorer
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ (no changes needed)
    - .specify/templates/spec-template.md ✅ (no changes needed)
    - .specify/templates/tasks-template.md ✅ (no changes needed)
  Follow-up TODOs: None
-->

# Weni Agents Constitution

## Core Principles

### I. Tool-First Architecture

All agent capabilities MUST be implemented as Tools using the `weni-agents-toolkit` library. Tools are the building blocks of agent functionality.

**Non-negotiables**:
- Every tool MUST extend the `Tool` base class from `weni`
- Every tool MUST implement the `execute(self, context: Context)` method
- Every tool MUST return a valid Response type (`TextResponse` or `FinalResponse`)
- Tools MUST be stateless—all state comes from the `Context` object
- Tools MUST be independently testable via `test_definition.yaml`
- Tools MAY send proactive messages to the contact via `self.send_broadcast()` (see Broadcasts section)
- Tools MAY register analytics events via `self.register_event()` (see Events section)

### II. Context-Driven Execution

Tools receive all required data through the immutable `Context` object. Never rely on external state or global variables.

**Context Namespaces**:
- `context.parameters`: Tool-specific parameters defined in `agent_definition.yaml`
- `context.credentials`: Configured secrets and API keys
- `context.constants`: Agent-level configuration values (non-sensitive)
- `context.globals`: Global configuration values
- `context.contact`: Contact/user data from the conversation (includes `urn`)
- `context.project`: Project-level information (includes `auth_token` for Weni API access)

**Non-negotiables**:
- MUST access parameters via `context.parameters.get("param_name", default_value)`
- MUST NOT modify context data (it is immutable)
- MUST handle missing parameters gracefully with default values
- MUST access credentials via `context.credentials` for sensitive data (API keys, tokens)
- MUST access constants via `context.constants` for non-sensitive configuration values
- MUST access the Weni auth token via `context.project.get("auth_token")` when calling Weni Flows APIs

### III. Response Type Discipline

Tools MUST return appropriate Response types based on the intended user interaction. Never return raw data.

**Available Response Types** (from `weni.responses`):
- `TextResponse(data)`: Simple text messages — the agent receives the data and MAY compose a follow-up message to the contact
- `FinalResponse()`: Signals the tool fully handled the interaction — the agent stops and does NOT send any follow-up message

> **Important**: Only `TextResponse` and `FinalResponse` are supported. Do NOT use `AttachmentResponse`, `QuickReplyResponse`, `ListMessageResponse`, `CTAMessageResponse`, `OrderDetailsResponse`, or `LocationResponse` — these are legacy types and must not be used. For rich interactive messages (buttons, lists, catalogs, etc.), use Broadcasts instead (see Broadcasts section).

**TextResponse vs FinalResponse**:

| Return Type | Agent sends follow-up? | When to use |
|-------------|------------------------|-------------|
| `TextResponse(data=...)` | Yes — agent may generate a message based on data | The agent should interpret results and respond to the user |
| `FinalResponse()` | No — agent stops immediately | The tool already handled user-facing communication (broadcasts, side effects) |

**Non-negotiables**:
- MUST use `TextResponse` when the agent should interpret data and respond
- MUST use `FinalResponse` when the tool sends broadcasts and does not want agent-generated follow-up
- MUST use `FinalResponse` for side-effect-only tools (DB updates, webhooks with no user response)
- MUST NOT return `TextResponse` when also sending broadcasts unless duplicate messaging is intentional
- MUST NOT create custom response classes
- MUST include `data` parameter with the tool's execution result (except for `FinalResponse`)
- Response `data` MUST be JSON-serializable (dict, list, or primitive types)

### IV. Agent Definition Compliance

All agents MUST be defined in `agent_definition.yaml` following the exact YAML schema from Weni CLI. Validation failures will block deployment.

**Required Agent Fields**:
- `name`: String, **maximum 55 characters**
- `description`: String, required (see Description Best Practices below)
- `tools`: Array of tool definitions, required (at least one tool)

**Optional Agent Fields**:
- `instructions`: Array of strings, each **minimum 40 characters**
- `guardrails`: Array of strings, each **minimum 40 characters**
- `credentials`: Object defining secrets (see Credentials Configuration)
- `constants`: Object defining non-sensitive configuration (see Constants Configuration)
- `components`: Array of component definitions

**Description Best Practices** (critical for Manager orchestration):
- MUST clearly describe the agent's capabilities and when it should be invoked
- MUST be concise—the Manager uses this as the sole context for routing decisions
- SHOULD include the primary use cases or triggers for this agent
- SHOULD NOT exceed 2-3 sentences (avoid overly verbose descriptions)
- MUST NOT include implementation details or technical jargon

**Required Tool Fields**:
- `name`: String, **maximum 40 characters**
- `description`: String, **maximum 200 characters**
- `source`: Object with `path` and `entrypoint` (both required strings)
- `source.path`: Relative path to tool folder (e.g., `tools/my_tool`)
- `source.entrypoint`: Module and class name (e.g., `main.MyTool`)

**Optional Tool Fields**:
- `source.path_test`: String, path to test file (default: `test_definition.yaml`)
- `parameters`: Array of parameter definitions

**Parameter Definition**:
- `description`: String, required
- `type`: String, required, one of: `string`, `number`, `integer`, `boolean`, `array`
- `required`: Boolean, optional (default: false)
- `contact_field`: Boolean, optional (see Contact Field Constraints)

### V. Clean Code & Python Standards

All code MUST follow Python best practices and be self-documenting through expressive naming.

**Non-negotiables**:
- Follow [PEP 8](https://peps.python.org/pep-0008/) for formatting, naming, and layout
- Use `snake_case` for functions, variables, modules; `PascalCase` for classes
- Group imports: (1) standard library, (2) third-party, (3) weni toolkit, (4) local
- Use type annotations for all function signatures
- Keep functions with a single responsibility
- Prefer explicit over implicit, simple over complex

**Import Order Example**:
```python
# Standard library
import json
from datetime import datetime

# Third-party
import requests

# Weni toolkit
from weni import Tool
from weni.context import Context
from weni.responses import TextResponse, FinalResponse
from weni.broadcasts import Text, QuickReply
from weni.events.event import Event

# Local
from .helpers import format_data
```

## Manager-Collaborator Architecture

### Overview

Agents created via Weni CLI operate within a **Manager-Collaborator** orchestration model. Understanding this architecture is essential for designing effective agents.

**Architecture Components**:
- **Manager Agent**: The central orchestrator that receives user messages and routes them to appropriate collaborator agents. The Manager is configured exclusively through the Weni UI—it cannot be modified via CLI.
- **Collaborator Agents**: Specialized agents created and deployed via Weni CLI. Each collaborator handles specific domains or capabilities.
