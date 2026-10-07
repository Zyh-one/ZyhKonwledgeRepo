# 张量并行（Tensor Parallelism, TP）

更新时间：2026-10-07

> 视角：推理 infra 工程师，围绕 vLLM / SGLang / Megatron 风格 TP 展开。
> 本笔记初稿素材来自 GPT（网页版）结构化咨询，经本地校订与仓库语境适配。
>
> 关联：[SPTP.md](SPTP.md)（序列维补充）、[PP.md](PP.md)（层间切分）、[CP.md](CP.md)（上下文切分）、[EP.md](EP.md)（专家切分）、[模型结构/GLM-5.3.md](../模型结构/GLM-5.3.md)（TP 落地对象：64 头 / MLA / W4A8）。

---

# 0. 一句话定位

**TP = 沿 Transformer 层内部的计算维度切分参数/激活，让多张 GPU 协同完成一个 layer，并用少量 collective 恢复下一层所需的数学等价结果。**

从推理 infra 视角，更值得记住的版本是：

> TP 的本质不是"分模型"，而是"分 GEMM / 分 Attention head；代价是每层都要付通信"。

核心 trade-off：

```text
TP 增大
 ├─ 每卡 weight 显存 ≈ 1/P 下降        （收益）
 ├─ 每卡 KV cache / activation 下降    （收益，GQA/MLA 下打折）
 ├─ 单次 GEMM 计算量 ≈ 1/P 下降        （收益）
 ├─ collective 次数不变、单次成本上升  （代价）
 └─ decode / 小 batch 下极易通信受限   （代价放大）
```

# 1. 与其他并行的边界（先立坐标系）

| 并行 | 主要切分维度 | 主要解决的问题 |
| --- | --- | --- |
| TP | hidden / head / FFN 维 | 权重太大、单卡算不动一个 layer |
| SP | activation 的 sequence 维 | TP 场景下 LayerNorm/Dropout 等激活显存 |
| CP | 全局 sequence / context 维 | 长上下文的 KV / attention |
| PP | 层深度 | 模型总规模（层数多） |
| DP | batch / request | 吞吐（多副本各处理不同请求） |
| EP | MoE 专家 | 专家规模 |

实用判断法：

- "权重放不下单卡" → TP / PP / EP 等模型态切分
- "上下文太长，KV 爆炸" → CP / KV cache 策略
- "GPU 闲但请求多" → DP
- "MoE 专家太大" → EP + TP

注意 **TP ≠ DP**：TP 是多张 GPU **共同完成同一个 request 的一个 layer**；DP 是不同 GPU 独立处理不同 request。

# 2. 数学基础：Column / Row Parallel

## 2.1 Column Parallel Linear（沿输出维切）

设 `Y = X·A`，`X ∈ [B×H]`，`A ∈ [H×4H]`。TP=P 时按**输出维**切 `A = [A₁, A₂, …, A_P]`，`Aᵢ ∈ [H×4H/P]`：

```text
X （每卡都有完整输入）
 │
 ├──→ GPU0: Y₀ = X·A₀  [B×4H/P]
 ├──→ GPU1: Y₁ = X·A₁  [B×4H/P]
 └──→ ...             （P 卡各得一份输出分片）
```

**forward 本身不需要通信**——每个 GPU 都有完整 X，只算自己负责的输出列。对应 vLLM 的 `ColumnParallelLinear`，用于 FFN up/gate 层和 QKV projection。

## 2.2 Row Parallel Linear（沿输入维切）

设 `Y = X·A`，`A ∈ [4H×H]`。按**输入维**切 `A = [A₁; A₂; …; A_P]`，同时输入也切 `X = [X₁, X₂, …, X_P]`，则 `Y = Σᵢ Xᵢ·Aᵢ`：

```text
GPU0: X₀·A₀ → Y₀ ─┐
GPU1: X₁·A₁ → Y₁ ─┼── AllReduce → Y
GPU2: X₂·A₂ → Y₂ ─┤
GPU3: X₃·A₃ → Y₃ ─┘
```

**输出侧必须 All-Reduce**（各卡 partial sum 相加才是完整 Y）。对应 vLLM 的 `RowParallelLinear`，用于 Attention output projection 和 FFN down 层。

