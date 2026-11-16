# 控制面与运行时 PromQL（可选扩展）

本文收录控制面与组件资源的可选查询，原始指标说明紧跟在对应 PromQL 后；没有当前查询的关联指标统一列在后文。通用统计规则见 [PromQL 统计范式](../../../PromQL统计范式.md)。

> **当前未接入：** 以下 4 条查询来自 `docs/dev/aibrix-metrics.md` 的设计草案，不在当前 `gw-query.constant.ts` 中，也不属于现有 12 张网关面板。它们用于后续扩展或手工只读排查。

## 1. `aibrixReconcileErrorsPerSecondPerStep` — reconcile 错误速率

按 `controller` 拆分 reconcile 错误 Counter 的窗口平均速率，输出单位为 error/s。

```promql
sum by (cluster, controller) (
  rate(
    controller_runtime_reconcile_errors_total{
      cluster=~"%(cluster)s",
      job="aibrix-controller-manager-metrics-service"
    }[%(time)s:30s]
  )
)
```

### 关联指标：`controller_runtime_reconcile_errors_total`

Counter，单位为 error，按 `controller` 标签记录累计调和错误次数。`rate()` 可得到错误速率。它反映控制器调和错误，不是推理请求错误率。

关联的 `controller_runtime_reconcile_total` 也是 Counter，单位为 reconcile，按 `controller` 标签记录累计调和次数，当前没有对应查询。若需 reconcile 错误占比，应与相同 `controller` 维度的 reconcile 总量速率相除，并处理无调和时分母为 0 的情况。

## 2. `aibrixWorkqueueDepthPerStep` — 工作队列积压

按队列 `name` 对 workqueue 深度 Gauge 求窗口平均后求和，输出单位为 item。

```promql
sum by (cluster, name) (
  avg_over_time(
    workqueue_depth{
      cluster=~"%(cluster)s",
      job="aibrix-controller-manager-metrics-service"
    }[%(time)s:30s]
  )
)
```

### 关联指标：`workqueue_depth`

Gauge，单位为 item，按 `name` 标签表示工作队列当前积压深度。上述查询展示各队列窗口平均深度之和。

持续积压说明入队速度超过处理速度，但不能仅凭深度判断根因，应结合 reconcile 错误、耗时和组件日志。

## 3. `aibrixComponentMemoryPerStep` — 组件内存占用

按 `job` 汇总 gateway-plugins 与 controller-manager 的进程 RSS 窗口平均值，输出单位为 byte。

```promql
sum by (cluster, job) (
  avg_over_time(
    process_resident_memory_bytes{
      cluster=~"%(cluster)s",
      job=~"aibrix-gateway-plugins|aibrix-controller-manager-metrics-service"
    }[%(time)s:30s]
  )
)
```

### 关联指标：`process_resident_memory_bytes`

Gauge，单位为 byte，表示进程常驻内存 RSS。上述结果是每个组件各 Pod RSS 窗口平均值之和，不是 Go 堆大小，也不是容器 memory limit。需要定位单副本时保留 `pod`。

## 4. `aibrixComponentCpuPerStep` — 组件 CPU 占用

按 `job` 汇总进程 CPU 时间 Counter 的速率，输出单位为 CPU core。

```promql
sum by (cluster, job) (
  rate(
    process_cpu_seconds_total{
      cluster=~"%(cluster)s",
      job=~"aibrix-gateway-plugins|aibrix-controller-manager-metrics-service"
    }[%(time)s:30s]
  )
)
```

### 关联指标：`process_cpu_seconds_total`

Counter，单位为 second，表示进程累计 CPU 时间。`rate(process_cpu_seconds_total)` 的单位是 `second/second`，数值解释为平均 CPU 核数，不是 0～100 的百分比。若需利用率，还需选择一致的 CPU request/limit 或节点容量口径。

## 5. 其他关联指标（当前无对应查询）

### 5.1 apiserver 客户端

`rest_client_requests_total` 是 Counter，单位为 request，按 `code`、`method`、`host` 记录访问 Kubernetes apiserver 的累计请求数。它是控制器与 apiserver 的客户端指标，不是推理业务请求量。

### 5.2 Go 与进程运行时

gateway-plugins、controller-manager 等 Go 组件除上述 CPU 和 RSS 外，还可使用下列通用指标：

| metric | 类型 | 单位 | 含义与查询注意点 |
| --- | --- | --- | --- |
| `go_goroutines` | Gauge | goroutine | 当前 goroutine 数，持续增长需结合堆和请求状态排查 |
| `go_memstats_heap_inuse_bytes` | Gauge | byte | Go 堆正在使用的内存 |
| `go_gc_duration_seconds` | Summary | second | GC 耗时分布，分位标签以裸样本为准 |
| `process_open_fds` | Gauge | fd | 当前打开的文件描述符数 |
| `process_start_time_seconds` | Gauge | Unix second | 进程启动时间戳，不是运行时长 |

### 5.3 Envoy 进程状态

| metric | 类型 | 单位 | 含义 |
| --- | --- | --- | --- |
| `envoy_server_live` | Gauge | 0/1 | 存活时通常为 1；无数据不能直接解释为进程死亡 |
| `envoy_server_uptime` | Gauge | second | Envoy 已运行时间，可用于识别重启 |
| `envoy_server_memory_allocated` | Gauge | byte | Envoy 已分配内存 |

## 6. 使用边界

- 这些查询描述控制面或进程资源，不能替代 Envoy Proxy 数据面的请求量、上游时延和状态码。
- `job=envoy-gateway` 的 Go/process/controller/client 指标只反映 Envoy Gateway 控制面，不反映推理业务流量。
- Envoy Gateway 控制面暴露的 `go_*`、`process_*`、`controller_runtime_*`、`rest_client_*` 等指标，不包含业务数据面的请求量、时延和错误率。
- 排查推理流量时，应使用 `namespace="envoy-gateway-system"` 下的 Envoy Proxy 数据面指标；不能用控制面 reconcile 次数代替请求 QPS，也不能用 apiserver client 时延代替上游推理时延。
- `go_goroutines`、GC、文件描述符、进程启动时间等可继续按相同范式扩展，但当前没有已实现的对应面板。
