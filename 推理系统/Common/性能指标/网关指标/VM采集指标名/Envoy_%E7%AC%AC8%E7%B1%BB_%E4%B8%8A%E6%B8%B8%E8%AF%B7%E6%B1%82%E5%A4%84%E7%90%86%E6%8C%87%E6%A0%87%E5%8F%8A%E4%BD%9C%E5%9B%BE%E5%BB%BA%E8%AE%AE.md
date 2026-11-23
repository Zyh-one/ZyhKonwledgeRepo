# Envoy 第8类：上游请求处理指标（Upstream Request）及 Grafana 作图建议

> 范围：黄区 VictoriaMetrics 实测具有 `envoy_cluster_name=~"httproute/.*"` 标签的 **22 个** `envoy_cluster_upstream_rq_*` 指标。本文按 Envoy 的 Upstream Cluster 粒度分析，面向 AiBrix / Envoy Gateway / vLLM 在线推理请求链路。
>
> 核心问题：**请求是否到达上游、是否排队、是否超时或重置、是否触发重试，以及当前请求并发是否异常。**

## 1. 范围、术语与请求生命周期

```text
Client (Downstream)
       │
       ▼
Envoy：HTTPRoute 匹配 / AiBrix ExtProc 等路由处理
       │
       ▼
Envoy Upstream Cluster
       ├── Connection Pool Pending（有可能等待）
       ├── 获取或复用连接
       ├── Upstream Request（发送给后端）
       └── Response / Timeout / Reset / Retry
       │
       ▼
vLLM：Waiting Queue → Running / Prefill / Decode
       │
       ▼
Envoy → Client（SSE 或非流式响应）
```

- **Downstream Request**：客户端发送给 Envoy 的请求。
- **Upstream Request**：Envoy 发起的上游请求尝试；一次客户端请求可能因重试产生多次上游尝试。
- **Connection** 不等于 **Request**：HTTP/2 可以在同一条连接上并行承载多个请求。
- **Envoy Pending** 不等于 **vLLM Waiting**：前者通常等待上游连接/连接池容量，后者等待模型调度资源。
- `envoy_cluster_name="httproute/<namespace>/<route>/rule/0"` 是 Envoy Cluster 的统计标识，可关联 HTTPRoute 规则，但真正的指标粒度是 Envoy Cluster，且多个 Envoy Pod 的状态彼此独立。

## 2. 全部 22 个指标及五组分类

### 2.1 请求数量与并发（4 个）

| 指标全名 | 类型 | 说明 | 监控价值 |
|---|---|---|---|
| `envoy_cluster_upstream_rq_total` | Counter | 累计发起的上游请求数 | 高：请求速率/RPS |
| `envoy_cluster_upstream_rq_active` | Gauge | 当前活跃上游请求数 | 高：请求并发 |
| `envoy_cluster_upstream_rq_completed` | Counter | 累计完成的上游 HTTP 请求数；**不等于成功数** | 高：请求结束量 |
| `envoy_cluster_upstream_rq_maintenance_mode` | Counter | 上游维护模式触发的本地拒绝/503 事件 | 低：特殊模式排障 |

注意：`rq_total` 是上游尝试数，不严格等于客户端请求量；`rq_completed` 可能包括非 2xx 响应，不能直接作为业务成功率分子。`rq_active` 也不等于 vLLM `num_requests_running`。

### 2.2 连接池等待与拒绝（4 个）

| 指标全名 | 类型 | 说明 | 监控价值 |
|---|---|---|---|
| `envoy_cluster_upstream_rq_pending_active` | Gauge | 当前等待上游连接池分配资源的请求数 | 高：瞬时等待 |
| `envoy_cluster_upstream_rq_pending_total` | Counter | 累计进入连接池等待流程的请求数 | 中：等待发生频率 |
| `envoy_cluster_upstream_rq_pending_overflow` | Counter | 因连接池/并发请求熔断限制而失败的请求数 | 高：被拒绝事件 |
| `envoy_cluster_upstream_rq_pending_failure_eject` | Counter | 等待连接期间因连接失败或远端终止而失败的请求数 | 中：连接池请求失败 |

