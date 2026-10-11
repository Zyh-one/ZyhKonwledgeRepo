# GLM-5.3 config.json 逐项梳理

> 本文对 `config.json` 全部 **58 个顶层字段 + 14 个 `quantization_config` 子字段**逐项给出值、含义与 infra 影响，作为字段视角的全量对照手册。模块视角的结构拆解与量级估算见同目录 [GLM-5.3.md](GLM-5.3.md)，机制细节见 [推理算法](../../推理算法/) 各篇——本文只做"字段是什么、管什么"，不重复展开机制。
>
> 数据来源：黄区 cam-train-144 `/opt/models/GLM-5.3-W4A8/config.json`（只读读取，2026-10-10）。同目录的 GLM-5.2-W4A8 与本 config 逐字段 diff 仅 3 处非架构差异（见文末 §9）。字段值本身均**已确认**；字段语义为官方 README 已证实的标**已确认**，其余标推断/存疑。

---

# 1. 模型身份与元数据（11 项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `architectures` | `GlmMoeDsaForCausalLM` | transformers 加载的模型类名：MoE + DSA 稀疏注意力 + 因果 LM | 决定推理引擎按哪套实现类解析权重 |
| `model_type` | `glm_moe_dsa` | 模型类型标识，与架构类配套 | HF hub 分类用 |
| `vocab_size` | `154880` | 词表大小，决定 Embedding 与 LM Head 的行/列数 | 与 tokenizer.json 一致 |
| `tie_word_embeddings` | `false` | 输入 Embedding 与输出 LM Head 不共享权重 | 多一份 `[154880, 6144]` 权重，W8 下约 1 GB |
| `pad_token_id` | `154820` | padding token id | 与第一个 eos 相同（复用），推理 batch 时用于补齐 |
| `eos_token_id` | `[154820, 154827, 154829]` | 3 个结束符 id | 生成循环遇到任一即停；具体语义（text/tool 等）需查 tokenizer，存疑 |
| `use_cache` | `true` | transformers 生成时启用 KV Cache | 推理引擎自管 cache，此字段主要约束 HF 路径 |
| `dtype` / `torch_dtype` | `bfloat16` | 基座权重精度（量化前） | 两个字段同时出现且同值，`dtype` 为导出工具额外写入 |
| `transformers_version` | `5.15.0` | 导出该 config 的 transformers 版本 | 工具链痕迹，非架构信息；5.2 为 `5.12.0` |
| `generate_datetime` | `2026-09-01 12:29:02` | 该量化版本生成时间 | 5.2 为 2026-06-25，两版本相隔两个多月 |
| `pretraining_tp` / `ep_size` | `1` / `1` | 训练/导出时的 TP、EP 切分数 | 均为 1 表示单副本全量导出；`ep_size=1` 即所有 256 专家在同一切分单元内 |

> 注：权重分片 **282 个 safetensors、共 376 GB** 来自目录清单而非 config 字段。

# 2. 层与维度主干（9 项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `num_hidden_layers` | `78` | Transformer 层数 | `indexer_types`/`mlp_layer_types` 数组长度均为 78，交叉自证 |
| `hidden_size` | `6144` | 残差流宽度 D，每层输入输出张量 `[S, 6144]` | 全层不变 |
| `num_attention_heads` | `64` | Q 头数 Hq | MLA 下按 64 头还原 Q |
| `num_key_value_heads` | `64` | KV 头数，**与 Q 头数相等** | 不代表 MHA：MLA 靠低秩潜维省 Cache 而非共享头数（见 [MLA](../../推理算法/自注意力模块/存储轴/MLA.md) §0 判据） |
| `head_dim` | `192` | 头维，等于 `qk_nope_head_dim` 的别名 | 阅读时以 MLA 专字段为准 |
| `v_head_dim` | `256` | V 头维，与 QK 头维不同 | 还原出的 V 为 `[64, S, 256]` |
| `hidden_act` | `silu` | 激活函数，GLU 的门控激活 | 见 [GLU](../../推理算法/MLP模块/GLU/GLU.md) |
| `rms_norm_eps` | `1e-05` | RMSNorm 数值稳定项 | Norm 不改形状，见 §7 |
| `attention_bias` | `false` | QKV 投影无 bias | MLA 权重吸收的前提之一（吸收路径干净） |

另有 `attention_dropout=0.0`（训练期 dropout，推理恒无效）与 `initializer_range=0.02`（初始化标准差，训练遗留）两项，推理均不读。

# 3. MLA 存储轴（5 项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `kv_lora_rank` | `512` | KV 低秩压缩潜维 r_kv，**每 token 每层实际缓存的主体** | 1M 上下文 78 层 bf16 下主潜变量约 76 GB，是 1M 可行的显存基础 |
| `q_lora_rank` | `2048` | Q 低秩压缩潜维 | Q 潜变量 `[S, 2048]` 不缓存，仅当步计算 |
| `qk_nope_head_dim` | `192` | 不带位置的 Q/K 头维 | 可被权重吸收的段 |
| `qk_rope_head_dim` | `64` | RoPE 解耦头维 | 带位置、单独缓存 K_rope，无法吸收 |
| `qk_head_dim` | `256` | 192 + 64，还原后完整 Q/K 头维 | 与 `v_head_dim=256` 凑成 QKV 各 256 |