## 2.3 Column → Row 组合：一个 block 只有 2 个通信点

```text
X [H]
 │  Column Parallel（up/gate, QKV）
 ▼  [4H/P 或 head 分片]     ←—— 无通信
 │  activation / local attention
 ▼  Row Parallel（down, o_proj）
 │  AllReduce               ←—— 通信点
 ▼  [H]
 │  residual / RMSNorm
 ▼  （回到 X，进入下一处 Column Parallel）
```

> **经典 Megatron TP 的 dense Transformer block，forward 主要通信点约 2 次/层：Attention output projection 一次、MLP down projection 一次。** 实际 vLLM/SGLang 会因 fusion、通信调度、attention backend 改变形态，写文档时表述为"约 2 个主要 reduction 点"，不要绝对化。

# 3. all-reduce / all-gather / reduce-scatter 到底发生在哪

这是最容易被写混的地方：

| 位置 | 操作 | 原因 |
| --- | --- | --- |
| Column Parallel 输入/输出 | 无 | 每卡已有完整输入，输出维已分片 |
| Row Parallel 输入 | 无 | 输入本来就是分片 |
| Row Parallel 输出 | **All-Reduce** | partial sum 必须相加 |
| Attention head 内部 | 通常无 | head 之间独立计算 |

> **纯推理 TP 的经典路径里最重要的是 All-Reduce；All-Gather / Reduce-Scatter 并非天然每层存在。** 很多资料说"TP 有 AG/RS"，实际是把 **Sequence Parallelism** 混进来了：Megatron 的 SP 在 forward 对 LayerNorm 输入 all-gather、backward 做 reduce-scatter。**推理没有 backward，不要把训练时代"TP+SP = AG/RS"的通信模型直接套到推理上。**

vLLM 提供了 AG/RS 等 collective API（`tensor_model_parallel_all_gather` 等），但"API 存在"≠"经典 forward 每层调用"。

# 4. Attention 按 head 切分：MHA / GQA / MLA

## 4.1 MHA：head 并行是最自然的

`N_h` 个 head 相互独立，TP=P 时每卡分 `N_h/P` 个 head，各算各的 `Attention(Qᵢ, Kᵢ, Vᵢ)`。**Attention TP 的核心就是 head parallelism。**

## 4.2 GQA：第一个特殊情况

`N_Q > N_KV`（如 32 Q 头 / 8 KV 头，TP=4）：每卡 8 个 Q 头 + 2 个 KV 头，最理想。

**但 TP > N_KV 时（如 KV 头=2、TP=8），KV head 无法切成"少于 1 个"**，工程上只能在部分/全部 rank 上 **replication**（vLLM `QKVParallelLinear` 明确处理此逻辑）。由此：

> **GQA 下 TP 对 KV cache 显存的收益不保证严格 1/P；`N_KV < TP` 时 KV cache 的 TP scaling 明显变差。** 大 TP 前先算 `N_KV / TP`。

## 4.3 MLA：不能照搬 MHA/GQA 思路

MLA 把历史 KV 压缩成 latent（`kv_lora_rank` 维潜向量）+ 投影恢复，**KV 不再等价于"若干完整 K/V head"**（详见 [MLA.md](../推理算法/自注意力模块/存储轴/MLA.md)）。TP 下 latent 的切分与投影恢复相互纠缠，"head 数 / TP"不能直接判断 KV cache 是否 1/P。GLM-5.3 这类 MLA 模型的并行组合（DP attention + EP 等）需要单独分析，见 [GLM-5.3.md](../模型结构/GLM-5.3.md)。

# 5. 通信量与显存的定量模型

## 5.1 通信量

一次 Row Parallel 输出需要 AllReduce 的张量大小 `M = T×H×D`（T=激活 token 数，H=hidden，D= dtype 字节数）。ring AllReduce 的**每卡流量 ≈ 2·(P-1)/P·M**，全系统总流量 `2(P-1)·M`：

| TP | 每卡流量（近似） | 全系统总流量 |
| --- | --- | --- |
| 2 | 1.00M | 2M |
| 4 | 1.50M | 6M |
| 8 | 1.75M | 14M |

## 5.2 显存

sharded weight ≈ `W/P`，但**实际显存绝不是简单除以 P**：

