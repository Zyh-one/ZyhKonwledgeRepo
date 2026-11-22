# 1.初识：

PD 分离（prefill-decode disaggregation）；TTFT / TPOT；goodput；prefill-decode interference；并行策略联合优化；放置算法

核心：prefill 与 decode 的计算特性和延迟目标完全不同，混在同一批 GPU 上既相互干扰、又把资源分配和并行方案绑死——拆到不同 GPU 上，能否提升「每 GPU 有效吞吐」？

## 1.1Abstract

现有系统把 prefill 和 decode 混部并一起 batching，问题有二：

1. **prefill-decode 干扰**：prefill 步通常远慢于 decode 步，混批时 decode 的 TPOT 被拉长；decode 混入也让 TTFT 变差；即便拆开调度，二者仍抢资源。
2. **资源耦合**：两阶段最优并行策略不同（prefill 吃算力，偏好小规模 TP/大规模并行；decode 吃带宽，偏好大 batch），混部无法各取所需。

DistServe 把两阶段分配到不同 GPU：

- 给定应用要求的 TTFT / TPOT，**联合优化**两阶段的 GPU 数量与并行策略，最大化 per-GPU goodput；
- 再按副本横向扩展满足流量；
- 按集群带宽做**放置**，降低中间状态（KV cache）传输开销。

评估：多种模型/应用/延迟约束下，可服务 **7.4×** 更多请求，或在同等负载下收紧 **12.6×** 的 SLO，同时 >90% 请求满足延迟约束。

```
混部（现有系统）                       PD 分离（DistServe）
GPU0..n: [prefill+decode 混批]         prefill 组（compute-bound）
   ↑ 互相拖慢、并行策略被迫折中            │  KV cache 点对点传输
                                        ▼
                                       decode 组（memory-bound，大 batch）
单 GPU goodput 1.6 rps                按带宽放置，减少跨机通信
```

论文给的对照数据（13B，单 A100，输入 512 / 输出 64）：混部 per-GPU goodput 约 1.6 rps；单独跑 prefill 5.6 rps、单独跑 decode 10 rps；按 2 卡 prefill + 1 卡 decode 分配，整体可达 10 rps，即 3.3 rps/GPU，约 2.1× 提升。

我的关注点：goodput 的定义要记牢——**在满足 SLO 达成率（如 90%）约束下每 GPU 能服务的最大请求速率**，它把「吞吐」和「延迟」合成单一优化目标，这是全篇评价体系的支点。

## 1.2Introduction

- 应用差异：实时聊天在乎 TTFT，文档摘要在乎 TPOT，系统必须按 SLO 配比资源，否则只能过度配置 GPU。
- 指标：请求延迟 ≈ TTFT + TPOT × 输出 token 数；两阶段各有 SLO。
- 两个根因：干扰（interference）与资源耦合（resource coupling），后者使「为某一阶段选更合适的并行方式」变得不可能。
- 方案：解耦 → 消除干扰 + 独立伸缩；代价是 KV 传输，但现代集群带宽下可忽略。
- 贡献三条：识别干扰与耦合问题、提出放置/配置联合优化算法、用三类真实应用（chatbot、编程助手、文档摘要）做完整评估。
- 待读：3.1 两阶段的 roofline/算力-带宽刻画、3.3 传输开销测量、4 节优化与放置算法。
