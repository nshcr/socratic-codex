# Socratic Codex

**Socratic Codex is an experimental agent plugin for keeping long-running work aligned with the user's actual goal. It ships for both Codex and Claude Code.**

It gives the agent a goal lifecycle: bind the intent, inspect before asking, checkpoint only at user-owned boundaries, recover when work drifts, and close only with evidence.

**中文摘要：** Socratic Codex 是一个实验性的 agent plugin，同时支持 Codex 和 Claude Code，用来让长任务始终围绕用户真正想要的目标推进。它给 agent 加上一套 goal lifecycle：绑定意图、先检查再提问、只在用户拥有的决策边界停下、漂移时重新校准，最后用证据收尾。

## Quick start

```bash
codex plugin marketplace add nshcr/socratic-codex
codex plugin add socratic-codex@socratic-codex
```

Then invoke it in a Codex session:

```text
Use $socratic-codex to bind this goal.
Use $socratic-codex to steer this lifecycle.
Use $socratic-codex to close acceptance.
```

Check installation:

```bash
codex plugin marketplace list
codex plugin list
```

You should see `socratic-codex@socratic-codex` as installed and enabled.
Restart Codex after installation. If you enable the bundled hooks, review and trust the Socratic Codex hook definitions in Codex before relying on them.

**中文摘要：** 先用 Codex CLI 添加 marketplace 并安装插件，然后在 Codex 会话中通过 `$socratic-codex` 显式调用。安装后可用 `codex plugin marketplace list` 和 `codex plugin list` 验证，正常情况下会看到 `socratic-codex@socratic-codex` 已安装并启用。安装后重启 Codex；如果启用随插件打包的 hooks，需要先在 Codex 中完成这些 hook 定义的 review 和 trust。

## Quick start (Claude Code)

```bash
claude plugin marketplace add nshcr/socratic-codex
claude plugin install socratic-codex@socratic-codex
```

Then invoke it in a Claude Code session:

```text
/socratic-codex
Use the socratic-codex skill to bind this goal.
Use the socratic-codex skill to close acceptance.
```

Claude Code can also invoke the skill implicitly based on its description. Check installation:

```bash
claude plugin list
```

The bundled hooks load automatically from the plugin's `hooks/hooks.json` when the plugin is enabled. Hook commands run with your user permissions, so review `hooks/socratic_hooks.py` before enabling if that matters in your environment.

**中文摘要：** Claude Code 用户用 `claude plugin marketplace add nshcr/socratic-codex` 添加 marketplace，再用 `claude plugin install socratic-codex@socratic-codex` 安装。会话中可用 `/socratic-codex` 显式调用，Claude Code 也会根据 skill 描述自动调用。插件启用后，打包的 hooks 会从 `hooks/hooks.json` 自动加载；hooks 以你的用户权限运行，建议先 review `hooks/socratic_hooks.py`。

## What it changes

Socratic Codex changes how Codex handles work that has more than one obvious step.

- Turns a loose request into a compact goal contract.
- Separates facts Codex can inspect from choices only the user can make.
- Prevents plans, generated tests, clean logs, or tool success from becoming false proof.
- Stops before risky scope, architecture, irreversible, or acceptance-boundary changes.
- Recovers from drift by re-reading the ask, the evidence, and the current workspace state.
- Closes with what was verified, what remains assumed, and what still needs acceptance.

**中文摘要：** 它会改变 Codex 处理多步骤任务的方式：把模糊请求压缩成目标契约；区分 Codex 能自己核查的事实和必须由用户决定的边界；避免把计划、生成的测试、干净日志或命令成功误当成完成证明；在风险边界前暂停；发生漂移时重新对齐原始请求、证据和当前工作区；最终说明哪些已验证、哪些仍是假设、哪些需要用户验收。

## Hook-backed guardrails

The plugin bundles lifecycle hooks that reinforce the same skill contract with deterministic state:

- **Contract persistence and restore.** The skill maintains the goal contract in `.socratic/contract.md` (contract, delta log, verification evidence). A `SessionStart` hook re-injects it after compaction or resume, so the contract of record survives context loss. Consider adding `.socratic/` to your local git excludes.
- **Behavioral acceptance gate.** The `Stop` hook keeps a per-session activity ledger (in the plugin data directory) and blocks a completion claim once when *no verification command ran this turn* and *the contract's Verification section was not updated this turn*. Saying "verified" is not enough; doing something verifiable is what counts. Word-face checking remains only as a fallback when the ledger is unavailable.
- **Boundary Gate before risky calls.** `PreToolUse` parses shell commands structurally (chains, substitutions, env prefixes) against a destructive-command table, and gates edits to sensitive plugin/agent config files (`plugin.json`, `hooks.json`, `settings.json`, `.mcp.json`, `config.toml`).
- **Lifecycle context, once.** `UserPromptSubmit` injects compact lifecycle context only on strong signals (`$socratic-codex`, `/goal`, acceptance/drift/rollback language) and only once per session; the flag resets after compaction.
- **Audit log.** Every hook intervention (injection or block) is appended to `audit.jsonl` in the plugin data directory, so you can inspect whether and how the guardrails actually fire.
- **Claude Code only: semantic acceptance gate.** A prompt-type `Stop` hook (in `hooks/claude.json`) asks a fast model to judge whether a completion claim cites concrete evidence. Codex parses but skips prompt-type hooks, so this layer activates only in Claude Code. It adds a small model call at turn end; disable the plugin if that cost matters more than the gate.

