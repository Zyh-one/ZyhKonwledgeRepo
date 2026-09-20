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

批注-zyh：什么是tokenizer？简短介绍，大致含义每一个不同的模型都是不同tokenizer，每一轮prompt都会被tokenizer，同时tokenizer内部又包含hidden_size和`Vocabulary Size`参数，同时你需要强调这这些参数的含义

Tokenizer 是将文本切分为离散 Token 并映射为 Token ID 的组件；不同模型通常使用各自训练好的 Tokenizer，因此词表与切分规则各不相同。每一段 Prompt 在进入模型前都会先经过 Tokenizer。需要区分两个参数：词表大小 V 由 Tokenizer 决定，限定了 Token ID 的取值范围；隐藏维度 H 是模型配置的超参数，属于模型而非 Tokenizer。二者共同决定后续 Embedding Matrix 的形状 `[V, H]`。

Tokenizer 将其编码为：

```text
[t1, t2, t3, t4]
```

其中每个元素是一个 Token ID。Token ID 本身只是离散整数索引，作用是在下一步通过 Embedding 取出该 Token 对应的 Hidden State；它不参与后续 Self-Attention 的相关计算。

设：

```text
S = 4       # 当前序列长度
H = 8       # Hidden Size
V = 10000   # Vocabulary Size
```

批注-zyh：“`[t1, t2, t3, t4]`”中的元素为token_id，其作用就是为后续定位获取每个token的hidden_size，token_id是不会参与后续自注意力的相关计算


---

## 2. Embedding：Token ID → Hidden State

批注-zyh：强调Embedding Matrix的出现原因，为什么由模型持有，而非tokenizer？

Embedding Matrix 是模型在预训练中学习到的连续语义向量表，它把离散的 Token ID 映射为连续的 Hidden State。正因为它是可学习的参数并承载语义表示，所以由模型持有，而不是只负责文本切分的 Tokenizer。

模型内部有 Embedding Matrix：

```text
W_embedding: [V, H]
```

每个 Token ID 对应其中一行。

因此：

```text
[t1, t2, t3, t4]
        ↓
Embedding
        ↓
X: [S, H]
```

批注-zyh：这里不要把x看成x1,x2.....，你需要强调此时的x是一个[s,h]的矩阵张量

此时 `X` 是一个 `[S, H]` 的矩阵张量，后续运算都把它作为整体张量处理。为便于按位置理解，可将其按行拆解为：

```text
x1
x2
x3
x4
```

其中每个 `xi` 都是一个长度为 `H` 的向量。但需注意，`x1~x4` 只是 `X` 的各行视图，`X` 本身仍是一个 `[S, H]` 张量。

从此以后，Transformer 主要处理 Hidden State，而不是 Token ID。

---

## 3. 进入 Transformer Layer

批注-zyh：后续统一换为S,H,V，不要用4和8等具体举例数值，容器产生歧义

输入：

```text
X: [S, H]
```

经过一个 Transformer Layer：

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

输入输出 Shape 保持：

```text
[S, H] → [S, H]
```

输出可以写成：

```text
Y = [y1, y2, y3, y4]
```

每个 `yi` 都表示对应 Token 在经过上下文融合后的 Hidden State。

批注-zyh：这一小节是可以简单先梳理一个transformer的组成模块，同时简单强调经过一层transformer的张量维度不变，因为后续会在正对transformer内部模型进行逐一梳理

一层 Transformer 主要由 Self-Attention 与 MLP 两个子模块组成，并配合残差连接（Residual）与归一化（Norm）。经过一层 Transformer 后，张量维度保持不变，仍为 `[S, H]`；后续章节会逐一梳理 Self-Attention 内部的 Q/K/V、Attention 计算以及 MLP 的细节。

---

## 4. Self-Attention 中的 Q / K / V

Self-Attention 首先执行：

```text
Q = XWq
K = XWk
V = XWv
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

对于 Decoder-only 模型，还需要 Causal Mask：

```text
       K1  K2  K3  K4

Q1     ✓   ×   ×   ×
Q2     ✓   ✓   ×   ×
Q3     ✓   ✓   ✓   ×
Q4     ✓   ✓   ✓   ✓
```

因此，第 4 个 Token 可以利用：

```text
t1 + t2 + t3 + t4
```

的信息。

经过 Softmax 后：

```text
AttentionWeight: [S,S]
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

最终得到 Attention Output。

---

## 6. MLP 后仍然得到 `[S,H]`

Attention 输出继续经过 MLP：

```text
[S,H]
  ↓
MLP
  ↓
[S,H]
```

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

LM Head 的权重可以写成：

```text
W_lm: [H,V]
```

因此：

```text
Y: [S,H]
×
W_lm: [H,V]

→

Logits: [S,V]
```

理论上每一个位置都会得到 Vocabulary 上的预测分数。

但推理时只需要最后一个位置：

```text
logits[-1]: [V]
```

它表示：

```text
Vocabulary 中每个 Token 成为下一个 Token 的分数。
```

经过：

```text
Softmax / Temperature / Top-k / Top-p / Sampling
```

最终得到：

```text
t5
```

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

要生成：

```text
t6
```

模型不再重新计算 `t1~t4`。

只把最新生成的：

```text
t5
```

作为新的输入。

Embedding 后：

```text
x5: [1,H]
```

进入同一个 Transformer Layer：

```text
q5 = x5Wq
k5 = x5Wk
v5 = x5Wv
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
×
K_cache^T [H,S]

→

Attention Score [1,S]
```

这意味着：

```text
虽然当前只重新计算了 t5，
但 t5 仍然可以访问 t1~t5 的历史上下文。
```

再执行：

```text
AttentionWeight [1,S]
×
V_cache [S,H]

→

Attention Output [1,H]
```

随后经过 MLP：

```text
[1,H]
```

再进入 LM Head：

```text
[1,H] × [H,V]
      ↓
    [1,V]
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

直到：

```text
EOS
```

或者达到最大输出长度。

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
