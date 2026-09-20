# vLLM KVConnector：External Prefix Cache、KVOffload 与 PD 分离梳理

> 目标：把目前容易混在一起的 **Prefix Cache、External Prefix Cache、KVOffload、KVConnector、PD（Prefill/Decode）分离** 放进同一套框架中理解，后续可以按 Connector 逐个拆源码。
>
> 更新时间：2026-09-13
> 说明：本文以 upstream vLLM 当前 KVConnector 设计为主；寒武纪 MLU 版本可能包含厂商侧适配或自定义实现，涉及 `MLU_to_CPU` / `CPU_to_MLU` 的具体触发条件时，应以当前 vLLM-MLU 分支源码为最终依据。

---

## 1. 先建立一个总认识

KVConnector 不应该只理解成“PD 分离时传 KV 的组件”。

更准确地说：

> **KVConnector 是 vLLM 将 KV Cache 与外部数据面连接起来的一层抽象。**

这个“外部数据面”可以是：

- 另一个 vLLM 实例；
- CPU Host Memory；
- 远端 DRAM；
- SSD / 文件系统；
- 分布式 KV Store；
- RDMA / NIXL / Mooncake 等传输后端。

因此，KVConnector 可以服务于两类看起来不同、实际上高度相关的问题：

1. **KV Cache 复用**
   - External Prefix Cache
   - CPU / SSD / Distributed KV Cache Pool
   - KVOffload
2. **KV Cache 跨实例传递**
   - Prefill → Decode
   - PD 分离
   - P2P / RDMA KV Transfer

可以把整个体系概括为：

```text
                         KVConnector
                              │
             ┌────────────────┴────────────────┐
             │                                 │
      KV Cache Reuse                    KV Cache Transfer
             │                                 │
   External Prefix Cache                PD Prefill → Decode
             │                                 │
 CPU / DRAM / SSD / Store               P2P / RDMA / NIXL
             │
         KVOffload
```

---

## 2. KVConnector 在 vLLM 中负责什么

vLLM V1 中的 `KVConnectorBase_V1` 同时连接 Scheduler 和 Worker。

可以粗略划分为：

### Scheduler 侧

负责“这个请求需要哪些外部 KV、外部有多少可以命中、应该怎样安排传输”。

典型接口包括：

```text
get_num_new_matched_tokens()
update_state_after_alloc()
update_connector_output()
request_finished()
```

其中非常关键的是：

```text
get_num_new_matched_tokens()
```

它解决的是：

> 本地 Prefix Cache 之外，外部 KV Cache 还能额外命中多少 token？

### Worker 侧

负责真正的数据搬运，例如：

```text
start_load_kv()
wait_for_layer_load()

save_kv_layer()
wait_for_save()
```

因此可以把 KVConnector 看成：

```text
Scheduler
  │
  │ 决定：
  │ - 查什么
  │ - 命中多少
  │ - 哪些 block 要 load/store
  ▼
KVConnector Metadata
  │
  ▼
Worker
  │
  │ 真正执行：
  │ - Load KV
  │ - Save KV
  │ - P2P Transfer
  ▼
GPU / MLU / CPU / Remote Store
```

---

# 3. Local Prefix Cache 与 External Prefix Cache

## 3.1 Local Prefix Cache

最普通的 Prefix Cache 位于当前 vLLM 实例自己的设备 KV Cache 中。

请求进入后，vLLM 根据 token/block 对应的 hash 查找已经计算过的 KV block。

例如：

```text
Request A:
[System Prompt 20K] + [Question A]

Request B:
[System Prompt 20K] + [Question B]
```

当 B 到来时：

```text
Token Prefix
    ↓
Block Hash
    ↓
Local KV Cache Lookup
    ↓
Hit
    ↓
直接复用对应 KV
```

这里没有跨设备、跨节点的数据传输。

---

## 3.2 External Prefix Cache

当本地没有完整命中时，KVConnector 可以继续查询外部 KV Store。

完整逻辑可理解为：

```text
Request
   ↓
Local Prefix Cache Lookup
   ↓
Local Hit Tokens
   ↓
KVConnector External Lookup
   ↓
External Hit Tokens
   ↓
Load External KV
   ↓
只计算剩余未命中 Token
```

因此：

```text
Local Prefix Cache
```

和：

```text
External Prefix Cache
```

并不是两套完全独立的算法。

它们都围绕：

```text
token sequence
    ↓
block/chunk hash
    ↓
KV block
```

