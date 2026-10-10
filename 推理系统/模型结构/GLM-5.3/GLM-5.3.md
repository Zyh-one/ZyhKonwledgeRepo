# GLM-5.3 架构拆解（infra 视角）

> 数据来源：黄区 cam-train-144 上 `/opt/models/GLM-5.3-W4A8/config.json`（只读读取）。本文从推理 infra 视角拆解每个模块，重点标注对显存、KV Cache、访存、并行切分的影响。
>
> 关联：[自注意力模块/存储轴/MLA.md](../推理算法/自注意力模块/存储轴/MLA.md)（MLA 张量流）、[自注意力模块/存储轴/MLA动机.md](../推理算法/自注意力模块/存储轴/MLA动机.md)（低秩压缩的设计动机）、[推理算法/自回归生成](<../推理算法/0-Transformer%20自回归生成的最小闭环.md>)（张量主线）、[模型并行](../模型并行/)（切分）。

---

# 0. 一句话定位

GLM-5.3（架构 `GlmMoeDsaForCausalLM`）= **MoE（256 路由专家 + 1 共享专家）+ DSA 稀疏索引注意力 + MLA 低秩潜注意力 + RoPE 解耦 + W4A8 量化**，78 层，上下文 1M token。它的复杂度在于「三种省显存/省算力的机制叠在一起」：MoE 省激活算力、DSA 省长上下文 Attention 复杂度、MLA 省 KV Cache。

# 1. 关键参数总表（已确认，来自 config.json）

| 字段                                | 值                            | 含义                            |
| ----------------------------------- | ----------------------------- | ------------------------------- |
| `architectures`                   | `GlmMoeDsaForCausalLM`      | GLM 自家的 Moe + DSA 架构       |
| `num_hidden_layers`               | 78                            | Transformer 层数                |
| `hidden_size`                     | 6144                          | 隐藏维度 H                      |
| `vocab_size`                      | 154880                        | 词表大小                        |
| `tie_word_embeddings`             | false                         | Embedding 与 LM Head 不共享     |
| `num_attention_heads`             | 64                            | Q 头数 N                        |
| `num_key_value_heads`             | 64                            | KV 头数（MLA 下 = N，详见 §3） |
| `head_dim` / `qk_nope_head_dim` | 192                           | 不带位置的 K/Q 头维             |
| `qk_rope_head_dim`                | 64                            | RoPE 解耦头维                   |
| `qk_head_dim`                     | 256                           | 192 + 64（nope + rope）         |
| `v_head_dim`                      | 256                           | V 头维                          |
| `kv_lora_rank`                    | 512                           | KV 低秩压缩潜维 r_kv ★MLA       |
| `q_lora_rank`                     | 2048                          | Q 低秩压缩潜维 ★MLA            |
| `index_head_dim`                  | 128                           | DSA 索引头维                    |
| `index_n_heads`                   | 32                            | DSA 索引头数                    |
| `index_topk`                      | 2048                          | DSA 每层稀疏 top-k token 数     |
| `index_topk_freq`                 | 4                             | full 索引层每 4 层一次          |
| `first_k_dense_replace`           | 3                             | 前 3 层 MLP 为 dense，其余 MoE  |
| `n_routed_experts`                | 256                           | 路由专家数                      |
| `n_shared_experts`                | 1                             | 共享专家数                      |
| `num_experts_per_tok`             | 8                             | 每 token 激活专家数             |
| `intermediate_size`               | 12288                         | dense 层 MLP 中间维             |
| `moe_intermediate_size`           | 2048                          | MoE 专家中间维                  |
| `topk_method`                     | `noaux_tc`                  | 专家路由 top-k 方法             |
| `norm_topk_prob`                  | true                          | 归一化专家概率                  |
| `max_position_embeddings`         | 1048576                       | 最大上下文 1M                   |
| `rope_theta`                      | 8e6                           | RoPE 基频                       |
| `rope_interleave`                 | true                          | RoPE 交错                       |
| `rms_norm_eps`                    | 1e-5                          | RMSNorm eps                     |
| `attention_bias`                  | false                         | QKV 投影无 bias                 |
| `activation_precision`            | int8                          | 激活 int8（W4A8 的 A8）         |
| 权重文件                            | 282 个 safetensors，约 375 GB | W4 量化                         |

## 1.5 字段分类索引

上表字段按「回答哪个 infra 问题」分 7 类，便于按主题检索：

