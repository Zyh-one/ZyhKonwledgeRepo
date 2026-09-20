# 03 · 工作原理：KVConnectorBase_V1

> 本篇下沉到 vLLM V1 `KVConnectorBase_V1` 的接口级。接口签名与职责依据 vLLM 官方文档（见末尾参考），寒武纪 MLU 版本可能含厂商适配，具体调用点以 vLLM-MLU 分支源码为准。

## 3.1 整体架构

`KVConnectorBase_V1` 同时挂在 Scheduler 和 Worker 上，两侧职责清晰、通过元数据下发耦合：

```
   Scheduler 侧                                  Worker 侧
   ──────────────                                ──────────────
   决策：查什么 / 命中多少 /                       执行：Load / Save / P2P Transfer
   哪些 block 要 load/store
        │                                                │
        │   build_connector_meta()                       │
        └────────── KVConnectorMetadata ─────────────────┘
                     （随 SchedulerOutput 下发）
                                                     bind_connector_metadata()
                                                     start_load_kv() / save_kv_layer()
```

设计意图：**Scheduler 只做调度决策，不碰数据；Worker 只搬数据，不做命中判断。** 两侧通过 `KVConnectorMetadata` 在每个 engine step 通信。

## 3.2 Scheduler 侧接口与职责

### 核心决策接口

| 方法 | 职责 |
|---|---|
| `get_num_new_matched_tokens(request, num_computed_tokens) -> tuple[int\|None, bool]` | 返回外部 KV 可额外命中的新 token 数。`None` = 稍后重查；第二项 `True` = 异步加载（新 token 数为 0 时必须 `False`）。**只考虑调用时实际可用的最大前缀。** |
| `update_state_after_alloc(request, blocks, num_external_tokens)` | block 分配后更新 connector 状态；依据 `num_external_tokens` 决定是否加载（0 表示不加载）。若先前声明异步加载，同一请求可能被调两次。 |
| `build_connector_meta(scheduler_output) -> KVConnectorMetadata` | 构建本步元数据下发 Worker；**不应修改 scheduler_output**，调用会重置 connector 状态。 |
| `request_finished(request, block_ids) -> tuple[bool, dict\|None]` | 请求完成、block 释放前调一次。返回 `True` 表示异步保存/发送并暂缓释放。 |
| `update_connector_output(connector_output)` | 根据 Worker 侧 connector 输出更新 Scheduler 状态。 |

### 请求与状态钩子

| 方法 | 职责 |
|---|---|
| `on_new_request(request)` | 新请求加入时调用，可做预检查/簿记；默认 no-op。 |
| `bind_kv_cache_manager(kv_cache_manager)` | cache manager 构造后绑定，内部调 `bind_gpu_block_pool`。 |
| `bind_gpu_block_pool(gpu_block_pool)` | 绑定 GPU block pool，按 GPU block 跟踪状态。 |
| `has_pending_block_frees() -> bool` | 待处理传输是否能释放 block，而无需触发抢占。 |
| `has_pending_push_work() -> bool` | 是否存在 push 模式工作（如等待被写入 D 节点的 P 侧请求），需主循环继续 step。默认 `False`。 |
| `register_finished_partial_tail(...)` | 块清理前注册 finish-time partial-tail 源；返回 `True` 表示 connector 接管，请求块须保留到 `get_finished()`。 |

### 事件与统计

`take_events()`（取出新 KV cache 事件）、`take_events()` 配套，以及统计/握手类：`get_finished_count()`、`build_kv_connector_stats()`、`set_xfer_handshake_metadata()` / `..._pp_aware()`。

## 3.3 Worker 侧接口与职责

### 数据搬运核心（抽象，必须实现）

| 方法 | 职责与时机 |
|---|---|
| `start_load_kv(forward_context, **kwargs)` | 开始从 connector 向 vLLM paged KV buffer 加载。**当前 forward 依赖的加载须在其开始前启动**；独立异步加载可在提交后启动。 |
| `wait_for_layer_load(layer_name)` | 阻塞到指定层 KV 加载完成；**在 attention 层内调用**，用于逐层流水线。 |
| `save_kv_layer(layer_name, kv_layer, attn_metadata, **kwargs)` | 开始从 paged buffer 保存一层 KV 到 connector；**在 attention 层内调用**，支持执行期间异步拷贝。 |
| `wait_for_save()` | 阻塞到所有保存完成；**在 forward context 退出时调用**，防止 paged buffer 被覆盖。 |

这四个方法是 KVConnector "异步逐层流水线" 的支点：计算到哪层、就搬哪层，load/save 与 attention 计算重叠。

### 生命周期与元数据

| 方法 | 职责 |
|---|---|
| `bind_connector_metadata(connector_metadata)` | 保存 Scheduler 下发的元数据；model runner 每次执行前调用。 |
| `clear_connector_metadata()` | 清除元数据；model runner 每次执行后调用。 |
| `register_kv_caches(kv_caches)` | 初始化时注册 KV caches（如 NIXL 预注册）。 |
| `finish_forward()` | 通知 connector 模型不再读取本步 KV。 |
| `handle_preemptions(kv_connector_metadata)` | 块被覆盖前处理被抢占请求/驱逐块；异步保存类 connector 需实现。 |
| `reset_capture_state()` | 重置 CUDA graph 捕获期间被修改的 worker 状态。 |
| `shutdown()` | worker 退出时调用，等待异步操作完成并清理。 |

### 完成与错误回报

