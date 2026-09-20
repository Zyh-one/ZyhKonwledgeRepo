# KVConnector

> 本目录是 **vLLM V1 KVConnector 体系** 的总纲与枢纽，从背景、概念、原理、示例、生态五个维度做全方位梳理。
>
> 更新时间：2026-09-13

## 这套文档解决什么

`KVConnector` 是 vLLM 把 **KV Cache 与外部数据面** 连接起来的统一抽象层。这个"外部数据面"可以是另一个 vLLM 实例、CPU Host Memory、远端 DRAM、SSD、分布式 KV Store，或 RDMA / NIXL / Mooncake 等传输后端。

围绕它容易混在一起的三件事，本质上是同一套抽象下的不同正交能力：

| 能力 | 解决的问题 | 典型场景 |
|---|---|---|
| **External Prefix Cache** | 以前算过的 KV 能不能复用 | 共享 system prompt、跨实例命中 |
| **KVOffload** | 这些可复用 KV 放在哪里、如何在设备与外部 Cache 间搬运 | Device↔CPU 二级 Cache |
| **PD Transfer** | 当前请求的 Prompt KV 如何从 Prefill 交给 Decode | Prefill/Decode 分离 |

三者不是独立体系，而是围绕 `KVConnectorBase_V1` 串在一起。

## 文档清单

| 文档 | 内容 |
|---|---|
| [01-背景与动机](./01-背景与动机.md) | 为什么会有 KVConnector：访存墙、V0 零散传输、Disagg 统一诉求、V1 解法 |
| [02-基本概念](./02-基本概念.md) | KV Cache / Prefix Cache / External Cache / KVOffload / PD Transfer 基本概念 |
| [03-工作原理-KVConnectorBase_V1](./03-工作原理-KVConnectorBase_V1.md) | Scheduler/Worker 接口、请求生命周期调用时序、MultiConnector |
| [04-典型示例](./04-典型示例.md) | MooncakeConnector、OffloadingConnector 端到端时序；其余 Connector 简表 |
| [05-生态全景与学习路径](./05-生态全景与学习路径.md) | Connector 清单、拆解顺序、10 问 Checklist、参考资料 |

## 与仓库其他文档的关系

本目录是 **KVConnector 抽象本身** 的梳理。涉及具体传输后端和 PD 分离工程细节时，交回各自子页，不在本目录重复展开：

- PD 分离总论 → [`../其他细节/PD分离/PD分离.md`](../其他细节/PD分离/PD分离.md)
- KV Cache 传输模式（P2P / Pod 间接 / 混合）→ [`../其他细节/PD分离/KVCache传输.md`](../其他细节/PD分离/KVCache传输.md)
- Mooncake Transfer Engine → [`../其他细节/PD分离/MoonCake/MoonCake_transfer_engine.md`](../其他细节/PD分离/MoonCake/MoonCake_transfer_engine.md)
- NIXL 握手 → [`../其他细节/PD分离/Nixl/Nixl握手.md`](../其他细节/PD分离/Nixl/Nixl握手.md)
- PagedAttention / PrefixCache 基础 → [`../其他细节/PagedAttention.md`](../其他细节/PagedAttention.md) / [`../其他细节/PrefixCache.md`](../其他细节/PrefixCache.md)

> 旧版 ChatGPT 总结保留在 [`../其他细节/KVConnector.md`](../其他细节/KVConnector.md)，本目录是其重构与扩展。

## 一句话定位

> **KVConnector 是 vLLM KV Cache 数据面的统一接口；External Prefix Cache 解决"以前算过的 KV 能不能复用"，KVOffload 解决"这些可复用 KV 放在哪里、如何在设备与外部 Cache 间搬运"，PD 分离解决"当前请求的 Prompt KV 如何从 Prefill 交给 Decode"。三者不是独立体系，而是围绕 KVConnector 串在一起。**
