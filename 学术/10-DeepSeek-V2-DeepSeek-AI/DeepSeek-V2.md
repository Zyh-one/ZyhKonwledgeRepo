# 1.初识：

MLA（Multi-head Latent Attention）；KV cache 低秩压缩；DeepSeekMoE；稀疏激活；236B 总参 / 21B 激活；128K 上下文

核心：MoE 把训练成本压下来，但长上下文的 KV cache 仍是推理瓶颈——能否把 KV 压成一个 latent 向量缓存，在保住性能的同时把 KV cache 砍掉一个数量级？

## 1.1Abstract

DeepSeek-V2 是 MoE 语言模型，**236B 总参数、每 token 激活 21B**，支持 **128K** 上下文。两项核心架构：

- **MLA（Multi-head Latent Attention）**：把 KV cache 低秩压缩成 latent 向量再缓存，推理时上投影还原，显著压缩 KV cache；
- **DeepSeekMoE**：稀疏计算，以经济成本训练强模型。

相对 DeepSeek 67B（Dense）的收益：

| 指标 | 变化 |
|---|---|
| 训练成本 | 降低 **42.5%** |
| KV cache | 减少 **93.3%** |
| 最大生成吞吐 | 提升至 **5.76×** |

预训练语料 8.1T tokens，之后做 SFT + RL。仅 21B 激活参数的情况下，开源模型中仍属第一梯队。

```
标准 MHA：每 token 每层缓存 K、V        → 2 · n_h · d_h 个数
MLA：      只缓存低秩 latent c_KV（+ 解耦的 RoPE key）
           推理时 c_KV × W_UK / W_UV 还原出 K、V
           → 缓存量由 n_h·d_h 级降到 d_c 级
```

我的关注点：这不是「近似压缩」，KV 还原是精确的，省的是**缓存宽度**（存 latent 而不是存 K/V 全量）。和 GQA/MQA 的区别在于：GQA/MQA 靠共享 head 减少 KV 头数，MLA 靠低秩分解 + 解耦 RoPE，表达能力损失更小。附录 D 给了 MHA/GQA/MQA/MLA 的消融，值得对照看。

## 1.2Introduction

- 现状：开源模型（LLaMA、Mixtral 等）性能在涨，但训练成本与推理成本是落地瓶颈。
- 两条主线：MoE 降训练成本（稀疏激活）；MLA 降推理成本（KV cache 与吞吐）。
- 论文的定位：不只报一个模型，而是把「结构设计如何反向决定推理系统成本」讲清楚——KV cache 体积直接决定 batch size，进而决定吞吐。
- 训练侧：8.1T tokens 高质量多源语料；SFT + RL 对齐。
- 待读：2.1.2 低秩 KV 联合压缩、2.1.3 解耦 RoPE（为什么 RoPE 不能直接压进 latent）、2.2 DeepSeekMoE 的 device-limited routing 与负载均衡辅助损失、3.2.3 训练/推理效率实测。
