# TP：张量并行（Tensor Parallelism）

> 本文是「模型并行」系列的第 1 篇。TP 沿 Transformer 层内部的计算维度切分权重与激活，让 P 张卡协同完成**同一个 layer**。本文沿用推理算法目录的张量口径——Attention 路径挂 [MHA](../推理算法/自注意力模块/存储轴/MHA.md)/[GQA](../推理算法/自注意力模块/存储轴/GQA.md)/[MLA](../推理算法/自注意力模块/存储轴/MLA.md)，MLP 路径挂 [经典MLP](../推理算法/MLP模块/经典MLP.md)/[GLU](../推理算法/MLP模块/GLU/GLU.md)——先推导 Column/Row Parallel 的切分数学，再逐模块走 TP 张量流，最后落到通信量、显存账与 TP size 的工程决策。系列其余各篇：[PP](PP.md)（层间切分）、[EP](EP.md)（专家切分）、[CP](CP.md)（上下文切分）、[SPTP](SPTP.md)（序列维补充）。
>
> 关联：[prefill 与 decode 的张量差异](../推理算法/prefill_decode_kv_cache.md) §12-§13（两阶段的 Tq 口径）、[GLM-5.3](../模型结构/GLM-5.3.md)（TP 落地实例：MLA / MoE / W4A8）。

更新时间：2026-10-08

> 本笔记第一版素材来自 GPT（网页版）结构化咨询；本次重构统一符号到推理算法口径、补齐逐模块张量流推导（§3/§4），工程决策与坑清单段落承自初稿。

---

# 0. 符号约定

沿用「注意力变种」「MLP」系列的口径（各篇 §0）：

```text
S     : 序列长度（Prefill 为 Prompt 长度；Decode 的 Tq=1，见 §6.4）
H     : 隐藏维度（hidden_size）
N     : Query 头数
d     : 每头维度
G     : GQA 的 KV 组数（1 ≤ G ≤ N）
d_ff  : MLP 中间维度（经典取 4H；GLU 门控下 ≈ 8H/3）
r_kv  : MLA 的 KV 低秩潜维（kv_lora_rank）
d_rope: MLA 的 RoPE 解耦头维
Wo    : 注意力输出投影，形状 [N·d, H]

本文新增：
P     : 张量并行度（TP 卡数）
D     : dtype 字节数（bf16 = 2）
```

> 命名提示：推理算法路线图规划中的《张量符号与推理阶段约定》用 `P` 表示 packed token 总数（尚未落稿）；本文 `P` 一律指 TP 度，全文不涉及 packed 口径。

---

# 1. 动机与定位

**TP = 沿 Transformer 层内部的计算维度切分参数/激活，让多张 GPU 协同完成一个 layer，并用少量 collective 恢复下一层所需的数学等价结果。**

从推理 infra 视角，更值得记住的版本是：

> TP 的本质不是「分模型」，而是「分 GEMM / 分 head；代价是每层都要付通信」。

它解决的是两个问题：**权重放不下单卡**（显存）与**单卡算不动一个 layer**（算力）。核心 trade-off：

```text
TP 增大
 ├─ 每卡 weight 显存 ≈ 1/P 下降        （收益）
 ├─ 每卡 KV cache / activation 下降    （收益，GQA/MLA 下打折，见 §3.2/§3.3）
 ├─ 单次 GEMM 计算量 ≈ 1/P 下降        （收益）
 ├─ collective 次数不变、单次成本上升  （代价）
 └─ decode / 小 batch 下极易通信受限   （代价放大，见 §6.4）
```

## 1.1 与其他并行的边界（先立坐标系）

| 并行 | 主要切分维度 | 主要解决的问题 |
| --- | --- | --- |
| TP | hidden / head / FFN 维 | 权重太大、单卡算不动一个 layer |
| SP | activation 的 sequence 维 | TP 场景下 LayerNorm/Dropout 等激活显存 |
| CP | 全局 sequence / context 维 | 长上下文的 KV / attention |
| PP | 层深度 | 模型总规模（层数多） |
| DP | batch / request | 吞吐（多副本各处理不同请求） |
| EP | MoE 专家 | 专家规模 |

