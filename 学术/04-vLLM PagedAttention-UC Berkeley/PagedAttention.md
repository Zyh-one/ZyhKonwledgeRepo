# 1.初识：

KV cache 分页；显存碎片；块级共享；copy-on-write；continuous batching；前缀复用

核心：每个请求的 KV cache 大小动态增长、生命周期和长度事先未知，若按「最大长度连续分配」就会产生大量内部/外部碎片且无法共享——能不能借用操作系统虚拟内存分页的思路来管理它？

## 1.1Abstract

高吞吐服务 LLM 需要足够大的 batch，但 KV cache 显存占用巨大且动态伸缩。现有系统把每个请求的 KV cache 放在**连续显存**里，导致碎片和重复冗余，限制 batch size。

PagedAttention 把 KV cache 切成固定大小的 block，block 在物理显存里**不必连续**，用 block table 做逻辑到物理的映射。在此之上实现 vLLM：(1) KV cache 近零浪费；(2) 请求内/跨请求的块级共享。

实测：相同延迟下吞吐比 FasterTransformer、Orca 等 SOTA 高 **2–4×**；序列越长、模型越大、解码算法越复杂，收益越明显。

```
请求的逻辑视图        [blk0][blk1][blk2][blk3]...
                        │     │     │     │
                   block table（逻辑块 → 物理块）
                        ▼     ▼     ▼     ▼
物理显存（不连续）    [p7]  [p2]  [p9]  [p1] ...
固定块大小 → 无外部碎片；按需分配 → 内部碎片仅最后一块
相同前缀的请求共享物理块，写入时 copy-on-write
```

论文给的动机数据很关键：13B 模型在 A100 40GB 上，权重占约 65%、KV cache 占近 30%；而现有系统里真正存放 token 状态的 KV 显存只有 **20.4%–38.2%**，其余全是碎片和预留浪费。

我的关注点：「分页」的类比要落到三个对象上——block ↔ page、token ↔ byte、request ↔ process。这一层抽象后来直接变成了 prefix caching / 分布式 KV 池的接口基础。

## 1.2Introduction

- 成本动机：处理一个 LLM 请求的成本可达传统关键词查询的 10×，吞吐直接等于成本，因此 batch size 是关键。
- 自回归特性：prompt 阶段可并行（矩阵乘，吃算力），生成阶段逐 token、矩阵向量乘，GPU 利用率低、memory-bound，是单请求延迟的主要来源。
- 现有系统的两个低效点：
  1. **碎片**：按请求最大长度（如 2048）连续预分配，实际长度往往短得多；请求存活期间整块被占，短请求也用不上，外部碎片随之放大。
  2. **无法共享**：并行采样、beam search 等一次请求产生多条序列，前缀相同却各存一份。
- 贡献四条：量化内存分配问题、提出 PagedAttention、实现 vLLM（含抢占式调度与块级内存管理）、在多种模型/负载上验证 2–4× 提升。
- 待读：4 节的内存管理细节（block table、swap/recompute 两种抢占）、6.2 节的碎片实验。
