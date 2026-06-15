# LibreChat stack

Self-hosted LibreChat (dev image) behind Traefik, with MCP servers wired in for
Actual Budget, Home Assistant (official `mcp_server`), and **ha-mcp** (the
third-party Home Assistant MCP server — see the `homeassistant` stack).

## Editing `librechat.yaml` — bump the config version

`librechat.yaml` is mounted as an **immutable Docker Swarm config**
(`librechat_config_vN`). Editing the file is not enough: you MUST bump `vN` →
`vN+1` in **both** places in `docker-compose.yml`:

- the service's `configs:` → `source:` reference
- the top-level `configs:` definition

Without the bump, the swarm keeps serving the old config and your edit silently
never reaches the container. Then redeploy:

```
USER=coder LOGNAME=coder task ansible:deploy:service -- -e "stack_name=librechat"
```

(The `USER=coder LOGNAME=coder` prefix works around stale root env in dev shells.)

## MCP tools + local Ollama models — DOESN'T WORK on LibreChat 0.8.6

**Bottom line: local Ollama models do NOT reliably execute MCP tools through
LibreChat 0.8.6. Use Claude via the native Anthropic endpoint for tool/MCP work.**
The model narrates the tool call as text in the chat (e.g. prints
`{"name": "ha_search", ...}` or `ha_call_read_tool_mcp_ha-mcp`) instead of
LibreChat executing it.

This is a LibreChat-layer problem, not the stack: hitting Ollama's `/v1/`
directly always returns correct structured `tool_calls` (llama3.1:8b and
qwen2.5:14b both work in direct API tests) — but the same models fail through
LibreChat. It matches the maintainer's own unfixed reproduction of this exact
Ollama + Home Assistant MCP stack:
[danny-avila/LibreChat#13428](https://github.com/danny-avila/LibreChat/issues/13428).
There is no fix in any release ≥ v0.8.6 (latest stable); the tool-call parsing
lives in the `@librechat/agents` npm package.

**To use Claude instead:** set a real `sk-ant-...` key in
`LIBRECHAT_ANTHROPIC_API_KEY` in the root `.env` (it shipped as a placeholder that
401s), bump the config + redeploy. Claude is then a native endpoint with
first-class tool-calling — ha-mcp tools work from the chat dropdown or an agent.

### Everything we tried (all FAILED to fix the text-instead-of-call symptom)

The Ollama stack itself was never the problem. Documented here so nobody repeats
the dead ends:

1. **Do NOT name the custom endpoint `"Ollama"`.** LibreChat hardcodes
   special-case routing for that exact name (case-insensitive) that breaks the
   agents/MCP tool path. Ours is named `ollama-local`.
   See [danny-avila/LibreChat#10327](https://github.com/danny-avila/LibreChat/issues/10327).

2. **Model choice.** In **direct** Ollama API tests, `llama3.1:8b` reliably emits
   OpenAI-style `tool_calls` (and was the default via `LIBRECHAT_OLLAMA_DEFAULT_MODEL`)
   — but through LibreChat even it narrates the call as text. The others are worse:
   - `qwen3:14b` ✗ — a reasoning model; burns its output budget on hidden
     `reasoning_content` and hits `finish_reason: length` before emitting the
     call. Also breaks on any **hyphen** in the tool name. Fine for plain non-tool
     chats. ([LibreChat#13428](https://github.com/danny-avila/LibreChat/issues/13428) — maintainer reproduced our exact HA-MCP + Ollama stack.)
   - `qwen2.5:14b` ✗ — breaks on any tool-name suffix in our tests.
   - `mistral-nemo:12b` ✗ — emits `[TOOL_CALLS]` as literal text.

3. **Raise Ollama's context window.** Ollama defaults to `num_ctx=4096`, which
   silently truncates prompts carrying MCP tool schemas (~9–12K tokens) — the
   model gets half a prompt and returns nothing. Fixed with
   `OLLAMA_CONTEXT_LENGTH=16384` in the `ollama` stack (sized to the ~15.5 GiB GPU).

4. **Agent vs chat dropdown.** MCP tool execution routes through the Agents
   runtime, and the malformed-call guard (`filterMalformedContentParts`) lives in
   the agents client — so an Agent is the most robust path. We tested a properly
   bound Agent on `ollama-local` with ha-mcp tools anyway: still narrates as text.

5. **Hyphens in the MCP server key break Qwen models.** LibreChat decorates tool
   names as `<tool>_mcp_<serverKey>`; a hyphenated key (`ha-mcp`) yields
   `..._mcp_ha-mcp`, which Qwen's template can't parse. `llama3.1` is unaffected,
   so the `mcpServers` key is left as `ha-mcp`. If switching to a Qwen model,
   rename the key to a hyphen-free `hamcp` (the URL value still points at the
   `ha-mcp:8086` container, which is unaffected).

### Not the fix: LiteLLM

A common community suggestion is to front Ollama with a LiteLLM proxy. Don't —
LiteLLM is itself a *source* of the tool-call-as-text bug (it relocates
`tool_calls` into the `content` field), and the LibreChat-side
`capabilities:`/`params:` keys from that thread are **not valid** custom-endpoint
fields. See [LibreChat discussion #7639](https://github.com/danny-avila/LibreChat/discussions/7639).

### The answer: use Claude (Anthropic endpoint)

Claude does MCP tool-calling natively and reliably in LibreChat — no proxy, no
workarounds, ha-mcp tools work from the chat dropdown or an agent. Cost is
cloud/per-token instead of the free local model, but it actually executes tools.
Set a real `sk-ant-...` key in `LIBRECHAT_ANTHROPIC_API_KEY` (it shipped as a
placeholder that 401s; the Mistral/Portkey keys 401 too), bump the config +
redeploy. This is the recommended path for any LibreChat MCP/tool work here.