压缩-还原张量流与吸收机制见 [MLA](../../推理算法/自注意力模块/存储轴/MLA.md)；设计动机见 [MLA动机](../../推理算法/自注意力模块/存储轴/MLA动机.md)。

# 4. DSA 计算轴（9 项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `index_topk` | `2048` | 每个 query 只对索引选出的 top-2048 个 token 做注意力 | `O(S²)` → `O(S·2048)`，1M 长上下文的算力基础 |
| `index_n_heads` | `32` | 索引器头数 | 索引器是独立的一组轻量注意力头 |
| `index_head_dim` | `128` | 索引器头维 | 注意与主注意力的 192/256 区分，两套机制字段都含 `head_dim` 易混 |
| `index_topk_freq` | `4` | full 索引层每 4 层出现一次 | 即官方 IndexShare 机制（已确认，arXiv 2603.12201）：同一索引跨 4 层稀疏注意力复用，1M 上下文下每 token FLOPs 降 2.9× |
| `indexer_types` | 78 项数组 | 逐层标注 `full`/`shared`：前 3 层 full，其后每 4 层 1 个 full | 总计 21 层 full（自算索引）、57 层 shared（复用最近 full 层的索引） |
| `index_share_for_mtp_iteration` | `true` | 索引可跨 MTP 推测解码的迭代轮次复用 | draft 与被验证 token 位置相邻，top-k 集合基本相同 |
| `index_skip_topk_offset` | `3` | 字面为"跳过 top-k 的偏移量 3" | 两种读法见 §8 存疑 |
| `indexer_rope_interleave` | `true` | 索引器自身的 RoPE 采用交错排布 | 与主注意力 `rope_interleave` 同风格 |
| `index_topk_pattern` | `null` | 未启用，推测为备选的 top-k 选法开关 | null 即默认按分数全局选 |

# 5. RoPE 位置轴（3 项 + 2 子项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `rope_parameters.rope_theta` | `8000000` | RoPE 基频 8e6 | 偏大，配合 1M 上下文的远距离衰减调优 |
| `rope_parameters.rope_type` | `default` | 标准 RoPE，无变体 | 无 NTK/YaRN 等外推模式 |
| `rope_interleave` | `true` | 旋转分量的交错排布 | 实现 kernel 需匹配，排布错会导致输出错乱 |
| `max_position_embeddings` | `1048576` | 最大上下文 1M token | 位置编码与 KV 容量的上限依据 |

RoPE 只作用于 `qk_rope_head_dim=64` 的解耦段，`qk_nope=192` 段不带位置可被吸收——这是 MLA「吸收省还原 + 带位置信息」并存的关键，见 [RoPE](../../推理算法/自注意力模块/位置轴/rope.md)。

# 6. MoE 与 MLP 编排（14 项）

| 字段 | 值 | 含义 | 备注 |
| ---- | --- | ---- | ---- |
| `mlp_layer_types` | 78 项数组 | 逐层标注 `dense`/`sparse`：前 3 层 dense、后 75 层 MoE | 与 `first_k_dense_replace`/`moe_layer_freq` 同义的展开形式 |
| `first_k_dense_replace` | `3` | 前 3 层 MLP 为 dense | 浅层 token 未分化、路由不可靠的通行做法 |
| `moe_layer_freq` | `1` | 其余层每层都是 MoE（频率 1/1） | 若为 2 则隔层 MoE |
| `n_routed_experts` | `256` | 路由专家数 | 权重显存大头；EP 的天然切分对象 |
| `n_shared_experts` | `1` | 共享专家数，每 token 必激活 | 与 top-k 选择无关、恒计算 |
| `num_experts_per_tok` | `8` | 每 token 激活的路由专家数 K | 单 token 激活参数 ≈ (8+1)×3×6144×2048/层 |
| `moe_intermediate_size` | `2048` | 每个专家的中间维 | 与 dense 层 `intermediate_size` 各管一摊 |
| `intermediate_size` | `12288` | 仅前 3 层 dense MLP 的中间维 | |
| `scoring_func` | `sigmoid` | 专家打分用独立 sigmoid（非 softmax 竞争） | 分数互不挤压，利于细粒度专家 |
| `topk_method` | `noaux_tc` | 无辅助损失的 bias 修正 top-k（DeepSeek 式） | 训练时 bias 项只影响路由不影响 loss，推理时参与 top-k |
| `norm_topk_prob` | `true` | 选中专家的概率做归一化 | 归一化基准含共享专家权重（推断，见 [MoE](../../推理算法/MLP模块/MoE/MoE.md)） |
| `routed_scaling_factor` | `2.5` | 路由输出乘 2.5 缩放 | 补偿稀疏激活削小的输出量级 |
| `n_group` / `topk_group` | `1` / `1` | DeepSeek 式分组路由的分组数 | =1 即无分组约束，noaux_tc 直接全局 top-8 |
| `moe_router_dtype` | `float32` | router 计算精度 | **GLM-5.3 独有**（5.2 无此字段）：sigmoid 分数差距小，fp32 稳住 top-k 选择；infra 上 router 走独立精度路径，不能顺手压 int8 |