```text
M_GPU ≈ M_TP-weight/P + M_replicated(Embedding/LMHead/LayerNorm/元数据)
                       + M_KV + M_activation/workspace + M_runtime
                         (CUDA graph buffer、NCCL buffer、量化 scale/zp、碎片)
```

## 5.3 性能模型

```text
T_layer(P) = T_compute(P) + T_TP-comm(P) + T_launch(P) + T_sync(P)
T_TP-comm  ≈ α·N_collective + β·V(P)/BW      （α=collective latency，V(P)=每卡流量）
```

> **计算量约按 1/P 降，通信不按 1/P 降**——这就是 TP scaling 的数学本质。示意：

```text
TP=1  ████████████████ compute
TP=2  ████████ compute ██ comm
TP=4  ████ compute ████ comm
TP=8  ██ compute ██████ comm
```

## 5.4 为什么 decode 比 prefill 更怕 TP 通信

decode 时 `T ≈ batch` 个 token。例：H=8192、BF16、batch=8 → 一次 all-reduce 消息 `M ≈ 128KB`。这么小的 collective，实际支付的是 **NCCL launch + 同步 + ring 延迟 + 链路穿越**，而不是带宽传输时间：

> **decode 的 TP 瓶颈往往是 latency 而非 bandwidth；prefill 的消息大，带宽才重要。** 所以 prefill benchmark 好看、decode ITL 却崩，是 TP 配置常见症状。

# 6. 推理 vs 训练：TP 的场景差异

| 维度 | 训练 | 推理 |
| --- | --- | --- |
| 反向传播 | 有（backward all-reduce / gradient RS） | **无**，通信模型完全不同 |
| 每 step token 量 | 大 batch + 长序列，通信被大计算量摊薄 | decode 每 step 只有 batch 个 token |
| 典型组合 | TP + SP + PP + DP | 单机 TP 优先；跨机 TP+PP |
| 通信占比 | 可被 amortize | decode 下 collective latency 占比高 |

另外推理 runtime 大量使用 **CUDA Graph / piecewise CUDA graph**，这和 TP 叠加产生额外约束：

- graph capture 要求固定 shape / 固定 buffer，TP rank 间必须严格一致
- 某 rank fallback eager 会拖慢整个 TP group
- collective 的 launch 与 buffer 生命周期必须在 graph 内稳定
- 不同 attention backend 对 CUDA Graph 的 shape 一致性要求不同（vLLM 文档有支持矩阵）

> TP 是 collective 级同步，CUDA Graph 是执行级同步；两者叠加后 runtime 对一致性的要求更高。

# 7. TP 对算子与量化（W4A8）的影响

## 7.1 算子契约改变

`nn.Linear` 被替换为 `ColumnParallelLinear` / `RowParallelLinear` / `QKVParallelLinear`（处理 MHA/GQA head 分片与复制）/ `ReplicatedLinear`。attention 路径变成：QKV Column TP → head shard → local attention → Row Parallel o_proj → AllReduce。

## 7.2 kernel shape 改变

例：H=8192、FFN=28672、TP=8 → up projection 每卡 GEMM 从 `8192→28672` 变成 `8192→3584`。GEMM 变小、tile 利用率和 Tensor Core 效率都可能变化：

> **TP 越大不一定 GEMM 越快；TP=8 时 shard 维度可能落入对 kernel 不友好的 tile 尺寸。**

## 7.3 W4A8 的特殊问题（GLM-5.3 即 W4A8）

- weight bytes → `/P`，但**量化元数据（scale / zero-point / group index / packing）不一定同比减少**，各有 shard 策略
- **quantization group 对齐**：group_size=128 而 `K/P` 不是 group 对齐的形状 → padding / repacking / kernel fallback / 加载时转换 / checkpoint 不兼容
- W4A8 已把 weight 带宽压得很低：若原本是 memory-bandwidth bound，**继续加 TP 的收益可能变小**；收益矩阵必须实测，不能从 BF16 的 scaling 推断

> 量化 checkpoint 的 sharding layout 与 TP layout 必须一起设计。benchmark 要覆盖 `BF16×TP{1,2,4,8}` 与 `W4A8×TP{1,2,4,8}` 两张表。

# 8. 单机 vs 跨机 TP，以及 TP 怎么选

## 8.1 链路等级