**重要边界**：`pending_overflow` 不必然只由 Pending Queue 已满导致，可能涉及并发请求熔断。应同时参考第四类 `rq_open`、`rq_pending_open`，以及第六类连接失败指标。

### 2.3 超时、取消与请求重置（7 个）

| 指标全名 | 类型 | 说明 | 监控价值 |
|---|---|---|---|
| `envoy_cluster_upstream_rq_cancelled` | Counter | 获取连接池连接之前被取消的请求 | 中；**不覆盖所有客户端取消** |
| `envoy_cluster_upstream_rq_timeout` | Counter | 上游请求等待响应期间发生的超时 | 高 |
| `envoy_cluster_upstream_rq_max_duration_reached` | Counter | 请求到达最大持续时间限制而终止 | 中 |
| `envoy_cluster_upstream_rq_per_try_timeout` | Counter | 单次上游尝试达到 per-try 超时 | 中高 |
| `envoy_cluster_upstream_rq_per_try_idle_timeout` | Counter（按名称推断） | 单次上游尝试空闲超时相关事件；**须结合所用 Envoy 版本 HELP/源码确认** | 中 |
| `envoy_cluster_upstream_rq_rx_reset` | Counter | 收到上游远端发起的异常请求/流重置 | 高 |
| `envoy_cluster_upstream_rq_tx_reset` | Counter | Envoy 本地发起上游请求/流重置 | 高 |

区分：`cx_connect_timeout`（建连超时）与 `rq_timeout`（上游请求超时）不同；`per_try_timeout` 是某次尝试超时，最终客户端请求仍可能通过重试成功。`rx_reset` 和 `tx_reset` 表示重置的方向，不能单凭名称判断哪一方存在程序 Bug。

流式 SSE 请求中，建议联合 `envoy_cluster_upstream_cx_destroy_with_active_rq`、`..._destroy_remote_with_active_rq`、Envoy 响应标志和 vLLM 日志确认中断原因。

### 2.4 请求重试（6 个）

| 指标全名 | 类型 | 说明 | 监控价值 |
|---|---|---|---|
| `envoy_cluster_upstream_rq_retry` | Counter | 累计发起的重试次数 | 高：重试负载 |
| `envoy_cluster_upstream_rq_retry_success` | Counter | 重试成功累计次数 | 中高 |
| `envoy_cluster_upstream_rq_retry_limit_exceeded` | Counter | 达到单请求可重试次数限制，停止继续重试 | 中 |
| `envoy_cluster_upstream_rq_retry_overflow` | Counter | 受重试熔断或 Retry Budget 限制，重试未获准 | 高 |
| `envoy_cluster_upstream_rq_retry_backoff_exponential` | Counter | 指数退避重试事件 | 低 |
| `envoy_cluster_upstream_rq_retry_backoff_ratelimited` | Counter | 限流相关退避重试事件 | 低 |

**举例**：一次客户端请求先返回 503，重试一次再返回 200：`rq_retry` 可增加 1，`rq_retry_success` 可增加 1。若一次请求重试两次后成功，则两者的增长单位不同，不能将 `retry_success / retry` 直接解释为“按客户端请求计的成功率”。LLM 请求重复尝试可能放大 GPU 工作量；已经向客户端输出部分 SSE 的请求不能简单透明重试。

### 2.5 特殊协议（1 个）

| 指标全名 | 类型 | 说明 | 监控价值 |
|---|---|---|---|
| `envoy_cluster_upstream_rq_0rtt` | 需核实 | 0-RTT Early Data 相关请求事件；所统计的具体事件须查部署版本 | 低 |

**数量校验：4 + 4 + 7 + 6 + 1 = 22，全部来自原始列表。**

## 3. Grafana 面板规划

建议采用 **6 组逻辑图表、7 个 Grafana 面板**：第一组将请求速率和并发拆为两张，避免 RPS 与请求数量使用同一纵轴。所有 Counter 建议展示 `rate(...[5m])`（事件/秒）或 `increase(...[5m])`（5 分钟事件数），Gauge 使用瞬时值。

