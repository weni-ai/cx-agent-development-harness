"""Seed for the adopt-mixed scenario: a partner folder full of agents in every shape.

Run by `dev/harness sandbox new adopt-mixed` with the sandbox as cwd. Expected
discovery (discover_agents.py):

    IN_PLACE  order-status                agents/order-status
    LOOSE     weather-bot                 weather_bot           (extra files, local .env)
    LOOSE     returns-agent               clients/acme/returns-agent
    LOOSE     store-locator               clients/globex/store_locator
    LOOSE     multi-agent-pack            multi_agent_pack      (warning: 2 agents)
    LOOSE     order-status                legacy/order-status   -> SKIPPED, slug taken
    INVALID   broken_tool_path            tool folder missing
    INVALID   shared_tools_agent          tool path outside the folder
    INVALID   empty_definition            no agents
    INVALID   bad_yaml                    not valid YAML
    ignored   node_modules/, .archive/, docs/, scripts/, data/, misc/ (not agents)
"""

from pathlib import Path

ROOT = Path.cwd()

MAIN_PY = '''from weni import Tool
from weni.context import Context
from weni.responses import TextResponse


class {cls}(Tool):
    def execute(self, context: Context) -> TextResponse:
        value = context.parameters.get("{param}", "")
        return TextResponse(data={{"{param}": value, "status": "ok"}})
'''

TEST_DEFINITION = '''tests:
  happy_path:
    parameters:
      {param}: "123"
'''


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def tool(folder: str, cls: str, param: str) -> None:
    write(f"{folder}/main.py", MAIN_PY.format(cls=cls, param=param))
    write(f"{folder}/requirements.txt", "requests==2.32.3\n")
    write(f"{folder}/test_definition.yaml", TEST_DEFINITION.format(param=param))


def tool_entry(key: str, path: str, cls: str, param: str) -> str:
    return f'''      - {key}:
          name: "{key.replace('_', ' ').title()}"
          description: "Looks up {param} and returns the result as structured data."
          source:
            path: "{path}"
            entrypoint: "main.{cls}"
          parameters:
            - {param}:
                description: "The {param} to look up"
                type: "string"
                required: true
'''


def agent(folder: str, key: str, name: str, tools: list[tuple[str, str, str]], extra_agent: str = "") -> None:
    """Write a valid single-agent definition plus its tool folders."""
    entries = "".join(tool_entry(t_key, f"tools/{t_key}", cls, param) for t_key, cls, param in tools)
    write(f"{folder}/agent_definition.yaml", f'''agents:
  {key}:
    name: "{name}"
    description: "Helps customers with {name.lower()} questions using the store's APIs."
    instructions:
      - "Always confirm the identifier the customer gave before calling any tool."
    guardrails:
      - "Never share data about a customer other than the one in this conversation."
    tools:
{entries}{extra_agent}''')
    for t_key, cls, param in tools:
        tool(f"{folder}/tools/{t_key}", cls, param)
    write(f"{folder}/agent_evaluation.yml", f"tests:\n  basic:\n    steps:\n      - user: \"Hi, I need help with {name.lower()}\"\n")


# 1. Already in place.
agent("agents/order-status", "order_status", "Order Status", [("get_order", "GetOrder", "order_id")])

# 2. Loose sibling folder with extra files and a local secret.
agent("weather_bot", "weather_bot", "Weather Bot", [("get_forecast", "GetForecast", "city")])
write("weather_bot/README.md", "# Weather Bot\n\nOld notes from the partner.\n")
write("weather_bot/notes/ideas.txt", "- add 3-day forecast\n")
write("weather_bot/tools/get_forecast/.env", "WEATHER_API_KEY=fake-key\n")

# 3-4. Nested inside client folders.
agent("clients/acme/returns-agent", "returns_agent", "Returns", [("create_return", "CreateReturn", "order_id"),
                                                                  ("return_status", "ReturnStatus", "return_id")])
agent("clients/globex/store_locator", "store_locator", "Store Locator", [("find_store", "FindStore", "zip_code")])
write("clients/acme/contract.pdf", "%PDF-1.4 fake\n")
write("clients/globex/brief.docx", "fake docx\n")

# 5. Two agents packed in one definition (adoptable, with a warning).
agent("multi_agent_pack", "faq_agent", "FAQ", [("search_faq", "SearchFaq", "question")], extra_agent='''  promo_agent:
    name: "Promotions"
    description: "Tells customers about current promotions."
    tools:
      - list_promos:
          name: "List Promos"
          description: "Lists active promotions."
          source:
            path: "tools/list_promos"
            entrypoint: "main.ListPromos"
''')
tool("multi_agent_pack/tools/list_promos", "ListPromos", "category")

# 6. Same slug as the agent already in place: must be skipped, never overwrite.
agent("legacy/order-status", "order_status_v1", "Order Status v1", [("get_order", "GetOrder", "order_id")])

# 7-10. Invalid definitions: reported, never moved.
agent("broken_tool_path", "broken_agent", "Broken", [("missing_tool", "Missing", "id")])
import shutil  # noqa: E402
shutil.rmtree(ROOT / "broken_tool_path" / "tools" / "missing_tool")

write("shared_tools_agent/agent_definition.yaml", '''agents:
  shared_agent:
    name: "Shared"
    description: "Uses a tool from a shared folder outside the agent."
    tools:
'''+ tool_entry("shared_lookup", "../shared_lib/lookup", "SharedLookup", "sku"))
tool("shared_lib/lookup", "SharedLookup", "sku")

write("empty_definition/agent_definition.yaml", "agents: {}\n")
write("bad_yaml/agent_definition.yaml", "agents:\n  oops: [unclosed\n")

# Noise: must never be detected as agents.
write("node_modules/some-pkg/agent_definition.yaml", "agents:\n  pkg: {}\n")
write(".archive/old_bot/agent_definition.yaml", "agents:\n  old: {}\n")
write("docs/architecture.md", "# Architecture\n\n```mermaid\nflowchart LR\n  Manager --> agents\n```\n")
write("docs/diagram.png", "not really a png\n")
write("scripts/sync_catalog.py", "print('sync')\n")
write("data/products.csv", "sku,name,price\n1,Shirt,10\n2,Shoes,40\n")
write("misc/config.yaml", "env: staging\nfeatures:\n  - search\n")
write("misc/tools/helper/main.py", "def helper():\n    return 1\n")
write("package.json", '{"name": "partner-workspace", "private": true}\n')
write("README.md", "# Partner workspace\n\nEvery agent we built for this account, in no particular order.\n")
