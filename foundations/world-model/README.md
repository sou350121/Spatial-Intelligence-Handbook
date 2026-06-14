# World Models · Decision-Useful Slice Only

**Status:** v1 — opinionated lane intro. UNVERIFIED policy applies to all benchmark / latency claims downstream.
**Scope tier:** W2 lane（Cosmos + Genie 解构待真实世界 VLA 训练数据 delta 测出后再升 W1）。

---

World model 是 2025 年空间 AI 里最被过度宣称的品类。论文承诺"现实的模拟器"，demo 展示的是漂亮但 3 秒后就漂的视频。本仓本 lane 故意忽略约 70% 打着 "world model" 旗号的内容，**只保留能闭合到具身策略上的那一片**。每条入选都过两道闸门：(1) 它生成的数据 / 观测 / rollout，VLA / RL 策略能否真的消费？(2) 它能否撑过机器人会遇到的几何 / 时序合理性检查？任一答案为否，归类去生成式媒体综述，不入本仓。

严格的"only decision-useful"规则继承自项目 PRD：*Genie Sim 入选（它向 VLA 训练管线灌轨迹）；Marble 多数出局（它的目标用户是逛生成场景的人类，不是消费深度的机器人）*。我们解构 Cosmos 是看其 sim2real 数据生成路径；解构 Genie 是看其 action-conditional 推理时规划面；解构 Marble 仅限其 depth-from-video / NVS 这一片——策略可能用其作增广。任何"world model"本质上只是上下文更长的文本到视频，按本仓评分系统打 ❌ 标签，不写解构。

| File | Tier | Decision-useful angle |
|---|---|---|
| [`nvidia_cosmos_dissection.md`](./nvidia_cosmos_dissection.md) | W2 🔧 [WorldModel] | 机器人训练数据工厂（sim2real video synthesis） |
| [`genie_dissection.md`](./genie_dissection.md) | W2 ⚡ [WorldModel] | 推理时 action-conditional 规划器，**不是**数据源 |
| [`aether_dissection.md`](./aether_dissection.md) | [WorldModel] | geometry-aware 统一世界模型（4D 重建 + action-conditioned video + 规划），ICCV 2025 Outstanding |
| [`marble_decision_view.md`](./marble_decision_view.md) | W3 📖 [WorldModel] | depth-from-video + NVS 作策略数据增广；消费级 3D 场景生成显式排除 |
| [`github_failure_atlas.md`](./github_failure_atlas.md) | atlas | Cosmos / Genie / Marble 三线 repo 与产品页的 momentum + 失败模式（非 dissection）|

**Boundary**：单方法的物理真实度解构去 `foundations/physics/`；具身侧的"它真的有助于我的 VLA 吗？"等真实测量出来后去 `bridge-to-vla/` 与 `embodiments/manipulation/`。跨方法对比（Cosmos vs Genie vs UniSim vs DriveDreamer）归 `crossing/representation-migration/`——不在每篇解构里重复。

---

*Last lane review: 2026-05-21.*