| 面板 | 名称 | 主要指标 | 单位/图形 | 目的 |
|---|---|---|---|---|
| 1 | 上游请求速率 | `rq_total`, `rq_completed` | req/s，两条折线 | 比较进入上游与完成速率，注意统计时点和重试 |
| 2 | 当前请求并发 | `rq_active` | requests，折线 | 当前活跃上游请求量 |
| 3 | 连接池等待 | `rq_pending_active`, `rq_pending_total` | 分两轴/两查询；优先拆上下两个视图 | 当前等待 vs 进入等待频率 |
| 4 | Pending 异常 | `rq_pending_overflow`, `rq_pending_failure_eject`, `rq_cancelled` | 次/5min，折线 | 拒绝、等待失败、获取连接前取消 |
| 5 | 超时与请求终止 | `rq_timeout`, `rq_per_try_timeout`, `rq_per_try_idle_timeout`, `rq_max_duration_reached` | 次/5min，折线 | 定位超时类型 |
| 6 | 请求重置 | `rq_rx_reset`, `rq_tx_reset` | 次/5min，折线 | 判断远端/本地重置方向 |
| 7 | 重试与受限 | `rq_retry`, `rq_retry_success`, `rq_retry_limit_exceeded`, `rq_retry_overflow` | 次/5min，折线 | 观察重试、成功及限制 |

`rq_maintenance_mode`、`rq_retry_backoff_*`、`rq_0rtt` 建议放在附加诊断面板，不必占用核心布局。`per_try_idle_timeout` 在核实语义前应注明“版本待验证”。

### 3.1 通用 PromQL：按 HTTPRoute 关联 Cluster 筛选

以下表达式使用实际存在的 `envoy_cluster_name=~"httproute/.*"` 标签。为了诊断不同 Envoy Proxy 的故障，优先保留 `pod`；跨 Pod 汇总时再去掉 `pod`。

**面板 1：上游请求速率（req/s）**

```promql
sum by (__name__, envoy_cluster_name) (
  rate({__name__=~"envoy_cluster_upstream_rq_(total|completed)",
        envoy_cluster_name=~"httproute/.*"}[5m])
)
```

**面板 2：活跃上游请求（requests）**

```promql
sum by (envoy_cluster_name, pod) (
  envoy_cluster_upstream_rq_active{envoy_cluster_name=~"httproute/.*"}
)
```

**面板 3A：当前等待连接池的请求（requests）**

```promql
sum by (envoy_cluster_name, pod) (
  envoy_cluster_upstream_rq_pending_active{envoy_cluster_name=~"httproute/.*"}
)
```

**面板 3B：进入等待流程的速率（req/s）**

```promql
sum by (envoy_cluster_name, pod) (
  rate(envoy_cluster_upstream_rq_pending_total{envoy_cluster_name=~"httproute/.*"}[5m])
)
```

**面板 4：Pending 相关异常事件（次/5min）**

