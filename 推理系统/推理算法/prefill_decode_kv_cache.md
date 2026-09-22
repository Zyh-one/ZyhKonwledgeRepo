# Prefill 与 Decode 中 Q/K/V 和 KV Cache 的核心机制

## 1. 核心结论

在自回归 Transformer 推理中，Prefill 和 Decode 的计算方式存在明显差异：

- **Prefill 阶段**：需要处理 Prompt 中的所有 token。
- **Decode 阶段**：每一步只需要处理当前最新生成的一个 token。
- **KV Cache**：保存历史 token 在每一层 Transformer 中已经计算完成的 K/V，从而避免重复计算。

最核心的原因是：

> **Prefill 开始时，Prompt 中所有 token 在每一层对应的 KV Cache 都还没有建立，因此所有 token 都必须逐层计算。**

而到了 Decode 阶段：

> **Prompt 的历史 KV Cache 已经完整建立，并且由于 causal attention，未来 token 不会改变历史 token 的 hidden state 和 K/V，因此只需要计算当前新 token，并把它的 K/V 追加到每一层已有的 KV Cache 中。**

---

## 2. Prefill 阶段为什么需要处理所有 token？

假设 Prompt 长度为 `S`，hidden size 为 `H`。

输入 hidden states：`X ∈ R^{S×H}`。

经过 Q/K/V 投影后：`Q, K, V ∈ R^{S×H}`。

Attention Score 为：`QK^T`。

因此：`[S,H] × [H,S] → [S,S]`。

这个 `[S,S]` 的含义是：

> Prompt 中每一个 token，都需要计算自己对历史 token 的注意力。

例如 Prompt 为：

```text
A B C D
```

在 causal mask 下：

```text
A 只能看 A

B 可以看 A B

C 可以看 A B C

D 可以看 A B C D
```

因此 Prefill 实际上同时计算：

```text
Q_A
Q_B
Q_C
Q_D
```

对应的 Attention。

---

## 3. 为什么不能只计算 Prompt 最后一个 token？

表面上看，为了预测下一个 token，我们最终只需要 Prompt 最后一个位置的输出。

例如：

```text
A B C D
```

只需要 `D` 的最终 hidden state 就可以送入 LM Head，预测下一个 token。

因此很容易产生一个疑问：

```text
既然最终只需要 D，
为什么不能只计算 Q_D？
```

如果 Transformer 只有一层，这种想法看起来似乎可行：

```text
Q_D

×

K_A K_B K_C K_D

→ 得到 D 的 Attention 输出
```

但真实模型有很多层 Transformer。

---

## 4. 多层 Transformer 决定了所有 Prompt token 都必须计算

假设第一层输入为：

```text
A B C D
```

第一层 Attention 后得到：

```text
h_A¹
h_B¹
h_C¹
h_D¹
```

第二层的 K/V 并不是从最初的 embedding 直接生成，而是由第一层的 hidden state 得到：`K_A² = h_A¹ · W_K²`，`V_A² = h_A¹ · W_V²`。

同理：

```text
K_B², V_B²
K_C², V_C²
K_D², V_D²
```

因此，第二层中 `D` 如果需要 Attention：

```text
A B C D
```

就必须拥有：

```text
K_A² K_B² K_C² K_D²
V_A² V_B² V_C² V_D²
```

而这些 K/V 的前提是第一层已经计算出：

```text
h_A¹
h_B¹
h_C¹
h_D¹
```

如果第一层只计算 `D`，那么：

```text
h_A¹
h_B¹
h_C¹
```

都不存在。

于是第二层也就无法得到：

```text
K_A² K_B² K_C²
V_A² V_B² V_C²
```

那么 `D` 在第二层就无法继续读取前面的 A/B/C。

因此：

> **Prefill 必须让 Prompt 中的所有 token 都逐层完成计算。**

整个过程可以理解为：

```text
Prompt: A B C D

        ↓

Layer 1
A B C D 全部计算
        ↓
h_A¹ h_B¹ h_C¹ h_D¹

        ↓

Layer 2
A B C D 全部计算
        ↓
h_A² h_B² h_C² h_D²

        ↓

...

        ↓

Layer N
```

同时，每一层都会建立这一层对应的 KV Cache。

---

## 5. Prefill 的真正目的之一：建立完整的历史 KV Cache

Prefill 并不仅仅是在计算 Prompt 最后一个 token 的输出。

