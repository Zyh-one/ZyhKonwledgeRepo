详细

# Transformer 推理中的 Token 自回归生成与张量流

> 本文只讨论最小推理闭环：
> **一段 Prompt 如何进入 Transformer，经过一次前向计算生成第一个 Token，并继续自回归生成后续 Token。**
>
> 为了突出主线，暂时作如下简化：
>
> - Transformer Layer 数量：1
> - Batch Size：1
> - 只考虑单头 Self-Attention
> - 不讨论 TP / SP / DP / EP
> - 不讨论 PD 分离
> - 重点关注 Token、Hidden State、Q/K/V、KV Cache、LM Head 的张量变化

---

## 1. 从 Prompt 到 Token

假设输入：

```text
我 喜欢 学习 AI
```

此时模型的tokenizer为第一个处理prompt的模块，每个模型都有自己的tokenizer，不同模型的tokenizer的设计也基本不同，这也是不同模型之间的token不互通的根因

## 1.1 tokenizer（分词器）

-----将原始Prompt拆分为多个连续token

Tokenizer 是将文本切分为离散 Token 并映射为 Token ID 的组件；每一段 Prompt 在进入模型前都会先经过 Tokenizer。

tokenizer中需要区分两个参数：

* 词表大小 V 由 Tokenizer 决定，限定了 Token ID 的取值范围；
* 隐藏维度 H 是模型配置的超参数，属于模型而非 Tokenizer；其含义是：每一个 Token 在后续 Embedding 之后都会被表示为一个长度为 H 的向量（即一个 H 维的张量），H 就是这个向量有多长。二者共同决定后续 Embedding Matrix 的形状 `[V, H]`。

Tokenizer 将其编码为：

```text
[t1, t2, t3, t4]
```

其中每个元素是一个 Token ID。Token ID 本身只是唯一标识索引，作用是在下一步通过 Embedding 取出该 Token 对应的 Hidden State；它不参与后续 Self-Attention 的相关计算。

---

## 2. Embedding：Token ID → Hidden State

Embedding Matrix 是模型内部的向量表，它的唯一作用就是把离散的 Token ID 映射为连续的 Hidden State，这一点也完全可以从Embedding Matrix的维度中看出

模型内部有 Embedding Matrix：

```text
W_embedding: [V, H]
```

每个 Token ID 对应其中一行。

因此：

```text
prompt = [t1, t2, t3, t4, ....]
        ↓
Embedding Matirx
        ↓
X: [S, H]；S为序列长度，len(prompt)
```

此时 `X` 是一个 `[S, H]` 的矩阵张量，后续运算都把它作为整体张量处理。为便于按位置理解，可将其按行拆解为：

![X：[S, H] 张量矩阵，S=4 行、每行为一个 H 维向量](images/embedding_X_matrix.png)

其中每个 `xi` 都是一个长度为 `H` 的向量。但需注意，`x1~x4` 只是 `X` 的各行视图，`X` 本身仍是一个 `[S, H]` 张量。

从此以后，Transformer 主要处理 Hidden State，而不是 Token ID。

---

## 3. 进入 Transformer Layer

一层 Transformer 主要由 Self-Attention 与 MLP 两个子模块组成，并配合残差连接（Residual）与归一化（Norm）。在本章节中，只需要把Self-Attention，MLP，残差连接，归一化理解为数学计算过程，不讨论其出现原因，同时牢记，**在本章节中，Prompt输入张量X，在经过这些模块的计算时，维度始终保持不变**

张量`X: [S, H]`输入，经过一个 Transformer Layer：

批注

```text
X
↓
Self-Attention
↓
Residual / Norm
↓
MLP
↓
Residual
↓
Y
```

张量X，输出 Shape 始终保持一致，直到最后一步LMHead（生成next token的概率分布）：

```text
[S, H] → [S, H]
```

经过多次最终的输出可以写成：

```text
Y = [y1, y2, y3, y4, ...]
```

每个 `yi` 都和原始Prompt X中token一一对应，只不过其中的每个token都是经过**上下文融合**后的 Hidden State，这样做的目标是，提取token间的关联信息，为预测下一个token做准备

后续章节会逐一梳理 Self-Attention 内部的 Q/K/V、Attention 计算以及 MLP 的细节。

---

## 4. Self-Attention 中的 Q / K / V

Self-Attention 的第一步，是用三个权重矩阵 Wq、Wk、Wv 分别对输入张量 X 做矩阵乘法，从而得到 Q、K、V：

```text
Q = X × Wq
K = X × Wk
V = X × Wv
```

在当前简化模型中：

```text
X : [S, H]
Wq: [H, H]
Wk: [H, H]
Wv: [H, H]
```

因此：

```text
Q: [S, H]
K: [S, H]
V: [S, H]
```

也可以表示为：

```text
Q = [q1, q2, q3, q4]
K = [k1, k2, k3, k4]
V = [v1, v2, v3, v4]
```