进行匹配，只是 KV 数据所在的位置不同。

---

## 3.3 `external_prefix_cache_hits` 应如何理解

它更应该理解为：

> **从外部 KV Cache 命中的 token 数量**

而不是：

> “命中了多少次请求”。

因此如果：

```text
External Prefix Hit = 54K
```

通常表示：

```text
约 54K token 的 KV
无需重新 Prefill
```

---

# 4. KVOffload：现代语义与旧的 Swap/Preemption 必须区分

这是最容易混淆的一部分。

## 4.1 旧理解：KV 不够 → Preemption → Swap

早期/传统的理解更像：

```text
GPU KV Cache 不足
       ↓
Scheduler 抢占请求
       ↓
将请求 KV 搬到 CPU
       ↓
以后再恢复
```

这是一类：

```text
Request Preemption / Swap
```

机制。

---

## 4.2 当前 KVOffload 更像“二级 KV Cache”

当前 vLLM 的 OffloadingConnector 思路更接近：

```text
GPU / AI Card
      │
      │ Store completed KV blocks
      ▼
CPU / Secondary Tier
      │
      │ 以后 Prefix 再次命中
      ▼
GPU / AI Card
```

即：

### Store

```text
AI Card → CPU
```

把已经计算完成的 KV Block 保存到更大、更慢的 Cache Tier。

### Load

```text
CPU → AI Card
```

未来发生 External Prefix Hit 后，再把对应 KV 加载回设备。

这与 Preemption 没有必然关系。

因此完全可能出现：

```text
MLU → CPU = 几百 GB / 1 TB
num_preemptions = 0
```

二者并不矛盾。

---

# 5. KVOffload 到底什么时候触发

现在不能再使用：

```text
KV Cache 不够 → 一定触发 KVOffload
```

这种统一模型。

更加准确的是：

> **什么时候 Store / Load，由 Connector 的实现和策略决定。**

常见模式包括：

## 5.1 Eager / Produce-time Store

```text
KV Block 计算完成
      ↓
满足保存条件
      ↓
AI Card → CPU / Store
```

此时并不要求设备 KV Cache 已经不足。

这种机制本质上是在主动构建一个更大的 External Prefix Cache。

---

## 5.2 Lazy / Eviction-oriented Store

有些实现会更接近：

```text
GPU Cache Block
      ↓
进入 Eviction / Free Queue 附近
      ↓
即将从设备 Cache 淘汰
      ↓
再 Offload 到 CPU
```

这种模式与“内存压力”更相关。

但是：

```text
Cache Block Eviction
```

仍然不等于：

```text
Running Request Preemption
```

---

## 5.3 Hit-driven Load

External KV 的加载通常是：

```text
Request
   ↓
External Lookup
   ↓
Hit
   ↓
分配设备 KV Block
   ↓
CPU / Store → Device
```

因此之前观察到：

```text
External Prefix Hit 曲线
≈
CPU → MLU Bytes 曲线
```

是非常合理的。

如果模型、TP、KV dtype 等固定，则理论上近似：

```text
CPU_to_MLU_bytes
≈
external_hit_tokens × KV_bytes_per_token
```

---

# 6. 为什么 External Prefix Hit 和 CPU→MLU 曲线高度一致

假设：

```text
External Hit = 54K tokens
CPU → MLU   = 88 GB
```

那么：

```text
88 × 10^9 / 54 × 10^3
≈ 1.63 MB / token
```

如果其它峰值也接近这一比例，就说明：

```text
External Hit Token
        ↓
找到外部 KV
        ↓
Load KV
        ↓
CPU → MLU
```

这一链路高度自洽。

注意：

> **“External Lookup/Hit” 与 “CPU→MLU 数据传输”不是同一个动作。**

而是：

```text
Lookup
   ↓
Hit
   ↓
Load
```

---

# 7. AI Card→CPU 为什么通常明显大于 CPU→AI Card

这也是正常的 Cache 行为。

例如：

```text
新 Prompt 被计算
      ↓
很多 KV Block 被 Store
      ↓
MLU → CPU = 900 GB
```

但未来真正被重复请求的只有一部分：

```text
External Prefix Hit
      ↓
CPU → MLU = 88 GB
```

因此完全可能：

```text
Store Bytes >> Load Bytes
```

原因很简单：

> 写进 Cache 的 KV，不代表未来一定会再次被命中。

---

# 8. PD 分离与 KVConnector

PD 分离解决的是另一个核心问题：

