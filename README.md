# Socratic Codex

**Socratic Codex is a Codex plugin for keeping long-running work aligned with the user's actual goal.**

It is not a generic "ask better questions" prompt. It gives Codex a goal lifecycle: bind the intent, inspect before asking, checkpoint only at real user-owned boundaries, recover when work drifts, and close only with evidence.

**中文：** Socratic Codex 是一个 Codex plugin（插件），用来让长任务始终围绕用户真正想要的目标推进。它不是通用提问模板，而是给 Codex 加上一套 goal lifecycle（目标生命周期）控制：先绑定意图，能检查就先检查，只在真正需要用户决策的边界停下，发现漂移时重新校准，最后用证据收尾。

## Why "Socratic"

"Socratic" points to the discipline of using questions to expose assumptions, clarify intent, and test whether an answer is actually justified. In this plugin, that does not mean Codex should keep interrogating the user. It means Codex should question its own assumptions first, inspect available evidence, and ask the user only when the answer would change the next action.

**中文：** “Socratic” 指的是用问题暴露假设、澄清意图、检验答案是否真的站得住。放在这个插件里，它不是让 Codex 不停追问用户，而是要求 Codex 先质疑自己的假设、先检查可获得的证据，只在用户的答案会改变下一步行动时才提问。

## What it does

Socratic Codex changes how Codex handles work that has more than one obvious step.

- Turns a loose request into a compact goal contract.
- Separates facts Codex can inspect from choices only the user can make.
- Prevents plans, generated tests, or tool success from becoming false proof.
- Stops before risky scope, architecture, irreversible, or acceptance-boundary changes.
- Recovers from drift by re-reading the ask, the evidence, and the current repo state.
- Closes with what was verified, what remains assumed, and what still needs acceptance.

**中文：** 它会改变 Codex 处理多步骤任务的方式：把模糊请求压缩成目标契约；区分 Codex 能自己核查的事实和必须由用户决定的边界；避免把计划、测试或命令成功误当成完成证明；在风险边界前暂停；发生漂移时重新对齐原始请求、证据和当前代码；最终说明哪些已验证、哪些仍是假设、哪些需要用户验收。

## Why use it

Use it when the cost of a confident wrong answer is higher than the cost of one well-placed checkpoint.

It is useful for advanced Codex sessions where the model is capable enough to do real work, but still needs guardrails around goal drift, premature completion claims, and hidden assumption changes.

**中文：** 当“自信但错误地推进”比“在关键处停下来确认一次”代价更高时，就该用它。它尤其适合高级 Codex 会话：模型已经能做复杂工作，但仍需要防止目标漂移、过早声称完成、以及悄悄改变假设。

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

**中文：** 适合在 `/goal` 起草与推进、容易漂移的方案型请求、会影响后续工作的架构或目标变更、反复失败的诊断、风险编辑或不可逆副作用、最终验收等场景使用。不要把它用于单个确定命令、小型机械修改、或已经很清楚的常规实现任务。

## Install

From GitHub:

```bash
codex plugin marketplace add nshcr/socratic-codex
codex plugin add socratic-codex@socratic-codex
```

From a local checkout:

```bash
git clone https://github.com/nshcr/socratic-codex.git
cd socratic-codex
codex plugin marketplace add .
codex plugin add socratic-codex@socratic-codex
```

If the marketplace is already added, skip `codex plugin marketplace add ...` and run only `codex plugin add socratic-codex@socratic-codex`.

For Codex Desktop, install with the same CLI commands, then restart the app so it picks up the plugin.

**中文：** 通过 Codex CLI（命令行界面）安装时，先添加 marketplace（插件市场），再安装 `socratic-codex@socratic-codex`。如果 marketplace 已经添加过，只需要执行 `codex plugin add socratic-codex@socratic-codex`。Codex Desktop 使用同一套 CLI 安装命令，安装后重启应用即可。

## Use

Invoke it explicitly when you want lifecycle control:

```text
Use $socratic-codex to bind this goal.
Use $socratic-codex to steer this lifecycle.
Use $socratic-codex to close acceptance.
```

The plugin also allows implicit invocation, so Codex may use it automatically when a request clearly needs goal-lifecycle protection.

**中文：** 将本仓库作为 Codex plugin 安装或加载后，即可通过 `$socratic-codex` 显式调用。这个插件也允许 implicit invocation（隐式调用），所以当请求明显需要目标生命周期保护时，Codex 可以自动使用它。

## Verify

Check that the marketplace and plugin are visible:

```bash
codex plugin marketplace list
codex plugin list
```

You should see `socratic-codex@socratic-codex` as installed and enabled.

**中文：** 安装后可以用 `codex plugin marketplace list` 和 `codex plugin list` 检查。正常情况下，列表里会显示 `socratic-codex@socratic-codex` 已安装并启用。

## What happens after activation

Codex should become less eager to "just continue" when continuation would cross a user-owned boundary.

You should see behavior like:

- A compact goal slice before sustained work.
- Fewer speculative questions.
- More inspection of files, commands, tests, logs, and docs before asking you.
- Short checkpoints only when your answer changes the next action.
- Clear re-anchoring after "this is wrong", "go back", "stop", or drift signals.
- Completion claims tied to evidence instead of confidence.

**中文：** 激活后，Codex 不会在跨越用户拥有的决策边界时盲目继续。你应该看到更紧凑的目标切片、更少的空泛追问、更多先查文件/命令/测试/日志/文档的行为、只在答案会改变下一步时做短暂停顿、在收到“错了”“回到前面”“停止”等信号后重新对齐，以及用证据而不是信心来声明完成。

## Repository layout

```text
./.agents/plugins/marketplace.json
plugins/socratic-codex/
  .codex-plugin/plugin.json
  skills/socratic-codex/SKILL.md
  skills/socratic-codex/agents/openai.yaml
```

The source of truth is `skills/socratic-codex/SKILL.md`. Marketplace discovery starts at `.agents/plugins/marketplace.json`. Plugin display metadata lives in `.codex-plugin/plugin.json` and `agents/openai.yaml`.

**中文：** 核心行为以 `skills/socratic-codex/SKILL.md` 为准。marketplace 发现入口是 `.agents/plugins/marketplace.json`。插件展示与触发相关元数据在 `.codex-plugin/plugin.json` 和 `agents/openai.yaml` 中。
