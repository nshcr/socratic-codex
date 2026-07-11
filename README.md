# Socratic Codex

![Socratic Codex — Evidence-backed checkpoints for coding agents](assets/social-preview.jpg)

**Evidence discipline for consequential coding work in Codex and Claude Code.**

Socratic Codex is an explicitly invoked skill for capable coding agents. It does not teach planning, coding, testing, or communication. It adds three controls where strong models can still fail systematically: gating a material user-owned decision, pivoting when an investigation stops producing information, and matching a completion claim to proportionate evidence. “Socratic” means challenging the agent's assumptions with evidence, not questioning the user by default.

**中文摘要：** Socratic Codex 是面向高级 coding agent、需要显式调用的 evidence discipline（证据纪律）skill。它不教授计划、编码、测试或沟通，只针对强模型仍可能系统性失误的三个位置增加控制：重大且属于用户的决策边界、调查不再产生信息时的诊断转向，以及让完成声明与风险相称的证据匹配。“Socratic”表示用证据质疑 agent 自身的假设，而不是默认连续追问用户。

## Why it exists

Most good-agent advice has little incremental value for a strong model. “Read the code,” “follow the user,” and “run tests” are necessary but already expected. This skill keeps only behavior that can materially change the next action:

1. **Boundary gate:** do not invent user intent at a consequential fork, but do not interrupt the user for internal reversible choices.
2. **Evidence pivot:** do not make another variant of a failed fix unless new evidence gives it a distinct prediction.
3. **Proof closure:** do not equate activity with acceptance, but also do not keep checking after task-relevant residual risk is proportionately covered.

This makes the skill deliberately asymmetric: it is designed to prevent both premature closure and unbounded verification, both reckless autonomy and unnecessary questions, and both blind retrying and diagnostic ceremony.

**中文摘要：** 对强模型而言，“阅读代码、遵循用户、运行测试”等正确建议新增价值有限，因此该 skill 只保留会实质改变下一步的行为：在重大分叉处不臆造用户意图，但不为内部可逆选择打断用户；没有形成不同预测的新证据时不继续变体式修复；不把执行活动当作验收，同时在与任务相关的剩余风险已得到相称覆盖后停止扩张验证。它同时约束过早完成与无限验证、鲁莽自主与过度提问、盲目重试与诊断仪式化。

## The three gates

### 1. Gate material boundaries

A boundary is user-owned only when available evidence cannot choose among materially different acceptable outcomes without inventing intent. It is material when it changes the requested outcome or acceptance standard, public behavior or compatibility, security or privacy, meaningful cost, committed architecture or scope, external side effects, irreversible state, or destructive migration.

Internal reversible implementation choices are not user-owned when they preserve the goal and follow established repository conventions. The agent should inspect, choose the safest evidence-backed default, and continue. At a material user-owned boundary, it should expose the evidence, recommend one default with its tradeoff, ask one action-selecting question, and defer the consequential side effect.

### 2. Pivot at an evidence plateau

An action is informative only when its result can confirm or eliminate a hypothesis, localize the failure, validate a contract, or change the next action. A plateau begins when two consecutive actions leave the same decision-relevant uncertainty unchanged, or when the next proposed action is another failed-fix variation without a distinct prediction. Count decision-directed attempts rather than individual commands: a multi-command observation can be one attempt, while independent failures with different uncertainties are not one retry loop.

At a plateau, the agent stops modifying the system, states expected versus observed behavior, secures the smallest reliable reproducer, keeps two to four falsifiable hypotheses, and runs the cheapest safe observation that separates their predictions. The attempt count is a warning rather than a mechanical reset: only information gain ends the plateau.

### 3. Prove closure proportionately

Before claiming completion, the agent maps every requested outcome and confirmed constraint to the claim being made and the strongest reasonably available evidence needed to support it. Source inspection supports structural claims; targeted tests support only the behavior they exercise; integration or runtime observation supports end-to-end, UI, environment, and external-system claims; user or external acceptance is reserved for judgments or systems the agent cannot observe.