> Prefill 和 Decode 不在同一个 vLLM 实例中，Prefill 计算完成的 Prompt KV 如何交给 Decode？

基本结构：

```text
Client
  ↓
Router
  ↓
Prefill
  │
  │ 计算 Prompt KV
  ▼
KVConnector
  │
  │ P2P / RDMA
  ▼
Decode
  │
  │ 使用 Prompt KV
  ▼
生成 Token
```

在这里 KVConnector 是：

```text
KV Producer → KV Consumer
```

的传输层。

典型角色：

```text
Prefill: kv_producer
Decode : kv_consumer
```

---

# 9. PD KV Transfer 与 KVOffload 不要混为一谈

这两条数据路径可能同时存在：

```text
                         Prefill
                            │
           ┌────────────────┴────────────────┐
           │                                 │
   External Prefix Cache               Current Request KV
           │                                 │
        CPU Store                            │
           │                                 │
       CPU → MLU                             │
           │                                 │
           └──────────→ Prefill ─────────────┘
                                      │
                                      │ PD KV Transfer
                                      ▼
                                    Decode
```

左边：

```text
CPU ↔ MLU
```

解决的是：

> **历史 Prefix KV 的保存与复用**

右边：

```text
Prefill → Decode
```

解决的是：

> **当前请求 Prompt KV 的跨实例交接**

这两者可以由不同 Connector 完成，也可以借助 `MultiConnector` 组合。

---

# 10. 为什么 PD 场景通常主要在 Prefill 侧做 Prefix KVOffload

Prefill 的职责：

```text
找 KV
+
算 KV
```

Decode 的职责：

```text
接 KV
+
用 KV
+
继续增长 KV
```

Prefix Cache 的核心问题：

> “这个 Prompt 前缀是不是以前已经算过？”

天然发生在 Prefill 阶段。

因此常见 PD 架构是：

```text
Prefill
  ├─ Local Prefix Cache
  ├─ External Prefix Cache
  ├─ KVOffload
  └─ Prefill Compute
          ↓
       KV Transfer
          ↓
Decode
  ├─ 接收 Prompt KV
  └─ Autoregressive Decode
```

所以在实际部署中经常看到：

```text
Prefill:
ENABLE_KV_OFFLOAD=true
CPU KV Cache / External Store

Decode:
不配置 Prefix KVOffload
```

但这不是“Decode 永远不能 Offload”。

Decode 也可能为了：

- 长上下文；
- HBM 压力；
- 多级 KV Cache；
- Decode KV 的跨请求复用；

而使用其它 Offload 策略。

---

# 11. 一个完整的 PD + External Cache + KVOffload 流程

可以把完整请求生命周期画成：

```text
                     Request
                        │
                        ▼
                 ┌──────────────┐
                 │ Prefill Node │
                 └──────┬───────┘
                        │
             Local Prefix Lookup
                        │
           ┌────────────┴─────────────┐
           │                          │
       Local Hit                  Local Miss
                                      │
                                      ▼
                           External KV Lookup
                                      │
                           ┌──────────┴─────────┐
                           │                    │
                       External Hit          Miss
                           │                    │
                           ▼                    │
                      CPU/Store                 │
                           │                    │
                     CPU → MLU                  │
                           │                    │
                           └──────────┬─────────┘
                                      │
                             Compute Remaining
                                      │
                               Prompt KV Ready
                                      │
                ┌─────────────────────┴─────────────────────┐
                │                                           │
        Store reusable KV                            PD KV Transfer
                │                                           │
          MLU → CPU/Store                             Prefill → Decode
                │                                           │
                ▼                                           ▼
        External KV Cache                              Decode Node
                                                            │
                                                            ▼
                                                        Generate
```

这张图基本覆盖了目前讨论的几个核心指标。

---

# 12. 监控指标应该如何放进这张图

## 12.1 External Prefix Cache Hit

含义：

```text
外部缓存额外命中的 Token 数
```

重点观察：

- hit tokens；
- query tokens；
- hit rate；
- 与 CPU→Device bytes 的比例。

---

## 12.2 KV Offload：CPU → AI Card

代表：

```text
External KV Load
```

即：

```text
CPU / External Tier
      ↓
Device KV Cache
```

适合计算：

```text
Bytes per External Hit Token
=
CPU_to_Device_bytes
/
External_hit_tokens
```

---

## 12.3 KV Offload：AI Card → CPU

代表：

```text
External KV Store / Offload
```

即：

```text
Device KV Cache
      ↓
CPU / External Tier
```