These hooks do not replace the skill's judgment and are not a complete security boundary. Codex cannot intercept `unified_exec` shell paths, and regex/parse-based gates can be bypassed; treat them as reminders at the points where the agent is most likely to start, cross a boundary, or stop too early. Codex requires users to review and trust plugin-bundled hooks before they run; Claude Code loads plugin hooks when the plugin is enabled.

**中文摘要：** hooks 现在带确定性状态：skill 把目标契约写入 `.socratic/contract.md`，`SessionStart` hook 在 compaction/resume 后自动恢复契约；`Stop` hook 维护会话级行为台账，只有当本回合既没跑过验证命令、也没更新契约的 Verification 段时才拦截完成声明（只说“已验证”不算数）；`PreToolUse` 用结构化解析而非单条正则识别危险命令；生命周期上下文每会话只注入一次；所有干预写入 audit 日志可事后审计。Claude Code 独享一层 prompt 型语义验收门（Codex 会解析但跳过）。这些 hooks 仍不是完整安全边界：Codex 的 `unified_exec` 路径无法拦截，解析门也可被绕过，它们是关键时点的提醒层而非强制层。

## Why use it

Use it when the cost of a confident wrong answer is higher than the cost of one well-placed checkpoint.

It is useful for advanced Codex sessions where the model is capable enough to do real work, but still needs guardrails around goal drift, premature completion claims, hidden assumption changes, and diagnostic loops that stop producing new evidence.

**中文摘要：** 当“自信但错误地推进”比“在关键处停下来确认一次”代价更高时，就该用它。它尤其适合高级 Codex 会话：模型已经能做复杂工作，但仍需要防止目标漂移、过早声称完成、悄悄改变假设，以及陷入不再产生新证据的诊断循环。

## When to use it

Use `$socratic-codex` for:

- `/goal` drafting, binding, and steering.
- Solution-shaped requests where scope can drift.
- Architecture or target changes that affect later work.
- Debugging sessions with repeated failures or contradictory evidence.
- Risky edits, migrations, teardown, or irreversible side effects.
- Final acceptance, handoff, or "is this actually done?" checks.

Skip it for:

- One deterministic command.
- Small mechanical edits with obvious acceptance.
- Routine implementation where the current task is already clear.

**中文摘要：** 适合在 `/goal` 起草与推进、容易漂移的方案型请求、会影响后续工作的架构或目标变更、反复失败的诊断、风险编辑或不可逆副作用、最终验收等场景使用。不要把它用于单个确定命令、小型机械修改、或已经很清楚的常规实现任务。

## What happens after activation

Codex should become less eager to "just continue" when continuation would cross a user-owned boundary.

You should see:

- A compact goal slice before sustained work.
- Fewer speculative questions.
- More inspection of files, commands, tests, logs, and docs before asking you.
- Short checkpoints only when your answer changes the next action.
- Clear re-anchoring after "this is wrong", "go back", "stop", or drift signals.
- Completion claims tied to evidence instead of confidence.

**中文摘要：** 激活后，Codex 不会在跨越用户拥有的决策边界时盲目继续。你应该看到更紧凑的目标切片、更少的空泛追问、更多先查文件/命令/测试/日志/文档的行为、只在答案会改变下一步时做短暂停顿、在收到“错了”“回到前面”“停止”等信号后重新对齐，以及用证据而不是信心来声明完成。

## Scope and status

Socratic Codex is experimental and intentionally narrow.

It is written for advanced models, usually GPT-5.5-class, Claude Sonnet 4.5-class, or stronger, where the model can already inspect evidence, maintain a compact goal contract, and choose when not to ask. Weaker models may follow the words while missing the judgment the plugin relies on.

This repository ships one plugin for two hosts: Codex (via `.codex-plugin/` and `.agents/plugins/marketplace.json`) and Claude Code (via `.claude-plugin/`). Both hosts load the same `SKILL.md` and the same hooks. The behavior still depends on host-specific skill loading, implicit invocation, goal-oriented collaboration, and how each host exposes tools, workspace state, approvals, and acceptance handoff. Porting the text is easy; preserving the behavior is the hard part, so treat non-Codex behavior as less validated.

