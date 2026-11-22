# 1.初识：

work partitioning；warp 分工；non-matmul FLOPs；occupancy；序列维并行；MFU

核心：FlashAttention 已经规避了 HBM 瓶颈，但只跑到峰值 FLOPs 的 25–40%，远不如 GEMM 的 80–90%——瓶颈到底在哪，怎么逼近 GEMM 的效率？

## 1.1Abstract

FlashAttention 把显存从平方降到线性、相对优化基线有 2–4× 加速且无近似，但仍只达到理论峰值 FLOPs/s 的 25–40%。作者定位到原因是 **thread block / warp 之间的工作划分不优**：要么 occupancy 低，要么 shared memory 读写冗余。

FlashAttention-2 的三处改动：

1. **减少 non-matmul FLOPs**：GPU 的矩阵乘单元吞吐可达非矩阵运算的 16×，把 rescale 等操作合并/挪位置，保持数值结果不变；
2. **沿序列长度维并行**：除了 batch 维和 head 维，连单个 head 也切到多个 thread block，长序列、小 batch 时提升 occupancy；
3. **warp 内再分工**：同一 thread block 内按 warp 划分工作，减少 shared memory 通信。

效果：相对 FlashAttention 约 2×，A100 上前向达理论峰值 50–73%；端到端训练 GPT 类模型达 225 TFLOPs/s/A100（72% MFU）。

```
FlashAttention-1                      FlashAttention-2
block 只按 (batch, head) 切            block 再按 seq 维切
warp 之间重复读写 shared mem          warp 各管一段 → 少通信
大量 non-matmul rescale               rescale 合并，占比下降
          ↓ occupancy 低 / 空转               ↓ 逼近 GEMM 效率
```

我的关注点：这篇本质是**并行粒度**的论文，不是算法论文——数学结果与 FA1 完全一致。读的时候把「FLOPs 利用率」当作主线指标。

## 1.2Introduction

- 长上下文需求在涨：GPT-4 32K、MPT 65K、Claude 100K，训练/推理都想要更长序列。
- 现状：近似 attention 方法不少，但大规模训练仍在用标准 attention；FA1 已被广泛采用，可仍未打满硬件。
- 前向只到峰值 30–50%，反向更差（A100 上 25–35%），而优化过的 GEMM 能到 80–90%。
- 结论性判断：问题不在算法复杂度，而在 **work partitioning**（thread block 之间、warp 之间），因此三处改动都围绕「谁算哪块、怎么少通信」。
- 待读：3.1 的算法微调（如何保证数学等价）、3.2 的前向/反向并行划分、4 节的 benchmark 设置（causal / 非 causal、不同 head dim）。