```promql
sum by (__name__, envoy_cluster_name, pod) (
  increase({__name__=~"envoy_cluster_upstream_rq_(pending_overflow|pending_failure_eject|cancelled)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

**面板 5：上游超时及最大时长事件（次/5min）**

```promql
sum by (__name__, envoy_cluster_name, pod) (
  increase({__name__=~"envoy_cluster_upstream_rq_(timeout|per_try_timeout|per_try_idle_timeout|max_duration_reached)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

**面板 6：上下游请求重置方向（次/5min）**

```promql
sum by (__name__, envoy_cluster_name, pod) (
  increase({__name__=~"envoy_cluster_upstream_rq_(rx_reset|tx_reset)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

**面板 7：重试与资源限制（次/5min）**

```promql
sum by (__name__, envoy_cluster_name, pod) (
  increase({__name__=~"envoy_cluster_upstream_rq_(retry|retry_success|retry_limit_exceeded|retry_overflow)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

> Grafana 实践：面板 Legend 建议使用 `{{envoy_cluster_name}} · {{pod}} · {{__name__}}`，跨多个 HTTPRoute 作图时注意序列过多；先用变量筛选 `envoy_cluster_name`。若需要趋势对比，Counter 使用速率，若需要故障次数就使用窗口增量。由于存在 Counter 重置和采集窗口影响，`increase` 返回小数属于 PromQL 正常外推行为。

## 4. 结合第 4、6、7 类联合排障

| 现象 | 第 8 类主指标 | 辅助指标 | 排查逻辑 |
|---|---|---|---|
| 请求并发升高 | `rq_active` | 第 4 类 `rq_open`、vLLM `num_requests_waiting/running` | 区分 Envoy 活跃请求与推理调度瓶颈 |
| 请求等待连接 | `rq_pending_active`、`pending_total` | 第 6 类 `cx_active`, `cx_connect_fail` | 判断连接池是否不足或无法建连 |
| 请求因容量被拒绝 | `pending_overflow` | 第 4 类 `rq_pending_open`, `rq_open` | Gauge 是状态，Counter 表示发生过拒绝 |
| 请求执行时中断 | `rq_rx_reset`, `rq_tx_reset` | 第 6 类 `cx_destroy_with_active_rq` | 判断重置方向及是否发生连接级中断 |
| 超时明显增长 | `rq_timeout`, `per_try_timeout` | vLLM TTFT/E2E、网关超时配置 | 区分代理超时、模型排队和计算耗时 |
| 重试增多 | `rq_retry`, `retry_overflow` | 第 4 类 `rq_retry_open`, vLLM 请求量 | 判断重试是否放大推理负载 |
| SSE 输出不畅 | `rq_active`, `rq_timeout`, `rq_rx_reset` | 第 7 类 `rx_bytes_buffered`, `paused_reading_total` | 关联响应数据积压、流控和中断事件 |

### 典型场景：vLLM TTFT 变长，但 Envoy Pending 为零

- `rq_pending_active ≈ 0`：Envoy 连接池不一定拥塞。
- `rq_active` 升高：说明上游请求在途量增多。
- vLLM `num_requests_waiting` 升高：更倾向于模型 Scheduler 内部排队。
- 仍需观察 AiBrix 路由选择、vLLM TTFT/Prefill 和客户端 E2E，不能简单用两个系统的指标差值定位“丢失请求”。

### 典型场景：请求失败与重试增加

- `rq_rx_reset ↑` + `cx_destroy_remote_with_active_rq ↑`：更值得检查上游/网络连接中断。
- `rq_tx_reset ↑` + `rq_timeout ↑`：更值得检查 Envoy 超时或主动终止。
- `rq_retry ↑` + `rq_retry_overflow ↑`：检查 Retry Policy、Circuit Breaker、Retry Budget；注意可能增加 GPU 重复工作。
- 多个计数器可能记录同一故障中的不同事件，**不能将它们直接相加作为唯一失败请求数**。

## 5. 关键监控边界与注意事项

1. **Cluster 粒度**：标签包含 `httproute/...` 不意味着指标是 HTTPRoute CRD 自身输出；它依旧是 Envoy Upstream Cluster 指标。
2. **Pod 粒度**：熔断、连接和请求统计由各 Envoy Proxy 实例维护；聚合时应明确是观察单 Pod 还是总体。
3. **计数语义不同**：Client Request、Upstream Attempt、Connection、vLLM Request 的计数时点不同；重试会破坏简单的一比一对应关系。
4. **完成不等于成功**：`rq_completed` 不能直接计算业务成功率；还需要 HTTP 状态码、响应标志或业务层请求完成状态。
5. **Reset 不等于错误归责**：收到远端重置或本地发起重置，只能说明方向，仍需结合日志判断原因。
6. **指标可见性与版本**：`rq_per_try_idle_timeout`、`rq_0rtt` 等具体事件和类型必须以所部署 Envoy 版本的 Metrics HELP、源码及配置为准。
7. **当前 133 项清单局限**：此处没有上游请求耗时 Histogram、按 2xx/4xx/5xx 细分等指标；若要完整分析延迟及成功率，应结合 Envoy HTTP 统计、AiBrix 与 vLLM 指标。

## 6. 核心结论

**第 8 类是 HTTPRoute 上游请求转发最重要的请求级监控类别之一。** 推荐按以下顺序建立基线与定位故障：

```text
上游请求 RPS → 活跃并发 → 连接池等待 → 超时 / Reset → Retry → 最终业务结果
```

在 Grafana 中优先落地 **7 个面板**：请求速率、活跃并发、连接池等待、Pending 异常、超时、Reset、重试。结合第 4 类“限额开关”、第 6 类“连接故障”和第 7 类“流控与吞吐”形成完整的 Envoy 侧观测链路，再与 vLLM 指标关联进行分层诊断。
