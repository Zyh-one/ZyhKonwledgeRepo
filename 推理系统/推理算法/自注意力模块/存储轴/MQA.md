# MQA：多查询注意力（Multi-Query Attention）

> 本文是「注意力变种」系列的第 2 篇。MQA 在 MHA 的基础上把 **K/V 共享为所有头共用一组**，Q 仍保持 N 个头。重点对比 K/V 在头维度上的变化。
>
> 关联：[MHA](MHA.md)（基准）、[注意力模块演进](../注意力模块演进.md) §2。

---

# 0. 符号约定（与 MHA 一致）

```text
S : 序列长度
H : 隐藏维度
N : 头数（Query 头数）
d : 每头维度，d = H / N
```

唯一与 MHA 不同的是：**K/V 不再分 N 份，而是只有一份**，所有 Query 头共用。

---

# 1. Q：仍按 N 头切分

Q 的投影与分头和 MHA 完全相同：

```text
X : [S, H]
Q_raw = X × Wq   →  [S, H] × [H, H]  →  [S, H]
Q     : [N, S, d]        （reshape + transpose）
```

Wq 形状仍是 `[H, H] = [H, N·d]`，Q 仍分成 N 个头，保证模型从 N 个维度去关注 token 关联的能力不变（见 [演进 §1](../注意力模块演进.md)）。

---

# 2. K/V：所有头共用一组

MQA 的关键改动在 Wk/Wv：它们不再投影出 N 份，只投影出**一份**，即一个头的维度 `d`：

```text
Wk : [H, d]          （MHA 中是 [H, N·d]）
Wv : [H, d]

K = X × Wk   →  [S, H] × [H, d]  →  [S, d]
V = X × Wv   →  [S, H] × [H, d]  →  [S, d]
```

K/V 没有头维度（或者说头维度为 1），所有 N 个 Query 头都用这同一组 K/V。

---

# 3. 每个头内的 Attention 计算

对第 `i` 个 Query 头：

```text
Q_i : [S, d]
K   : [S, d]      （所有头共用）
V   : [S, d]

Score_i = Q_i × K^T   →  [S, d] × [d, S]  →  [S, S]
Weight_i = Softmax(Score_i + Mask)  →  [S, S]
O_i = Weight_i × V    →  [S, S] × [S, d]  →  [S, d]
```

N 个头共用 K/V，但各自用不同的 Q_i 算各自的 Attention，得到各自的 `O_i`：

```text
O : [N, S, d]
```

随后的拼回与输出投影和 MHA 完全一致：

```text
[N, S, d] → [S, N, d] → [S, H]  × Wo:[H,H]  →  [S, H]
```

---

# 4. KV Cache 形状：缩到 1/N

MQA 下，每层只缓存一组 K/V：

```text
K Cache : [S, d]
V Cache : [S, d]
```

对比 MHA 的 `[N, S, d]`，头维度 `N` 被消去，体积直接降到 **1/N**。Decode 时每步追加的 `k/v` 也只有一份。

这是 MQA 的核心收益：**在不减少 Query 头数（表达力主体）的前提下，把 K/V 的存储与访存压到最低。** 代价是所有头被迫看同一份 K/V 表征，部分维度的区分度丢失。

---

# 5. 小结

```text
X:[S,H]
  × Wq:[H,H]   →  Q:[N,S,d]      （仍分 N 头）
  × Wk:[H,d]   →  K:[S,d]        （只一份，所有头共用）
  × Wv:[H,d]   →  V:[S,d]
  每头用各自 Q_i × 共享 K/V → O:[N,S,d]
  拼回 × Wo    →  Y:[S,H]

KV Cache: [S,d] × 2   ← 对比 MHA 的 [N,S,d] × 2
```

MQA 的本质：**Q 保持 N 头，K/V 压成 1 份共享。** 它是「共享投影」路线的极端形态，也是理解 GQA（分组共享）的起点。