它还有一个非常关键的作用：

> **为整个 Prompt 建立每一层 Transformer 对应的 KV Cache。**

例如 Prompt：

```text
A B C D
```

Prefill 完成后：

```text
Layer 1 KV Cache:

K_A¹ K_B¹ K_C¹ K_D¹
V_A¹ V_B¹ V_C¹ V_D¹


Layer 2 KV Cache:

K_A² K_B² K_C² K_D²
V_A² V_B² V_C² V_D²


...


Layer N KV Cache:

K_Aᴺ K_Bᴺ K_Cᴺ K_Dᴺ
V_Aᴺ V_Bᴺ V_Cᴺ V_Dᴺ
```

因此可以把 Prefill 理解为：

```text
整个 Prompt
    ↓
完整经过所有 Transformer Layers
    ↓
建立所有历史 token 在每一层的 KV Cache
```

---

## 6. Decode 阶段为什么只需要一个 token？

假设 Prefill 已经处理完：

```text
A B C D
```

此时每一层已经拥有：

```text
KV(A B C D)
```

现在要处理新 token：

```text
E
```

此时历史 token：

```text
A B C D
```

在每一层对应的 K/V 都已经计算完成。

因此没有必要重新计算它们。

`E` 进入第一层，只需要计算：`Q_E¹, K_E¹, V_E¹`。

然后把新的 K/V 追加到 Layer 1 的 KV Cache：

```text
原来：

K_A¹ K_B¹ K_C¹ K_D¹
V_A¹ V_B¹ V_C¹ V_D¹

追加：

K_E¹
V_E¹

得到：

K_A¹ K_B¹ K_C¹ K_D¹ K_E¹
V_A¹ V_B¹ V_C¹ V_D¹ V_E¹
```

然后：

```text
Q_E¹
```

与这一层完整的历史 KV 做 Attention。

得到：

```text
h_E¹
```

然后只有 `E` 的 hidden state 继续进入第二层。

---

## 7. Decode 中新 token 如何逐层执行？

Decode 的完整过程是：

```text
E
│
▼
Layer 1
│
├── 计算 Q_E¹
├── 计算 K_E¹
├── 计算 V_E¹
├── K_E¹ / V_E¹ 追加到 Layer 1 KV Cache
└── Q_E¹ 查询 Layer 1 全部历史 KV
│
▼
h_E¹
│
▼
Layer 2
│
├── 计算 Q_E²
├── 计算 K_E²
├── 计算 V_E²
├── K_E² / V_E² 追加到 Layer 2 KV Cache
└── Q_E² 查询 Layer 2 全部历史 KV
│
▼
...
│
▼
Layer N
│
▼
LM Head
│
▼
预测下一个 token
```

所以 Decode 阶段并不是“不经过多层 Transformer”。

相反：

> **当前新 token 仍然需要完整经过所有 Transformer Layers。**

只是历史 token 不需要重新经过这些层。

---

## 8. 为什么历史 KV 可以一直复用？

这是 KV Cache 能够成立的核心。

原因是：

### Causal Attention

在自回归模型中：

```text
A 只能看 A

B 只能看 A B

C 只能看 A B C

D 只能看 A B C D
```

即使后续生成：

```text
E F G
```

过去 token 能看到的范围仍然不会改变。

例如 `C`：

```text
生成 D 前：

C → A B C

生成 D 后：

C → 仍然只能看 A B C

生成 E/F/G 后：

C → 仍然只能看 A B C
```

因此未来 token 不会影响：`h_C^(l)`。

也就是说，历史 token 在任意 Transformer Layer 中的 hidden state 都不会因为未来 token 出现而改变。

---

## 9. 为什么历史 K/V 也不会改变？

某一层的 K/V 通常由上一层 hidden state 投影得到：`K_i^(l) = h_i^(l-1) · W_K^(l)`，`V_i^(l) = h_i^(l-1) · W_V^(l)`。

在推理过程中：

1. 模型参数固定；
2. causal attention 保证未来 token 不改变历史 token 的 hidden state。

所以：`h_i^(l-1)` 不变，并且 `W_K^(l), W_V^(l)` 也不变。

因此：`K_i^(l), V_i^(l)` 自然也不会变化。

所以历史 KV 可以安全缓存并持续复用。

这里需要注意：

