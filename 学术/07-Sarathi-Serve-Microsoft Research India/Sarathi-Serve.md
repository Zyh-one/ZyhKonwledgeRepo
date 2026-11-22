# 1.初识：

chunked prefill；stall-free batching；TBT（time-between-tokens）；pipeline bubble；吞吐-延迟权衡

核心：prefill 优先会打断 decode 造成数秒级「generation stall」，decode 优先又浪费吞吐——能否在不停下 decode 的前提下把 prefill 塞进 batch，同时拿到高吞吐和低 TBT？

## 1.1Abstract

LLM 请求分两段：prefill 处理整个 prompt（算力密集、延迟高），decode 逐 token 生成（带宽密集、单次计算量小，适合 batching）。二者混在一个 batch 里就会互相干扰。

论文把现有调度分成两类并指出各自的坑：

| 策略 | 代表 | 问题 |
|---|---|---|
| decode 优先 | FasterTransformer（请求级 batching） | 吞吐差：早完成的请求让 batch 缩水，仍要等最后一个 |
| prefill 优先 | Orca / vLLM（iteration 级 + 急切调度 prefill） | 延迟差：长 prefill 打断 decode，造成 generation stall |

Sarathi-Serve 的两个机制：

- **chunked-prefills**：把长 prefill 切成等计算量的 chunk，分多个 iteration 完成；
- **stall-free scheduling**：每个 iteration = 正在进行的 decode + 一个（或多个）prefill chunk，且 prefill token 数有上限（throttle），保证单 iteration 时长有界、与 prompt 总长基本无关。

收益：Mistral-7B 单 A100 **2.6×**、Yi-34B 双 A100 **3.7×** serving capacity；Falcon-180B 配合流水并行达 **5.6×**。

```
vLLM（prefill 优先）:
  decode decode [======== 长 prefill ========] decode ...   ← 停顿数秒
Sarathi（stall-free）:
  iter: [decode… | prefill chunk ≤ budget]  [decode… | chunk]  ...
        每轮计算量近似均匀 → TBT 稳定、流水气泡少
```

额外好处：hybrid batch 计算量均匀，做流水并行的 micro-batch 时各段时长接近，pipeline bubble 显著减少。

我的关注点：这和 DistServe 是同一问题的两条路线——Sarathi 在**同一组 GPU 上做时间维度解耦**（chunk + 限流），DistServe 做**空间维度解耦**（不同 GPU）。对比阅读这两篇最有价值。

## 1.2Introduction

- 背景：推理已成主流 GPU 负载，吞吐决定成本、延迟决定体验，二者都要。
- 现状：batch 能提吞吐，但现有 batching 方式必然牺牲吞吐或延迟之一（Figure 2 的三分法：decode 优先 / prefill 优先 / disaggregated）。
- Orca 式 iteration-level batching 改善了吞吐，却没解决 prefill 抢占 decode 的问题，也没解决 PP 部署下的 pipeline bubble。
- 两条设计原则：单 iteration 的 prefill token 量设上限（bound latency）；新请求只以「chunk」形式加入正在跑的 batch（不打断 decode）。
- 实验覆盖单卡、TP、PP、商品以太网多种部署，强调「对在线推理普遍有效」。
- 待读：3 节调度算法（chunk 大小如何定、SLO 如何映射）、4 节与 PP micro-batching 的结合。
