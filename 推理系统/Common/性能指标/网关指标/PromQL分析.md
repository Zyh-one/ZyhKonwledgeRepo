# 网关性能指标 PromQL 分析（含指标说明）

本文集中说明 AIBrix gateway-plugins、Envoy Proxy 及控制面组件的原始 metric、当前 PromQL、聚合方式和最终业务口径。通用规则见 [PromQL 统计范式](../PromQL统计范式.md)。

> **当前实现：** 以下“原始 PromQL 语句”逐字对应 `gw-query.constant.ts` 的 13 个常量，组成 12 张图；`gwPrefixCacheEntriesPerStep` 与 `gwPrefixCacheCapacityPerStep` 同图，`gwUpstreamLatencyTPPerStep` 分别代入 0.99、0.9、0.5 形成三条序列。
>
> **未实现扩展：** 下游连接、controller reconcile、workqueue 和组件资源查询不在当前常量中，统一放在分类文档的“可选扩展”部分。
>
> **证据边界：** 指标名和标签依据当前工作区的 `docs/dev/aibrix-metrics.md`、`gw-query.constant.ts` 整理；历史实测记录的时间是 2026-11-05（北京时间，UTC+8）。本次仅整理文档，没有重新连接 34 或黄区集群。某个面板当前“无数据”不等于 metric 不存在，也不等于原始状态为 0。

各分类已将原始指标说明放在对应 PromQL 后，适合逐项查阅：

- [前缀缓存 PromQL](./metric指标/前缀缓存/PromQL.md)
- [网关流量 PromQL](./metric指标/网关流量/PromQL.md)
- [上游时延与健康 PromQL](./metric指标/上游时延与健康/PromQL.md)
- [控制面与运行时 PromQL（可选）](./metric指标/控制面与运行时/PromQL.md)

## 1. 采集来源与标签约定

| 组件 | 当前筛选方式 | 提供的主要数据 |
| --- | --- | --- |
| AIBrix gateway-plugins | `job="aibrix-gateway-plugins"`，系统 namespace 为 `aibrix-system` | balanced 本地前缀缓存、前缀索引状态、Go/process 运行时 |
| Envoy Proxy 数据面 | `namespace="envoy-gateway-system"` | 下游请求、上游请求与时延、上游成员健康、连接与进程状态 |
| AIBrix controller-manager | `job="aibrix-controller-manager-metrics-service"` | reconcile、workqueue、apiserver client、Go/process 运行时 |
| Envoy Gateway 控制面 | `job="envoy-gateway"`，`namespace="envoy-gateway-system"` | Go/process/controller/client 控制面指标，不提供业务请求量、时延或错误率 |

这些组件是平台共享组件，指标不携带租户业务的 `label_id`、`label_version` 等标签。当前前端通过集群级 `/v1/range` 查询，仅管理员有权限；非管理员请求返回 403 时，页面显示空图。

`cluster` 是 VictoriaMetrics 抓取链路注入的集群标签；`envoy_cluster_name` 是 Envoy 配置中的上游 cluster 名，两者不是同一概念。后者可用于区分上游服务，但不能默认等同于模型名。

## 2. 原始 PromQL 语句

