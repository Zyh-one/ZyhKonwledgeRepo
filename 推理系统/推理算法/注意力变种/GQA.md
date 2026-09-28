# GQA：分组查询注意力（Grouped-Query Attention）

> 本文是「注意力变种」系列的第 3 篇。GQA 是 MHA 与 MQA 的折中：**把 N 个 Query 头分成 G 组，每组内共用一组 K/V**。`G=N` 退化为 MHA，`G=1` 退化为 MQA。
>
> 关联：[MHA](MHA.md)、[MQA](MQA.md)、[注意力变种概述](注意力变种概述.md) §3。

---

# 0. 符号约定

```text
S : 序列长度
H : 隐藏维度
N : Query 头数
d : 每头维度，d = H / N
G : KV 组数（1 ≤ G ≤ N，且 G 整除 N）
   group_size = N / G   （每组内有几个 Query 头共享同一组 K/V）
```

GQA 引入了一个新的自由度 `G`：K/V 不再是「每头一份」（G=N）或「全局一份」（G=1），而是「每 group_size 个头共用一份」。

---

# 1. Q：仍按 N 头切分

Q 的投影与分头与 MHA/MQA 一致：

```text
X : [S, H]
Q_raw = X × Wq  →  [S, H] × [H, H]  →  [S, H]
Q     : [N, S, d]
```

Wq 仍是 `[H, H]`，Query 始终保持 N 头，表达力的主体不动。

---

# 2. K/V：按 G 组投影

Wk/Wv 只投影出 G 份（G 组），而不是 N 份：

```text
Wk : [H, G·d]        （MHA 是 [H, N·d]，MQA 是 [H, d]）
Wv : [H, G·d]

K_raw = X × Wk  →  [S, H] × [H, G·d]  →  [S, G·d]
V_raw = X × Wv  →  [S, H] × [H, G·d]  →  [S, G·d]
```

分头（组）：

```text
K_raw : [S, G·d]
       ↓ reshape (G, d)
       [S, G, d]
       ↓ transpose
K     : [G, S, d]
V     : [G, S, d]
```

K/V 的头维度长度是 `G`，介于 MHA 的 `N` 和 MQA 的 `1` 之间。

---

# 3. 每个头内的 Attention：组内共享 K/V

第 `i` 个 Query 头（`i = 0..N-1`）归属的组号为：

```text
g(i) = i // group_size      （group_size = N / G）
```

取出该组的 K/V：

```text
Q_i       : [S, d]
K_{g(i)}  : [S, d]
V_{g(i)}  : [S, d]

Score_i = Q_i × K_{g(i)}^T   →  [S, d] × [d, S]  →  [S, S]
Weight_i = Softmax(Score_i + Mask)
O_i = Weight_i × V_{g(i)}    →  [S, S] × [S, d]  →  [S, d]
```

同一组内的 `group_size` 个 Query 头共用同一组 K/V，但各自用不同的 `Q_i` 算各自输出。N 个头输出汇总：

```text
O : [N, S, d]
```

拼回与输出投影同 MHA：

```text
[N, S, d] → [S, H]  × Wo:[H,H]  →  [S, H]
```

---

# 4. KV Cache 形状：G/N

GQA 下，每层缓存 G 组 K/V：

```text
K Cache : [G, S, d]
V Cache : [G, S, d]
```

体积为 MHA 的 **G/N**：

- `G = N` → `[N, S, d]`，即 MHA；
- `G = 1` → `[S, d]`，即 MQA；
- 中间取值在表达力与显存之间折中，这是 GQA 成为新一代基座主流的原因。

Decode 时每步追加 1 组 `k/v`，Cache 在 S 维增 1，组维度 `G` 保留。

---

# 5. 退化关系一览

```text
G = N   →  每组只含 1 个头，K/V 各 N 份  →  MHA
1 < G < N  →  组内 group_size 个头共享    →  GQA（折中）
G = 1   →  所有头一组，K/V 各 1 份        →  MQA
```

张量上的统一视角：**K/V 的头维度长度 = G**。MHA/MQA 都是 GQA 在 `G=N` 与 `G=1` 两端的特例。

---

# 6. 小结

```text
X:[S,H]
  × Wq:[H,H]     →  Q:[N,S,d]        （N 头）
  × Wk:[H,G·d]   →  K:[G,S,d]        （G 组）
  × Wv:[H,G·d]   →  V:[G,S,d]
  第 i 个 Q 头用第 i//(N/G) 组 K/V → O_i:[S,d]
  汇总 O:[N,S,d] → 拼回 [S,H] × Wo → Y:[S,H]

KV Cache: [G,S,d] × 2   ← MHA 的 G/N，MQA 的 G 倍
```

GQA 的本质：**Q 保持 N 头，K/V 按 G 组共享。** 它是「共享投影」路线的主流折中形态，也因其分组结构，与后续 [模型并行 TP](../../模型并行/TP.md) 按 head 切分天然契合。