它不等于发生 Request Preemption。

---

## 12.4 Request Preemption

这是 Scheduler 的资源调度指标。

更接近：

```text
设备 KV 资源无法满足当前调度
       ↓
请求被抢占 / 回到等待
```

因此：

```text
Offload Bytes > 0
Preemption = 0
```

完全正常。

---

# 13. 推荐重点拆解的 KVConnector

下面不是简单按“哪个好”排序，而是按照学习价值和与你当前场景的相关度排序。

---

## 13.1 MooncakeConnector —— 第一优先级

### 主要用途

```text
Prefill → Decode
```

直接 P2P KV Transfer。

适合研究：

- PD 分离；
- producer / consumer；
- RDMA；
- Prefill / Decode handshake；
- KV 生命周期；
- 请求完成后 Prefill KV 何时释放；
- KV Transfer metadata。

### 为什么最值得你先拆

当前寒武纪 PD 场景本身就在使用 Mooncake 体系，因此它能直接对应真实生产链路。

重点源码方向：

```text
MooncakeConnector
MooncakeConnectorScheduler
MooncakeConnectorWorker
```

重点问题：

1. Scheduler 如何知道某请求需要 remote KV？
2. Prefill 如何通知 Decode KV 已准备好？
3. KV block 如何映射到远端地址？
4. 数据面什么时候开始 RDMA？
5. transfer 完成信号如何反馈 Scheduler？
6. 请求 abort 后 KV 如何清理？

---

## 13.2 MooncakeStoreConnector —— 第二优先级

### 主要用途

它和 `MooncakeConnector` 不一样。

```text
MooncakeConnector
= Prefill ↔ Decode P2P Transfer

MooncakeStoreConnector
= Shared External KV Cache Pool
```

MooncakeStoreConnector 使用 Mooncake Distributed Store，多个实例可以：

```text
PUT KV
GET KV
LOOKUP KV
```

从而形成真正的跨实例 External Prefix Cache。

特别适合研究：

- External Prefix Cache；
- Hash-based deduplication；
- CPU / DRAM / SSD KV Pool；
- 跨 vLLM 实例共享 KV；
- Store / Load；
- 多级存储。

在 PD 场景中可以通过 `MultiConnector`：

```text
MooncakeConnector
       +
MooncakeStoreConnector
```

同时得到：

```text
P → D P2P KV Transfer
       +
Shared Prefix KV Cache
```

这是非常值得深入理解的一套架构。

---

## 13.3 OffloadingConnector —— 理解 KVOffload 本质

### 主要用途

将 completed KV blocks 扩展到：

```text
GPU/Device
   ↓
CPU
   ↓
Optional Secondary Tier
```

当前 upstream 支持：

- CPUOffloadingSpec
- TieringOffloadingSpec

核心问题：

```text
什么时候 Store？
什么时候 Load？
什么时候 Evict？
CPU Pool 如何组织？
异步 DMA 如何与计算 overlap？
```

非常适合专门拆解：

```text
AI → CPU
CPU → AI
```

这两组指标到底从哪里增加。

### 注意

upstream vLLM 当前官方说明 OffloadingConnector 直接支持 CUDA、ROCm、XPU。

当前使用 MLU 的：

```text
vllm:kv_offload_total_bytes_total
transfer_type="MLU_to_CPU"
```

很可能包含寒武纪侧适配。

因此拆源码时应该优先找到当前 vLLM-MLU 分支：

```text
kv_offload_total_bytes_total.inc(...)
```

的真实调用位置。

---

## 13.4 LMCacheConnectorV1 / LMCacheMPConnector —— External KV Cache 的典型实现

LMCache 很适合用来学习：

```text
LLM Inference Engine
       │
       ▼
KV Cache Middleware
       │
       ├─ CPU
       ├─ Disk
       └─ Distributed Storage
```

LMCache 的典型路径：

```text
Request
   ↓
Token/Chunk Lookup
   ↓
Hit
   ├─ Load KV
   │
   └─ Skip Compute
   ↓
Miss
   ↓
Compute
   ↓
Store New KV
```

它同时覆盖：

- External Prefix Cache；
- KV Offload；
- 跨实例 Cache Sharing；
- PD transport。

当前 LMCache 还提供 multi-process 模式：

```text
vLLM
   ↓
LMCacheMPConnector
   ↓
Standalone LMCache Server
```

适合作为“KV Cache 独立服务化”的学习对象。

---

## 13.5 NixlConnector —— 高性能 PD KV 数据面的代表

