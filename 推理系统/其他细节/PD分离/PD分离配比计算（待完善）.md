# P/D 分离配比计算实验操作文档

## 1. 文档目标

本文档用于在实际 P/D 分离推理服务中，通过可重复的压测实验，标定单个 Prefill 实例和单个 Decode 实例的有效处理能力，并据此计算初始 P/D 配比。

实验最终目标不是将某一侧设备算力利用率拉满，而是找到：

> 在目标 TTFT、TPOT 和请求成功率约束下，Prefill 与 Decode 两侧处理能力基本匹配，且系统 Goodput 最大的资源配比。

---

## 2. 核心原则

### 2.1 不以设备算力利用率作为唯一判断标准

Decode 阶段可能受以下因素限制：

- 显存或内存带宽；
- KV Cache 访问；
- Decode step 时延；
- Tensor Parallel 通信；
- Scheduler 调度；
- KVConnector 等待；
- 活跃序列数量。

因此，即使设备计算利用率没有达到 100%，只要出现以下现象，实例仍可能已经达到能力边界：

1. 输入压力继续增加；
2. 有效吞吐不再明显增加；
3. waiting queue 持续增长；
4. P99 TTFT 或 P99 TPOT 明显恶化。

### 2.2 单 P、单 D 分别标定，完整链路最终验证

单侧标定用于得到：

- 单个 Prefill 实例有效能力 `μP`；
- 单个 Decode 实例有效能力 `μD`。

随后计算初始配比，并使用完整 P/D 链路验证。

### 2.3 前期只保留三个工作负载变量

第一阶段只控制：

- 输入长度；
- 输出长度；
- 请求到达速率 RPS。

其他条件全部固定，不作为前期实验变量。

---

## 3. 实验环境固定项

在开始压测前，记录并固定以下配置：

```text
模型名称及版本：
量化方式：
设备型号：
Prefill TP / DP：
Decode TP / DP：
max_model_len：
Prefill max_num_seqs / max_running_requests：
Decode max_num_seqs / max_running_requests：
Prefill max_num_batched_tokens：
Decode max_num_batched_tokens：
gpu_memory_utilization / 等效参数：
KVConnector 类型及配置：
P/D 节点网络路径：
请求超时时间：
Prefix Cache 状态：
压测工具及版本：
```

压测过程中，不要同时修改实例参数和 RPS，否则无法判断性能变化来自参数调整还是负载变化。

---

## 4. 基准工作负载设计

前期只设计三种固定长度场景。

| 场景 | 输入长度 | 输出长度 | 主要用途 |
|---|---:|---:|---|
| Prefill-heavy | 例如 64K | 128 | 标定单 P 能力 |
| Decode-heavy | 例如 4K | 2K | 标定单 D 能力 |
| 综合场景 | 例如 64K | 2K | 验证候选 P/D 配比 |

以上长度应根据当前业务实际范围调整，但实验期间必须保持固定。

### 4.1 RPS 阶梯

根据模型和硬件能力，从较低压力开始逐步提高，例如：

```text
0.05 → 0.1 → 0.2 → 0.4 → 0.6 → 0.8 → 1.0 RPS
```

对于超大模型或长输出场景，可以使用更细的低 RPS 阶梯：

```text
0.01 → 0.02 → 0.05 → 0.1 → 0.15 → 0.2 RPS
```

每一档压力都必须运行到系统进入稳态，并覆盖多轮完整请求生命周期。

建议：

- 短输出场景：每档至少 5～10 分钟；
- 长输出场景：至少覆盖 30～100 个完整请求；
- 观察 waiting queue 是否能够回落，而不是只看瞬时峰值。

---

## 5. Prefix Cache 处理方式

### 5.1 Prefix Cache 的含义

当多个请求具有相同 Prompt 前缀时，推理引擎可以直接复用已经计算完成的前缀 KV Cache，只计算新增部分。

例如：

```text
总输入长度：64K token
可复用前缀：48K token
实际新增 Prefill：16K token
```

Prefix Cache 主要降低 Prefill 工作量，但不会同比降低 Decode 的输出工作量，因此高命中率会使系统配比向更多 Decode 实例倾斜。

### 5.2 第一阶段实验要求

基础能力标定阶段应保证：

```text
Prefix Cache 命中率 = 0%
```

推荐方法：