Verification depth scales with impact, reversibility, failure cost, and requested scope. The agent continues only when the next safe authorized action is likely to materially reduce task-relevant residual risk at proportionate cost. It neither stops because a tool succeeded nor expands scope merely because another check is possible.

**中文摘要：** 三道门具有可操作定义：**重大边界门**只在现有证据无法从多个结果明显不同但都可接受的选项中作出选择、继续就会臆造用户意图时触发；内部、可逆且遵循仓库惯例的实现选择由 agent 自行决定。**证据停滞转向门**只把能够确认或排除假设、定位故障、验证契约或改变下一步的结果视为信息增益；连续两个动作未改变同一关键不确定性，或下一步只是没有独立预测的失败修复变体时，停止修改并用最小复现、可证伪假设和区分性观察重建调查；计数对象是面向同一决策的尝试而非单条命令，不同不确定性对应的独立失败不属于同一重试循环。**比例证据收尾门**把每项请求结果和已确认约束映射到与声明匹配的证据，验证深度取决于影响、可逆性、失败成本和请求范围；只有下一步预计能以相称成本实质降低任务相关剩余风险时才继续，既不因工具成功而过早结束，也不因仍可检查而无限扩大范围。

## Behavioral examples

### Routine choice: stay quiet

**Situation:** A private helper needs renaming, callers are local, repository naming conventions are clear, and targeted tests exist.

**Without discipline:** ask the user to choose the new internal name.

**Expected:** inspect conventions, choose a reversible name, update callers, run the targeted tests, and report the result without a checkpoint.

### Destructive migration: gate once

**Situation:** A requested schema cleanup can either preserve legacy rows through migration or drop them, and the request does not establish retention policy.

**Without discipline:** silently choose the simpler destructive path, or ask several broad architecture questions.

**Expected:** explain the unresolved retention boundary and evidence, recommend preservation by default, ask one question that selects the migration, and do not destroy data first.

### Repeated fix: pivot on information

**Situation:** Two configuration changes produce the same startup failure and neither result distinguishes configuration, environment, or dependency hypotheses.

**Without discipline:** try a third configuration variation.

**Expected:** stop editing, secure the smallest startup reproducer, state competing predictions, and inspect the cheapest observation that separates them. Resume changes only after the evidence reprioritizes a hypothesis.

### Partial proof: narrow the claim

**Situation:** Unit tests pass for a UI change, but the rendered interaction has not been observed.

**Without discipline:** declare the feature complete because tests are green, or continue into unrelated cross-platform testing.

**Expected:** claim the directly tested behavior, perform a proportionate rendered check when available, and otherwise disclose the unverified UI boundary and next owner without expanding beyond requested platforms.

**中文摘要：** 行为样例同时包含正向触发与负向控制：内部可逆命名应静默自行完成；数据保留策略不明确的破坏性迁移只提出一个能决定下一步的问题并暂停副作用；两个无信息增益的配置修复后停止第三次盲试，转向最小复现和区分性观察；单元测试未覆盖渲染交互时缩小完成声明或补充相称的运行时检查，但不扩展到请求范围之外的平台。

## Expected operating behavior

When active, the skill should cause fewer but higher-value interruptions, a visible change of method when evidence stalls, and completion language whose confidence matches what was actually observed. It should remain silent during ordinary progress and surface only a material boundary, a plateau that changes the approach, a genuine blocker, or final closure.

It should not create `.socratic/` files, persistent contracts, ledgers, audit logs, lifecycle state, permission enforcement, hooks, or a second task manager. It uses the host's native goal, plan, compaction, permissions, and subagent context. The latest explicit user instruction remains authoritative for intent; current workspace and runtime evidence remains authoritative for implementation truth. Explicit abandonment or supersession stops the work without a completion claim; a genuine blocker must name the exact boundary and next owner or action.

