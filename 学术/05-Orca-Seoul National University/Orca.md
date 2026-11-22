# 1.初识：

iteration-level scheduling；selective batching；连续批处理（continuous batching）前身；分布式推理；TP/PP

核心：生成模型一个请求要跑多次迭代（每轮出一个 token），而传统 serving 按「请求粒度」调度——同 batch 里先完成的请求要干等，新请求要等整 batch 结束。能不能改成按「一次迭代」调度？

## 1.1Abstract

现有推理系统（Triton + FasterTransformer 组合）在自回归生成负载上表现差，根因是调度不灵活：batch 一旦下发，中途不能变。

Orca 提出 **iteration-level scheduling**：调度器每次只让执行引擎跑模型的**一个 iteration**，每次返回后检查哪些请求已结束可立刻返回、哪些新请求可加入。再配合 **selective batching** 解决「各请求已处理 token 数不同导致 attention 变长、无法批量」的问题——只对可批量的算子（GEMM/FFN 等）做 batch，Attention 按请求单独算。

评估：GPT-3 175B 上，同延迟水平下吞吐比 FasterTransformer 提升 **36.9×**（可扩展到 341B 参数）。

```
Request-level（旧）:
  [===== batch 全部跑完才返回 =====]
  新请求只能等整批结束；先完成的请求也被扣在批里

Iteration-level（Orca）:
  iter1 [A B C] → iter2 [A B C D] → iter3 [B C D E]
  每次 iteration 结束：完成的立即返回，新到的下一轮即可加入
```

selective batching 的取舍很漂亮：Attention 不带模型参数，批处理省不了参数加载的显存读，所以不批它损失很小；其余算子带权重，批处理能摊薄权重读取。

我的关注点：这篇是 vLLM / Sarathi / DistServe 共同引用的「continuous batching 起点」，要抓住「调度粒度 = 一个 iteration」这一句话。vLLM 的 PagedAttention 解决的是这条调度线下面的显存问题，两者是上下层关系。

## 1.2Introduction

- 背景：GPT 式模型是自回归的，一次请求需多轮迭代，每轮消耗上一轮输出；而 ResNet/BERT 一次前向就出结果，传统 serving 的「请求级调度」假设被打破。
- 旧架构的问题：Triton 负责组 batch、FasterTransformer 负责执行，batch 中途不可变——早完成的请求延迟被拖长，新请求排队时间被放大。
- 两个核心设计：iteration-level scheduling（调度粒度下沉）、selective batching（批处理只作用于选中的算子）。
- 工程要点：为支撑百亿/千亿参数，采用 intra-layer（张量并行）与 inter-layer（流水并行）模型并行，并配套内存管理与跨 worker 流水执行。
- 待读：4 节调度器实现（iteration 级抢占与批次重组）、5 节 selective batching 的 tensor 形状处理。