- 关闭 Automatic Prefix Caching；
- 每个请求使用不同的随机前缀；
- 不要让压测请求共享长系统提示词；
- 每轮实验前重启实例或清理缓存；
- 确认监控指标中的 Prefix Cache hit 为 0 或接近 0。

否则，测得的单 P 能力会被高估。

---

## 6. 监控指标

### 6.1 服务质量指标

- P50 / P95 / P99 TTFT；
- P50 / P95 / P99 TPOT；
- P50 / P95 / P99 E2E latency；
- 请求成功率；
- 请求超时率；
- 请求 abort 率；
- SLO 达标率。

### 6.2 Prefill 侧指标

- Prefill waiting requests；
- Prefill running requests；
- Prompt / input token throughput；
- Prefill batch 执行时间；
- Prefill 计算时间；
- KV 生成完成速率；
- KV 发送等待时间；
- KV transfer latency；
- KV transfer bytes/s。

### 6.3 Decode 侧指标

- Decode waiting requests；
- Decode running requests；
- 活跃序列数量；
- output token throughput；
- Decode step latency；
- KV Cache usage；
- TPOT；
- 抢占、重计算或 eviction 次数。

### 6.4 系统和链路指标

- 设备计算利用率；
- 显存或内存使用率；
- 显存或内存带宽利用率；
- P/D 节点间网络带宽；
- RDMA 带宽和错误计数；
- KVConnector 队列和错误日志；
- Gateway 请求排队和路由耗时。

---

## 7. 单个 Prefill 实例能力标定

## 7.1 实验目标

测量单个 Prefill 实例在以下条件下的最大稳定处理能力：

- P99 TTFT 满足目标；
- Prefill waiting queue 不持续增长；
- KV 能够稳定交付给 Decode；
- Decode 侧不是瓶颈。

## 7.2 部署方式

固定：

```text
1 个 Prefill + 多个 Decode
```

逐步增加 Decode 数量，例如：

```text
1P:1D
1P:2D
1P:4D
```

目的是使 Decode 总能力明显高于单 P 能力。

注意：增加 Decode 数量只能排除 Decode 计算瓶颈，不能自动排除 KVConnector 或网络瓶颈。

## 7.3 工作负载

```text
输入长度：64K（或业务代表性长输入）
输出长度：128（短输出）
Prefix Cache：0% 命中
变量：仅 RPS
```

## 7.4 操作步骤

1. 启动 `1P:1D` 服务并完成预热。
2. 从最低 RPS 开始压测。
3. 每档压力运行到稳态。
4. 记录 Prefill、Decode、KVConnector 和网络指标。
5. 若 Decode 出现排队或 TPOT 明显恶化，增加 Decode 数量。
6. 重复实验，直到增加 Decode 不再显著提升系统吞吐。
7. 检查 KV transfer latency 是否稳定。
8. 找到 Prefill throughput 平台点和 Prefill queue 发散点。

## 7.5 Prefill 达到能力边界的判据

以下现象同时出现时，可以认为单 P 接近能力边界：

- RPS 继续增加；
- Prompt token throughput 基本不再增加；
- Prefill waiting queue 持续增加且不能回落；
- P99 TTFT 出现明显拐点；
- Decode waiting queue 较低；
- Decode TPOT 保持稳定；
- KV transfer latency 没有明显发散；
- 网络吞吐没有提前达到平台。

### 7.6 结果记录表

| RPS | 成功 RPS | Input tok/s | P99 TTFT | P waiting | KV transfer P99 | D waiting | 结论 |
|---:|---:|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

### 7.7 单 P 有效能力

定义：

```text
μP = 最后一个同时满足 TTFT SLO、队列稳定、KV 正常交付的 RPS
```

也可记录 token 维度能力：

```text
CP = μP × 平均输入 token 数
```

生产使用时不建议直接使用极限值，可以保留 15%～25% 余量：

```text
μP_effective = μP × 0.75～0.85
```

---

## 8. 单个 Decode 实例能力标定

## 8.1 实验目标

测量单个 Decode 实例在以下条件下的最大稳定处理能力：

- P99 TPOT 满足目标；
- Decode waiting queue 不持续增长；
- output token throughput 未明显进入平台；
- Prefill 和 KV 传输不是瓶颈。

## 8.2 部署方式

固定：

```text
多个 Prefill + 1 个 Decode
```

