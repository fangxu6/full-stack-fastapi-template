---
title: "Configuration Reference – Codex | OpenAI Developers"
source: "https://developers.openai.com/codex/config-reference"
author:
published:
created: 2026-06-07
description: "Complete reference for Codex config.toml and requirements.toml"
tags:
  - "clippings"
---
[API Dashboard](https://platform.openai.com/login)

Use this page as a searchable reference for Codex configuration files. For conceptual guidance and examples, start with [Config basics](https://developers.openai.com/codex/config-basic) and [Advanced Config](https://developers.openai.com/codex/config-advanced).

## config.toml

User-level configuration lives in `~/.codex/config.toml`. You can also add project-scoped overrides in `.codex/config.toml` files. Codex loads project-scoped config files only when you trust the project.

Project-scoped config can’t override machine-local provider, auth, host-owned app request metadata, notification, configuration profile selection, or telemetry routing keys. Codex ignores `openai_base_url`,`chatgpt_base_url`, `apps_mcp_product_sku`, `model_provider`,`model_providers`, `notify`, `profile`, `profiles`,`experimental_realtime_ws_base_url`, and `otel` when they appear in a project-local `.codex/config.toml`; put provider, notification, and telemetry keys in user-level config instead. Config [profile files](https://developers.openai.com/codex/config-advanced#profiles) live next to `config.toml` as `$CODEX_HOME/profile-name.config.toml`; select one with `--profile profile-name`.

For sandbox and approval keys (`approval_policy`, `sandbox_mode`, and `sandbox_workspace_write.*`), pair this reference with [Sandbox and approvals](https://developers.openai.com/codex/agent-approvals-security#sandbox-and-approvals), [Protected paths in writable roots](https://developers.openai.com/codex/agent-approvals-security#protected-paths-in-writable-roots), and [Network access](https://developers.openai.com/codex/agent-approvals-security#network-access). For beta permission profiles, see [Permissions](https://developers.openai.com/codex/permissions).

Key

`agents.<name>.config_file`

Type / Values

`string (path)`

Details

Path to a TOML config layer for that role; relative paths resolve from the config file that declares the role.

Key

`agents.<name>.description`

Type / Values

`string`

Details

Role guidance shown to Codex when choosing and spawning that agent type.

Key

`agents.<name>.nickname_candidates`

Type / Values

`array<string>`

Details

Optional pool of display nicknames for spawned agents in that role.

Key

`agents.job_max_runtime_seconds`

Type / Values

`number`

Details

Default per-worker timeout for `spawn_agents_on_csv` jobs. When unset, the tool falls back to 1800 seconds per worker.

Key

`agents.max_depth`

Type / Values

`number`

Details

Maximum nesting depth allowed for spawned agent threads (root sessions start at depth 0; default: 1).

Key

`agents.max_threads`

Type / Values

`number`

Details

Maximum number of agent threads that can be open concurrently. Defaults to `6` when unset.

Key

`analytics.enabled`

Type / Values

`boolean`

Details

Enable or disable analytics for this machine/profile. When unset, the client default applies.

Key

`approval_policy`

Type / Values

`untrusted | on-request | never | { granular = { sandbox_approval = bool, rules = bool, mcp_elicitations = bool, request_permissions = bool, skill_approval = bool } }`

Details

Controls when Codex pauses for approval before executing commands. You can also use `approval_policy = { granular = { ... } }` to allow or auto-reject specific prompt categories while keeping other prompts interactive. `on-failure` is deprecated; use `on-request` for interactive runs or `never` for non-interactive runs.

Key

`approval_policy.granular.mcp_elicitations`

Type / Values

`boolean`

Details

When `true`, MCP elicitation prompts are allowed to surface instead of being auto-rejected.

Key

`approval_policy.granular.request_permissions`

Type / Values

`boolean`

Details

When `true`, prompts from the `request_permissions` tool are allowed to surface.

Key

`approval_policy.granular.rules`

Type / Values

`boolean`

Details

When `true`, approvals triggered by execpolicy `prompt` rules are allowed to surface.

Key

`approval_policy.granular.sandbox_approval`

Type / Values

`boolean`

Details

When `true`, sandbox escalation approval prompts are allowed to surface.

Key

`approval_policy.granular.skill_approval`

Type / Values

`boolean`

Details

When `true`, skill-script approval prompts are allowed to surface.

Key

`approvals_reviewer`

Type / Values

`user | auto_review`

Details

Who reviews eligible approval prompts under `on-request` or granular approval policies. Defaults to `user`; `auto_review` uses the reviewer subagent. This setting doesn't change sandboxing or review actions already allowed inside the sandbox.

Key

`apps._default.destructive_enabled`

Type / Values

`boolean`

Details

Default allow/deny for app tools with `destructive_hint = true`.

Key

`apps._default.enabled`

Type / Values

`boolean`

Details

Default app enabled state for all apps unless overridden per app.

Key

`apps._default.open_world_enabled`

Type / Values

`boolean`

Details

Default allow/deny for app tools with `open_world_hint = true`.

Key

`apps.<id>.default_tools_approval_mode`

Type / Values

`auto | prompt | approve`

Details

Default approval behavior for tools in this app unless a per-tool override exists.

Key

`apps.<id>.default_tools_enabled`

Type / Values

`boolean`

Details

Default enabled state for tools in this app unless a per-tool override exists.

Key

`apps.<id>.destructive_enabled`

Type / Values

`boolean`

Details

Allow or block tools in this app that advertise `destructive_hint = true`.

Key

`apps.<id>.enabled`

Type / Values

`boolean`

Details

Enable or disable a specific app/connector by id (default: true).

Key

`apps.<id>.open_world_enabled`

Type / Values

`boolean`

Details

Allow or block tools in this app that advertise `open_world_hint = true`.

Key

`apps.<id>.tools.<tool>.approval_mode`

Type / Values

`auto | prompt | approve`

Details

Per-tool approval behavior override for a single app tool.

Key

`apps.<id>.tools.<tool>.enabled`

Type / Values

`boolean`

Details

Per-tool enabled override for an app tool (for example `repos/list`).

Key

`auto_review.policy`

Type / Values

`string`

Details

Local Markdown policy instructions for automatic review. Managed `guardian_policy_config` takes precedence. Blank values are ignored.

Key

`background_terminal_max_timeout`

Type / Values

`number`

Details

Maximum poll window in milliseconds for empty `write_stdin` polls (background terminal polling). Default: `300000` (5 minutes). Replaces the older `background_terminal_timeout` key.

Key

`check_for_update_on_startup`

Type / Values

`boolean`

Details

Check for Codex updates on startup (set to false only when updates are centrally managed).

Key

`cli_auth_credentials_store`

Type / Values

`file | keyring | auto`

Details

Control where the CLI stores cached credentials (file-based auth.json vs OS keychain).

Key

`commit_attribution`

Type / Values

`string`

Details

Commit co-author trailer used when `[features].codex_git_commit` is enabled. Defaults to `Codex <noreply@openai.com>`; set `""` to disable.

Key

`compact_prompt`

Type / Values

`string`

Details

Inline override for the history compaction prompt.

Key

`default_permissions`

Type / Values

`string`

Details

Name of the default permissions profile to apply to sandboxed tool calls. Built-ins are `:read-only`, `:workspace`, and `:danger-full-access`; custom profile names require matching `[permissions.<name>]` tables. Don't combine with `sandbox_mode` or `[sandbox_workspace_write]`.

Key

`developer_instructions`

Type / Values

`string`

Details

Additional developer instructions injected into the session (optional).

Key

`disable_paste_burst`

Type / Values

`boolean`

Details

Disable burst-paste detection in the TUI.

Key

`experimental_compact_prompt_file`

Type / Values

`string (path)`

Details

Load the compaction prompt override from a file (experimental).

Key

`experimental_use_unified_exec_tool`

Type / Values

`boolean`

Details

Legacy name for enabling unified exec; prefer `[features].unified_exec` or `codex --enable unified_exec`.

Key

`features.apps`

Type / Values

`boolean`

Details

Enable ChatGPT Apps/connectors support (experimental).

Key

`features.codex_git_commit`

Type / Values

`boolean`

Details

Enable Codex-generated git commits. When enabled, Codex uses `commit_attribution` to append a `Co-authored-by:` trailer to generated commit messages.

Key

`features.enable_request_compression`

Type / Values

`boolean`

Details

Compress streaming request bodies with zstd when supported (stable; on by default).

Key

`features.fast_mode`

Type / Values

`boolean`

Details

Enable model-catalog service tier selection in the TUI, including Fast-tier commands when the active model advertises them (stable; on by default).

Key

`features.hooks`

Type / Values

`boolean`

Details

Enable lifecycle hooks loaded from `hooks.json` or inline `[hooks]` config. `features.codex_hooks` is a deprecated alias.

Key

`features.memories`

Type / Values

`boolean`

Details

Enable [Memories](https://developers.openai.com/codex/memories) (off by default).

Key

`features.multi_agent`

Type / Values

`boolean`

Details

Enable multi-agent collaboration tools (`spawn_agent`, `send_input`, `resume_agent`, `wait_agent`, and `close_agent`) (stable; on by default).

Key

`features.network_proxy`

Type / Values

`boolean | table`

Details

Enable sandboxed networking. Use a table form when setting network policy options such as `domains` (experimental; off by default).

Key

`features.network_proxy.allow_local_binding`

Type / Values

`boolean`

Details

Allow broader local/private-network access. Defaults to `false`; exact local IP literal or `localhost` allow rules can still permit specific local targets.

Key

`features.network_proxy.allow_upstream_proxy`

Type / Values

`boolean`

Details

Allow chaining through an upstream proxy from the environment. Defaults to `true`.

Key

`features.network_proxy.dangerously_allow_all_unix_sockets`

Type / Values

`boolean`

Details

Permit arbitrary Unix socket destinations instead of allowlist-only access. Defaults to `false`; use only in tightly controlled environments.

Key

`features.network_proxy.dangerously_allow_non_loopback_proxy`

Type / Values

`boolean`

Details

Permit non-loopback listener addresses. Defaults to `false`; enabling it can expose proxy listeners beyond localhost.

Key

`features.network_proxy.domains`

Type / Values

`map<string, allow | deny>`

Details

Domain policy for sandboxed networking. Unset by default, which means no external destinations are allowed until you add `allow` rules. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules; prefer scoped rules because `*` broadly opens public outbound access. Add `deny` rules for blocked destinations; `deny` wins on conflicts.

Key

`features.network_proxy.enable_socks5`

Type / Values

`boolean`

Details

Expose SOCKS5 support. Defaults to `true`.

Key

`features.network_proxy.enable_socks5_udp`

Type / Values

`boolean`

Details

Allow UDP over SOCKS5. Defaults to `true`.

Key

`features.network_proxy.enabled`

Type / Values

`boolean`

Details

Enable sandboxed networking. Defaults to `false`.

Key

`features.network_proxy.proxy_url`

Type / Values

`string`

Details

HTTP listener URL for sandboxed networking. Defaults to `"http://127.0.0.1:3128"`.

Key

`features.network_proxy.socks_url`

Type / Values

`string`

Details

SOCKS5 listener URL. Defaults to `"http://127.0.0.1:8081"`.

Key

`features.network_proxy.unix_sockets`

Type / Values

`map<string, allow | deny>`

Details

Unix socket policy for sandboxed networking. Unset by default; add `allow` entries for permitted sockets.

Key

`features.personality`

Type / Values

`boolean`

Details

Enable personality selection controls (stable; on by default).

Key

`features.prevent_idle_sleep`

Type / Values

`boolean`

Details

Prevent the machine from sleeping while a turn is actively running (experimental; off by default).

Key

`features.shell_snapshot`

Type / Values

`boolean`

Details

Snapshot shell environment to speed up repeated commands (stable; on by default).

Key

`features.shell_tool`

Type / Values

`boolean`

Details

Enable the default `shell` tool for running commands (stable; on by default).

Key

`features.skill_mcp_dependency_install`

Type / Values

`boolean`

Details

Allow prompting and installing missing MCP dependencies for skills (stable; on by default).

Key

`features.undo`

Type / Values

`boolean`

Details

Enable undo support (stable; off by default).

Key

`features.unified_exec`

Type / Values

`boolean`

Details

Use the unified PTY-backed exec tool (stable; enabled by default except on Windows).

Key

`features.web_search`

Type / Values

`boolean`

Details

Deprecated legacy toggle; prefer the top-level `web_search` setting.

Key

`features.web_search_cached`

Type / Values

`boolean`

Details

Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "cached"`.

Key

`features.web_search_request`

Type / Values

`boolean`

Details

Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "live"`.

Key

`feedback.enabled`

Type / Values

`boolean`

Details

Enable feedback submission via `/feedback` across Codex surfaces (default: true).

Key

`file_opener`

Type / Values

`vscode | vscode-insiders | windsurf | cursor | none`

Details

URI scheme used to open citations from Codex output (default: `vscode`).

Key

`hide_agent_reasoning`

Type / Values

`boolean`

Details

Suppress reasoning events in both the TUI and `codex exec` output.

Key

`history.max_bytes`

Type / Values

`number`

Details

If set, caps the history file size in bytes by dropping oldest entries.

Key

`history.persistence`

Type / Values

`save-all | none`

Details

Control whether Codex saves session transcripts to history.jsonl.

Key

`hooks`

Type / Values

`table`

Details

Lifecycle hooks configured inline in `config.toml`. Uses the same event schema as `hooks.json`; see the Hooks guide for examples and supported events.

Key

`hooks.<Event>`

Type / Values

`array<table>`

Details

Matcher groups for hook events such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, or `Stop`.

Key

`hooks.<Event>[].hooks`

Type / Values

`array<table>`

Details

Hook handlers for a matcher group. Command hooks are currently supported; prompt and agent hook handlers are parsed but skipped.

Key

`hooks.<Event>[].hooks[].commandWindows`

Type / Values

`string`

Details

Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted.

Key

`instructions`

Type / Values

`string`

Details

Reserved for future use; prefer `model_instructions_file` or `AGENTS.md`.

Key

`log_dir`

Type / Values

`string (path)`

Details

Directory where Codex writes log files; defaults to `$CODEX_HOME/log`. Setting this explicitly also enables the opt-in plaintext TUI log, `codex-tui.log`, in that directory.

Key

`mcp_oauth_credentials_store`

Type / Values

`auto | file | keyring`

Details

Preferred store for MCP OAuth credentials.

Key

`mcp_servers.<id>.args`

Type / Values

`array<string>`

Details

Arguments passed to the MCP stdio server command.

Key

`mcp_servers.<id>.bearer_token_env_var`

Type / Values

`string`

Details

Environment variable sourcing the bearer token for an MCP HTTP server.

Key

`mcp_servers.<id>.command`

Type / Values

`string`

Details

Launcher command for an MCP stdio server.

Key

`mcp_servers.<id>.cwd`

Type / Values

`string`

Details

Working directory for the MCP stdio server process.

Key

`mcp_servers.<id>.default_tools_approval_mode`

Type / Values

`auto | prompt | approve`

Details

Default approval behavior for MCP tools on this server unless a per-tool override exists.

Key

`mcp_servers.<id>.disabled_tools`

Type / Values

`array<string>`

Details

Deny list applied after `enabled_tools` for the MCP server.

Key

`mcp_servers.<id>.enabled`

Type / Values

`boolean`

Details

Disable an MCP server without removing its configuration.

Key

`mcp_servers.<id>.enabled_tools`

Type / Values

`array<string>`

Details

Allow list of tool names exposed by the MCP server.

Key

`mcp_servers.<id>.env`

Type / Values

`map<string,string>`

Details

Environment variables forwarded to the MCP stdio server.

Key

`mcp_servers.<id>.env_vars`

Type / Values

`array<string | { name = string, source = "local" | "remote" }>`

Details

Additional environment variables to whitelist for an MCP stdio server. String entries default to `source = "local"`; use `source = "remote"` only with executor-backed remote stdio.

Key

`mcp_servers.<id>.experimental_environment`

Type / Values

`local | remote`

Details

Experimental placement for an MCP server. `remote` starts stdio servers through a remote executor environment; streamable HTTP remote placement is not implemented.

Key

`mcp_servers.<id>.required`

Type / Values

`boolean`

Details

When true, fail startup/resume if this enabled MCP server cannot initialize.

Key

`mcp_servers.<id>.scopes`

Type / Values

`array<string>`

Details

OAuth scopes to request when authenticating to that MCP server.

Key

`mcp_servers.<id>.startup_timeout_ms`

Type / Values

`number`

Details

Alias for `startup_timeout_sec` in milliseconds.

Key

`mcp_servers.<id>.startup_timeout_sec`

Type / Values

`number`

Details

Override the default 10s startup timeout for an MCP server.

Key

`mcp_servers.<id>.tool_timeout_sec`

Type / Values

`number`

Details

Override the default 60s per-tool timeout for an MCP server.

Key

`mcp_servers.<id>.tools.<tool>.approval_mode`

Type / Values

`auto | prompt | approve`

Details

Per-tool approval behavior override for one MCP tool on this server.

Key

`mcp_servers.<id>.url`

Type / Values

`string`

Details

Endpoint for an MCP streamable HTTP server.

Key

`memories.consolidation_model`

Type / Values

`string`

Details

Optional model override for global memory consolidation.

Key

`memories.disable_on_external_context`

Type / Values

`boolean`

Details

When `true`, threads that use external context such as MCP tool calls, web search, or tool search are kept out of memory generation. Defaults to `false`. Legacy alias: `memories.no_memories_if_mcp_or_web_search`.

Key

`memories.extract_model`

Type / Values

`string`

Details

Optional model override for per-thread memory extraction.

Key

`memories.generate_memories`

Type / Values

`boolean`

Details

When `false`, newly created threads are not stored as memory-generation inputs. Defaults to `true`.

Key

`memories.max_raw_memories_for_consolidation`

Type / Values

`number`

Details

Maximum recent raw memories retained for global consolidation. Defaults to `256` and is capped at `4096`.

Key

`memories.max_rollout_age_days`

Type / Values

`number`

Details

Maximum age of threads considered for memory generation. Defaults to `30` and is clamped to `0` - `90`.

Key

`memories.max_rollouts_per_startup`

Type / Values

`number`

Details

Maximum rollout candidates processed per startup pass. Defaults to `16` and is capped at `128`.

Key

`memories.max_unused_days`

Type / Values

`number`

Details

Maximum days since a memory was last used before it becomes ineligible for consolidation. Defaults to `30` and is clamped to `0` - `365`.

Key

`memories.min_rate_limit_remaining_percent`

Type / Values

`number`

Details

Minimum remaining percentage required in Codex rate-limit windows before memory generation starts. Defaults to `25` and is clamped to `0` - `100`.

Key

`memories.min_rollout_idle_hours`

Type / Values

`number`

Details

Minimum idle time before a thread is considered for memory generation. Defaults to `6` and is clamped to `1` - `48`.

Key

`memories.use_memories`

Type / Values

`boolean`

Details

When `false`, Codex skips injecting existing memories into future sessions. Defaults to `true`.

Key

`model`

Type / Values

`string`

Details

Model to use (e.g., `gpt-5.5`).

Key

`model_auto_compact_token_limit`

Type / Values

`number`

Details

Token threshold that triggers automatic history compaction (unset uses model defaults).

Key

`model_catalog_json`

Type / Values

`string (path)`

Details

Optional path to a JSON model catalog loaded on startup. A selected `$CODEX_HOME/profile-name.config.toml` profile file can override this per profile.

Key

`model_context_window`

Type / Values

`number`

Details

Context window tokens available to the active model.

Key

`model_instructions_file`

Type / Values

`string (path)`

Details

Replacement for built-in instructions instead of `AGENTS.md`.

Key

`model_provider`

Type / Values

`string`

Details

Provider id from `model_providers` (default: `openai`).

Key

`model_providers.<id>`

Type / Values

`table`

Details

Custom provider definition. Built-in provider IDs (`openai`, `ollama`, and `lmstudio`) are reserved and cannot be overridden.

Key

`model_providers.<id>.auth`

Type / Values

`table`

Details

Command-backed bearer token configuration for a custom provider. Do not combine with `env_key`, `experimental_bearer_token`, or `requires_openai_auth`.

Key

`model_providers.<id>.auth.args`

Type / Values

`array<string>`

Details

Arguments passed to the token command.

Key

`model_providers.<id>.auth.command`

Type / Values

`string`

Details

Command to run when Codex needs a bearer token. The command must print the token to stdout.

Key

`model_providers.<id>.auth.cwd`

Type / Values

`string (path)`

Details

Working directory for the token command.

Key

`model_providers.<id>.auth.refresh_interval_ms`

Type / Values

`number`

Details

How often Codex proactively refreshes the token in milliseconds (default: 300000). Set to `0` to refresh only after an authentication retry.

Key

`model_providers.<id>.auth.timeout_ms`

Type / Values

`number`

Details

Maximum token command runtime in milliseconds (default: 5000).

Key

`model_providers.<id>.base_url`

Type / Values

`string`

Details

API base URL for the model provider.

Key

`model_providers.<id>.env_key`

Type / Values

`string`

Details

Environment variable supplying the provider API key.

Key

`model_providers.<id>.env_key_instructions`

Type / Values

`string`

Details

Optional setup guidance for the provider API key.

Key

`model_providers.<id>.experimental_bearer_token`

Type / Values

`string`

Details

Direct bearer token for the provider (discouraged; use `env_key`).

Key

`model_providers.<id>.name`

Type / Values

`string`

Details

Display name for a custom model provider.

Key

`model_providers.<id>.query_params`

Type / Values

`map<string,string>`

Details

Extra query parameters appended to provider requests.

Key

`model_providers.<id>.request_max_retries`

Type / Values

`number`

Details

Retry count for HTTP requests to the provider (default: 4).

Key

`model_providers.<id>.requires_openai_auth`

Type / Values

`boolean`

Details

The provider uses OpenAI authentication (defaults to false).

Key

`model_providers.<id>.stream_idle_timeout_ms`

Type / Values

`number`

Details

Idle timeout for SSE streams in milliseconds (default: 300000).

Key

`model_providers.<id>.stream_max_retries`

Type / Values

`number`

Details

Retry count for SSE streaming interruptions (default: 5).

Key

`model_providers.amazon-bedrock.aws.profile`

Type / Values

`string`

Details

AWS profile name used by the built-in `amazon-bedrock` provider.

Key

`model_providers.amazon-bedrock.aws.region`

Type / Values

`string`

Details

AWS region used by the built-in `amazon-bedrock` provider.

Key

`model_reasoning_summary`

Type / Values

`auto | concise | detailed | none`

Details

Select reasoning summary detail or disable summaries entirely.

Key

`model_supports_reasoning_summaries`

Type / Values

`boolean`

Details

Force Codex to send or not send reasoning metadata.

Key

`notice.hide_full_access_warning`

Type / Values

`boolean`

Details

Track acknowledgement of the full access warning prompt.

Key

`notice.hide_gpt-5.1-codex-max_migration_prompt`

Type / Values

`boolean`

Details

Track acknowledgement of the gpt-5.1-codex-max migration prompt.

Key

`notice.hide_gpt5_1_migration_prompt`

Type / Values

`boolean`

Details

Track acknowledgement of the GPT-5.1 migration prompt.

Key

`notice.hide_rate_limit_model_nudge`

Type / Values

`boolean`

Details

Track opt-out of the rate limit model switch reminder.

Key

`notice.hide_world_writable_warning`

Type / Values

`boolean`

Details

Track acknowledgement of the Windows world-writable directories warning.

Key

`notice.model_migrations`

Type / Values

`map<string,string>`

Details

Track acknowledged model migrations as old->new mappings.

Key

`notify`

Type / Values

`array<string>`

Details

Command invoked for notifications; receives a JSON payload from Codex.

Key

`openai_base_url`

Type / Values

`string`

Details

Base URL override for the built-in `openai` model provider.

Key

`oss_provider`

Type / Values

`lmstudio | ollama`

Details

Default local provider used when running with `--oss` (defaults to prompting if unset).

Key

`otel.environment`

Type / Values

`string`

Details

Environment tag applied to emitted OpenTelemetry events (default: `dev`).

Key

`otel.exporter`

Type / Values

`none | otlp-http | otlp-grpc`

Details

Select the OpenTelemetry exporter and provide any endpoint metadata.

Key

`otel.exporter.<id>.endpoint`

Type / Values

`string`

Details

Exporter endpoint for OTEL logs.

Key

`otel.exporter.<id>.protocol`

Type / Values

`binary | json`

Details

Protocol used by the OTLP/HTTP exporter.

Key

`otel.exporter.<id>.tls.ca-certificate`

Type / Values

`string`

Details

CA certificate path for OTEL exporter TLS.

Key

`otel.exporter.<id>.tls.client-certificate`

Type / Values

`string`

Details

Client certificate path for OTEL exporter TLS.

Key

`otel.exporter.<id>.tls.client-private-key`

Type / Values

`string`

Details

Client private key path for OTEL exporter TLS.

Key

`otel.log_user_prompt`

Type / Values

`boolean`

Details

Opt in to exporting raw user prompts with OpenTelemetry logs.

Key

`otel.metrics_exporter`

Type / Values

`none | statsig | otlp-http | otlp-grpc`

Details

Select the OpenTelemetry metrics exporter (defaults to `statsig`).

Key

`otel.trace_exporter`

Type / Values

`none | otlp-http | otlp-grpc`

Details

Select the OpenTelemetry trace exporter and provide any endpoint metadata.

Key

`otel.trace_exporter.<id>.endpoint`

Type / Values

`string`

Details

Trace exporter endpoint for OTEL logs.

Key

`otel.trace_exporter.<id>.protocol`

Type / Values

`binary | json`

Details

Protocol used by the OTLP/HTTP trace exporter.

Key

`otel.trace_exporter.<id>.tls.ca-certificate`

Type / Values

`string`

Details

CA certificate path for OTEL trace exporter TLS.

Key

`otel.trace_exporter.<id>.tls.client-certificate`

Type / Values

`string`

Details

Client certificate path for OTEL trace exporter TLS.

Key

`otel.trace_exporter.<id>.tls.client-private-key`

Type / Values

`string`

Details

Client private key path for OTEL trace exporter TLS.

Key

`permissions.<name>.description`

Type / Values

`string`

Details

Human-readable description for this named profile. A profile does not inherit its parent's description through `extends`.

Key

`permissions.<name>.extends`

Type / Values

`string`

Details

Optional parent profile applied before this named profile. Set it to another named profile, `:read-only`, or `:workspace`; `:danger-full-access`, undefined parents, and cycles are rejected.

Key

`permissions.<name>.filesystem`

Type / Values

`table`

Details

Named filesystem permission profile. Each key is an absolute path or special token such as `:minimal` or `:workspace_roots`.

Key

`permissions.<name>.filesystem.":workspace_roots".<subpath-or-glob>`

Type / Values

`"read" | "write" | "deny"`

Details

Scoped filesystem access relative to each effective workspace root. Use `"."` for the root itself; glob subpaths such as `"**/*.env"` can deny reads with `"deny"`.

Key

`permissions.<name>.filesystem.<path-or-glob>`

Type / Values

`"read" | "write" | "deny" | table`

Details

Grant direct access for a path, glob pattern, or special token, or scope nested entries under that root. Use `"deny"` to deny reads for matching paths.

Key

`permissions.<name>.filesystem.glob_scan_max_depth`

Type / Values

`number`

Details

Maximum depth for expanding deny-read glob patterns on platforms that snapshot matches before sandbox startup. Must be at least `1` when set.

Key

`permissions.<name>.network.allow_local_binding`

Type / Values

`boolean`

Details

Permit broader local/private-network access through sandboxed networking. Exact local IP literal or `localhost` allow rules can still permit specific local targets when this stays `false`.

Key

`permissions.<name>.network.allow_upstream_proxy`

Type / Values

`boolean`

Details

Allow sandboxed networking to chain through another upstream proxy.

Key

`permissions.<name>.network.dangerously_allow_all_unix_sockets`

Type / Values

`boolean`

Details

Allow arbitrary Unix socket destinations instead of the default restricted set. Use only in tightly controlled environments.

Key

`permissions.<name>.network.dangerously_allow_non_loopback_proxy`

Type / Values

`boolean`

Details

Permit non-loopback bind addresses for sandboxed networking listeners. Enabling it can expose listeners beyond localhost.

Key

`permissions.<name>.network.domains`

Type / Values

`table`

Details

Domain rules for sandboxed networking. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules. `deny` wins on conflicts.

Key

`permissions.<name>.network.domains.<pattern>`

Type / Values

`allow | deny`

Details

Allow or deny an exact host or scoped wildcard pattern such as `*.example.com` or `**.example.com`.

Key

`permissions.<name>.network.enable_socks5`

Type / Values

`boolean`

Details

Expose SOCKS5 support when this permissions profile enables sandboxed networking.

Key

`permissions.<name>.network.enable_socks5_udp`

Type / Values

`boolean`

Details

Allow UDP over the SOCKS5 listener when enabled.

Key

`permissions.<name>.network.enabled`

Type / Values

`boolean`

Details

Enable network access for this named permissions profile. This changes the sandbox network policy; it does not start the network proxy by itself.

Key

`permissions.<name>.network.mode`

Type / Values

`limited | full`

Details

Network proxy mode used for subprocess traffic.

Key

`permissions.<name>.network.proxy_url`

Type / Values

`string`

Details

HTTP listener URL used when this permissions profile enables sandboxed networking.

Key

`permissions.<name>.network.socks_url`

Type / Values

`string`

Details

SOCKS5 proxy endpoint used by this permissions profile.

Key

`permissions.<name>.network.unix_sockets`

Type / Values

`table`

Details

Unix socket allowlist overrides for sandboxed networking. Use socket paths as keys; `allow` adds a path, and `deny` rejects it.

Key

`permissions.<name>.network.unix_sockets.<path>`

Type / Values

`allow | deny`

Details

Add an absolute Unix socket path to the effective allowlist with `allow`, or reject it with `deny`. Denied entries are omitted from the effective allowlist.

Key

`permissions.<name>.workspace_roots`

Type / Values

`table`

Details

Profile-defined workspace roots that receive `:workspace_roots` filesystem rules alongside the session's runtime workspace roots.

Key

`permissions.<name>.workspace_roots.<path>`

Type / Values

`boolean`

Details

Opt a path into the profile's workspace root set when `true`. Disabled entries remain inactive.

Key

`personality`

Type / Values

`none | friendly | pragmatic`

Details

Default communication style for models that advertise `supportsPersonality`; can be overridden per thread/turn or via `/personality`.

Key

`plan_mode_reasoning_effort`

Type / Values

`none | minimal | low | medium | high | xhigh`

Details

Plan-mode-specific reasoning override. When unset, Plan mode uses its built-in preset default.

Key

`plugins.<plugin>.mcp_servers.<server>.default_tools_approval_mode`

Type / Values

`auto | prompt | approve`

Details

Default approval behavior for tools on a plugin-provided MCP server.

Key

`plugins.<plugin>.mcp_servers.<server>.disabled_tools`

Type / Values

`array<string>`

Details

Deny list applied after `enabled_tools` for a plugin-provided MCP server.

Key

`plugins.<plugin>.mcp_servers.<server>.enabled`

Type / Values

`boolean`

Details

Enable or disable an MCP server bundled by an installed plugin without changing the plugin manifest.

Key

`plugins.<plugin>.mcp_servers.<server>.enabled_tools`

Type / Values

`array<string>`

Details

Allow list of tools exposed from a plugin-provided MCP server.

Key

`plugins.<plugin>.mcp_servers.<server>.tools.<tool>.approval_mode`

Type / Values

`auto | prompt | approve`

Details

Per-tool approval behavior override for a plugin-provided MCP tool.

Key

`project_doc_fallback_filenames`

Type / Values

`array<string>`

Details

Additional filenames to try when `AGENTS.md` is missing.

Key

`project_doc_max_bytes`

Type / Values

`number`

Details

Maximum bytes read from `AGENTS.md` when building project instructions.

Key

`project_root_markers`

Type / Values

`array<string>`

Details

List of project root marker filenames; used when searching parent directories for the project root.

Key

`projects.<path>.trust_level`

Type / Values

`string`

Details

Mark a project or worktree as trusted or untrusted (`"trusted"` | `"untrusted"`). Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules.

Key

`review_model`

Type / Values

`string`

Details

Optional model override used by `/review` (defaults to the current session model).

Key

`sandbox_mode`

Type / Values

`read-only | workspace-write | danger-full-access`

Details

Sandbox policy for filesystem and network access during command execution.

Key

`sandbox_workspace_write.exclude_slash_tmp`

Type / Values

`boolean`

Details

Exclude `/tmp` from writable roots in workspace-write mode.

Key

`sandbox_workspace_write.exclude_tmpdir_env_var`

Type / Values

`boolean`

Details

Exclude `$TMPDIR` from writable roots in workspace-write mode.

Key

`sandbox_workspace_write.network_access`

Type / Values

`boolean`

Details

Allow outbound network access inside the workspace-write sandbox.

Key

`sandbox_workspace_write.writable_roots`

Type / Values

`array<string>`

Details

Additional writable roots when `sandbox_mode = "workspace-write"`.

Key

`service_tier`

Type / Values

`string`

Details

Preferred service tier for new turns. Built-in values include `flex` and `fast`; legacy `fast` config maps to the request value `priority`, and catalog-provided tier IDs can also be stored.

Key

`shell_environment_policy.exclude`

Type / Values

`array<string>`

Details

Glob patterns for removing environment variables after the defaults.

Key

`shell_environment_policy.experimental_use_profile`

Type / Values

`boolean`

Details

Use the user shell profile when spawning subprocesses.

Key

`shell_environment_policy.ignore_default_excludes`

Type / Values

`boolean`

Details

Keep variables containing KEY/SECRET/TOKEN before other filters run.

Key

`shell_environment_policy.include_only`

Type / Values

`array<string>`

Details

Whitelist of patterns; when set only matching variables are kept.

Key

`shell_environment_policy.inherit`

Type / Values

`all | core | none`

Details

Baseline environment inheritance when spawning subprocesses.

Key

`shell_environment_policy.set`

Type / Values

`map<string,string>`

Details

Explicit environment overrides injected into every subprocess.

Key

`show_raw_agent_reasoning`

Type / Values

`boolean`

Details

Surface raw reasoning content when the active model emits it.

Key

`skills.config`

Type / Values

`array<object>`

Details

Per-skill enablement overrides stored in config.toml.

Key

`skills.config.<index>.enabled`

Type / Values

`boolean`

Details

Enable or disable the referenced skill.

Key

`skills.config.<index>.path`

Type / Values

`string (path)`

Details

Path to a skill folder containing `SKILL.md`.

Key

`sqlite_home`

Type / Values

`string (path)`

Details

Directory where Codex stores the SQLite-backed state DB used by agent jobs and other resumable runtime state.

Key

`suppress_unstable_features_warning`

Type / Values

`boolean`

Details

Suppress the warning that appears when under-development feature flags are enabled.

Key

`tool_output_token_limit`

Type / Values

`number`

Details

Token budget for storing individual tool/function outputs in history.

Key

`tool_suggest.disabled_tools`

Type / Values

`array<table>`

Details

Disable suggestions for specific discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`.

Key

`tool_suggest.discoverables`

Type / Values

`array<table>`

Details

Allow tool suggestions for additional discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`.

Key

`tools.view_image`

Type / Values

`boolean`

Details

Enable the local-image attachment tool `view_image`.

Key

`tools.web_search`

Type / Values

`boolean | { context_size = "low|medium|high", allowed_domains = [string], location = { country, region, city, timezone } }`

Details

Optional web search tool configuration. The legacy boolean form is still accepted, but the object form lets you set search context size, allowed domains, and approximate user location.

Key

`tui`

Type / Values

`table`

Details

TUI-specific options such as enabling inline desktop notifications.

Key

`tui.alternate_screen`

Type / Values

`auto | always | never`

Details

Control alternate screen usage for the TUI (default: auto; auto skips it in Zellij to preserve scrollback).

Key

`tui.animations`

Type / Values

`boolean`

Details

Enable terminal animations (welcome screen, shimmer, spinner) (default: true).

Key

`tui.keymap.<context>.<action>`

Type / Values

`string | array<string>`

Details

Keyboard shortcut binding for a TUI action. Supported contexts include `global`, `chat`, `composer`, `editor`, `vim_normal`, `vim_operator`, `vim_text_object`, `pager`, `list`, and `approval`. Selected composer actions fall back to matching `tui.keymap.global` bindings; context-specific bindings take precedence when supported.

Key

`tui.keymap.<context>.<action> = []`

Type / Values

`empty array`

Details

Unbind the action in that keymap context. Key names use normalized strings such as `ctrl-a`, `shift-enter`, `page-down`, or `minus`.

Key

`tui.model_availability_nux.<model>`

Type / Values

`integer`

Details

Internal startup-tooltip state keyed by model slug.

Key

`tui.notification_condition`

Type / Values

`unfocused | always`

Details

Control whether TUI notifications fire only when the terminal is unfocused or regardless of focus. Defaults to `unfocused`.

Key

`tui.notification_method`

Type / Values

`auto | osc9 | bel`

Details

Notification method for terminal notifications (default: auto).

Key

`tui.notifications`

Type / Values

`boolean | array<string>`

Details

Enable TUI notifications; optionally restrict to specific event types.

Key

`tui.raw_output_mode`

Type / Values

`boolean`

Details

Start the TUI in raw scrollback mode for copy-friendly terminal selection (default: false). You can toggle it with `/raw` or the default `alt-r` key binding.

Key

`tui.show_tooltips`

Type / Values

`boolean`

Details

Show onboarding tooltips in the TUI welcome screen (default: true).

Key

`tui.terminal_title`

Type / Values

`array<string> | null`

Details

Ordered list of terminal window/tab title item identifiers. Defaults to `["spinner", "project"]`; `null` disables title updates.

Key

`tui.theme`

Type / Values

`string`

Details

Syntax-highlighting theme override (kebab-case theme name).

Key

`tui.vim_mode_default`

Type / Values

`boolean`

Details

Start the composer in Vim normal mode instead of insert mode (default: false). You can still toggle it per session with `/vim`.

Key

`web_search`

Type / Values

`disabled | cached | live`

Details

Web search mode (default: `"cached"`; cached uses an OpenAI-maintained index and does not fetch live pages; if you use `--yolo` or another full access sandbox setting, it defaults to `"live"`). Use `"live"` to fetch the most recent data from the web, or `"disabled"` to remove the tool.

Key

`windows_wsl_setup_acknowledged`

Type / Values

`boolean`

Details

Track Windows onboarding acknowledgement (Windows only).

Key

`windows.sandbox`

Type / Values

`unelevated | elevated`

Details

Windows-only native sandbox mode when running Codex natively on Windows.

Key

`windows.sandbox_private_desktop`

Type / Values

`boolean`

Details

Run the final sandboxed child process on a private desktop by default on native Windows. Set `false` only for compatibility with the older `Winsta0\\Default` behavior.

You can find the latest JSON schema for `config.toml` [here](https://developers.openai.com/codex/config-schema.json).

To get autocompletion and diagnostics when editing `config.toml` in VS Code or Cursor, you can install the [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) extension and add this line to the top of your `config.toml`:

```toml
#:schema https://developers.openai.com/codex/config-schema.json
```

Note: Rename `experimental_instructions_file` to `model_instructions_file`. Codex deprecates the old key; update existing configs to the new name.

## requirements.toml

`requirements.toml` is an admin-enforced configuration file that constrains security-sensitive settings users can’t override. For details, locations, and examples, see [Admin-enforced requirements](https://developers.openai.com/codex/enterprise/managed-configuration#admin-enforced-requirements-requirementstoml).

For ChatGPT Business and Enterprise users, Codex can also apply cloud-fetched requirements. See the security page for precedence details.

Use `[features]` in `requirements.toml` to pin feature flags by the same canonical keys that `config.toml` uses. Omitted keys remain unconstrained.

Key

`allow_managed_hooks_only`

Type / Values

`boolean`

Details

When `true`, Codex skips user, project, session, and plugin hooks while still allowing managed hooks from `requirements.toml` and other managed config layers.

Key

`allowed_approval_policies`

Type / Values

`array<string>`

Details

Allowed values for `approval_policy` (for example `untrusted`, `on-request`, `never`, and `granular`).

Key

`allowed_approvals_reviewers`

Type / Values

`array<string>`

Details

Allowed values for `approvals_reviewer`, such as `user` and `auto_review`.

Key

`allowed_sandbox_modes`

Type / Values

`array<string>`

Details

Allowed values for `sandbox_mode`.

Key

`allowed_web_search_modes`

Type / Values

`array<string>`

Details

Allowed values for `web_search` (`disabled`, `cached`, `live`). `disabled` is always allowed; an empty list effectively allows only `disabled`.

Key

`experimental_network`

Type / Values

`table`

Details

Network access requirements enforced from `requirements.toml`. These constraints are separate from `features.network_proxy` and can configure sandboxed networking without the user feature flag.

Key

`experimental_network.allow_local_binding`

Type / Values

`boolean`

Details

Permit broader local/private-network access for sandboxed networking. Exact local IP literal or `localhost` allow rules can still permit specific local targets when this stays `false`.

Key

`experimental_network.allow_upstream_proxy`

Type / Values

`boolean`

Details

Allow sandboxed networking to chain through an upstream proxy from the environment.

Key

`experimental_network.allowed_domains`

Type / Values

`array<string>`

Details

List-shaped administrator allow rules for sandboxed networking. Do not combine this with `experimental_network.domains`.

Key

`experimental_network.dangerously_allow_all_unix_sockets`

Type / Values

`boolean`

Details

Permit arbitrary Unix socket destinations instead of allowlist-only access. Use only in tightly controlled environments.

Key

`experimental_network.dangerously_allow_non_loopback_proxy`

Type / Values

`boolean`

Details

Permit non-loopback listener addresses for `[experimental_network]` requirements. Enabling it can expose listeners beyond localhost.

Key

`experimental_network.denied_domains`

Type / Values

`array<string>`

Details

List-shaped administrator deny rules for sandboxed networking. Do not combine this with `experimental_network.domains`.

Key

`experimental_network.domains`

Type / Values

`map<string, allow | deny>`

Details

Map-shaped administrator domain policy for sandboxed networking. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules; prefer scoped rules because `*` broadly opens public outbound access. `deny` wins on conflicts. Do not combine this with `experimental_network.allowed_domains` or `experimental_network.denied_domains`.

Key

`experimental_network.enabled`

Type / Values

`boolean`

Details

Enable sandboxed networking requirements. This does not grant network access when the active sandbox keeps command networking off.

Key

`experimental_network.http_port`

Type / Values

`integer`

Details

Loopback HTTP listener port to use for `[experimental_network]` requirements.

Key

`experimental_network.managed_allowed_domains_only`

Type / Values

`boolean`

Details

When `true`, only administrator-managed allow rules remain effective while sandboxed networking requirements are active; user allowlist additions are ignored. Without managed allow rules, user-added domain allow rules do not remain effective.

Key

`experimental_network.socks_port`

Type / Values

`integer`

Details

Loopback SOCKS5 listener port to use for `[experimental_network]` requirements.

Key

`experimental_network.unix_sockets`

Type / Values

`map<string, allow | deny>`

Details

Administrator-managed Unix socket policy for sandboxed networking.

Key

`features`

Type / Values

`table`

Details

Pinned feature values keyed by the canonical names from `config.toml` 's `[features]` table.

Key

`features.<name>`

Type / Values

`boolean`

Details

Require a specific canonical feature key to stay enabled or disabled.

Key

`features.browser_use`

Type / Values

`boolean`

Details

Set to `false` in `requirements.toml` to disable Browser Use and Browser Agent availability.

Key

`features.in_app_browser`

Type / Values

`boolean`

Details

Set to `false` in `requirements.toml` to disable the in-app browser pane.

Key

`guardian_policy_config`

Type / Values

`string`

Details

Managed Markdown policy instructions for automatic review. This takes precedence over local `[auto_review].policy`. Blank values are ignored.

Key

`hooks`

Type / Values

`table`

Details

Admin-enforced managed lifecycle hooks. Requires a managed hook directory and uses the same event schema as inline `[hooks]` in `config.toml`.

Key

`hooks.<Event>`

Type / Values

`array<table>`

Details

Matcher groups for a hook event such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, or `Stop`.

Key

`hooks.<Event>[].hooks`

Type / Values

`array<table>`

Details

Hook handlers for a matcher group. Command hooks are currently supported; prompt and agent hook handlers are parsed but skipped.

Key

`hooks.<Event>[].hooks[].commandWindows`

Type / Values

`string`

Details

Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted.

Key

`hooks.managed_dir`

Type / Values

`string (absolute path)`

Details

Directory containing managed hook scripts on macOS and Linux. Codex validates that it is absolute and exists before loading managed hooks.

Key

`hooks.windows_managed_dir`

Type / Values

`string (absolute path)`

Details

Directory containing managed hook scripts on Windows. Codex validates that it is absolute and exists before loading managed hooks.

Key

`mcp_servers`

Type / Values

`table`

Details

Allowlist of MCP servers that may be enabled. Both the server name (`<id>`) and its identity must match for the MCP server to be enabled. Any configured MCP server not in the allowlist (or with a mismatched identity) is disabled.

Key

`mcp_servers.<id>.identity`

Type / Values

`table`

Details

Identity rule for a single MCP server. Set either `command` (stdio) or `url` (streamable HTTP).

Key

`mcp_servers.<id>.identity.command`

Type / Values

`string`

Details

Allow an MCP stdio server when its `mcp_servers.<id>.command` matches this command.

Key

`mcp_servers.<id>.identity.url`

Type / Values

`string`

Details

Allow an MCP streamable HTTP server when its `mcp_servers.<id>.url` matches this URL.

Key

`permissions.filesystem.deny_read`

Type / Values

`array<string>`

Details

Admin-enforced filesystem read denials. Entries can be paths or glob patterns, and users cannot weaken them with local config.

Key

`plugin_sharing`

Type / Values

`boolean`

Details

Set to `false` in cloud-managed `requirements.toml` to disable workspace sharing for locally built plugins.

Key

`remote_sandbox_config`

Type / Values

`array<table>`

Details

Host-specific sandbox requirements. The first entry whose `hostname_patterns` match the resolved host name overrides top-level `allowed_sandbox_modes` for that requirements source. Host-specific entries currently override sandbox modes only.

Key

`remote_sandbox_config[].allowed_sandbox_modes`

Type / Values

`array<string>`

Details

Allowed sandbox modes to apply when this host-specific entry matches.

Key

`remote_sandbox_config[].hostname_patterns`

Type / Values

`array<string>`

Details

Case-insensitive host name patterns. Supports `*` for any sequence of characters and `?` for one character.

Key

`rules`

Type / Values

`table`

Details

Admin-enforced command rules merged with `.rules` files. Requirements rules must be restrictive.

Key

`rules.prefix_rules`

Type / Values

`array<table>`

Details

List of enforced prefix rules. Each rule must include `pattern` and `decision`.

Key

`rules.prefix_rules[].decision`

Type / Values

`prompt | forbidden`

Details

Required. Requirements rules can only prompt or forbid (not allow).

Key

`rules.prefix_rules[].justification`

Type / Values

`string`

Details

Optional non-empty rationale surfaced in approval prompts or rejection messages.

Key

`rules.prefix_rules[].pattern`

Type / Values

`array<table>`

Details

Command prefix expressed as pattern tokens. Each token sets either `token` or `any_of`.

Key

`rules.prefix_rules[].pattern[].any_of`

Type / Values

`array<string>`

Details

A list of allowed alternative tokens at this position.

Key

`rules.prefix_rules[].pattern[].token`

Type / Values

`string`

Details

A single literal token at this position.

Key

`windows.allowed_sandbox_implementations`

Type / Values

`array<string>`

Details

Allowed native Windows sandbox implementations for `windows.sandbox` (`elevated` and `unelevated`). The list must not be empty. When both are allowed and no mode is selected, Codex prefers `elevated`.

Configuration Reference – Codex | OpenAI Developers