| 类 | 字段 | 回答的问题 |
|----|------|----------|
| ① 模型身份与规模 | `architectures`、`num_hidden_layers`、`hidden_size`、`vocab_size`、`tie_word_embeddings`、`max_position_embeddings` | 多大、多少层、词表多大、结构族 |
| ② 注意力·MLA | `num_attention_heads`、`num_key_value_heads`、`qk_nope_head_dim`、`qk_rope_head_dim`、`qk_head_dim`、`v_head_dim`、`kv_lora_rank`、`q_lora_rank` | KV Cache 压到多少、潜维/头维多大 |
| ③ 注意力·DSA | `index_head_dim`、`index_n_heads`、`index_topk`、`index_topk_freq`、`indexer_types`、`index_share_for_mtp_iteration` | 长上下文算力：每层看几 token、索引怎么共享 |
| ④ RoPE | `rope_theta`、`rope_interleave` | 位置编码基频与排布 |
| ⑤ MoE/MLP | `first_k_dense_replace`、`n_routed_experts`、`n_shared_experts`、`num_experts_per_tok`、`intermediate_size`、`moe_intermediate_size`、`topk_method`、`norm_topk_prob` | 专家多少、每 token 激活几个、显存大头在哪 |
| ⑥ Norm/bias | `rms_norm_eps`、`attention_bias` | 归一化与投影 bias 的实现细节 |
| ⑦ 量化 | `activation_precision` | 权重/激活各多少 bit，kernel 要求 |

要点：

- **②③ 是两套独立注意力机制**，字段名都含 `head_dim` 易混；DSA 以 `index_*` 前缀判别，MLA 以 `*_lora_rank` 判别，互斥。
- **⑤ 里 `intermediate_size` 与 `moe_intermediate_size` 各管一摊**：前者只给前 3 层 dense MLP，后者给后 75 层 MoE 专家。
- **④ 字段少但独立成类**：RoPE 在 MLA 下只作用 `qk_rope_head_dim` 那段解耦 K，是「能否吸收权重」的关键。
- **⑥⑦ 字段少但 infra 影响重**：`attention_bias=false` 决定投影矩阵能否干净吸收，`activation_precision=int8` 是 W4A8 的 A8，二者是 kernel 实现门槛的直接来源。

> 注：本表是 §1 总表的**分类视图**，字段范围以 §1 + §4 补充的 `indexer_types`/`index_share_for_mtp_iteration` 为准，并非 config.json 全量字段。

---

# 2. 整体层结构

每一层（共 78 层）的数据流：

```text
x : [S, H]
  ↓ RMSNorm
  ↓ Attention = MLA（每层）+ DSA 稀疏索引（按层交替 full/shared）
  ↓ 残差
  ↓ RMSNorm
  ↓ MLP = dense（前 3 层）/ MoE（其余 75 层）
  ↓ 残差
y : [S, H]
```

关键点（已确认）：

- **注意力与 MLP 的稀疏是两套独立机制**：MLP 的 dense/sparse 由 `first_k_dense_replace=3` + `moe_layer_freq=1` 决定（前 3 dense、后 75 MoE）；注意力的稀疏由 `indexer_types` 数组逐层标注 `full`/`shared` 决定（见 §4）。
- 层内维度全程 `[S, H]` 不变，与 [自回归生成](<../推理算法/0-Transformer%20自回归生成的最小闭环.md>) 主线一致。

---

# 3. 注意力：MLA（低秩潜注意力）— 已确认

GLM-5.3 的逐 token 注意力用的是 **MLA**，与 DeepSeek-V2/V3 同源。判定依据：`kv_lora_rank`、`q_lora_rank`、`qk_nope/qk_rope` 解耦字段同时出现（见 [MLA.md](../推理算法/自注意力模块/存储轴/MLA.md) §0 的签名）。

## 3.1 压缩-还原张量流（代入实际数值）

```text
X : [S, 6144]
  × W_dq [6144, 2048]   → c_Q  : [S, 2048]      （Q 潜变量，不缓存）
  × W_dkv[6144, 512]    → c_KV : [S, 512]       ★KV 只缓存这个
  还原：
  c_Q  × W_uq [2048, 64×256]  → Q : [64, S, 256]  (nope192 + rope64)
  c_KV × W_uk [512, 64×192]   → K_nope : [64, S, 192]
  c_KV × W_uv [512, 64×256]   → V : [64, S, 256]
  X × W_kr [6144, 64]         → K_rope : [..., S, 64]  （位置解耦，单独缓存）
```

权重吸收后推理不显式还原 K/V（详见 [MLA.md](../推理算法/自注意力模块/存储轴/MLA.md) §4）；RoPE 部分因非线性无法吸收，单独保留。