逐步增加 Prefill 数量，例如：

```text
1P:1D
2P:1D
4P:1D
```

目的是使 Prefill 总能力明显高于单 D 能力。

## 8.3 工作负载

```text
输入长度：4K（或业务代表性短输入）
输出长度：2K（长输出）
Prefix Cache：固定为 0% 命中
变量：仅 RPS
```

## 8.4 操作步骤

1. 启动 `1P:1D` 服务并完成预热。
2. 从最低 RPS 开始压测。
3. 每档压力运行到足够多请求完整结束。
4. 记录 Decode running、waiting、TPOT 和 output token throughput。
5. 若 Prefill waiting 增长或 TTFT 明显恶化，增加 Prefill 数量。
6. 重复实验，直到 Prefill 明显不是瓶颈。
7. 检查 KV 是否能及时到达 Decode。
8. 找到 output throughput 平台点和 Decode queue 发散点。

## 8.5 Decode 达到能力边界的判据

以下现象同时出现时，可以认为单 D 接近能力边界：

- RPS 继续增加；
- output token throughput 基本不再增加；
- Decode waiting queue 持续增加；
- Decode running requests 长期处于高位；
- P99 TPOT 明显恶化；
- KV Cache usage 接近高位；
- Prefill waiting queue 较低；
- Prefill TTFT 保持稳定；
- KV 接收等待时间没有明显发散。

### 8.6 结果记录表

| RPS | 成功 RPS | Output tok/s | P99 TPOT | D running | D waiting | KV usage | 结论 |
|---:|---:|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

### 8.7 单 D 有效能力

定义：

```text
μD = 最后一个同时满足 TPOT SLO、队列稳定的 RPS
```

也可记录 token 维度能力：

```text
CD = μD × 平均输出 token 数
```

生产使用时保留余量：

```text
μD_effective = μD × 0.75～0.85
```

---

## 9. KVConnector 瓶颈识别

## 9.1 为什么必须单独判断

完整 P/D 链路的实际能力为：

```text
min(Prefill 计算能力, KVConnector 能力, 网络能力, Decode 能力)
```

因此，仅增加另一侧节点数量，不能保证测到的是目标实例的纯计算能力。

## 9.2 KVConnector 可能成为瓶颈的表现

- Prefill 计算已经完成，但 KV 长时间未交付；
- KV transfer latency 随 RPS 快速上升；
- KV 发送队列持续增长；
- Decode 设备利用率较低，但请求迟迟不能开始生成；
- 增加 Decode 数量没有明显提升吞吐；
- P/D 网络带宽进入平台；
- RDMA 出现错误、重试或拥塞；
- 请求超时集中发生在 Prefill 完成到 Decode 开始之间。

## 9.3 对照实验

固定：

```text
1P
相同输入长度
相同 RPS
```

改变：

```text
1P:1D → 1P:2D → 1P:4D
```

判断：

### 情况 A：P 成为瓶颈

- 1D 到 2D 吞吐提升；
- 2D 到 4D 吞吐不再明显提升；
- Prefill 已饱和；
- KV transfer latency 稳定。

### 情况 B：KVConnector 或网络成为瓶颈

- 增加 D 后吞吐几乎不变；
- D 大量空闲；
- KV transfer latency 很高或持续增加；
- 网络吞吐达到平台。

### 情况 C：D 仍然不足

- 增加 D 后吞吐仍持续明显增加；
- P 尚未出现吞吐平台；
- 说明还没有进入单 P 标定条件。

---

## 10. 初始 P/D 配比计算

假设：

```text
单 P 有效能力 = μP requests/s
单 D 有效能力 = μD requests/s
```

要承接相同请求流，需要满足：

```text
NP × μP ≥ λ
ND × μD ≥ λ
```

初始配比可计算为：

```text
P:D ≈ μD:μP
```

等价表达：

```text
每 1 个 P 需要的 D 数量 ≈ μP / μD
```

示例：

```text
μP = 0.6 RPS
μD = 0.2 RPS
```

则：

```text
每 1 个 P 大约需要 3 个 D
初始配比约为 P:D = 1:3
```

### 10.1 按目标 RPS 计算节点数量

目标请求速率为 `λ_target` 时：

```text
NP = ceil(λ_target / μP_effective)
ND = ceil(λ_target / μD_effective)
```