There is no benchmark yet. The useful measurement is not whether the plugin sounds more careful, but whether it reduces real drift, bad checkpoints, unsupported completion claims, and wasted diagnostic loops in long-running work. That needs task traces and review criteria that are not ready yet.

**中文摘要：** 这个插件仍处于实验阶段，并且刻意保持窄范围：它主要面向高级推理模型。仓库现在同时发布 Codex 和 Claude Code 两套 plugin 入口，共用同一份 SKILL.md 和 hooks，但行为仍依赖各 host 的 skill 加载、implicit invocation、工具、工作区状态、审批和验收交接等运行环境；目前还没有 benchmark，真正要评估的是它能否在长任务中减少目标漂移、错误停顿、无证据完成声明和低效诊断循环。

## Why "Socratic"

"Socratic" points to the discipline of using questions to expose assumptions, clarify intent, and test whether an answer is actually justified.

In this plugin, that does not mean Codex should keep interrogating the user. It means Codex should question its own assumptions first, inspect available evidence, and ask the user only when the answer would change the next action.

**中文摘要：** “Socratic” 指的是用问题暴露假设、澄清意图、检验答案是否真的站得住。放在这个插件里，它不是让 Codex 不停追问用户，而是要求 Codex 先质疑自己的假设、先检查可获得的证据，只在用户的答案会改变下一步行动时才提问。

## Local checkout install

If you are installing from a local clone:

```bash
git clone https://github.com/nshcr/socratic-codex.git
cd socratic-codex
codex plugin marketplace add .
codex plugin add socratic-codex@socratic-codex
```

If the marketplace is already added, skip `codex plugin marketplace add ...` and run only `codex plugin add socratic-codex@socratic-codex`.

For Codex Desktop, install with the same CLI commands, then restart the app so it picks up the plugin.
Review and trust the bundled hooks after install if you want hook-backed guardrails to run.

For Claude Code, the same clone works:

```bash
claude plugin marketplace add .
claude plugin install socratic-codex@socratic-codex
```

**中文摘要：** 如果从本地 clone 安装，进入仓库后执行 `codex plugin marketplace add .` 和 `codex plugin add socratic-codex@socratic-codex`。如果 marketplace 已经添加过，只需要执行安装命令。Codex Desktop 使用同一套 CLI 安装命令，安装后重启应用即可；如果要运行随插件打包的 hook-backed guardrails，安装后还需要完成这些 hooks 的 review 和 trust。Claude Code 用户在同一份 clone 里执行 `claude plugin marketplace add .` 和 `claude plugin install socratic-codex@socratic-codex` 即可。

## Repository layout

```text
./.agents/plugins/marketplace.json    # Codex marketplace
./.claude-plugin/marketplace.json     # Claude Code marketplace
plugins/socratic-codex/
  .codex-plugin/plugin.json           # Codex plugin manifest
  .claude-plugin/plugin.json          # Claude Code plugin manifest
  hooks/hooks.json                    # Shared lifecycle hooks (both hosts)
  hooks/claude.json                   # Claude-only semantic acceptance gate
  hooks/socratic_hooks.py             # Hook logic: ledger, contract restore, audit
  skills/socratic-codex/SKILL.md      # Shared skill core (both hosts)
  skills/socratic-codex/references/   # Progressive-disclosure protocol details
  skills/socratic-codex/agents/openai.yaml
```

The source of truth is `skills/socratic-codex/SKILL.md`, with the full Diagnostic Recovery and Acceptance Close protocols split into `references/` so simple invocations pay less context. Hooks in `hooks/` are lifecycle guardrails aligned to that skill, not a second policy layer. Both hosts share `hooks/hooks.json`: its commands reference `${CLAUDE_PLUGIN_ROOT}`, which Claude Code sets natively and Codex sets for compatibility. `hooks/claude.json` is loaded only through the Claude manifest. Runtime state (session ledger, audit log) lives in the plugin data directory; the goal contract lives in the workspace at `.socratic/contract.md`. Codex marketplace discovery starts at `.agents/plugins/marketplace.json`; Claude Code discovery starts at `.claude-plugin/marketplace.json`.

**中文摘要：** 核心行为以 `skills/socratic-codex/SKILL.md` 为准，诊断与验收的完整协议拆到 `references/` 按需加载以降低简单任务的上下文成本。两个 host 共用 `hooks/hooks.json`（`${CLAUDE_PLUGIN_ROOT}` 双端兼容），`hooks/claude.json` 仅由 Claude manifest 加载。运行时状态（会话台账、审计日志）存在插件数据目录，目标契约存在工作区 `.socratic/contract.md`。Codex 的 marketplace 入口是 `.agents/plugins/marketplace.json`，Claude Code 的入口是 `.claude-plugin/marketplace.json`。