实用判断法：

- 「权重放不下单卡」→ TP / PP / EP 等模型态切分
- 「上下文太长，KV 爆炸」→ CP / KV cache 策略
- 「GPU 闲但请求多」→ DP
- 「MoE 专家太大」→ EP + TP

注意 **TP ≠ DP**：TP 是多张 GPU **共同完成同一个 request 的一个 layer**；DP 是不同 GPU 独立处理不同 request。

---

# 2. 数学基础：Column / Row Parallel

TP 切的「层内计算维度」最终都落在 GEMM 上，而 GEMM 只有两种切法：沿输出维（Column）或沿输入维（Row）。

## 2.1 Column Parallel Linear（沿输出维切）

设 `Y = X·A`，`X ∈ [S×H]`，`A ∈ [H×d_ff]`。TP=P 时按**输出维**切 `A = [A₀, A₁, …, A_{P-1}]`，`Aᵢ ∈ [H×d_ff/P]`：

```text
X （每卡都有完整输入）
 │
 ├──→ GPU0: Y₀ = X·A₀  [S×d_ff/P]
 ├──→ GPU1: Y₁ = X·A₁  [S×d_ff/P]
 └──→ ...              （P 卡各得一份输出分片）
```

**forward 本身不需要通信**——每个 GPU 都有完整 X，只算自己负责的输出列。对应 vLLM 的 `ColumnParallelLinear`，用于 FFN 的 gate/up 投影和 QKV 投影。

## 2.2 Row Parallel Linear（沿输入维切）

设 `Y = X·A`，`A ∈ [d_ff×H]`。按**输入维**切 `A = [A₀; A₁; …; A_{P-1}]`，同时输入也切 `X = [X₀, X₁, …, X_{P-1}]`（Column Parallel 的输出分片恰好就是这里的输入分片——这是两种切法能配对的原因），则 `Y = Σᵢ Xᵢ·Aᵢ`：

```text
GPU0: X₀·A₀ → Y₀ ─┐
GPU1: X₁·A₁ → Y₁ ─┼── AllReduce → Y
GPU2: X₂·A₂ → Y₂ ─┤
GPU3: X₃·A₃ → Y₃ ─┘
```

**输出侧必须 All-Reduce**（各卡 partial sum 相加才是完整 Y）。对应 vLLM 的 `RowParallelLinear`，用于 Attention 的输出投影 Wo 和 FFN 的 down 投影。

## 2.3 Column → Row 组合：一个 block 只有 2 个通信点

```text
X [S, H]
 │  Column Parallel（gate/up, QKV）
 ▼  [S, d_ff/P 或 head 分片]    ←—— 无通信
 │  逐元素操作 / local attention
 ▼  Row Parallel（down, Wo）
 │  AllReduce                   ←—— 通信点
 ▼  [S, H]
 │  residual / RMSNorm（replicated）
 ▼  （回到 X，进入下一处 Column Parallel）
```

> **经典 Megatron TP 的 dense Transformer block，forward 主要通信点约 2 次/层：Attention 的 Wo 一次、MLP 的 W_down 一次。** 实际 vLLM/SGLang 会因 fusion、通信调度、attention backend 改变形态，表述为「约 2 个主要 reduction 点」，不要绝对化。

## 2.4 all-reduce / all-gather / reduce-scatter 的辨析

这是最容易被写混的地方：

| 位置 | 操作 | 原因 |
| --- | --- | --- |
| Column Parallel 输入/输出 | 无 | 每卡已有完整输入，输出维已分片 |
| Row Parallel 输入 | 无 | 输入本来就是分片 |
| Row Parallel 输出 | **All-Reduce** | partial sum 必须相加 |
| Attention head 内部 | 通常无 | head 之间独立计算 |

