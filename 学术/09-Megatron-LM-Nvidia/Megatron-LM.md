# 1.初识：

张量并行（tensor parallelism, TP）；intra-layer model parallelism；LayerNorm 位置；activation checkpointing；512 GPU 扩展

核心：单卡显存放不下十亿级参数的模型，如何在**不改框架、不写 C++ / 不换编译器**的前提下做模型并行，并且保持高效率？

## 1.1Abstract

大模型训练受显存限制（权重 + Adam 动量等优化器状态）。Megatron-LM 提出一种简单高效的 **intra-layer（层内）模型并行**：只对 PyTorch 现有 Transformer 实现做少量定向修改，插入几个通信算子即可；与 pipeline 式模型并行（如 GPipe）正交、可叠加。

结果：

- 8.3B 参数模型跑在 **512 张 GPU** 上，全应用持续 **15.1 PetaFLOPs**，相对单卡强基线（V100 32GB，1.2B 参数，39 TFLOPs，30% 峰值）达到 **76% 扩展效率**；
- GPT-2 8.3B：WikiText103 perplexity **10.8**（此前 SOTA 15.8），LAMBADA **66.5%**（SOTA 63.2%）；
- BERT 3.9B：RACE **90.9%**（SOTA 89.4%）。

一个重要经验结论：BERT 类模型变大时会退化，**LayerNorm 与残差的放置顺序**必须调整，否则规模上去精度反而下降。

```
MLP:  Y = GeLU(X·A)·B
       A 按列切 → [A₁ | A₂] 分到两张卡，各自算 GeLU(X·A_i)
       B 按行切 → 各卡乘以自己的行块，再 all-reduce 求和
       前向 1 次 all-reduce，反向 1 次 all-reduce

Attention: 多头天然可分 → 每个 head 分到不同卡，输出投影按行切
```

我的关注点：TP 的通信量是每层 2 次 all-reduce（前向/反向各一），所以**强依赖 NVLink/高带宽互联**——这解释了为什么后面 DistServe 说 TP 不适合商品网络、要换 PP。这条因果链值得单独记一笔。

## 1.2Introduction

- 背景：更大模型在 NLP 上持续涨点，但超出单卡显存；activation checkpointing 与 Adam 状态进一步压缩可用空间。
- 既有方案：GPipe / Mesh-TensorFlow 提供模型并行框架，但需要重写模型、依赖自研编译器，落地成本高。
- 本文思路：利用 Transformer 自身的结构（FFN 的两层线性、multi-head 的天然可切分）做层内切分，**改动最小化**。
- 两种并行范式定位：data parallelism 切 mini-batch；model parallelism 切显存与计算。本文做后者中的 tensor 并行，与 layer-wise pipeline 并行互补。
- 贡献：极简实现（仅 PyTorch 插通信）、512 GPU 上 76% 扩展效率的系统性实证、更大模型持续涨点的证据、开源代码与训练/评测流水线。
- 待读：3 节 MLP/Attention 的切分公式与通信原语、4 节 LayerNorm 放置的消融（Post-LN vs Pre-LN 式改法）。
