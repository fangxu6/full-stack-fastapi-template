```
docs/
├── specs/
│   ├── feature-001-checkin/              # 一个 feature 一个目录
│   │   ├── 00_context.md                 # 可选：一次性上下文（业务背景/现状/约束）
│   │   ├── 01_requirement.md             # 需求意图（PM/业务/Owner）
│   │   ├── 02_interface.md               # 接口契约（前后端/客户端共同协议）
│   │   ├── 03_implementation.md          # 实施细节（AI Coder 执行指令）
│   │   └── 04_test_spec.md               # 测试策略与用例（QA/Test Agent）
├── decisions/
│   ├── AI_CHANGELOG.md                   # 决策与变更日志（审计/追溯）
│   └── ADR-xxxx.md                       # 可选：重大架构决策记录
├── skills/
│   └── SKILL.md                          # 团队规则库/“家规”（防复发）
└── logs/
    └── ai-review-reports/                # 可选：每次 Review 报告归档
```