> **纯推理 TP 的经典路径里最重要的是 All-Reduce；All-Gather / Reduce-Scatter 并非天然每层存在。** 很多资料说「TP 有 AG/RS」，实际是把 **Sequence Parallelism** 混进来了：Megatron 的 SP 在 forward 对 LayerNorm 输入 all-gather、backward 做 reduce-scatter。**推理没有 backward，不要把训练时代「TP+SP = AG/RS」的通信模型直接套到推理上。**

vLLM 提供了 AG/RS 等 collective API（`tensor_model_parallel_all_gather` 等），但「API 存在」≠「经典 forward 每层调用」。

---

# 3. Attention 路径的 TP：从 head 切分到潜变量复制

Attention TP 的核心是 **head parallelism**——N 个 head 相互独立，天然可分。但「head 怎么切」在 MHA / GQA / MLA 三种存储轴形态下答案完全不同：**MHA 按 head 切得很干净；GQA 引入 KV 组的整除问题；MLA 的 KV cache 根本切不动（只能复制）。** 逐一展开。

## 3.1 MHA：head 切分是最自然的

沿用 [MHA](../推理算法/自注意力模块/存储轴/MHA.md) §1-§3 的张量流，把 TP=P 的切分标注上去。QKV 三投影通常融合成一个矩阵（与 GLU 的 gate/up 融合同一招，[GLU](../推理算法/MLP模块/GLU/GLU.md) §7），沿 head 列切：

```text
W_qkv : [H, 3·N·d]
        ↓ Column Parallel：按 N/P 个 head 列切
每卡   : [H, 3·(N/P)·d]

X : [S, H]                        （每卡完整）
Q/K/V : [N/P, S, d]               （每卡自己的 head 分片）
每头内 Attention 照常：            （head 之间独立，卡内自洽）
  Score_i = Q_i × K_i^T → Softmax → O_i : [S, d]
local O : [N/P, S, d] → 拼回 [S, (N/P)·d]
```

关键衔接点在 [MHA](../推理算法/自注意力模块/存储轴/MHA.md) §3 的输出投影：`Wo : [N·d, H]` 沿输入维（head 维）**Row 切**，每卡拿到自己 head 分片对应的 `W_o^i : [(N/P)·d, H]`：

```text
Y_partial = O_local × W_o^i  →  [S, H]    （partial sum）
AllReduce(Y_partial)        →  Y : [S, H]
```

**整除约束**：`N % P == 0`，否则 head 无法均分（如 64 头、TP=8 → 每卡 8 头；GLM-5.3 的 N=64 满足 TP≤64 的所有 2 的幂）。

MHA 的 KV Cache 每卡 `[N/P, S, d]`，严格随 P 缩小——这是三种形态里 TP 对 KV cache 收益最干净的一种。

## 3.2 GQA：KV 组的整除与复制

[GQA](../推理算法/自注意力模块/存储轴/GQA.md) 引入第二个自由度 `G`：Q 仍 N 头，K/V 只有 G 组（`[G, S, d]` Cache）。TP 切分变成两笔账：

```text
Wq   : [H, N·d]   → 列切 N/P 头        （每卡 N/P 个 Q 头）
Wk/Wv: [H, G·d]   → 列切 G/P 组        （每卡 G/P 组 KV）
```

理想情况（`G ≥ P` 且 `G % P == 0`，如 32 Q 头 / 8 KV 组、TP=4：每卡 8 个 Q 头 + 2 组 KV）：Q 与 KV 都干净切分，每卡 KV Cache `[G/P, S, d]`。

**但 `G < P` 时（如 KV 组=2、TP=8），KV 组无法切成「少于 1 个」**，工程上只能在部分/全部 rank 上 **replication**（vLLM `QKVParallelLinear` 明确处理此逻辑）。每卡实际持有 `ceil(G/P)` 组 KV：