# 7. Norm 与 MTP（1 项 + 概念说明）

- `num_nextn_predict_layers = 1`：附带 **1 层 MTP（Multi-Token Prediction）draft 层**，不计入 78 层主体，实际加载 79 份层权重。推理时用于推测解码（proposal → 验证 → 接受），接受长度较前代 +20%（官方已确认）。机制篇待写，PD 分离下它直接影响 decode 吞吐。
- Norm 相关仅有 §2 的 `rms_norm_eps` 一项——GLM-5.x 用 **RMSNorm + Pre-Norm 残差**（已确认：config 无 LayerNorm 字段、`attention_bias=false` 是其配套风格）。Norm 不改张量形状、无独立 infra 影响，故不设字段组。

# 8. quantization_config（14 个子字段）

SmoothQuant 系量化，**混合精度：专家 W4 + 非专家 W8 + 激活 int8**。

| 子字段 | 值 | 含义 |
| ------ | --- | ---- |
| `quant_method` | `smoothquant` | 量化方法族 |
| `quant_mode` | `SmoothQuant` | 模式标识 |
| `bits` | `8` | 标称位宽（以非专家权重计） |
| `weight_precision` | `int8` | 非专家权重（attention 投影、dense MLP、norm 等）8bit |
| `expert_weight_precision` | `int4` | MoE 专家权重 4bit |
| `experts_weight_bits` | `4` | 同上的冗余表述 |
| `activation_precision` | `int8` | 激活 8bit（WxA8 的 A8） |
| `expert_activation_precision` | `int8` | 专家内激活 8bit |
| `input_quant_method` | `per_token` | 激活逐 token 量化 |
| `group_size` | `128` | 专家权重的分组量化组大小（每 128 个权重共享一组 scale） |
| `only_expert_per_group` | `true` | 仅专家走 per-group W4，其余 per-channel W8 |
| `smooth_value` | `0.5` | smoothing 强度 α（激活与权重难度的均衡系数） |
| `scale_dtype` | `bfloat16` | 量化 scale 的存储精度 |
| `force_use_weightonly_except_expert` | `false` | 未强制非专家走 weight-only 路径 |

infra 要点：376 GB 权重体量 = ~700B 参数中专家压 4bit、其余压 8bit 的结果；per-group W4 需要 grouped int4 GEMM kernel 支持，是部署门槛之一。校准信息在同目录 `smooth_info.json`（act range 来自各自 W8A8 版本，`version.txt` 可溯源）。

# 9. GLM-5.2 对照（3 处差异）

| 差异项 | GLM-5.2-W4A8 | GLM-5.3-W4A8 |
| ------ | ------------ | ------------ |
| `moe_router_dtype` | 无此字段 | `float32` |
| `transformers_version` | `5.12.0` | `5.15.0` |
| `generate_datetime` | `2026-06-25` | `2026-09-01` |

其余 55 个字段（含量化全套）逐字段相同；两模型为同基座纯后训练迭代（官方已确认），**张量变化流程完全一致**，本手册对两者通用。非字段差异：chat 模板（5.3 新增 `reasoning_effort`/`clear_thinking`）、许可证（MIT → glm-5.3 专有）。

# 尚待确认

- `index_skip_topk_offset=3` 的语义：① 前 3 层跳过 top-k 选择、直接全量注意力；② 仅索引器实现偏移参数。需查推理引擎实现。
- 3 个 `eos_token_id` 各自对应的终止语义（text / tool call / 其他），需查 tokenizer_config。
- `norm_topk_prob` 归一化是否计入共享专家权重，需查参考实现。
- 与 `Draft/PD分离/XP1D部署问题.md`「shared expert 4096 维」说法冲突：config 中 `moe_intermediate_size=2048` 且无独立 shared expert 维度字段，4096 可能来自 serving 侧配置或误记。

## 交叉关联

- 模块视角拆解：[GLM-5.3.md](GLM-5.3.md)（层结构、MLA 张量流、KV Cache 体积估算、MoE/量化 infra 汇总）
- 机制篇：[MLA](../../推理算法/自注意力模块/存储轴/MLA.md)、[计算轴概述](../../推理算法/自注意力模块/计算轴/计算轴概述.md)（DSA 属路线②学习型稀疏）、[RoPE](../../推理算法/自注意力模块/位置轴/rope.md)、[MoE](../../推理算法/MLP模块/MoE/MoE.md)、[Prefill/Decode 与 KV Cache](../../推理算法/prefill_decode_kv_cache.md)
