# 1.初识：

跨模型；KVCache传输；同一模型家族；matched-KV

核心：能不能把模型 A 已经算好的 KV Cache，通过一个轻量映射直接变成模型 B 可用的 KV Cache，从而省掉模型 B 的 Prefill？

## 1.1Abstract

跨模型 KV 并不是完全不同的表示空间，它们之间存在可以直接利用的线性结构。

```
Cross-Model KV Cache Transfer

Source Model
已经 Prefill
     ↓
KV Cache
     ↓
Mapper
     ↓
Target KV Cache
     ↓
Target 直接 Decode
```

重点在**Mapper**

abstract中关于其中的数据，我不是十分理解，后续排查

## 1.2Introduction
