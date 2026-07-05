# Socratic Codex

**Socratic Codex is an experimental Codex plugin for keeping long-running work aligned with the user's actual goal.**

It gives Codex a goal lifecycle: bind the intent, inspect before asking, checkpoint only at user-owned boundaries, recover when work drifts, and close only with evidence.

**中文摘要：** Socratic Codex 是一个 experimental（实验性）的 Codex plugin（插件），用来让长任务始终围绕用户真正想要的目标推进。它给 Codex 加上一套 goal lifecycle（目标生命周期）：绑定意图、先检查再提问、只在用户拥有的决策边界停下、漂移时重新校准、最后用证据收尾。

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

**中文摘要：** 先用 Codex CLI（命令行界面）添加 marketplace（插件市场）并安装插件，然后在 Codex 会话中通过 `$socratic-codex` 显式调用。安装后可用 `codex plugin marketplace list` 和 `codex plugin list` 验证，正常情况下会看到 `socratic-codex@socratic-codex` 已安装并启用。

## What it changes

Socratic Codex changes how Codex handles work that has more than one obvious step.

- Turns a loose request into a compact goal contract.
- Separates facts Codex can inspect from choices only the user can make.
- Prevents plans, generated tests, clean logs, or tool success from becoming false proof.
- Stops before risky scope, architecture, irreversible, or acceptance-boundary changes.
- Recovers from drift by re-reading the ask, the evidence, and the current workspace state.
- Closes with what was verified, what remains assumed, and what still needs acceptance.

**中文摘要：** 它会改变 Codex 处理多步骤任务的方式：把模糊请求压缩成目标契约；区分 Codex 能自己核查的事实和必须由用户决定的边界；避免把计划、生成的测试、干净日志或命令成功误当成完成证明；在风险边界前暂停；发生漂移时重新对齐原始请求、证据和当前工作区；最终说明哪些已验证、哪些仍是假设、哪些需要用户验收。

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

It is written for advanced Codex models, usually GPT-5.5-class or stronger, where the model can already inspect evidence, maintain a compact goal contract, and choose when not to ask. Weaker models may follow the words while missing the judgment the plugin relies on.

This repository only ships a Codex plugin for now. The behavior depends on Codex-specific skill loading, implicit invocation, goal-oriented collaboration, and the way Codex exposes tools, workspace state, approvals, and acceptance handoff. Porting the text to another agent is easy; preserving the behavior is the hard part.

There is no benchmark yet. The useful measurement is not whether the plugin sounds more careful, but whether it reduces real drift, bad checkpoints, unsupported completion claims, and wasted diagnostic loops in long-running work. That needs task traces and review criteria that are not ready yet.

Support for more agents may wait until the plugin's effectiveness can be evaluated correctly inside Codex. Until then, adding more agent targets would mostly create maintenance surface without proving that the protocol transfers well.

**中文摘要：** 这个插件仍处于实验阶段，并且刻意保持窄范围：它主要面向 GPT-5.5 级别或更强的高级 Codex 模型，暂时只发布 Codex plugin，因为它依赖 Codex 的 skill 加载、implicit invocation（隐式调用）、工具/工作区/审批/验收交接等运行环境；目前没有 benchmark（基准测试），真正要评估的是它能否在长任务中减少目标漂移、错误停顿、无证据完成声明和低效诊断循环。在能正确评估 Codex 内效果之前，可能不会接受更多 agent 支持，以免只扩大维护面却无法证明协议可迁移。

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

**中文摘要：** 如果从本地 clone 安装，进入仓库后执行 `codex plugin marketplace add .` 和 `codex plugin add socratic-codex@socratic-codex`。如果 marketplace 已经添加过，只需要执行安装命令。Codex Desktop 使用同一套 CLI 安装命令，安装后重启应用即可。

## Repository layout

```text
./.agents/plugins/marketplace.json
plugins/socratic-codex/
  .codex-plugin/plugin.json
  skills/socratic-codex/SKILL.md
  skills/socratic-codex/agents/openai.yaml
```

The source of truth is `skills/socratic-codex/SKILL.md`. Marketplace discovery starts at `.agents/plugins/marketplace.json`. Plugin display metadata lives in `.codex-plugin/plugin.json` and `agents/openai.yaml`.

**中文摘要：** 核心行为以 `skills/socratic-codex/SKILL.md` 为准。marketplace 发现入口是 `.agents/plugins/marketplace.json`。插件展示与触发相关元数据在 `.codex-plugin/plugin.json` 和 `agents/openai.yaml` 中。