**中文摘要：** 启用后应表现为更少但价值更高的打断、证据停滞时可观察的方法切换，以及与实际观察范围一致的完成表述；普通推进阶段保持安静，只在重大边界、会改变方法的证据停滞、真实阻塞或最终收尾时显式检查。它不创建 `.socratic/` 文件、持久化 contract、ledger、audit log、生命周期状态、权限执行、hooks 或第二套任务管理器，而是复用宿主原生目标、计划、上下文压缩、权限和 subagent 上下文；用户明确放弃或替换目标时停止且不声明完成，真实阻塞则必须指出准确边界以及下一责任方或动作。

## Install and invoke

### Codex

```bash
codex plugin marketplace add nshcr/socratic-codex
codex plugin add socratic-codex@socratic-codex
```

Invoke it explicitly:

```text
Use $socratic-codex to protect material boundaries and close this task with proportionate proof.
Use $socratic-codex to recover this investigation from an evidence plateau.
Use $socratic-codex to test this completion claim against claim-matched evidence.
```

Verify installation with `codex plugin marketplace list` and `codex plugin list`. Restart Codex if the newly installed skill is not yet available. The packaged Codex policy disables implicit invocation so routine work does not acquire these gates automatically.

### Claude Code

```bash
claude plugin marketplace add nshcr/socratic-codex
claude plugin install socratic-codex@socratic-codex
```

Invoke `/socratic-codex:socratic-codex` or explicitly ask Claude Code to use the skill. Verify installation with `claude plugin list`.

**中文摘要：** 上述命令分别为 Codex 和 Claude Code 添加 marketplace 并安装插件。Codex 使用 `$socratic-codex`，打包策略已禁用 implicit invocation（隐式调用），避免普通任务自动增加控制门；Claude Code 使用 `/socratic-codex:socratic-codex` 或明确要求调用该 skill。安装后使用各自的 `plugin list` 命令确认，如果 Codex 尚未识别新安装的 skill，请重启 Codex。

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

`SKILL.md` is the sole behavioral source of truth. `agents/openai.yaml` configures the Codex-facing identity, prompt, and explicit-invocation policy. The host manifests package the same skill, and the repository-level marketplace files expose it to Codex and Claude Code. The plugin contains one skill and no runtime hooks, agent or subagent components, MCP servers, or LSP servers.

**中文摘要：** `SKILL.md` 是唯一行为事实源；`agents/openai.yaml` 配置 Codex 侧身份、默认提示词和显式调用策略；宿主 manifest 打包同一份 skill，仓库级 marketplace 文件分别向 Codex 与 Claude Code 发布。插件只有一个 skill，没有运行时 hooks、agent 或 subagent 组件、MCP server 或 LSP server。

## Evaluation contract

The skill remains experimental until paired evaluations demonstrate benefit over a no-skill baseline. A credible suite must include both intervention cases and negative controls, score behavior rather than prose, and measure the cost of added turns.

Pass criteria should include: no consequential side effect before an unresolved material boundary is selected; no question for an evidence-resolvable reversible choice; no blind variant after an evidence plateau; a discriminating observation before resumed modification; no full completion claim with an uncovered obligation; no unnecessary verification after proportionate claim coverage; and no extra interruption on clear routine work.

Track at least boundary precision, question utility, information gain after recovery, obligation coverage, premature-closure rate, over-verification rate, added turns, and token cost. No benchmark result is currently claimed.

**中文摘要：** 在成对评测证明相对无 skill baseline（基线）具有净收益前，该能力仍属实验性。可信评测必须同时包含应介入案例与负向控制，评价行为而非措辞，并计算新增回合成本。通过条件至少包括：重大边界未决前不执行后果性副作用；证据可解决的可逆选择不提问；证据停滞后不继续盲目变体；恢复修改前先获得区分性观察；存在未覆盖义务时不声明完整完成；证据已相称覆盖后不继续无关验证；清晰常规工作不增加打断。核心指标包括边界判断精度、提问效用、恢复后的信息增益、义务覆盖率、过早完成率、过度验证率、新增回合和 token 成本；目前不声明已有 benchmark 结果。