---

## 5. Token 之间如何建立注意力关系

Self-Attention 通过下面的公式来计算 Token 之间的注意力关系——让每个 Query 与所有 Key 做点积，得到该 Query 对每个 Key 的注意力分数：

计算：

```text
Q × K^T
```

Shape：

```text
[S, H] × [H, S]
        ↓
      [S, S]
```

这个 `[S,S]` 矩阵表示每个 Query Token 对每个 Key Token 的注意力分数。

对于 Decoder-only 模型，由于采用自回归生成——逐个预测下一个 Token，每个位置在计算注意力时只能看到自己及其之前的 Token，不能看到尚未生成的未来 Token；因此需要 Causal Mask 屏蔽上三角（未来位置），使注意力分数矩阵呈下三角分布：

```text
       K1  K2  K3  K4

Q1     ✓   ×   ×   ×
Q2     ✓   ✓   ×   ×
Q3     ✓   ✓   ✓   ×
Q4     ✓   ✓   ✓   ✓
```

因此，第 4 个 Token 对应的HiddenSize是集合前面3个token的相关信息

举例来说，对于第 4 个位置 Q4，经过 Softmax 后它对 [K1, K2, K3, K4] 的注意力权重可能是 [0.1, 0.2, 0.3, 0.4]（总和为 1）；那么 Q4 的注意力输出就是对应 V 的加权和：y4 = 0.1·v1 + 0.2·v2 + 0.3·v3 + 0.4·v4。权重越大的位置，其 V 对 y4 的贡献越大，这就是“融合其它 Token 相关信息”的含义。

Softmax 的作用很简单：把上面得到的一组注意力分数归一化为一个概率分布（每个分数变为正数且总和为 1），分数越高的位置权重越大，表示该 Query 对该 Key 的关注度越高。

经过 Softmax 后：

```text
AttentionWeight（自注意力权重）: [S,S]
```

再与：

```text
V: [S,H]
```

相乘：

```text
[S,S] × [S,H]
      ↓
    [S,H]
```

最终得到 Attention Output。这就是一次完整 Self-Attention 计算的结果：Output 中每个位置的向量都不再只是该 Token 自身的表示，而是融合了它所能看到的其它 Token 的相关信息（融合权重由注意力分数决定）。

---

## 6. MLP 后仍然得到 `[S,H]`

Attention 输出继续经过 MLP。MLP 内部并非保持维度不变，需要先做**升维**（把隐藏维度从 H 放大到更大的中间维度，常见为 4H，以扩大表达容量），经非线性激活后再做**降维**（从中间维度投影回 H）；因此输入输出维度都保持 [S, H]：

其内部并非一个黑盒，而是依次经过升维矩阵、非线性激活、降维矩阵三步：

```text
[S,H]
  ↓  × W_up   （升维矩阵，[H, 4H]）
[S, 4H]
  ↓  非线性激活（如 GELU / ReLU）
[S, 4H]
  ↓  × W_down （降维矩阵，[4H, H]）
[S,H]
```

其中 W_up 把 H 维投影到 4H 维（升维，扩大表达容量），W_down 再把 4H 维投影回 H 维（降维），中间的非线性激活为 MLP 引入非线性表达能力。

因此整个 Transformer Layer 最终输出：

```text
Y: [S,H]
```

其中最关键的是最后一个位置：

```text
y_last: [H]
```

因为当前任务是预测：

```text
t1 t2 t3 t4 → ?
```

---

## 7. LM Head：Hidden State → 下一个 Token

到这一步之前，Prompt 张量 X 已经依次经过了多层 Transformer 的处理（本篇为简化只画了一层，真实模型有几十层），但无论经过多少层，**进入 LM Head 之前的张量维度始终保持 [S, H]**，假设经过多层transformer的处理后，原始Prompt张量X变为张量Y：[S,H]

LM Head 本质上是一个线性变换层，其目标就是预测下一个token，后面详细介绍它是如何预测出下一个token的？

由于当前任务是预测下一个 Token，只有最后一个位置需要参与预测，因此这里只取张量 Y 的最后一个 token 的 Hidden State（记为 `y_last: [1, H]`），后续直接以这个 `[1, H]` 张量作为 LM Head 的输入。

批注-zyh：关于

它持有一个权重矩阵 **`W_lm: [H,V]`**，与张量Y: [S,H]相乘，该操作将张量 Y 投影到词表维度 V 上，得到每个位置在词表上的预测分数。

`Y: [S, H] × W_lm: [H, V] → Logits: [S, V]`

理论上每一个位置都会得到 Vocabulary 上的预测分数。

但推理时只需要最后一个位置：

```text
logits[-1]: [V]
```

它表示：Vocabulary 中每个 Token 成为下一个 Token 的分数。