```text
per-rank KV 收益因子 = G / ceil(G/P)    （上限是 P）
G=8,  P=4 → ceil=2   → 因子 4   （= P，干净）
G=2,  P=8 → ceil=1   → 因子 2   （< 8，复制拖累）
G=1 (MQA) → 任意 P   → 因子 1   （KV 完全无法切）
```

> **GQA 下 TP 对 KV cache 显存的收益不保证严格 1/P；`G < P` 时收益因子封顶在 G。** 大 TP 前先算 `ceil(G/P)`。

## 3.3 MLA：KV cache 切不动，只能复制

MLA 不能照搬 MHA/GQA 的 head 切分思路——[MLA](../推理算法/自注意力模块/存储轴/MLA.md) 把 KV 压缩成了**与头数无关**的潜变量。先看权重吸收后（MLA.md §4.1）推理真正物化的矩阵，TP 的切分对象完全变了：

| 矩阵 | 形状 | TP 切法 |
| --- | --- | --- |
| `W_dq` | `[H, r_q]` | 产出 c_Q（跨头共享）→ replicated |
| `W_dkv` | `[H, r_kv]` | 产出 c_KV（跨头共享）→ replicated |
| `W_kr` | `[H, d_rope]` | 产出 k_rope（跨头共享）→ replicated |
| `W_uq·W_uk^T`（融合） | `[r_q, N·(d+d_rope)]` | **按 head 列切 N/P** |
| `W_uv·Wo`（融合） | `[N·d, H]` | **按 head 行切** → AllReduce |

上两行融合矩阵的切法与 MHA 的 QKV/Wo 同构：head 维仍是可切分的计算维度。**但 Cache 侧是另一回事**：

```text
c_KV  : [S, r_kv]     ← 潜变量，跨头共享一份
k_rope: [S, d_rope]   ← 位置旁路，跨头共享一份（MLA.md §3.2「无头维」）
```

第 `i` 个 head 的分数是 `q_nope_i × (W_uk^T·c_KV)^T`——**任何一个 head 算分都需要完整的 r_kv 维潜变量**。按 head 切 TP 后，每卡只算 N/P 个 head，但每个 head 都要读全量 `c_KV`，于是：

> **MLA 下 TP 的 KV Cache 是每卡复制全量 `[S, r_kv] + [S, d_rope]`，不随 P 缩小——TP 对 KV cache 的收益 = 0。** 这正是 GQA「G < P 收益封顶在 G」推到极致的形态：MLA 相当于 KV 侧永久 G=1。

数学等价的替代切法是存在的——把 `W_dkv` 沿 r_kv 列切、每卡算 `c_KV` 的 1/P 分片，用前再 all-gather 拼回。但 `r_kv` 本来就小（GLM-5.3 仅 512，MLA.md §5 的压缩收益全在这），切它省不了多少显存，却把每层两次 all-reduce 变成 all-reduce + all-gather，得不偿失——常见实现（vLLM/FlashMLA 路线）都选复制。

工程后果：MLA 模型（DeepSeek-V3、GLM-5.3）的部署因此倾向 **attention 侧不切、走 DP**（每卡独立持有全量 KV cache、处理不同 request 的 attention 部分），MLP/MoE 侧继续 TP/EP——TP 的 KV cache 收益归零后，「切 attention」换来的只剩 Q 侧计算的 1/P，而 decode 下 Q 侧计算本就不是瓶颈（§6.4）。GLM-5.3 的具体部署组合见 [GLM-5.3](../模型结构/GLM-5.3.md) §10（待引擎实测确认）。

---

# 4. MLP 路径的 TP：GLU 打底，逐元素天然分片

MLP 侧没有 head 的自由度，切的是 FFN 中间维 `d_ff`。以当前事实标准 SwiGLU（[GLU](../推理算法/MLP模块/GLU/GLU.md)）为例，沿用其 §2 的张量流：

## 4.1 gate/up 列切、down 行切

