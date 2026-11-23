# RNN 局限性与 Transformer 对比

本文收束整个 RNN 系列：对比单向 Vanilla RNN 与 Causal Transformer 在信息路径、并行性、推理状态上的差异，列出 RNN 的三类主要困难，并给出七条关键结论速记。

## 6. RNN 的局限性及与 Transformer 的关系

![RNN 与 Transformer](../../../source/学术/01-Attention%20Is%20All%20You%20Need-Google/RNN/04-局限性与Transformer对比/06_RNN与Transformer.png)

| 对比点 | 单向 Vanilla RNN | Causal Transformer |
|---|---|---|
| 历史信息路径 | 通过 $h_{t-1}$ 递归压缩 | 从历史位置的 K/V 表示聚合信息 |
| 训练时序列维度 | 时间步递归依赖，难以充分并行 | Self-Attention 可并行处理已知序列（因果掩码） |
| 自回归生成 | 新 Token 仍逐步生成 | 新 Token 也逐步生成 |
| 推理状态 | 各层固定大小循环状态 | 标准 KV Cache 通常随序列长度增长 |
| 长距离依赖 | 压缩瓶颈、梯度消失/爆炸 | 有直接注意力交互路径，但注意力成本与上下文相关 |

Vanilla RNN 的主要困难包括：

- **时间串行依赖：** 对一个序列，后一个状态要等待前一个状态。
- **长距离历史保留不易：** 全部历史压缩至固定维度，可能遗忘早期信息。
- **训练困难：** 通过时间反向传播（BPTT）可能发生梯度消失或梯度爆炸。

LSTM/GRU 等通过门控机制改善历史信息保留与训练稳定性，但依旧具有循环依赖。2017 年论文《Attention Is All You Need》提出的 Transformer 则以 Attention 机制取代序列建模中的循环和卷积，是理解现代 Transformer 架构的重要起点。

## 7. 关键结论速记

1. **RNN 的核心：** 当前输入 $x_t$ + 上一隐藏状态 $h_{t-1}$ → 当前隐藏状态 $h_t$。
2. **隐藏状态：** 固定维度的历史上下文表示，不是逐 Token 的显式关联权重矩阵。
3. **前向传播：** 同一层跨时间步共享权重；多层之间一般不共享权重。
4. **二维结构：** 横向沿时间递归，纵向沿网络层堆叠。
5. **语言模型：** 可以有 Vocabulary、Tokenizer、Embedding 和 LM Head，但这些不是 RNN 架构本身的必要组成。
6. **推理缓存：** 每层保存最近隐藏状态，缓存规模与历史长度无关；代价是历史信息被压缩。
7. **与 Transformer 的关键差异：** 区别首先在**历史信息交互机制**，而不是 Embedding 和 Hidden Dim 是否相等。