拿到最后一个位置在词表上的预测分数后，需要经过采样环节，从词表中决定最终输出哪个 Token。

经过：

```text
Softmax / Temperature / Top-k / Top-p / Sampling
```

最终从模型的词汇表中选取t5

于是：

```text
t1 t2 t3 t4
        ↓
Transformer
        ↓
LM Head
        ↓
t5
```

这就是模型生成的第一个新 Token。

---

## 8. 第一次 Forward 同时建立 KV Cache

在刚才计算 Prompt 时，我们已经得到：

```text
K = [k1, k2, k3, k4]
V = [v1, v2, v3, v4]
```

这些张量不会立即丢弃，而是保存为：

```text
K Cache = [k1, k2, k3, k4]
V Cache = [v1, v2, v3, v4]
```

这一步非常关键。

因为后续生成 Token 时，没有必要重新计算历史 Token 的 K/V。

---

## 9. 开始自回归生成第二个 Token

> 说明：从本节起，S 表示当前 KV Cache 中的序列长度（Prefill 后为初始 Prompt 长度，每生成一个 Token 递增 1），与第 1 节中 S=4 的初始赋值是动态递增关系。

现在已有序列：

```text
t1 t2 t3 t4 t5
```

要生成`t6`，但是模型不再重新计算 `t1~t4`。

批注-zyh：这里需要补充，为什么只拿最新生成的t5作为新的输入就行？按照之前的介绍，原本需要将整个新生成的序列(`t1 t2 t3 t4 t5`)作为新一轮的输入，重复执行之前的计算流程，所以这里需要补充为什么只取t5？你可以参考

只把最新生成的 `t5` 作为新的输入。

Embedding 后：

```text
x5: [1,H]
```

进入同一个 Transformer Layer：

```text
q5 = x5 × Wq
k5 = x5 × Wk
v5 = x5 × Wv
```

得到：

```text
q5: [1,H]
k5: [1,H]
v5: [1,H]
```

其中：

```text
k5、v5
```

追加进入 KV Cache：

```text
K Cache:
[k1,k2,k3,k4]
        ↓
[k1,k2,k3,k4,k5]

V Cache:
[v1,v2,v3,v4]
        ↓
[v1,v2,v3,v4,v5]
```

---

## 10. Decode 时的新 Query 如何使用历史上下文

新的 Query：

```text
q5: [1,H]
```

与整个历史 K Cache 做 Attention：

```text
q_new [1,H]
×						→  				Attention Score [1,S]
K_cache^T [H,S]
```

这意味着：虽然当前只重新计算了 t5，但 t5 仍然可以访问 t1~t5 的历史上下文。

再执行：

```text
AttentionWeight [1,S]
×								→   			Attention Output [1,H]
V_cache [S,H]
```

随后经过 MLP，依旧为[1,H]维度，最后再进入 LM Head：

```text
[1,H] × [H,V]  = [1, V]
```

Sampling 得到：

```text
t6
```

---

## 11. 后续 Token 完全重复这一过程

生成 `t6` 后：

```text
t6
↓
Embedding
↓
q6 / k6 / v6
↓
k6、v6 追加到 KV Cache
↓
q6 与整个 K Cache 做 Attention
↓
Transformer Output
↓
LM Head
↓
t7
```

不断循环：

```text
Prompt
↓
t5
↓
t6
↓
t7
↓
t8
↓
...
```

直到 `EOS` 或者达到最大输出长度。

---

## 12. 整个自回归过程的核心

第一次处理 Prompt：

```text
t1 t2 t3 t4
      ↓
Embedding
      ↓
[S,H]
      ↓
Transformer
      ↓
建立 K/V Cache
      ↓
取最后一个 Hidden State
      ↓
LM Head
      ↓
t5
```

随后每一步：

```text
最新 Token
   ↓
Embedding
   ↓
[1,H]
   ↓
计算新的 q/k/v
   ↓
k/v 追加到 KV Cache
   ↓
q 访问整个历史 KV Cache
   ↓
Transformer
   ↓
LM Head
   ↓
下一个 Token
```

因此可以把大模型自回归推理理解成：

> **第一次需要处理整段 Prompt；之后每生成一个 Token，只重新计算新 Token 自己的状态，而历史上下文通过 KV Cache 保留下来。**

也正因为“第一次处理整段 Prompt”和“后续逐 Token 生成”的执行特征明显不同，才进一步产生了 Prefill 与 Decode 两个阶段，并为后面的 **PD 分离** 提供了基础。

建议-zyh：第 9 节起 S 改为表示当前 KV Cache 长度（动态递增），与第 1 节 S=4 的初始 Prompt 长度语义不同，后续可显式区分（如用 S_cache）以避免混淆。
建议-zyh：第 4 节可补充说明 Wq/Wk/Wv 与 Embedding Matrix 同属模型在预训练中学习到的权重矩阵，强化“模型持有可学习参数”这一主线。