```text
Z : [S, H]                         （每卡完整，来自 attention 的 AllReduce 之后）

W_gate/W_up : [H, d_ff]
              ↓ Column Parallel：列切 d_ff/P
每卡        : [H, d_ff/P]

G_i = Z × W_gate^i → [S, d_ff/P]   （门控支分片）
U_i = Z × W_up^i   → [S, d_ff/P]   （值支分片）
A_i = SiLU(G_i) ⊗ U_i              （§4.2：逐元素天然成立）

W_down : [d_ff, H]
              ↓ Row Parallel：行切 d_ff/P
每卡    : [d_ff/P, H]
Y_partial = A_i × W_down^i → [S, H]
AllReduce(Y_partial)       → Y : [S, H]
```

经典 MLP（[经典MLP](../推理算法/MLP模块/经典MLP.md)）完全同构：`W_up [H,4H]` 列切、`σ` 逐元素、`W_down [4H,H]` 行切——少了 gate 支，切法不变。

## 4.2 逐元素门控为什么天然成立

`SiLU(G) ⊗ U` 是**逐元素（element-wise）**操作（GLU.md §2.2）：`A[s, j] = SiLU(G[s, j]) · U[s, j]`，每个 `d_ff` 分量独立计算、互不影响。因此列切后各卡的 `[S, d_ff/P]` 分片上，门控相乘**不需要任何跨卡数据**——逐元素操作不跨维，列切的边界就是它的边界。这是「Column（逐元素）→ Row」组合每层只需 2 次通信的根本原因：**夹在两次切分之间的所有逐元素操作都是免费分片的**。

Attention 路径的「local attention」同理：head 内的 `Q×K^T→Softmax→×V` 不跨 head，按 head 列切的边界同样是它的计算边界（§3.1）。两条路径共用同一个结构性事实。

## 4.3 融合 GEMM 与 d_ff 对齐

- **融合 GEMM 的切分配对**：`W_gate` 与 `W_up` 形状相同、常拼成 `[H, 2·d_ff]` 一次 GEMM（GLU.md §7）。TP 列切必须沿 `d_ff` 维切并**保持 gate 段与 up 段的同区间分片落在同一卡**（每卡 `[H, 2·d_ff/P]`，其中 gate 分片 + up 分片各一半），而不是「gate 给一半卡、up 给另一半卡」——否则 `⊗` 无从配对。vLLM 用 `MergedColumnParallelLinear` 处理此逻辑。
- **`d_ff` 整除与对齐**：GLU 下 `d_ff ≈ 8H/3` 需取整对齐（LLaMA-7B 的 11008），TP 再切 `d_ff/P`（11008/8=1376 ✓）。若 `d_ff % P != 0` 需 padding；量化场景还有 group 对齐问题（§8.3）。

---

# 5. 不切的与切不了的：模块边界

| 模块 | TP 处理 | 原因 |
| --- | --- | --- |
| RMSNorm / LayerNorm | replicated | 逐 token 沿完整 H 维归一化，H 维是它的工作维 |
| 残差连接 | replicated（AllReduce 后相加） | 逐元素加法 |
| Embedding / LM Head | 可 vocab 切（VocabParallel），也可 replicated | 切 `[V, H]` 的 V 维，输出侧需 all-gather/all-reduce；权重占比小（GLM-5.3 约 0.5 GB，见其 §7） |
| MoE 专家 | TP 切专家内 GLU 或 EP 切专家 | 边界问题，见下 |

**MoE 的边界**（详细展开留给 [EP](EP.md)）：TP 可以把每个专家的 `W_gate/W_up [H, m_ff]` 照 §4.1 切成 `m_ff/P`——但每卡仍要持有**全部 E 个专家**的分片，只省单专家宽度；EP 按专家切，每卡只放 `E/P` 个**完整**专家，代价是 dispatch/combine 的 all-to-all。GLM-5.3 的 `m_ff=2048` 在 TP=8 下只剩 256 维（GLM-5.3.md §6.1），GEMM 过小——这是它选 EP 的直接原因之一。

---

