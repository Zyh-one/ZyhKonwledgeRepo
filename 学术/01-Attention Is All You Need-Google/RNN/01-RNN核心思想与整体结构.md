# RNN 核心思想与整体结构

本文回答「RNN 是什么、凭什么处理序列、放在语言模型里长什么样」：从隐藏状态递推公式出发，给出 Vanilla RNN 语言模型的整体架构与张量维度约定，并说明它与 Self-Attention 的本质区别。

> 学习定位：面向已了解 Transformer、Token、Embedding 和 LLM 推理链路的读者，以 **Vanilla RNN 自回归语言模型** 为主线，理解 RNN 的序列建模、前向传播、多层结构和推理缓存，并衔接《Attention Is All You Need》。
> 符号约定：$B$ 为 Batch Size，$S$ 为序列长度，$V$ 为词汇表大小，$E$ 为 Embedding 维度，$H$ 为 RNN 隐藏维度，$L$ 为 RNN 层数。除单独说明外，示例省略 Batch 维度。
>
> 本篇是 RNN 系列的第 1 篇，同系列还包括「前向传播与多层堆叠」「自回归推理与状态缓存」「局限性与 Transformer 对比」。

## 1. 背景与核心思想

RNN（Recurrent Neural Network，循环神经网络）是一类面向**序列数据**的网络。其目标不是天生就要"预测下一个 Token"，而是建模当前输入与历史上下文的关系；下一 Token 预测、文本分类、序列标注等都是可能的下游任务。

RNN 最重要的机制是：**当前时间步的隐藏状态来自当前输入与上一时间步隐藏状态的共同作用**。

$$
h_t=\tanh(W_x x_t+W_h h_{t-1}+b)
$$

这意味着，输入 `I love artificial intelligence` 时，最后的 $h_4$ 可以编码此前所有 Token 的部分信息，但并不等于无损保存了全部历史，也不等于 RNN 只能利用最后一个隐藏状态。对于逐位置语言建模，每一个 $h_t$ 都能参与输出预测。

![时间步递归](../../../source/学术/01-Attention%20Is%20All%20You%20Need-Google/RNN/01-RNN核心思想与整体结构/02_时间步递归.png)

**与 Attention 的区别：** Vanilla RNN 并不直接生成一张 Token×Token 的关联权重矩阵，而是把历史信息持续压缩进固定维度状态；Self-Attention 则显式依据 Query 与 Key 计算位置间的权重，再聚合 Value。

## 2. RNN 语言模型的结构

这里以**语言模型**为例，因此会包含 Tokenizer、Vocabulary、Embedding 与 LM Head；RNN 本身不要求必须有词汇表，处理数值时间序列时就可以直接输入特征向量。

![整体架构](../../../source/学术/01-Attention%20Is%20All%20You%20Need-Google/RNN/01-RNN核心思想与整体结构/01_整体架构.png)

一个可理解的示例配置：

| 配置项 | 示例值 | 含义 |
|---|---:|---|
| Vocabulary Size $V$ | 32,000 | 输出词汇表大小 |
| Embedding Dim $E$ | 512 | Token 查表得到的向量维度 |
| Hidden Dim $H$ | 1,024 | 每层循环隐藏状态的维度 |
| Layers $L$ | 3 | 堆叠的 RNN 层数 |
| Sequence Length $S$ | 128 | 本次输入 Token 数量 |

Token IDs 的形状为 $[B,S]$，Embedding 查表后得到 $[B,S,E]$。假设各层隐藏维度均为 $H$，那么 RNN 顶层所有时间步的输出形状为 $[B,S,H]$，LM Head 映射为 $[B,S,V]$（实际推理只取最后一步的 logits 也很常见）。

**重点：Embedding Dim 与 Hidden Dim 并非必须相同。** 第一层 RNN 用输入投影将 $E$ 维向量映射到 $H$ 维隐藏状态。即使在 Transformer 中，Embedding 维度和主干 `d_model` 也不是数学上必须相等；只是常见实现中二者相等，残差主干通常保持同一个维度。