| 方法 | 职责 |
|---|---|
| `get_finished(finished_req_ids) -> (sending/saving ids, recving/loading ids)` | 告知哪些请求已完成生成。 |
| `get_transfer_results(finished_req_ids)` | 汇总快照：已完成 send、receive 及 receive 失败。 |
| `get_block_ids_with_load_errors() -> set[int]` | 返回加载失败的 block ID；空集合表示无失败。 |
| `get_kv_connector_stats() / get_kv_connector_kv_cache_events()` | 收集区间统计/事件。 |

## 3.4 一个请求生命周期的接口调用时序

以一个进入 PD 分离 + External Cache 的请求为例，两侧接口大致按以下顺序触发：

```
┌───────────────────────── Scheduler 侧 ─────────────────────────┐
│
│  ① on_new_request(req)              # 新请求入队，预检查
│
│  ② get_num_new_matched_tokens(req, num_computed)
│        → (external_hit_tokens, is_async)
│        # 决定本地之外还能命中多少；None 表示稍后重查
│
│  ③ 分配 GPU block
│
│  ④ update_state_after_alloc(req, blocks, external_hit_tokens)
│        # 根据命中数决定加载哪些 block
│
│  ⑤ build_connector_meta(scheduler_output) → metadata
│        # 打包本步 load/save 计划，下发
│
└───────────────────────────┬────────────────────────────────────┘
                            │ KVConnectorMetadata
                            ▼
┌───────────────────────── Worker 侧 ───────────────────────────┐
│
│  ⑥ bind_connector_metadata(metadata)    # 执行前绑定
│
│  ⑦ start_load_kv(forward_context)        # 启动外部 KV 加载（命中部分）
│
│  ⑧ 逐 attention 层循环：
│        wait_for_layer_load(layer_name)    # 等本层加载完
│        attention 计算
│        save_kv_layer(layer_name, ...)     # 算完即异步保存/发送
│
│  ⑨ wait_for_save()                        # forward 退出，等保存完
│
│  ⑩ finish_forward()                       # 本步 KV 不再被读
│
│  ⑪ clear_connector_metadata()             # 执行后清理
│
│  ⑫ get_finished(finished_req_ids) / get_transfer_results()
│        # 上报哪些请求 send/receive 完成
│
└────────────────────────────────────────────────────────────────┘
                            ▼
┌───────────────────────── Scheduler 侧 ─────────────────────────┐
│
│  ⑬ update_connector_output(connector_output)   # 据 Worker 回报更新状态
│
│  ⑭ request_finished(req, block_ids) → (defer, params)
│        # 请求完成、释放前；defer=True 表示异步保存并暂缓释放
│
│  ⑮ (异步保存/传输完成后) has_pending_block_frees() → 释放 block
│
└────────────────────────────────────────────────────────────────┘
```

要点：
- 命中判断在 ②（Scheduler），数据搬运在 ⑦⑧⑨（Worker）；
- 加载与计算逐层 overlap（⑦+⑧），保存与计算也逐层 overlap（⑧的 save_kv_layer）；
- `request_finished` 返回 defer 让异步保存完成前 block 不被覆盖（⑭⑮）。

## 3.5 关键设计点

### 异步逐层流水线

`save_kv_layer` / `wait_for_layer_load` 在 attention 层内调用，使"算第 N 层"与"搬第 N-1 层 / 加载第 N+1 层"重叠。这是 KVConnector 区别于"整段同步传输"的核心。

### CUDA graph 兼容

异步逐层操作可能与 CUDA graph 重放冲突。`requires_piecewise_for_cudagraph()` 返回 `True` 时启用 **piecewise CUDA graph** 模式；启用异步逐层操作的 connector 必须返回 `True`。`reset_capture_state()` 负责重置捕获期间被改的状态。

### Producer / Consumer 角色

`role` 属性返回 `KVConnectorRole`；`requires_kv_delivery` 默认取 `is_kv_producer`，即仅 producer 角色要求 KV 可靠送达。PD 场景中 Prefill = producer、Decode = consumer。

### KV Cache Layout 要求

`get_required_kvcache_layout()` 返回该 connector 要求的 layout（如 HND / NHD），无要求返回 `None`。不同后端（尤其 RDMA 类）对张量排布有约束。

### 带外握手

`get_handshake_metadata()` / `build_connector_worker_meta()` 支持 P/D worker 间带外握手；`set_xfer_handshake_metadata_pp_aware()` 按 `(pp_rank, tp_rank)` 设置，PP 感知 connector 可消费所有 PP producer shard。

## 3.6 MultiConnector：正交能力的组合

`MultiConnector` 不是新存储后端，而是解决**一个请求同时需要多种 KV 能力**：

```
MultiConnector
   ├─ MooncakeConnector        # P → D P2P Transfer
   └─ MooncakeStoreConnector   # External Prefix Cache
```

这接近未来生产系统真实形态：

```
L1 Device Cache
L2 CPU Cache
L3 Distributed DRAM
L4 SSD
+
Prefill → Decode P2P
```

而非单一 Connector。MultiConnector 的价值正是让前面提到的三组正交能力（External Cache / KVOffload / PD Transfer）能任意组合，这正是 V0 做不到、V1 抽象带来的核心收益。

## 3.7 一句话总结

> `KVConnectorBase_V1` 把 KV 数据面切成"Scheduler 决策 + Worker 搬运"两侧，用元数据下发耦合，用逐层异步流水线让计算与搬运 overlap，用 MultiConnector 让正交能力可组合。所有具体 Connector（Mooncake / NIXL / Offloading / LMCache）都是"某后端如何实现这套契约"。

下一篇 [04-典型示例](./04-典型示例.md) 用两个代表 Connector 把上述时序走通。