NIXL 是非常值得学习的 KV Transport 抽象。

当前 vLLM 中：

```text
NixlPullConnector
NixlPushConnector
```

分别支持 READ/Pull 和 WRITE/Push 风格的数据传输。

适合研究：

- 异步 KV send/recv；
- RDMA / UCX / GDS；
- P/D 节点内存注册；
- Transfer descriptor；
- TP rank mapping；
- 跨节点零/少拷贝 KV Transfer。

如果目标是 AI Infra / 推理数据面，这个 Connector 很值得深入。

---

## 13.6 MultiConnector —— 最能体现 KVConnector 体系价值

`MultiConnector` 本身不是一种新的存储后端。

它解决的是：

> **一个请求同时需要多种 KV 能力怎么办？**

例如：

```text
MultiConnector
   │
   ├─ MooncakeConnector
   │      └─ P → D Transfer
   │
   └─ MooncakeStoreConnector
          └─ External Prefix Cache
```

这非常接近未来生产系统真实形态：

```text
L1 Device Cache
L2 CPU Cache
L3 Distributed DRAM
L4 SSD
+
Prefill → Decode P2P
```

而不是只有单一 Connector。

---

# 14. 推荐拆解顺序

建议按下面顺序走。

## 第一阶段：先把 vLLM KVConnector 抽象吃透

先看：

```text
KVConnectorBase_V1
```

重点：

```text
Scheduler Connector
Worker Connector
Metadata
get_num_new_matched_tokens()
start_load_kv()
save_kv_layer()
request_finished()
```

目标：

> 明白 vLLM Core 和外部 KV 系统的边界在哪里。

---

## 第二阶段：MooncakeConnector

因为与当前 PD 场景最直接相关。

目标：

> 完整画出一次 Prefill → Decode 的 KV 数据和控制流。

---

## 第三阶段：当前 MLU KVOffload 实现

不要先看 upstream 猜。

直接从指标反查：

```text
vllm:kv_offload_total_bytes_total
```

分别寻找：

```text
MLU_to_CPU
CPU_to_MLU
```

的 `inc()` 调用位置。

目标：

> 明确当前寒武纪版本 Store / Load 的真实触发条件。

---

## 第四阶段：MooncakeStoreConnector

目标：

> 明白 External Prefix Cache 从“单机 CPU Cache”扩展成“分布式 KV Pool”以后发生了什么。

重点：

```text
Hash
Lookup
Put
Get
Store namespace
TP shard
```

---

## 第五阶段：LMCache

目标：

> 从另一个成熟实现观察 KV Cache 服务化、多级存储和跨实例复用。

---

## 第六阶段：NIXL

目标：

> 深入 KV Transfer 数据面与 RDMA/UCX 等高性能通信。

---

## 第七阶段：MultiConnector

最终把：

```text
PD Transfer
+
External Prefix Cache
+
KVOffload
+
Multi-tier KV Cache
```

组合起来理解。

---

# 15. 每拆一个 Connector，都建议回答这 10 个问题

后续一一拆源码时，可以固定使用下面的 Checklist：

1. **它解决什么问题？**

   - PD Transfer？
   - External Cache？
   - CPU Offload？
   - Distributed Store？
2. **KV 存在哪里？**

   - Device？
   - CPU？
   - Remote DRAM？
   - SSD？
3. **KV 的 Key 是什么？**

   - Token Hash？
   - Block Hash？
   - Request ID？
   - Model / TP / PP / Rank 是否进入 Key？
4. **什么时候 Lookup？**
5. **什么时候 Store？**
6. **什么时候 Load？**
7. **什么时候 Evict / Free？**
8. **Scheduler 和 Worker 分别负责什么？**
9. **数据传输协议是什么？**

   - memcpy
   - RDMA
   - UCX
   - NIXL
   - Mooncake Transfer Engine
10. **有哪些指标能够证明数据链真的执行了？**

    - External Hit Tokens
    - Store Bytes
    - Load Bytes
    - Transfer Latency
    - Transfer Failure
    - Preemption
    - TTFT / TPOT / ITL

---

# 16. 对当前 MLU PD 环境的推荐关注顺序

结合当前的真实监控，可以优先串下面这几条：

```text
External Prefix Cache Queries
            ↓
External Prefix Cache Hits
            ↓
CPU → MLU Load Bytes
```

用于验证：

```text
Lookup → Hit → Load
```

再观察：

```text
Prefill Compute
      ↓
MLU → CPU Store Bytes
```

