# Socratic Codex

![Socratic Codex — Evidence-backed checkpoints for coding agents](assets/social-preview.jpg)

**A compact checkpoint policy that keeps long-running coding goals aligned, moving, and evidence-backed in Codex and Claude Code.**

Socratic Codex is a skill for capable coding agents, not a task manager or a general coding tutorial. It intervenes only where an explicit control policy can improve the order of action: preserving intent, deciding at consequential boundaries, escaping stalled diagnosis, and closing against observed evidence. It relies on the host for state, permissions, context continuity, plans, and subagent handoff.

**中文摘要：** Socratic Codex 是面向高级 coding agent 的紧凑 checkpoint policy（检查点策略），不是任务管理器或通用编码教程。它只在明确策略能够改善行动顺序的关键位置介入：保留用户意图、在重大边界前作出判断、摆脱停滞诊断，以及依据观察证据完成验收；状态、权限、上下文连续性、计划和 subagent 交接均由宿主原生能力负责。

## Why use it

Strong models can inspect code, plan, implement, test, and communicate without another procedural framework. They can still drift during sustained work: a plan can silently replace the requested outcome, an avoidable question can interrupt safe progress, repeated fixes can stop producing information, or a partial result can be presented as complete. Socratic Codex adds four narrow checkpoints to reduce those failures without duplicating the host runtime.

Its central invariant is simple: continue while a safe, authorized action can reduce uncertainty or satisfy an unmet outcome; stop only at evidenced completion, explicit abandonment or supersession, or a genuine user-owned blocker.

**中文摘要：** 高级模型不需要另一套编码流程，但持续任务仍可能出现目标被计划悄然替代、可自行核查的问题反复打断用户、修复尝试不再产生信息，或把部分结果当作完成等偏差。Socratic Codex 用四个窄范围检查点降低这些风险，其核心不变量是：只要仍有安全且已授权的动作能够减少不确定性或满足未完成目标，就继续推进；只有在证据已完成验收、用户明确放弃或替换目标，或遇到真正属于用户决策的阻塞边界时才停止。

## When to use it

Use it when one or more of these conditions apply:

- a long-running goal may drift in scope, constraints, or acceptance;
- the user corrects the direction or evidence contradicts the current plan;
- repeated failures require a disciplined diagnostic reset;
- work may stop after partial progress while safe authorized actions remain;
- the next step changes scope, architecture, external side effects, irreversible state, verification, or acceptance criteria;
- final acceptance or handoff must distinguish observed, inferred, assumed, and unverified results.

Skip it for a deterministic command, a small mechanical edit with obvious acceptance, or routine work whose goal and verification path are already clear. Explicit invocation is recommended so clear tasks do not acquire unnecessary checkpoints.

**中文摘要：** 适合容易发生范围、约束或验收漂移的持续任务，用户纠偏或证据冲突，反复失败后的诊断重置，仍有安全且已授权动作却可能过早停止的工作，涉及范围、架构、外部副作用、不可逆状态、验证或验收标准的重大变化，以及必须区分已观察、推断、假设和未验证结果的最终验收或交接。单个确定命令、验收显而易见的小型机械修改和路径清楚的常规工作无需启用；建议显式调用，避免为清晰任务增加不必要的检查点。

## How it works

The skill changes the agent's action order at four checkpoints:

1. **Preserve:** retain only the intended outcome, confirmed boundaries and constraints, evidence still required for acceptance, and the next unresolved choice that would change the action. Current workspace evidence outranks plans, summaries, memory, generated tests, and assumptions.
2. **Decide:** inspect available evidence before asking. Ask only when the answer belongs to the user and changes the next action; otherwise choose the safest reversible default that preserves the goal. Re-evaluate before consequential boundary changes.
3. **Recover:** after two attempts produce no useful evidence, stop varying the fix. Capture expected versus observed behavior, secure the smallest reproducer, form two to four falsifiable hypotheses, and run the cheapest observation that separates them. Do not make a third blind attempt.
4. **Close:** keep working while a safe authorized action can reduce uncertainty or satisfy an unmet outcome. Before claiming completion, map every requested outcome and confirmed constraint to observed evidence; state any remaining unverified result and its owner explicitly.

Tests count only for behavior they directly exercise. Tool success, clean logs, a completed plan, confident prose, a progress update, or the end of a turn is not acceptance by itself.

**中文摘要：** 该 skill 在四个检查点改变 agent 的行动顺序：**Preserve（保留）**仅保留目标、已确认边界与约束、验收仍需的证据，以及会改变下一步的待定选择，且当前工作区证据优先于计划、摘要、记忆、生成的测试和假设；**Decide（判断）**先核查再提问，只有答案属于用户且会改变下一步时才询问，否则采用最安全、可逆且不偏离目标的默认方案，并在重大边界变化前重新判断；**Recover（恢复）**在两次尝试均未产生有效证据后停止换一种修法，记录预期与实际行为、建立最小复现、提出两到四个可证伪假设，再执行成本最低且能区分假设的观察，禁止第三次盲试；**Close（收尾）**只要安全且已授权的动作仍能降低不确定性或满足未完成目标就继续，完成前逐项把请求结果和已确认约束映射到观察证据，并明确说明仍未验证的内容及其责任方。测试只能证明其直接覆盖的行为；工具成功、日志干净、计划完成、自信表述、进度汇报或回合结束本身都不等于验收完成。

## Expected behavior

When the skill is active, expect the agent to:

- preserve the latest explicit instruction without turning assumptions into requirements;
- inspect files, callers, tests, logs, runtime state, and authoritative documentation before asking for information;
- keep checkpoints concise: boundary, evidence, decision, and next action;
- react to correction by discarding plan inertia and making the smallest alignment-restoring change;
- replace repeated speculative fixes with a falsifiable diagnostic path;
- continue through safe authorized work instead of handing off prematurely;
- close with evidence for each requested outcome and disclose every unverified boundary.

Do not expect persistent contract files, ledgers, audit logs, lifecycle state, permission enforcement, or automatic activation. The skill intentionally delegates those concerns to the host and does not create `.socratic/` artifacts unless the user separately requests a durable artifact.

**中文摘要：** 启用后，agent 应保留最新明确指令且不把假设升级为要求，提问前核查文件、调用方、测试、日志、运行时状态和权威文档，以“边界、证据、判断、下一步”简洁表达检查点，收到纠偏后放弃既有计划惯性并作最小校正，用可证伪诊断替代重复猜测，在安全且已授权的范围内持续推进，最后为每项请求结果提供证据并披露所有未验证边界。它不会提供持久化 contract、ledger、audit log、生命周期状态、权限执行或自动启用，也不会自行创建 `.socratic/` 文件；这些职责属于宿主，除非用户另行要求生成持久化产物。

## Install and invoke

### Codex

```bash
codex plugin marketplace add nshcr/socratic-codex
codex plugin add socratic-codex@socratic-codex
```

Invoke the skill explicitly in the request:

```text
Use $socratic-codex to carry this goal through evidence-backed acceptance.
Use $socratic-codex to recover this stuck investigation.
Use $socratic-codex to close this request against evidence.
```

Verify installation with `codex plugin marketplace list` and `codex plugin list`. Restart Codex if the newly installed skill is not yet available. Implicit invocation is disabled by the packaged Codex policy.

### Claude Code

```bash
claude plugin marketplace add nshcr/socratic-codex
claude plugin install socratic-codex@socratic-codex
```

Invoke `/socratic-codex:socratic-codex` or explicitly ask Claude Code to use the skill. Verify installation with `claude plugin list`.

**中文摘要：** 上述命令分别为 Codex 和 Claude Code 添加 marketplace 并安装插件。Codex 在请求中使用 `$socratic-codex`，其打包策略已禁用 implicit invocation（隐式调用）；Claude Code 使用 `/socratic-codex:socratic-codex` 或明确要求调用该 skill。安装后使用各自的 `plugin list` 命令确认；如果 Codex 尚未识别新安装的 skill，请重启 Codex。

## Local development install

```bash
git clone https://github.com/nshcr/socratic-codex.git
cd socratic-codex
codex plugin marketplace add .
codex plugin add socratic-codex@socratic-codex
```

For Claude Code, run `claude plugin marketplace add .` and then `claude plugin install socratic-codex@socratic-codex` from the repository root.

**中文摘要：** 本地开发安装时，clone 仓库并进入根目录，将当前目录作为本地 marketplace 添加到对应宿主，再安装 `socratic-codex@socratic-codex`。

## Architecture and source of truth

```text
./.agents/plugins/marketplace.json
./.claude-plugin/marketplace.json
plugins/socratic-codex/
  .codex-plugin/plugin.json
  .claude-plugin/plugin.json
  skills/socratic-codex/
    SKILL.md
    agents/openai.yaml
```

`SKILL.md` is the sole behavioral source of truth. `agents/openai.yaml` configures the Codex-facing name, prompt, and explicit-invocation policy. The Codex and Claude Code manifests package the same skill, while the two repository-level marketplace files expose it to their respective hosts. The plugin currently contains one skill and no hooks, agents, MCP servers, or LSP servers.

Previous releases included lifecycle hooks. They were removed because keyword and command matching could not establish goal state or prove acceptance, persisted state could become stale, permission tables duplicated host controls, and contract injection duplicated native context and handoff. A future runtime component should be added only for an observable host gap supported by traces, a deterministic predicate, and a failure mode safer than pass-through.

**中文摘要：** `SKILL.md` 是唯一行为事实源；`agents/openai.yaml` 配置 Codex 侧的名称、默认提示词和显式调用策略；Codex 与 Claude Code 的 manifest 打包同一份 skill，仓库根目录的两个 marketplace 文件分别负责向对应宿主发布。插件当前只有一个 skill，没有 hooks、agents、MCP server 或 LSP server。旧版生命周期 hooks 已被移除，因为关键词和命令匹配既无法可靠判断目标状态或证明验收，持久化状态也可能过期，权限表和 contract 注入还会重复宿主原生能力；只有当 trace 证明存在可观察的宿主缺口、判断条件确定且失败模式比直接放行更安全时，才应增加新的运行时组件。

## Scope and evaluation

Socratic Codex is intentionally narrow and experimental. Evaluate it with paired task traces rather than prose quality. Useful measures include goal-changing actions taken without user-owned confirmation, questions that did not change the next action, third blind attempts in a diagnostic loop, premature handoffs while safe authorized actions remained, completion claims with uncovered outcomes, and added turns or interruptions on clear routine work. No benchmark is currently claimed.

**中文摘要：** Socratic Codex 是刻意保持窄范围的实验性能力，应通过成对任务 trace 而非文案质量评估。可观察指标包括未经用户确认便改变目标的动作、不影响下一步的无效提问、诊断中的第三次盲试、仍有安全且已授权动作时的过早交接、存在未覆盖结果的完成声明，以及对清晰常规任务增加的回合或打断；目前不声明已有 benchmark（基准测试）结果。