# 6. 通信量与显存的定量模型

## 6.1 通信量

一次 Row Parallel 输出需要 AllReduce 的张量大小 `M = Tq×H×D`（Tq=激活 token 数，H=hidden，D=字节数）。ring AllReduce 的**每卡流量 ≈ 2·(P-1)/P·M**，全系统总流量 `2(P-1)·M`：

| TP | 每卡流量（近似） | 全系统总流量 |
| --- | --- | --- |
| 2 | 1.00M | 2M |
| 4 | 1.50M | 6M |
| 8 | 1.75M | 14M |

Tq 的两阶段口径（[prefill/decode 张量差异](../推理算法/prefill_decode_kv_cache.md) §12-§13）：Prefill 时 `Tq ≈ Tkv = Prompt 长度`（chunked prefill 下为 chunk 长度），消息大；Decode 时 `Tq = batch`，消息小。这一差异决定 §6.4 的结论。

## 6.2 显存

sharded weight ≈ `W/P`，但**实际显存绝不是简单除以 P**：

```text
M_GPU ≈ M_TP-weight/P + M_replicated(Embedding/LMHead/Norm/元数据/MLA 的 KV cache 复制)
                       + M_KV + M_activation/workspace + M_runtime
                         (CUDA graph buffer、NCCL buffer、量化 scale/zp、碎片)
```

## 6.3 性能模型

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

## 6.4 为什么 decode 比 prefill 更怕 TP 通信

decode 时 `Tq ≈ batch` 个 token。例：H=8192、BF16、batch=8 → 一次 all-reduce 消息 `M ≈ 128KB`；GLM-5.3（H=6144、bf16、batch=1）只有 12KB。这么小的 collective，实际支付的是 **NCCL launch + 同步 + ring 延迟 + 链路穿越**，而不是带宽传输时间：

> **decode 的 TP 瓶颈往往是 latency 而非 bandwidth；prefill 的消息大，带宽才重要。** 所以 prefill benchmark 好看、decode ITL 却崩，是 TP 配置常见症状。

这与 §3.3 呼应：decode 下 Q 侧计算（TP 唯一还能 1/P 的部分）不是瓶颈，访存与通信才是——MLA 模型把 attention 侧改走 DP 的收益正在于此。

---

# 7. 推理 vs 训练：TP 的场景差异

| 维度 | 训练 | 推理 |
| --- | --- | --- |
| 反向传播 | 有（backward all-reduce / gradient RS） | **无**，通信模型完全不同 |
| 每 step token 量 | 大 batch + 长序列，通信被大计算量摊薄 | decode 每 step 只有 batch 个 token |
| 典型组合 | TP + SP + PP + DP | 单机 TP 优先；跨机 TP+PP；MLA 模型 attention DP |
| 通信占比 | 可被 amortize | decode 下 collective latency 占比高 |

另外推理 runtime 大量使用 **CUDA Graph / piecewise CUDA graph**，这和 TP 叠加产生额外约束：

- graph capture 要求固定 shape / 固定 buffer，TP rank 间必须严格一致
- 某 rank fallback eager 会拖慢整个 TP group
- collective 的 launch 与 buffer 生命周期必须在 graph 内稳定
- 不同 attention backend 对 CUDA Graph 的 shape 一致性要求不同（vLLM 文档有支持矩阵）

> TP 是 collective 级同步，CUDA Graph 是执行级同步；两者叠加后 runtime 对一致性的要求更高。

---

# 8. TP 对算子与量化（W4A8）的影响

## 8.1 算子契约改变

`nn.Linear` 被替换为 `ColumnParallelLinear` / `RowParallelLinear` / `MergedColumnParallelLinear`（gate/up 融合切分，§4.3）/ `QKVParallelLinear`（处理 MHA/GQA head 分片与复制，§3.2）/ `ReplicatedLinear`。attention 路径变成：QKV Column TP → head shard → local attention → Row Parallel o_proj（MLA 下是融合矩阵按 head 切，§3.3）→ AllReduce。

