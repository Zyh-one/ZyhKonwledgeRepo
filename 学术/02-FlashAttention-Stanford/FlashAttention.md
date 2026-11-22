# 1.初识：

IO-aware；tiling（分块）；online softmax；recomputation；HBM / SRAM；block-sparse attention

核心：在**不做任何近似**的前提下，能不能不靠减少 FLOPs，而是靠减少 HBM 与 SRAM 之间的读写次数，让 attention 又快又省显存？

## 1.1Abstract

self-attention 的时间和显存随序列长度 N 平方增长，是长序列 Transformer 的瓶颈。此前的近似 attention 方法（稀疏、低秩）降低了计算复杂度，却常常拿不到 wall-clock 加速——因为它们只盯 FLOPs，忽略了显存访问开销。

FlashAttention 的核心是 **IO-aware**：用 tiling 把 Q/K/V 分块搬进片上 SRAM 计算，避免把 N×N 的 attention 矩阵写回 HBM。IO 复杂度从标准的 Ω(Nd + N²) 降到 O(N²d²M⁻¹)（M 为 SRAM 大小），并给出了下界证明其在一段 SRAM 尺寸范围内最优。

| 场景 | 加速 |
|---|---|
| BERT-large（512） | 端到端 15% |
| GPT-2（1K） | 3× |
| Long Range Arena（1K–4K） | 2.4× |

质量侧：GPT-2 perplexity 改善 0.7，长文档分类提升 6.4 点；Path-X（16K）首次超过随机水平 61.4%，block-sparse 版 Path-256（64K）63.1%。

```
HBM（40GB，1.5TB/s）
  │  分块加载 K/V tile（外层循环）
  ▼
SRAM（每 SM 20MB，约 19TB/s）
  │  再分块取 Q tile（内层循环）
  │  QKᵀ → online softmax 增量归一化 → ·V
  ▼
只把最终 O（N×d）写回 HBM；N×N 中间矩阵从不落地
```

我的关注点：**别把「省 FLOPs」和「省时间」混为一谈**——这是全文的立论起点，也是后面所有 kernel 优化的共同前提。backward 用「存 softmax 归一化因子 + 重算」代替「存 P 矩阵」，用算力换带宽。

## 1.2Introduction

- 现象：GPU 算力增长快于显存带宽，Transformer 里大量算子（elementwise、reduction、softmax）是 memory-bound，性能由 HBM 访问次数决定。
- 标准实现的三步：`S=QKᵀ` 写 HBM → 读回做 softmax 写 `P` → 读回做 `PV`；中间还要为 backward 保存 P，显存 O(N²)。
- 两个关键技巧：(i) **tiling + online softmax**，在不看完整行的前提下增量完成 softmax 归约；(ii) **recomputation**，backward 时在片上重算 attention 而不是从 HBM 读回。
- FLOPs 反而增加了（重算），但 HBM 访问大减，净效果是更快且显存线性。
- 额外贡献：IO 复杂度分析与下界；block-sparse FlashAttention（比 FlashAttention 再快 2–4×，支持 64K）；讨论多 GPU attention、kernel regression 等扩展。