## 3.2 KV Cache 体积（infra 核心）

每层、每 token 实际缓存：

```text
c_KV  : [512]              主潜变量（与头数无关）
K_rope: 解耦位置部分（量级远小于完整 K/V）
```

对比「不压缩的等价多头注意力」每 token 每层所需的 `K+V ≈ 64×(256+256) = 32768` 元素，MLA 把主部分压到 `512`，**约一个数量级以上的削减**（精确比例取决于 K_rope 是否按头存，属实现细节，合理推断）。

换算到长上下文：1M token、78 层、bf16：

- 不压缩 ≈ `1e6 × 78 × 32768 × 2 byte ≈ 4.6 TB`（K+V，单卡根本装不下）
- MLA 主潜变量 ≈ `1e6 × 78 × 512 × 2 byte ≈ 76 GB`（外加 K_rope 小量）

**这就是 GLM-5.3 能开 1M 上下文的显存基础**（已确认机制，体量为合理估算）。

## 3.3 一个容易误判的点

`num_key_value_heads == num_attention_heads == 64`。如果套用「共享投影」路线（MQA/GQA）的判据「KV 头数 vs Q 头数」，会误读成 MHA。但 MLA 不靠共享头数省 Cache，而是靠低秩潜维省维度——所以 KV 头数字段保持等于 Q 头数，真正起作用的是 `kv_lora_rank=512`。这与 [MLA.md](../推理算法/自注意力模块/存储轴/MLA.md) §0 的分类口径完全一致。

---

# 4. 注意力：DSA 稀疏索引（合理推断为主）

除了逐层的 MLA，GLM-5.3 还叠了一层 **DSA（稀疏索引注意力）**，由一组 `index_*` 字段配置。这是 GLM 自家的机制（非标准 MLA 的一部分），config 字段名是其主要信息来源。

## 4.1 字段

```text
index_head_dim   : 128     索引头维
index_n_heads    : 32      索引头数
index_topk       : 2048    每层只对 top-2048 个 token 做注意力
index_topk_freq  : 4       full 索引层每 4 层出现一次
indexer_types    : [78 项] 逐层标注 full / shared
index_share_for_mtp_iteration : true
```

## 4.2 机制推断

- `indexer_types` 数组在前 3 层为 `full`，其后大致呈「1 个 full + 3 个 shared」的循环——**合理推断**：`full` 层独立做一次完整稀疏索引（选出 top-2048 token），`shared` 层复用相邻 full 层的索引结果（`index_share_for_mtp_iteration` 暗示索引可跨层/MTP 轮次共享）。
- `index_topk=2048`：每层 Attention 不再看全部 S 个 token，只看索引选出的 2048 个——把 Attention 的 `O(S²)` 复杂度降到 `O(S·2048)`，是 1M 长上下文的算力基础（与 §3 的显存基础互补）。

## 4.3 infra 影响

- 长上下文可行性：MLA 省 KV Cache 显存、DSA 省 Attention 算力，两者合起来才让 1M token 在工程上可服务（合理推断）。
- 实现复杂度：DSA 的稀疏索引在 vLLM/SGLang 等框架里需要定制 kernel，并非所有推理引擎都支持，是部署的潜在门槛（尚待确认，需看 serving 引擎实现）。

---

# 5. RoPE 位置编码（已确认）

```text
rope_theta        : 8e6
rope_interleave   : true
max_position      : 1048576
qk_rope_head_dim  : 64
```

- `rope_theta=8e6` 偏大，配合 1M 上下文做长程衰减调优（已确认）。
- 与 MLA 的关系：RoPE 只作用于 `qk_rope_head_dim=64` 这段解耦 K，`qk_nope=192` 段不带位置、可被权重吸收——这是 MLA 能同时满足「吸收省还原」与「带位置信息」的关键（见 [MLA.md](../推理算法/自注意力模块/存储轴/MLA.md) §3）。

---

# 6. MLP：MoE（已确认）

## 6.1 结构

```text
前 3 层：dense MLP
  × W_up   [6144, 12288]   ×3 (gate/up/down, silu)
  × W_down [12288, 6144]

后 75 层：MoE
  n_routed_experts   = 256    路由专家
  n_shared_experts    = 1      共享专家（每 token 必激活）
  num_experts_per_tok = 8     每 token 选 8 个路由专家
  moe_intermediate_size = 2048  每专家中间维
  topk_method = noaux_tc, norm_topk_prob = true
```