> **“模型参数不变”只是其中一个条件，更根本的是 causal attention 保证未来 token 不会影响过去 token 的 hidden state。**

完整逻辑是：

```text
Causal Attention
      +
推理期间模型参数固定
      ↓
历史 token 的 hidden state 不变
      ↓
历史 token 的 K/V 不变
      ↓
KV Cache 可以永久复用
```

---

## 10. 为什么新的 K/V 可以直接追加？

假设已经存在：

```text
A B C D
```

对应某层：

```text
K_A K_B K_C K_D
V_A V_B V_C V_D
```

现在新 token `E` 到来。

只需要计算：

```text
K_E
V_E
```

然后：

```text
[K_A K_B K_C K_D]
          +
        [K_E]

          ↓

[K_A K_B K_C K_D K_E]
```

V 同理。

这与重新把：

```text
A B C D E
```

完整计算一遍后得到的这一层 KV，在数学上是一致的。

原因仍然是：

```text
E 不会反过来改变 A/B/C/D
```

所以：

```text
旧 KV 保持原值
新 KV 只需要 append
```

---

## 11. 为什么 Decode 不需要缓存 Q？

K/V 是未来 token 还会继续使用的。

例如未来生成 `F`：

```text
Q_F
  ↓
查询
  ↓
K_A K_B K_C K_D K_E K_F
```

因此历史 K/V 必须保存。

但历史 Query：

```text
Q_A
Q_B
Q_C
Q_D
Q_E
```

以后不会再被使用。

生成 `F` 时，只需要：

```text
Q_F
```

因此：

```text
K/V → 缓存

Q → 当前 Attention 使用完成后即可丢弃
```

这也是它叫做：

```text
KV Cache
```

而不是：

```text
QKV Cache
```

---

## 12. Prefill 和 Decode 的张量差异

### Prefill

Prompt 长度为 `S`：`Q ∈ R^{S×H}`，`K ∈ R^{S×H}`。

因此：`QK^T`，得到 `[S,S]`。

含义：

> Prompt 中所有 token，同时计算自己对历史 token 的 Attention。

---

### Decode

历史序列长度为 `S`，当前只处理一个新 token：`Q_new ∈ R^{1×H}`。

历史 KV：`K_cache ∈ R^{S×H}`。

于是：`[1,H] × [H,S] → [1,S]`。

含义：

> 当前新 token 查询整个历史序列。

计算完新 token 后，它自己的 K/V 会追加到 Cache 中，因此下一轮：

```text
S → S + 1
```

---

## 13. Prefill 与 Decode 的本质区别

可以将二者压缩成下面两张图。

### Prefill

```text
Prompt:

A B C D
│ │ │ │
▼ ▼ ▼ ▼

Layer 1
所有 token 都计算
│
▼
建立 Layer 1 KV(A B C D)

Layer 2
所有 token 都计算
│
▼
建立 Layer 2 KV(A B C D)

...

Layer N
│
▼
建立 Layer N KV(A B C D)
```

核心：

> **历史 KV 还不存在，因此所有 token 都必须逐层计算。**

---

### Decode

```text
历史已有：

A B C D

每层 KV Cache 已经存在


新 token E
     │
     ▼
Layer 1
只计算 E 的 Q/K/V
K/V append
     │
     ▼
Layer 2
只计算 E 的 Q/K/V
K/V append
     │
     ▼
...
     │
     ▼
Layer N
```

核心：

> **历史 KV 已经存在，因此只需要增量计算当前新 token。**

---

## 14. 最终总结

整个逻辑可以浓缩成三句话：

> **Prefill 必须处理 Prompt 中所有 token，因为 Prefill 开始时，所有 Transformer Layer 中对应的历史 KV Cache 都还没有建立。每一个 token 都必须逐层形成自己的 hidden state，才能生成下一层正确的 K/V。**

> **Decode 只需要处理当前新 token，因为历史 token 在所有 Transformer Layer 中的 KV 已经由 Prefill 或之前的 Decode 步骤计算并缓存。**

> **新的 token 可以直接把自己的 K/V 追加到历史 KV Cache，是因为 causal attention 保证未来 token 不会改变过去 token 的 hidden state，再加上推理阶段模型参数固定，因此历史 K/V 永远不会因为后续 token 的出现而发生变化。**

一句话记忆：

```text
Prefill = 建立历史 KV

Decode = 复用历史 KV + 增量追加新 KV
```