验证：

```text
Compute → Store
```

同时观察：

```text
num_preemptions
```

用来明确：

```text
KVOffload
≠
Request Preemption
```

最后在 PD 链路增加：

```text
Prefill → Decode KV Transfer Bytes
Transfer Latency
Transfer Queue / Failure
```

最终形成：

```text
External Cache
      │
      ▼
Prefill
      │
      ▼
PD Transfer
      │
      ▼
Decode
```

的一整套 KV 数据面监控。

---

# 17. 最终知识框架

建议以后脑中一直保留下面这张图：

```text
                         ┌───────────────────────────┐
                         │         Request           │
                         └─────────────┬─────────────┘
                                       ▼
                         ┌───────────────────────────┐
                         │      Local Prefix Cache   │
                         └─────────────┬─────────────┘
                                       │ miss
                                       ▼
                         ┌───────────────────────────┐
                         │       KVConnector         │
                         └───────┬───────────┬───────┘
                                 │           │
                 External Cache │           │ PD Transfer
                                 │           │
                       ┌─────────▼───┐   ┌──▼───────────┐
                       │ CPU / Store │   │ Prefill → D  │
                       └─────┬───────┘   └──────────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
              Device → CPU        CPU → Device
                  Store                Load
                   │                   │
                   └─────────┬─────────┘
                             │
                     Prefix KV Reuse
```

一句话总结：

> **KVConnector 是 vLLM KV Cache 数据面的统一接口；External Prefix Cache 解决“以前算过的 KV 能不能复用”，KVOffload 解决“这些可复用 KV 放在哪里、如何在设备与外部 Cache 间搬运”，PD 分离解决“当前请求的 Prompt KV 如何从 Prefill 交给 Decode”。三者不是独立体系，而是围绕 KVConnector 串在一起。**

---

# 18. 推荐重点项目/Connector 清单

| Connector / 项目                                | 核心用途                                  | 学习优先级 |
| ----------------------------------------------- | ----------------------------------------- | ---------: |
| `KVConnectorBase_V1`                          | vLLM KVConnector 抽象                     | ★★★★★ |
| `MooncakeConnector`                           | PD P2P KV Transfer                        | ★★★★★ |
| `MooncakeStoreConnector`                      | Distributed External Prefix Cache         | ★★★★★ |
| `OffloadingConnector`                         | CPU / Multi-tier KV Offload               | ★★★★★ |
| `LMCacheConnectorV1` / `LMCacheMPConnector` | KV Cache 中间件、多级缓存、跨实例共享     | ★★★★☆ |
| `NixlConnector`                               | 高性能异步 PD KV Transfer                 | ★★★★☆ |
| `MultiConnector`                              | 组合多种 KV 能力                          | ★★★★☆ |
| `FlexKVConnectorV1`                           | 大规模分布式 KV Store / Multi-level Cache | ★★★☆☆ |

---

# 19. 官方资料入口

- vLLM KVConnector Base APIhttps://docs.vllm.ai/en/latest/api/vllm/distributed/kv_transfer/kv_connector/v1/base/
- vLLM Disaggregated Prefillinghttps://docs.vllm.ai/en/latest/features/disagg_prefill/
- vLLM KV Offloading Usage Guidehttps://docs.vllm.ai/en/latest/features/kv_offloading_usage/
- vLLM MooncakeConnector Usage Guidehttps://docs.vllm.ai/en/latest/features/mooncake_connector_usage/
- vLLM MooncakeStoreConnector Usage Guidehttps://docs.vllm.ai/en/latest/features/mooncake_store_connector_usage/
- vLLM NixlConnector Usage Guidehttps://docs.vllm.ai/en/latest/features/nixl_connector_usage/
- LMCache Architecturehttps://docs.lmcache.ai/developer_guide/architecture.html
- LMCache + vLLM examples
  https://github.com/vllm-project/vllm/tree/main/examples/disaggregated/lmcache

---

## 20. 下一步

后续建议按照：

```text
KVConnectorBase_V1
        ↓
MooncakeConnector
        ↓
MLU KVOffload
        ↓
MooncakeStoreConnector
        ↓
LMCache
        ↓
NIXL
        ↓
MultiConnector
```

逐个拆解。

每个 Connector 都同时从：

```text
控制面（Scheduler）
+
数据面（Worker / Transport）
+
KV Block 生命周期
+
监控指标
```

四个维度分析，这样最终能够形成一套完整的 **LLM KV Cache Infra** 知识体系。