每层 MoE 的每 token 计算量 ≈ `(8 路由 + 1 共享) × 3 × (6144 × 2048)`，而非 dense 的 `3 × (6144 × 12288)`——单 token 激活参数被压低（稀疏激活），是 MoE 省「算力」的本义。

## 6.2 infra 影响

- **权重显存的大头在专家**：256 个专家 × 75 层 × `3 × 6144 × 2048` 参数 ≈ 720B 量级参数（合理推断），W4 下约 360+ GB，与观测到的 282 分片 / 约 375 GB 总权重一致（已确认文件体量）。
- **切分对象**：MoE 专家是 [EP（专家并行）](../模型并行/EP.md) 的天然切分对象——256 个专家可分布到多卡/多机；而 dense 层与注意力更适合 TP。GLM-5.3 的部署通常是 TP（切 MLA 头 + dense）+ EP（切专家）混合（合理推断，需看实际 serving 配置）。
- **激活 int8**：`activation_precision=int8`（W4A8 的 A8），专家激活按 int8 计算，降低访存与算力开销（已确认）。

---

# 7. Embedding 与 LM Head（已确认）

```text
Embedding : [154880, 6144]   （tie_word_embeddings=false）
LM Head   : [6144, 154880]   独立权重，不与 Embedding 共享
```

- 不 tie 意味着多一份 `[154880, 6144]` 的输出权重，W4 下约 0.5 GB，相对专家权重很小。
- LM Head 只在 Decode 每步最后 `[1, H] × [H, V]` 一次，不是热点。

---

# 8. Norm 与残差（已确认）

- RMSNorm，`eps=1e-5`，`attention_bias=false`（QKV 投影无 bias）。
- 残差连接贯穿全层。无特殊 infra 影响。

---

# 9. 量化：W4A8（已确认）

```text
权重   : W4（4-bit，0.5 byte/param）   ← 375GB 权重文件的来源
激活   : int8（activation_precision=int8）
```

infra 影响：

- 权重显存相比 bf16 直接压到 1/4，是大模型能塞进单机多卡的前提。
- 激活 int8 降低 Attention/MLP 的访存与计算开销，但需要 int8 kernel 支持（DSA 稀疏索引 + MLA 吸收路径下的 int8 实现是部署门槛，尚待确认）。

---

# 10. 推理 infra 影响汇总

| 维度         | GLM-5.3 的处理                     | 量级/影响                                                      |
| ------------ | ---------------------------------- | -------------------------------------------------------------- |
| KV Cache     | MLA 低秩压缩，主潜维 512           | 1M token/78 层 ≈ 76 GB（主潜变量，bf16），等价 MHA 需 ~4.6 TB |
| 长上下文算力 | DSA 稀疏索引，top-2048             | Attention 从 O(S²) 降到 O(S·2048)                            |
| 权重显存     | 256 专家 MoE + W4                  | ~375 GB，~700B 参数量级                                        |
| 激活算力     | 每 token 8/256 专家稀疏激活 + int8 | 单 token 激活参数远小于总参数                                  |
| TP 切分点    | MLA 的 Q/KV 潜维、头数 64          | 按 head 或 kv_lora 切（合理推断）                              |
| EP 切分点    | 256 路由专家                       | 专家分布到多卡/多机（合理推断）                                |
| 部署门槛     | DSA + MLA 吸收 + W4A8 int8 kernel  | 需推理引擎定制支持（尚待确认）                                 |

## 交叉关联

- **MLA 张量细节**：见 [自注意力模块/存储轴/MLA.md](../推理算法/自注意力模块/存储轴/MLA.md)，本文的 `kv_lora_rank=512` 就是那篇里 `r_kv` 的实例。
- **PD 分离**：MLA + DSA 使 Prefill（算力密集，DSA 索引开销大）与 Decode（访存密集，KV Cache 由 MLA 压薄）特征差异明显，是 [PD 分离](../其他细节/PD分离/PD分离.md) 的动机之一（合理推断）。
- **并行策略**：TP 切 head、EP 切专家、CP/SP 切长序列（DSA 长上下文下的切分），见 [模型并行](../模型并行/)。

## 尚待确认

- DSA 的 `full`/`shared` 精确切分与索引共享机制（需论文/实现确认）。
- serving 引擎（vLLM/SGLang 等）对 GLM-5.3 MLA+DSA+W4A8 的实际支持路径（需看引擎实现与启动日志）。
- 精确总参数量与单 token 激活参数量（需精确核算或官方 spec）。