## 8.2 kernel shape 改变

例：H=8192、d_ff=28672、TP=8 → up projection 每卡 GEMM 从 `8192→28672` 变成 `8192→3584`。GEMM 变小、tile 利用率和 Tensor Core 效率都可能变化：

> **TP 越大不一定 GEMM 越快；TP=8 时 shard 维度可能落入对 kernel 不友好的 tile 尺寸。**

## 8.3 W4A8 的特殊问题（GLM-5.3 即 W4A8）

- weight bytes → `/P`，但**量化元数据（scale / zero-point / group index / packing）不一定同比减少**，各有 shard 策略
- **quantization group 对齐**：group_size=128 而 `K/P` 不是 group 对齐的形状 → padding / repacking / kernel fallback / 加载时转换 / checkpoint 不兼容
- W4A8 已把 weight 带宽压得很低：若原本是 memory-bandwidth bound，**继续加 TP 的收益可能变小**；收益矩阵必须实测，不能从 BF16 的 scaling 推断

> 量化 checkpoint 的 sharding layout 与 TP layout 必须一起设计。benchmark 要覆盖 `BF16×TP{1,2,4,8}` 与 `W4A8×TP{1,2,4,8}` 两张表。

---

# 9. 单机 vs 跨机 TP，以及 TP 怎么选

## 9.1 链路等级

```text
NVSwitch > NVLink > PCIe > 同节点 NIC > 跨节点 RDMA > 普通 Ethernet
```

决定 TP 性能的不是「8 张卡」这个数字，而是**这 8 张卡之间的有效 collective 带宽与延迟**。跨机 TP 的每个 per-layer collective 都要走 `GPU→NVLink/PCIe→NIC→网络→NIC→GPU`。

## 9.2 经验法则

- 能单机完成 TP → 单机 TP（collective latency 低、拓扑好、适合 decode）
- 跨节点 → **TP 对齐单节点 GPU 数，用 PP 扩展节点**（vLLM 文档典型 2 机 16 卡 = `TP=8, PP=2`，而不是 TP=16）：PP 跨节点通信次数远少于 TP 的 per-layer collective
- decode latency 优先 → 尽量小 TP
- MLA 模型 → attention 侧考虑 DP（§3.3），TP/EP 只切 MLP/MoE

## 9.3 工程决策表

| 条件 | 推荐 |
| --- | --- |
| TP1 能放下 | TP=1 |
| 放不下就翻倍 | TP=2 → 4 → 8 |
| 单机 8 GPU | 优先 TP=8 |
| 多机 8 GPU/节点 | TP=8 + PP |
| decode 延迟优先 | 尽量小 TP |
| GQA KV 组很少 | 警惕大 TP 的 KV 复制（§3.2 收益因子） |
| MLA | KV cache 收益=0，attention 走 DP（§3.3） |
| 长上下文 | 别用 TP 硬扛，考虑 CP |
| MoE | TP + EP（§5 边界） |
| 高并发吞吐 | TP 与 DP 一起评估 |

> **TP size 是显存约束决定的下界，不是「GPU 越多越快」的自由上界。** 最终是约束优化：`P* = argmin_P (T_compute + T_collective + T_runtime)`，s.t. `M_GPU(P) ≤ 可用显存`，且 `N % P == 0`、`ceil(G/P)` 可接受（GQA）、MLA 的 KV 复制可承受、`d_ff % P == 0`、量化 layout 可分片、kernel tile 合理、CUDA Graph 可用、拓扑够好。

---

# 10. 常见坑清单