```TypeScript
// 网关前缀缓存使用率 - 本地前缀缓存 entries/capacity 的占比
export const gwPrefixCacheUsagePercPerStep = `avg by(cluster) (avg_over_time(aibrix_balanced_local_prefix_cache_usage_ratio{cluster=~"%(cluster)s",job="aibrix-gateway-plugins"}[%(time)s:30s])) * 100`;

// 网关前缀缓存条目数 - 各副本本地缓存条目数总和
export const gwPrefixCacheEntriesPerStep = `sum by(cluster) (avg_over_time(aibrix_balanced_local_prefix_cache_entries{cluster=~"%(cluster)s",job="aibrix-gateway-plugins"}[%(time)s:30s]))`;

// 网关前缀缓存容量 - 各副本本地缓存容量上限总和
export const gwPrefixCacheCapacityPerStep = `sum by(cluster) (avg_over_time(aibrix_balanced_local_prefix_cache_capacity{cluster=~"%(cluster)s",job="aibrix-gateway-plugins"}[%(time)s:30s]))`;

// 前缀索引可用性 - 1=可用 0=不可用，按索引类型(local/sync)取最差值
export const gwPrefixCacheIndexerStatusPerStep = `min by(cluster,indexer_type) (avg_over_time(aibrix_prefix_cache_indexer_status{cluster=~"%(cluster)s",job="aibrix-gateway-plugins"}[%(time)s:30s]))`;

// 网关请求总量
export const gwRequestTotalPerStep = `sum by(cluster) (increase(envoy_http_downstream_rq_total{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 网关 QPS
export const gwRequestPerSecondPerStep = `sum by(cluster) (rate(envoy_http_downstream_rq_total{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 网关请求状态数量 - 按响应码类别(2xx/3xx/4xx/5xx)拆分，class label 值是单数字
export const gwRequestStatusPerStep = `sum by(cluster,envoy_response_code_class) (increase(envoy_http_downstream_rq_xx{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 网关成功率 - 2xx/3xx 响应占比
export const gwRequestSuccessRatePerStep = `sum by(cluster) (increase(envoy_http_downstream_rq_xx{cluster=~"%(cluster)s",namespace="envoy-gateway-system",envoy_response_code_class=~"2|3"}[%(time)s:30s])) / sum by(cluster) (increase(envoy_http_downstream_rq_total{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s])) * 100`;

// 网关活跃请求数 - 正在处理中的下游请求
export const gwRequestActivePerStep = `sum by(cluster) (avg_over_time(envoy_http_downstream_rq_active{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 网关上游时延分位 - 请求在网关到上游推理实例链路上的耗时分布（tp=0.5/0.9/0.99）
export const gwUpstreamLatencyTPPerStep = `histogram_quantile(%(tp)s, sum by(cluster,le) (rate(envoy_cluster_upstream_rq_time_bucket{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))) * 1000`;

// 上游 QPS - 按上游 cluster(推理服务)拆分
export const gwUpstreamRequestPerSecondPerStep = `sum by(cluster,envoy_cluster_name) (rate(envoy_cluster_upstream_rq_total{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 上游健康实例数
export const gwUpstreamMembershipHealthyPerStep = `sum by(cluster,envoy_cluster_name) (avg_over_time(envoy_cluster_membership_healthy{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s]))`;

// 上游健康比例 - 健康实例占实例总数的比例
export const gwUpstreamHealthyRatePerStep = `sum by(cluster,envoy_cluster_name) (avg_over_time(envoy_cluster_membership_healthy{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s])) / sum by(cluster,envoy_cluster_name) (avg_over_time(envoy_cluster_membership_total{cluster=~"%(cluster)s",namespace="envoy-gateway-system"}[%(time)s:30s])) * 100`;
```

## 3. 公共筛选、模板参数与权限

| 占位符 | 当前含义 | 注意点 |
| --- | --- | --- |
| `%(cluster)s` | VictoriaMetrics 的集群筛选值，使用正则匹配 | 当前组件传入 `.*`，不是 Envoy 的 `envoy_cluster_name` |
| `%(time)s` | 每个图表点向前读取的统计窗口 | 当前使用图表 step；不是整个图表的 start～end |
| `%(tp)s` | Histogram 分位参数 | 当前分别替换为 `0.99`、`0.9`、`0.5` |
| `:30s` | 范围子查询 resolution | 不能据此反推 vmagent 抓取间隔或组件埋点周期 |

AIBrix 查询用 `job="aibrix-gateway-plugins"` 锁定采集目标，Envoy 查询用 `namespace="envoy-gateway-system"` 锁定数据面。网关指标没有租户 `namespace`、`label_id`、`label_version` 等业务标签，不应照搬 LLM Serving 查询中的租户过滤条件。

当前所有查询走集群级 `/v1/range`，仅管理员可调用。前端将 403 和其他查询错误转换为空序列，因此空图既可能是无数据，也可能是权限或查询失败，不能统一解释为指标值 0。

## 4. 前缀缓存：原始指标、时间平均与副本聚合

### 4.1 原始指标

| metric | 类型与单位 | 原始含义 |
| --- | --- | --- |
| `aibrix_balanced_local_prefix_cache_usage_ratio` | Gauge，通常为 0～1 | 单副本 balanced 本地前缀缓存 `entries / capacity` |
| `aibrix_balanced_local_prefix_cache_entries` | Gauge，entry | 单副本当前保存的本地前缀缓存条目数 |
| `aibrix_balanced_local_prefix_cache_capacity` | Gauge，entry | 单副本本地前缀缓存容量上限 |
| `aibrix_prefix_cache_indexer_status` | Gauge，0/1 | 索引可用状态，`indexer_type` 区分 `local` 与 `sync` |

这些指标描述**路由器的本地前缀元数据缓存**，不是 vLLM KV Cache，也不是前缀缓存命中率。每个 gateway-plugins Pod 的缓存彼此独立，缓存为全局、model-agnostic 口径，没有 model label。历史源码记录表明，有数据需要 balanced 路由及 `AIBRIX_BALANCED_LOCAL_ROUTER_METRICS_ENABLED` 开关；无数据还需同时排查路由算法、开关、采集和权限。

缓存指标建议用 `(cluster, namespace, pod)` 定位，索引状态增加 `indexer_type`；完整序列身份以裸样本的全部标签为准。

### 4.2 使用率是“比率的平均”，不是“总量的比率”

`gwPrefixCacheUsagePercPerStep` 对每个 gateway-plugins 序列执行：

```text
单副本 usage_ratio 的窗口平均
  → 按 cluster 对各副本取平均
  → ×100 转为百分比
```

它不等于 `sum(entries) / sum(capacity)`。副本容量相同且时间窗一致时，两种口径可能接近；容量不同或副本倾斜时会出现差异。当前默认总览不保留 Pod，排查最高副本水位应按 `(cluster,pod)` 展开或改用 `max`。

### 4.3 条目与容量是“窗口平均后求和”

entries 和 capacity 都先执行 `avg_over_time()`，再按 `cluster` 求和。因此图中可能有小数，含义是各副本窗口平均值之和，不是窗口末时刻的精确整数总量。

### 4.4 索引状态是“窗口平均后的最差序列”

索引状态先求每个序列的窗口平均，再按 `(cluster,indexer_type)` 取最小值。原始 metric 只有 0/1，但派生结果可以位于 0～1 之间：既可能表示窗口内状态抖动，也可能表示副本间状态不同。`local` 与 `sync` 分别形成序列；无返回序列只表示无数据，不代表不可用。

## 5. 网关流量：原始指标、Counter 增量与状态码比率

### 5.1 原始指标

| metric | 类型与单位 | 原始含义 |
| --- | --- | --- |
| `envoy_http_downstream_rq_total` | Counter，request | 下游 HTTP Connection Manager 累计请求数 |
| `envoy_http_downstream_rq_xx` | Counter，request | 按响应码类别统计下游请求 |
| `envoy_http_downstream_rq_active` | Gauge，request | Envoy 正在处理的下游请求数 |
| `envoy_http_downstream_cx_total` | Counter，connection | 下游 HTTP 连接累计数，当前未接入 |
| `envoy_listener_downstream_cx_total` | Counter，connection | 监听器下游连接累计数，当前未接入 |

这里的 downstream 是“客户端 → Envoy”。请求指标建议用 `(cluster, namespace, pod, envoy_http_conn_manager_prefix)` 定位，响应码指标再增加 `envoy_response_code_class`。`envoy_http_downstream_cx_total` 带 `envoy_http_conn_manager_prefix` 标签，`envoy_listener_downstream_cx_total` 按 `envoy_listener_address` 拆分；两个连接指标处于不同统计层级，未核对埋点边界前不应直接相加。

### 5.2 请求总量与 QPS

`gwRequestTotalPerStep` 使用 `increase()`，输出每个 step 窗口的请求增量，单位为 request。`gwRequestPerSecondPerStep` 使用 `rate()`，输出窗口平均请求速率，单位为 request/s。二者都不是进程启动以来的累计原始值，原始 Counter 读数还会受进程重启影响。

### 5.3 状态码与成功率

`gwRequestStatusPerStep` 按 `envoy_response_code_class` 保留响应码类别。原始标签值是 `"2"`、`"3"`、`"4"`、`"5"`，前端图例再拼接 `xx`。

`gwRequestSuccessRatePerStep` 的定义是：

```text
窗口内 2xx + 3xx 响应增量 / 窗口内 downstream 请求总增量 × 100%
```

这是网关 HTTP 成功率，不是模型推理业务成功率；3xx 被明确视作成功，2xx 也不能单独证明流式响应完整结束或模型结果满足业务要求。分子与分母来自不同 Counter，短窗口内在途请求和窗口边界会影响结果。分母为 0 时比率没有定义。

### 5.4 活跃请求是窗口平均并发

`gwRequestActivePerStep` 对 Gauge 求窗口平均后跨 Envoy 副本求和，表示平均活跃请求数，可能出现小数。它应与 QPS、上游时延联合分析，不能单独用来判断“请求完成量”。

## 6. 上游：原始指标、Histogram 分位数与健康比例

### 6.1 原始指标

| metric | 类型与单位 | 原始含义 |
| --- | --- | --- |
| `envoy_cluster_upstream_rq_total` | Counter，request | 发往上游 cluster 的累计请求数 |
| `envoy_cluster_upstream_rq_time_bucket` | Histogram Bucket Counter，request | 上游请求耗时落入各累计桶的观测数，`le` 单位为 seconds |
| `envoy_cluster_membership_healthy` | Gauge，member | 当前 Envoy 副本观察到的上游健康成员数 |
| `envoy_cluster_membership_total` | Gauge，member | 当前 Envoy 副本观察到的上游成员总数 |
| `envoy_cluster_upstream_rq_xx` | Counter，request | 上游响应码类别计数，当前未接入 |
| `envoy_cluster_upstream_cx_active` | Gauge，connection | 上游活跃连接数，当前未接入 |
| `envoy_cluster_upstream_cx_total` | Counter，connection | 上游连接累计数，当前未接入 |

上游指标建议用 `(cluster, namespace, pod, envoy_cluster_name)` 定位，时延再增加 `le`。`envoy_cluster_name` 与模型的映射必须以实际 Envoy 配置为准。

### 6.2 时延只计算分位数

`gwUpstreamLatencyTPPerStep` 对 `envoy_cluster_upstream_rq_time_bucket` 使用 `rate()`，按 `(cluster,le)` 合并累计桶，再通过 `histogram_quantile()` 估算 P99/P90/P50，最后乘 1000 转为毫秒。

当前只导出 `_bucket`，没有 `_sum`/`_count`，无法按 `rate(_sum) / rate(_count)` 求精确平均时延。分位数受 bucket 边界和桶内插值影响，不是原始请求时延的精确排序值。

当前聚合没有保留 `envoy_cluster_name`，所以时延是全部上游合并后的分布；只有上游 QPS、健康实例数和健康比例按上游 cluster 拆分。若需单上游时延，必须在 `sum by` 中增加 `envoy_cluster_name`。

### 6.3 上游 QPS 与下游 QPS 不要求相等

`gwUpstreamRequestPerSecondPerStep` 按 `(cluster,envoy_cluster_name)` 计算上游请求速率。重试会使一次下游请求产生多次上游请求，因此上游合计与下游总量存在合理差异。

### 6.4 健康比例是平均成员数之比

健康实例数与健康比例都对 Gauge 先求窗口平均，再按上游求和。健康比例为：

```text
sum(avg_over_time(membership_healthy))
/
sum(avg_over_time(membership_total))
×100%
```

它不是“所有实例始终健康的时间占比”，分母为 0 时无定义。多 Envoy 副本可能分别观察同一批成员，健康实例数的求和可能带副本倍数；比例在分子、分母视图一致时可抵消该倍数，视图不一致时仍需按 Pod 排查。

## 7. 控制面与进程运行时（当前未接入）

| metric | 类型与单位 | 原始含义 |
| --- | --- | --- |
| `controller_runtime_reconcile_total` | Counter，reconcile | controller reconcile 累计次数 |
| `controller_runtime_reconcile_errors_total` | Counter，error | reconcile 错误累计次数 |
| `workqueue_depth` | Gauge，item | 工作队列当前积压深度 |
| `rest_client_requests_total` | Counter，request | 访问 apiserver 的累计请求数 |
| `go_goroutines` | Gauge，goroutine | 当前 goroutine 数 |
| `go_memstats_heap_inuse_bytes` | Gauge，byte | Go 堆正在使用的字节数 |
| `go_gc_duration_seconds` | Summary，second | Go GC 耗时分布，分位标签以裸样本为准 |
| `process_cpu_seconds_total` | Counter，second | 进程累计 CPU 时间 |
| `process_resident_memory_bytes` | Gauge，byte | 进程 RSS |
| `process_open_fds` | Gauge，fd | 进程打开的文件描述符数 |
| `process_start_time_seconds` | Gauge，Unix second | 进程启动时间的 Unix 秒时间戳 |
| `envoy_server_live` | Gauge，0/1 | Envoy 进程存活状态，存活时为 1 |
| `envoy_server_uptime` | Gauge，second | Envoy 已运行秒数 |
| `envoy_server_memory_allocated` | Gauge，byte | Envoy 已分配内存 |

`process_cpu_seconds_total` 经 `rate()` 后才表示平均 CPU 核数；原始值不是 CPU 百分比。`process_start_time_seconds` 是绝对时间戳，不是已经运行的秒数。Envoy Gateway 控制面的同类 Go/process 指标只能说明控制面进程状态，不能用来替代 Envoy Proxy 数据面的请求指标。可选查询见 [控制面与运行时 PromQL](./metric指标/控制面与运行时/PromQL.md)。

## 8. 查询关系

```text
客户端
  → Envoy downstream：请求总量 / QPS / 状态码 / 成功率 / 活跃请求
  → Envoy upstream：分上游 QPS / 合并上游时延 P99、P90、P50 / 成员健康
  → 推理服务内部：另查 vLLM TTFT、E2E、KV Cache 等模型实例指标

AIBrix gateway-plugins
  → balanced 本地前缀缓存：使用率 / entries / capacity
  → 前缀索引：local、sync 可用性
```

## 9. 当前能力边界与组合原则

- **没有模型维度：** 当前 Envoy 指标没有 model label，balanced 缓存也明确为 model-agnostic，因此不能按模型拆分网关 QPS、时延、错误率或缓存使用率。
- **缓存口径不同：** 网关前缀缓存描述路由器的本地前缀元数据；vLLM Prefix/KV Cache 描述推理引擎内部缓存。两者不能共用一个“命中率”或“利用率”定义。
- **上下游不强制相等：** 上游重试、路由和连接行为会使上游请求量不同于下游请求量；应按 `envoy_cluster_name` 和响应码继续拆解。
- **分位数不能直接相加：** 上游 P99 与模型 TTFT/E2E P99 来自不同 Histogram 和样本集合，不能直接相加或相减得到另一阶段 P99。
- **无流量与无数据要区分：** 比率分母为 0、采集缺失、权限不足、组件未启用和时间窗无序列，在图上可能都表现为空，不能统一解释为 0。
