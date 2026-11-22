# 1.初识：

Transformer；self-attention；multi-head attention；scaled dot-product；positional encoding；encoder-decoder；并行训练

核心：能不能彻底去掉 RNN/CNN 的循环与卷积，只用 attention 完成序列转换（机器翻译），从而把训练并行度提上去？

## 1.1Abstract

序列转换模型的主流做法是 RNN/CNN + encoder-decoder，attention 只是配角。本文提出 Transformer，完全基于 attention，不用循环也不用卷积。WMT 2014 EN-DE 上 28.4 BLEU（比此前最好结果含 ensemble 还高 2 个点）；EN-FR 上 41.8 BLEU，单模型 SOTA，8 张 GPU 训练 3.5 天。迁到英语成分句法分析同样有效。

```
Scaled Dot-Product Attention          Multi-Head Attention
Q,K,V                                 Q,K,V
  │                                     ├─ head₁ ─┐
  ├─ QKᵀ / √d_k                         ├─ head₂ ─┤ concat → W^O
  ├─ (mask) → softmax                   └─ head_h ─┘
  └─ · V  = O                           每个 head 独立做 scaled dot-product
```

单头注意力只能平均化一种关系，multi-head 让模型在多个子空间里并行关注不同位置——这也是后来所有推理系统里「head 维 d_h」的来源。

我的关注点：这篇是纯训练视角，attention 的 O(N²) 计算和 N×N 矩阵是直接落显存的；FlashAttention 省的是这份显存 IO，vLLM 管的是逐 token 累积的 KV cache，两者都是在这篇的公式上做工程。

## 1.2Introduction

- 当时的痛点：RNN 沿序列位置串行计算，`h_t = f(h_{t-1}, x_t)`，样本内无法并行；序列越长、batch 越受显存限制，训练越慢。factorization / conditional computation 只能缓解，去不掉「顺序计算」这个根本约束。
- 既有 attention 几乎都与 RNN 绑定使用，本文是第一个**完全依赖 self-attention**、不接序列对齐 RNN/卷积的 transduction 模型。
- 收益：并行度大幅提高，8×P100 训练 12 小时即达到当时翻译 SOTA。
- 结构：encoder/decoder 各 6 层；每层 = multi-head self-attention + position-wise FFN，外加 residual + LayerNorm；decoder 多一层 cross-attention，且用 mask 防止看到未来 token（自回归解码的雏形）。
- 待读：3.2 节 attention 公式、3.5 节 positional encoding（正弦式），以及 4 节为何 self-attention 在「每层计算量 / 路径长度 / 可并行」三项上占优。