1. **认为显存严格除以 TP** —— 还有 replicated 部分、KV cache、workspace、graph/NCCL buffer、量化元数据
2. **认为 TP=8 一定比 TP=4 快** —— decode 下 collective latency 上升，TP8 可能比 TP4 慢（1.1 vs 1.0 ms/token 时常发生）
3. **GQA 下默认 KV cache / TP** —— 先算 `G/ceil(G/P)`，复制就藏着（§3.2）
4. **MLA 下期待 TP 切 KV cache** —— c_KV 跨头共享，TP 收益=0（§3.3）
5. **把 TP 和 SP 混谈**（「TP 有 AG/RS」）—— 经典推理 TP forward 主要是 Row Parallel 后的 All-Reduce（§2.4）
6. **把 CP 当成更大的 TP** —— CP 切 sequence 维，解决长上下文
7. **跨 PCIe/Ethernet 期待线性 scaling** —— decode + 小 batch + 每层 collective = latency bound
8. **忽略拓扑** —— 同样 8 卡，NVSwitch 和普通 PCIe 是两个世界
9. **忽略 kernel shape** —— shard 后的 GEMM 维度可能不是好 tile（MoE 的 m_ff/P 尤甚，§5）
10. **只看 eager benchmark** —— 线上性能来自 scheduler→graph capture→replay→NCCL 的组合，benchmark 必须与生产执行模式一致

benchmark 时 prefill/decode 分开看：prefill 记 TTFT、prefill tokens/s、SM/TC 利用率、NCCL 时间、通信计算重叠；decode 记 ITL/TPOT、decode tokens/s、active sequences、每卡利用率、collective latency、graph replay/fallback（SGLang 自带工具已区分 TTFT/ITL/端到端）。

---

# 11. 小结

一个 dense Transformer block 在 TP=P 下的完整切分图（MHA + SwiGLU 形态）：

```text
X : [S, H]                                   （每卡完整）
 ├─ Attention ──────────────────────────────
 │   W_qkv [H,3Nd]   列切 head  → 每卡 [H, 3·(N/P)·d]
 │   Q/K/V [N/P,S,d] local attention（逐元素/head 独立，无通信）
 │   Wo [N·d,H]      行切 head  → partial [S,H] → AllReduce ①
 ├─ MLP ─────────────────────────────────────
 │   W_gate/W_up [H,d_ff] 列切 → 每卡 [H, d_ff/P]
 │   SiLU(G)⊗U 逐元素天然分片（无通信）
 │   W_down [d_ff,H] 行切 → partial [S,H] → AllReduce ②
 ├─ RMSNorm / 残差 / Embedding / LM Head ─── replicated（可 vocab 切）
 └─ 每层 forward ≈ 2 次 AllReduce；GQA 的 KV 组 ceil(G/P) 切不净则复制；
    MLA 的 c_KV/[S,r_kv] 干脆全量复制、收益=0
```

8 句话心智模型：

1. TP 是 **layer 内并行**：切 GEMM/Attention 本身，不是「切片模型」
2. Column Parallel 不需要合并：每卡得自己的输出分片；Row Parallel 必须合并：**Row → AllReduce**
3. 夹在两次切分之间的**逐元素操作全部免费分片**——每层只需 2 个通信点的结构性根源
4. Attention TP 本质是 head TP：MHA 干净、GQA 看 `ceil(G/P)`、MLA 的 KV cache 收益=0
5. 显存收益接近 1/P（KV cache 除外），性能收益远小于 1/P（通信不随 P 消失）
6. Decode 是 TP 最难的场景：小 GEMM + collective latency 占比高
7. 单机 TP 通常优于跨机 TP；跨机用 PP 扩展而非加大 TP；MLA 模型 attention 侧走 DP
8. TP size 的选择是约束优化问题（显存下界 + 整除性 + 量化对齐 + 拓扑），不是越大越好

TP 的本质：**用「head / d_ff 维的列切 + 行切配对」把一个 layer 的 GEMM 摊到 P 张卡，用每层 2 次 All-Reduce 换回数学等价——代价是通信不随 P 消失、且 KV cache 的收益在 GQA/MLA 下逐级打折直至归零。**

系列下一篇 [PP](PP.md)：当层数多到 TP 攒不下的规模，沿层深度切、把每层通信换成层间一次激活传递。