其中 `μP_effective`、`μD_effective` 已包含容量余量。

---

## 11. 候选配比完整链路验证

初始配比只是理论起点，必须通过综合场景验证。

例如初始计算得到：

```text
P:D = 1:3
```

建议测试：

```text
1P:2D
1P:3D
1P:4D
2P:5D
2P:6D
```

### 11.1 综合工作负载

```text
输入长度：64K
输出长度：2K
Prefix Cache：0%
变量：RPS
```

完成基础验证后，再引入真实业务长度分布和真实 Prefix Cache 命中率。

### 11.2 Goodput 定义

```text
Goodput = 单位时间内同时满足 TTFT、TPOT 和成功完成条件的请求数量
```

### 11.3 最终选择标准

选择同时满足以下条件的最小资源配置：

- P99 TTFT 满足目标；
- P99 TPOT 满足目标；
- 请求成功率满足目标；
- P waiting queue 不持续增长；
- D waiting queue 不持续增长；
- 请求完成速率接近请求到达速率；
- KV transfer latency 保持稳定；
- Goodput 最大或接近最大；
- 保留 15%～25% 容量余量。

---

## 12. 参数配置侧重点

| 参数 | Prefill 侧重点 | Decode 侧重点 |
|---|---|---|
| `max_model_len` | 覆盖最大输入加输出 | 同样覆盖完整上下文，通常与 P 一致 |
| `max_num_batched_tokens` | 较重要，偏大以提高 Prompt 吞吐 | 不必盲目设大，关注 Decode step 时延 |
| `max_num_seqs` | 中等，避免过多长 Prompt 同时进入 | 通常较高，用于容纳长期活跃序列 |
| `max_running_requests` | 中等 | 通常较高 |
| KV Cache 容量 | 关注计算和发送前的瞬时峰值 | 关注整个生成过程中的长期占用 |
| 主要 SLO | TTFT | TPOT |
| 主要吞吐 | Input token/s | Output token/s |

参数调优与能力标定应分开进行。建议先确定一组可稳定运行的参数，再标定能力；后续如需优化参数，应重新执行标定。

---

## 13. 实验结果汇总模板

### 13.1 环境信息

```text
模型：
设备：
P 配置：
D 配置：
KVConnector：
网络：
Prefix Cache：
TTFT SLO：
TPOT SLO：
成功率目标：
```

### 13.2 单 P 标定结果

```text
Prefill-heavy 输入/输出长度：
单 P 极限能力 μP：
单 P 有效能力 μP_effective：
Prompt token/s 平台值：
P99 TTFT 拐点：
KV transfer P99：
瓶颈归因：
```

### 13.3 单 D 标定结果

```text
Decode-heavy 输入/输出长度：
单 D 极限能力 μD：
单 D 有效能力 μD_effective：
Output token/s 平台值：
P99 TPOT 拐点：
最大稳定活跃序列：
瓶颈归因：
```

### 13.4 初始配比

```text
μP_effective：
μD_effective：
计算得到的 P:D：
目标 RPS：
计算得到的 P 数量：
计算得到的 D 数量：
```

### 13.5 完整链路验证

| P:D | 最大稳定 RPS | P99 TTFT | P99 TPOT | 成功率 | Goodput | KV P99 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

---

## 14. 推荐执行顺序

```text
1. 固定模型、实例参数和 KVConnector 配置
2. 关闭 Prefix Cache 或保证命中率为 0
3. 使用长输入、短输出标定单 P
4. 使用短输入、长输出标定单 D
5. 检查 KVConnector 和网络是否提前成为瓶颈
6. 计算初始 P/D 配比
7. 测试相邻候选配比
8. 以综合固定长度负载验证
9. 引入真实长度分布和 Prefix Cache 命中率
10. 选取 Goodput 最大且满足 SLO 的最小资源配置
```

---

## 15. 最终判定原则

P/D 配比实验不应寻找：

```text
Decode 设备利用率达到 100% 的配置
```

而应寻找：

```text
在目标工作负载和 SLO 下，P/D 两侧队列均不发散、
KV 传输稳定、有效吞吐最高且具备容量余量的配置。
```

当输入压力增加后，出现以下三个信号，即可认为目标阶段接近能力边界：

1. 有效吞吐进入平台；
2. waiting queue 持续增长；
3. P99 TTFT 或 P99 TPOT 明显恶化。
