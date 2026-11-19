"""Validate SKILL.md frontmatter and manifest JSON files (CI check)."""

import json
from pathlib import Path

root = Path(".")

for skill in [
    "plugins/jikeyan/skills/jikeyan-agent/SKILL.md",
    "plugins/jikeyan/skills/jikeyan-academic-colleague/SKILL.md",
]:
    text = (root / skill).read_text(encoding="utf-8")
    assert text.startswith("---\n"), skill
    frontmatter = text.split("---\n", 2)[1]
    assert "name:" in frontmatter and "description:" in frontmatter, skill
    print(f"frontmatter OK: {skill}")

marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
plugin = json.loads((root / "plugins/jikeyan/.claude-plugin/plugin.json").read_text())
mcp_json = json.loads((root / "plugins/jikeyan/.mcp.json").read_text())
server = json.loads((root / "server.json").read_text())
assert marketplace["plugins"][0]["name"] == plugin["name"], (
    "entry/manifest name mismatch"
)
assert "jikeyan" in mcp_json["mcpServers"], ".mcp.json server missing"
assert len(server["description"]) <= 100, "registry description > 100 chars"
pkg = server["packages"][0]
assert pkg["registryType"] == "oci", pkg
assert pkg["identifier"].startswith("ghcr.io/871922384/jikeyan-mcp:"), pkg
oci_tag = pkg["identifier"].rsplit(":", 1)[1]
# Registry rejects OCI packages carrying a 'version' field (400); the
# version lives in the identifier tag only. (A future PyPI entry would
# still REQUIRE a 'version' field matching the tag/version.)
assert "version" not in pkg, "OCI package must not have 'version' field"
assert pkg["transport"] == {"type": "stdio"}, pkg
pyproject = (root / "mcp/pyproject.toml").read_text()
assert f'version = "{oci_tag}"' in pyproject, "pyproject version mismatch"
assert server["version"] == oci_tag, "server.json version != OCI tag"
assert "mcp-name: io.github.871922384/jikeyan-agent-skill" in (
    root / "mcp/README.md"
).read_text(), "mcp-name token missing"
print("manifests OK")