```text
NVSwitch > NVLink > PCIe > 同节点 NIC > 跨节点 RDMA > 普通 Ethernet
```

决定 TP 性能的不是"8 张卡"这个数字，而是**这 8 张卡之间的有效 collective 带宽与延迟**。跨机 TP 的每个 per-layer collective 都要走 `GPU→NVLink/PCIe→NIC→网络→NIC→GPU`。

## 8.2 经验法则

- 能单机完成 TP → 单机 TP（collective latency 低、拓扑好、适合 decode）
- 跨节点 → **TP 对齐单节点 GPU 数，用 PP 扩展节点**（vLLM 文档典型 2 机 16 卡 = `TP=8, PP=2`，而不是 TP=16）：PP 跨节点通信次数远少于 TP 的 per-layer collective
- decode latency 优先 → 尽量小 TP

## 8.3 工程决策表

| 条件 | 推荐 |
| --- | --- |
| TP1 能放下 | TP=1 |
| 放不下就翻倍 | TP=2 → 4 → 8 |
| 单机 8 GPU | 优先 TP=8 |
| 多机 8 GPU/节点 | TP=8 + PP |
| decode 延迟优先 | 尽量小 TP |
| GQA KV 头很少 | 警惕大 TP 的 KV 复制 |
| 长上下文 | 别用 TP 硬扛，考虑 CP |
| MoE | TP + EP |
| 高并发吞吐 | TP 与 DP 一起评估 |

> **TP size 是显存约束决定的下界，不是"GPU 越多越快"的自由上界。** 最终是约束优化：`P* = argmin_P (T_compute + T_collective + T_runtime)`，s.t. `M_GPU(P) ≤ 可用显存`，且 `num_heads % P == 0`、`N_KV/P` 可接受、FFN 维可分片、量化 layout 可分片、kernel tile 合理、CUDA Graph 可用、拓扑够好。

# 9. 常见坑清单

1. **认为显存严格除以 TP** —— 还有 replicated 部分、KV cache、workspace、graph/NCCL buffer、量化元数据
2. **认为 TP=8 一定比 TP=4 快** —— decode 下 collective latency 上升，TP8 可能比 TP4 慢（1.1 vs 1.0 ms/token 时常发生）
3. **GQA 下默认 KV cache / TP** —— 先看 `N_KV/TP`，<1 就有复制
4. **把 TP 和 SP 混谈**（"TP 有 AG/RS"）—— 经典推理 TP forward 主要是 Row Parallel 后的 All-Reduce
5. **把 CP 当成更大的 TP** —— CP 切 sequence 维，解决长上下文
6. **跨 PCIe/Ethernet 期待线性 scaling** —— decode + 小 batch + 每层 collective = latency bound
7. **忽略拓扑** —— 同样 8 卡，NVSwitch 和普通 PCIe 是两个世界
8. **忽略 kernel shape** —— shard 后的 GEMM 维度可能不是好 tile
9. **忽略量化 packing** —— W4A8 不是简单 weight bytes/TP
10. **只看 eager benchmark** —— 线上性能来自 scheduler→graph capture→replay→NCCL 的组合，benchmark 必须与生产执行模式一致

benchmark 时 prefill/decode 分开看：prefill 记 TTFT、prefill tokens/s、SM/TC 利用率、NCCL 时间、通信计算重叠；decode 记 ITL/TPOT、decode tokens/s、active sequences、每卡利用率、collective latency、graph replay/fallback（SGLang 自带工具已区分 TTFT/ITL/端到端）。

# 10. 心智模型收敛（8 句话）

1. TP 是 **layer 内并行**：切 GEMM/Attention 本身，不是"切片模型"
2. Column Parallel 不需要合并：每卡得自己的输出分片
3. Row Parallel 必须合并：**Row → AllReduce**
4. Attention TP 本质是 head TP；GQA/MLA 改变显存与通信细节
5. 显存收益接近 1/P，性能收益远小于 1/P（通信不随 P 消失）
6. Decode 是 TP 最难的场景：小 GEMM + collective latency 占比高
7. 单机 TP 通常优于跨机 TP；跨机用 PP 扩展而非加大 TP
8. TP size 的选择是约束优化问题（显存下界 + 整除性 + 量化对齐 + 拓扑），不是越大越好
