# Envoy HTTPRoute Upstream Cluster 数据图与 PromQL

> 本文将 [envoy-aibrix-system-aibrix-eg.md](envoy-aibrix-system-aibrix-eg.md) 中已梳理的数据图单独汇总，以数据图为单位列出用途、完整指标名、PromQL、展示方式及已知问题。
>
> 范围：第 2、4、6、7、8 类，共 **24 个逻辑图表条目**，其中 **21 张核心图、3 张按需诊断图**。图 19“连接池等待”包含两个不同单位的视图；如果拆成两个独立 Grafana 面板，则实际为 **25 个面板：22 个核心、3 个按需**。
>
> 以下 PromQL 是基于已确认指标名和语义整理的作图模板，未逐条在黄区执行验证。实际使用前需确认 Grafana 变量、标签名、部署版本的指标类型及指标 HELP；本文不代表对集群或业务 API 执行过任何变更。

## 1. 图表总览

| 编号 | 数据图                       | 类别    | 建议           |
| ---: | ---------------------------- | ------- | -------------- |
|    1 | 上游 Endpoint 成员与健康状态 | 第 2 类 | 核心           |
|    2 | 上游连接数限制               | 第 4 类 | 核心           |
|    3 | 上游连接池数量限制           | 第 4 类 | 核心           |
|    4 | 上游并发请求限制             | 第 4 类 | 核心           |
|    5 | Pending Request 限制         | 第 4 类 | 核心           |
|    6 | 上游重试限制                 | 第 4 类 | 核心           |
|    7 | 上游连接负载与新建速率       | 第 6 类 | 核心           |
|    8 | 上游建连失败与建连耗时       | 第 6 类 | 核心           |
|    9 | 活跃请求期间的连接中断       | 第 6 类 | 核心           |
|   10 | 上游连接可用性与协议异常     | 第 6 类 | 核心           |
|   11 | 连接生命周期与复用异常       | 第 6 类 | 按需           |
|   12 | 上游连接协议分布             | 第 6 类 | 按需           |
|   13 | 上游数据吞吐量               | 第 7 类 | 核心           |
|   14 | 上游缓冲区占用               | 第 7 类 | 核心           |
|   15 | 响应方向流控                 | 第 7 类 | 核心           |
|   16 | 请求方向背压                 | 第 7 类 | 核心           |
|   17 | 上游请求速率                 | 第 8 类 | 核心           |
|   18 | 当前上游请求并发             | 第 8 类 | 核心           |
|   19 | 连接池等待                   | 第 8 类 | 核心，两个视图 |
|   20 | Pending 异常事件             | 第 8 类 | 核心           |
|   21 | 超时与请求终止               | 第 8 类 | 核心           |
|   22 | 上游请求重置方向             | 第 8 类 | 核心           |
|   23 | 重试与重试受限               | 第 8 类 | 核心           |
|   24 | 特殊请求与重试退避           | 第 8 类 | 按需           |

## 2. 通用查询和展示约定

### 2.1 Grafana 变量

建议设置：

- `$upstream_cluster`：匹配 `envoy_cluster_name`，默认选择一个具体的 `httproute/<业务namespace>/<HTTPRoute名称>/rule/<规则序号>`。
- `$pod`：匹配 Envoy Pod，默认 `.*`，排障时可选择单个 Pod。

公共筛选条件：

```promql
envoy_cluster_name=~"$upstream_cluster",
pod=~"$pod"
```

默认只查看一个 HTTPRoute Upstream Cluster，避免多个路由和 Envoy Pod 产生过多曲线。

### 2.2 查询与聚合

- 同一 PromQL 代码块中的多条语句需要分别建成 Grafana 的 Query A、Query B、Query C，**不是一条可以整体执行的 PromQL**。
- Counter：负载和吞吐使用 `rate()`；稀疏故障事件使用 `increase([5m])`。
- Gauge：直接展示瞬时值，不使用 `rate()` 或 `increase()`。
- 跨 Envoy Pod 汇总 Counter 时，先对每个序列计算 `rate()` 或 `increase()`，再使用 `sum`；以下查询的函数执行顺序已经满足这一点。
- 全局实际并发、连接数和 Buffer 总量可对 Gauge 求和；排查单 Pod 热点时保留 `pod` 分组或查看 `max`。
- `increase()` 因窗口外推出现小数属于正常现象，不表示真实发生了“小数次”请求。
- 不要把无数据直接当成真实零值；需区分指标未暴露、目标未采集和采集窗口无样本。
- 状态、数量、速率和事件增量应分视图或使用独立 Y 轴，不强行共用同一单位。

### 2.3 DEFAULT 与 HIGH

第 4 类查询以 `default` 为例。实际路由使用 HIGH 优先级时，将指标名中的 `default` 替换为 `high`；DEFAULT/HIGH 是路由优先级，不是告警等级，二者不能相加。

---

## 第 2 类：Endpoint 成员与健康状态

### 图 1：上游 Endpoint 成员与健康状态（核心）

**用途**：观察目标 Upstream Cluster 当前有多少 Endpoint，以及健康、降级和排除数量。

**包含指标**：

- `envoy_cluster_membership_total`：Endpoint 总数，Gauge。
- `envoy_cluster_membership_healthy`：健康 Endpoint 数，Gauge。
- `envoy_cluster_membership_degraded`：降级 Endpoint 数，Gauge。
- `envoy_cluster_membership_excluded`：被排除的 Endpoint 数，Gauge。

**PromQL**：

```promql
max by (__name__, envoy_cluster_name) (
  {
    __name__=~"envoy_cluster_membership_(total|healthy|degraded|excluded)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }
)
```

**展示**：单位“个”，4 条独立折线，不堆叠；跨 Envoy Pod 使用 `max` 去重，排障时可增加 `pod` 分组比较各实例视图。

**问题与注意事项**：

- `healthy`、`degraded`、`excluded` 不一定互斥，三者之和不必然等于 `total`。
- 多个 Envoy Pod 通常看到同一组 Endpoint，不能直接求和，否则会按副本数重复放大。
- `max` 适合总览去重，但可能掩盖不同 Envoy Pod 的 Endpoint 视图不一致；出现分歧时应按 `pod` 拆开检查。

---

## 第 4 类：熔断与并发限制

### 图 2：上游连接数限制（核心）

**用途**：联合观察连接限额状态、实际连接数和连接触发限额后的事件。

**包含指标**：

- `envoy_cluster_circuit_breakers_default_cx_open`：DEFAULT 优先级连接数限额状态，Gauge；HIGH 对应 `envoy_cluster_circuit_breakers_high_cx_open`。
- `envoy_cluster_upstream_cx_active`：当前上游连接数，Gauge。
- `envoy_cluster_upstream_cx_overflow`：连接数限额溢出事件，Counter。

**PromQL**：

```promql
# Query A：当前是否达到连接数限额，0/1
max by (envoy_cluster_name) (
  envoy_cluster_circuit_breakers_default_cx_open{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：当前实际连接数
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query C：最近 5 分钟连接溢出事件
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_cx_overflow{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
```

**展示**：Query A 为 0/1 状态，Query B 单位为连接数，Query C 单位为次/5min；分视图或独立 Y 轴。

**问题与注意事项**：

- `cx_open=1` 不代表所有现存请求失败，已有连接仍可能复用。
- `cx_open=0` 不能证明窗口内从未达到限额；可额外使用 `max_over_time(...[5m])` 查看采样期间是否出现过 1，但仍可能漏掉采集间隔内的瞬时状态。
- 连接数不等于请求数，HTTP/2 一条连接可以承载多个 Stream。

### 图 3：上游连接池数量限制（核心）

**用途**：观察连接池数量是否达到限制，以及是否发生连接池溢出。

**包含指标**：

- `envoy_cluster_circuit_breakers_default_cx_pool_open`：连接池数量限额状态，Gauge；HIGH 对应 `envoy_cluster_circuit_breakers_high_cx_pool_open`。
- `envoy_cluster_upstream_cx_pool_overflow`：连接池数量限制溢出事件，Counter。
- `envoy_cluster_upstream_cx_active`：仅作为连接负载参考，Gauge，不代表连接池数量。

**PromQL**：

```promql
# Query A：连接池数量限额状态，0/1
max by (envoy_cluster_name) (
  envoy_cluster_circuit_breakers_default_cx_pool_open{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：最近 5 分钟连接池溢出事件
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_cx_pool_overflow{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query C：实际连接数，仅供辅助参考
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：限额状态、事件增量和连接数分层展示。

**问题与注意事项**：

- 当前 133 项清单没有直接的“连接池数量”Gauge，不能用 `cx_active` 代替连接池数量。
- 连接池数量不等于 TCP 连接数，`cx_pool_open=1` 也不能直接解释为“所有连接已满”。
- 只有 `open` 状态而没有溢出事件时，不能直接认定请求已失败。

### 图 4：上游并发请求限制（核心）

**用途**：观察上游并发请求是否达到限额，以及实际在途请求量。

**包含指标**：

- `envoy_cluster_circuit_breakers_default_rq_open`：并发请求限额状态，Gauge；HIGH 对应 `envoy_cluster_circuit_breakers_high_rq_open`。
- `envoy_cluster_upstream_rq_active`：当前活跃上游请求数，Gauge。

**PromQL**：

```promql
# Query A：并发请求限额状态，0/1
max by (envoy_cluster_name) (
  envoy_cluster_circuit_breakers_default_rq_open{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：当前活跃上游请求数
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_rq_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：0/1 状态与 requests 分视图；长推理和 SSE 场景重点观察 `rq_active` 是否长期高位。

**问题与注意事项**：

- 当前清单没有直接的并发请求 Overflow 指标，不能假设其他版本可能存在的 `upstream_rq_active_overflow` 在现网可用。
- `rq_open=1` 与 `rq_active` 高只能说明容量压力，实际拒绝仍需结合响应状态、Access Log、超时和取消事件。
- `rq_active` 不等于 vLLM `num_requests_running`。

### 图 5：Pending Request 限制（核心）

**用途**：观察连接池等待限额、当前等待请求数和 Pending 溢出事件。

**包含指标**：

- `envoy_cluster_circuit_breakers_default_rq_pending_open`：Pending Request 限额状态，Gauge；HIGH 对应 `envoy_cluster_circuit_breakers_high_rq_pending_open`。
- `envoy_cluster_upstream_rq_pending_active`：当前等待连接池资源的请求数，Gauge。
- `envoy_cluster_upstream_rq_pending_overflow`：Pending 相关容量拒绝事件，Counter。

**PromQL**：

```promql
# Query A：Pending 限额状态，0/1
max by (envoy_cluster_name) (
  envoy_cluster_circuit_breakers_default_rq_pending_open{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：当前 Pending 请求数
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_rq_pending_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query C：最近 5 分钟 Pending 溢出事件
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_rq_pending_overflow{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
```

**展示**：状态、当前等待数和事件增量分视图。

**问题与注意事项**：

- `pending_overflow` 不必然只由 Pending Queue 已满导致，还可能涉及并发请求熔断，需要联查 `rq_open`。
- Envoy Pending 不是 vLLM Scheduler Waiting；Envoy Pending 为零时，vLLM 内部仍可能排队。
- 状态 Gauge 与事件 Counter 不能互相替代。

### 图 6：上游重试限制（核心）

**用途**：观察并发重试限额、重试负载、重试后成功和重试受限事件。

**包含指标**：

- `envoy_cluster_circuit_breakers_default_rq_retry_open`：并发重试限额状态，Gauge；HIGH 对应 `envoy_cluster_circuit_breakers_high_rq_retry_open`。
- `envoy_cluster_upstream_rq_retry`：累计重试次数，Counter。
- `envoy_cluster_upstream_rq_retry_success`：重试后成功事件，Counter。
- `envoy_cluster_upstream_rq_retry_overflow`：重试预算或重试熔断限制事件，Counter。
- `envoy_cluster_upstream_rq_retry_limit_exceeded`：达到单请求重试次数限制的事件，Counter。

**PromQL**：

```promql
# Query A：并发重试限额状态，0/1
max by (envoy_cluster_name) (
  envoy_cluster_circuit_breakers_default_rq_retry_open{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：最近 5 分钟重试及受限事件
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(retry|retry_success|retry_overflow|retry_limit_exceeded)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：状态单独展示，Counter 单位为次/5min，独立折线不堆叠。

**问题与注意事项**：

- 当前清单没有 Active Retry Gauge，不能展示当前并发重试数量。
- `max_retries` 熔断配置是并发重试资源限制，不是单条请求允许重试的次数。
- `retry_success / retry` 不能直接解释为按客户端请求计算的重试成功率。
- 重试可能放大 GPU 工作量；已输出部分 SSE 的请求不能假设可以透明重试并接续。

---

## 第 6 类：上游连接管理

### 图 7：上游连接负载与新建速率（核心）

**用途**：观察当前连接数量、新建连接速度，并与请求并发对照。

**包含指标**：

- `envoy_cluster_upstream_cx_active`：当前上游连接数，Gauge。
- `envoy_cluster_upstream_cx_total`：累计建立的上游连接数，Counter。
- `envoy_cluster_upstream_rq_active`：当前活跃上游请求数，Gauge，作为辅助曲线。

**PromQL**：

```promql
# Query A：当前连接数
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：新建连接速率
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query C：当前请求并发
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_rq_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：连接数、连接/秒、requests 分视图或独立 Y 轴。

**问题与注意事项**：

- 连接不等于请求，`cx_active=4`、`rq_active=100` 在 HTTP/2 多路复用时并不矛盾。
- `cx_active` 包含可能空闲可复用的连接，不等于正在传输数据的连接数。
- 新建连接速率升高可能由扩缩容、连接回收或协议配置造成，不能单独判定异常。

### 图 8：上游建连失败与建连耗时（核心）

**用途**：同时观察建连失败、建连超时、连续尝试超限和成功/实际建连耗时分布。

**包含指标**：

- `envoy_cluster_upstream_cx_connect_fail`：建连失败事件，Counter。
- `envoy_cluster_upstream_cx_connect_timeout`：建连超时事件，Counter。
- `envoy_cluster_upstream_cx_connect_attempts_exceeded`：连续连接尝试超过允许次数的事件，Counter。
- `envoy_cluster_upstream_cx_connect_ms_sum`：建连耗时总和，Histogram sum。
- `envoy_cluster_upstream_cx_connect_ms_count`：建连耗时观测次数，Histogram count。
- `envoy_cluster_upstream_cx_connect_ms_bucket`：建连耗时分桶，Histogram bucket。

**PromQL**：

```promql
# Query A：最近 5 分钟建连异常事件
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_cx_(connect_fail|connect_timeout|connect_attempts_exceeded)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)

# Query B：平均建连耗时
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_connect_ms_sum{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
/
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_connect_ms_count{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query C：P95 建连耗时
histogram_quantile(
  0.95,
  sum by (envoy_cluster_name, le) (
    rate(envoy_cluster_upstream_cx_connect_ms_bucket{
      envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
    }[5m])
  )
)
```

**展示**：异常事件单位为次/5min；平均和 P95 建连耗时按实际导出单位展示，通常为 ms，但需以 HELP 和 bucket 边界为准。

**问题与注意事项**：

- 建连耗时只统计实际新建连接，不是每个 HTTP 请求耗时；复用连接不会重新经历相同建连流程。
- 平均耗时应使用总 `sum / count`，不能平均各 Pod 的平均值。
- 分位数必须先按 `le` 聚合 Bucket，再执行 `histogram_quantile()`。
- 分母为零时平均值无意义；建连失败、超时和尝试超限可能记录同一故障的不同阶段，不能相加为唯一失败数。

### 图 9：活跃请求期间的连接中断（核心）

**用途**：观察连接关闭时仍有活跃请求的事件，并区分本地和远端关闭方向。

**包含指标**：

- `envoy_cluster_upstream_cx_destroy_with_active_rq`：关闭时存在活跃请求的连接事件，Counter。
- `envoy_cluster_upstream_cx_destroy_local_with_active_rq`：Envoy 本地关闭且存在活跃请求的连接事件，Counter。
- `envoy_cluster_upstream_cx_destroy_remote_with_active_rq`：上游远端关闭且存在活跃请求的连接事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_cx_destroy_(with_active_rq|local_with_active_rq|remote_with_active_rq)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位次/5min，3 条独立折线，不堆叠；联查图 21、22 的超时和 Reset。

**问题与注意事项**：

- 总数与 local/remote 子项可能存在包含关系，不能直接相加。
- 指标按连接事件计数，不是受影响请求数；HTTP/2 一条连接可包含多个活跃 Stream。
- 指标说明关闭时存在活跃请求，但不能单独证明业务请求最终失败，仍需 Access Log 和响应标志。
- 对 SSE 长连接尤其有价值，但方向信息不等于最终故障归责。

### 图 10：上游连接可用性与协议异常（核心）

**用途**：观察无健康后端、协议错误、连接溢出及健康 Endpoint 数量。

**包含指标**：

- `envoy_cluster_upstream_cx_none_healthy`：无可用健康后端导致无法获得连接的事件，Counter。
- `envoy_cluster_upstream_cx_protocol_error`：上游连接协议错误事件，Counter。
- `envoy_cluster_upstream_cx_overflow`：连接数限额溢出事件，Counter。
- `envoy_cluster_upstream_cx_pool_overflow`：连接池数量限制溢出事件，Counter。
- `envoy_cluster_membership_healthy`：健康 Endpoint 数，Gauge，作为状态参考。

**PromQL**：

```promql
# Query A：最近 5 分钟可用性、协议和溢出事件
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_cx_(none_healthy|protocol_error|overflow|pool_overflow)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)

# Query B：健康 Endpoint 数
max by (envoy_cluster_name) (
  envoy_cluster_membership_healthy{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：事件增量与健康 Endpoint 数分视图。

**问题与注意事项**：

- `none_healthy` 增长且健康 Endpoint 为零，才更支持“无健康后端”；健康 Endpoint 存在但建连失败时，应检查 Pod、端口和网络。
- 协议错误需要结合 Envoy 日志、响应标志和后端协议配置，不能仅凭计数定位原因。
- Overflow 与图 2、3 存在联查复用，不能把不同图中的同一事件重复累计为独立故障。

### 图 11：连接生命周期与复用异常（按需）

**用途**：分析连接持续时间、空闲回收、最大寿命、最大请求数和正常关闭行为。

**包含指标**：

- `envoy_cluster_upstream_cx_length_ms_sum`：连接持续时间总和，Histogram sum。
- `envoy_cluster_upstream_cx_length_ms_count`：连接持续时间观测次数，Histogram count。
- `envoy_cluster_upstream_cx_length_ms_bucket`：连接持续时间分桶，Histogram bucket。
- `envoy_cluster_upstream_cx_idle_timeout`：连接空闲超时关闭事件，Counter。
- `envoy_cluster_upstream_cx_max_duration_reached`：连接达到最大持续时间的事件，Counter。
- `envoy_cluster_upstream_cx_max_requests`：连接达到最大请求数的事件，Counter。
- `envoy_cluster_upstream_cx_close_notify`：协议层关闭通知事件，Counter。
- `envoy_cluster_upstream_cx_destroy`：连接销毁事件，Counter。
- `envoy_cluster_upstream_cx_destroy_local`：Envoy 本地关闭连接的事件，Counter，作为方向参考。
- `envoy_cluster_upstream_cx_destroy_remote`：上游远端关闭连接的事件，Counter，作为方向参考。

**PromQL**：

```promql
# Query A：平均连接持续时间
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_length_ms_sum{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
/
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_length_ms_count{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query B：P95 连接持续时间
histogram_quantile(
  0.95,
  sum by (envoy_cluster_name, le) (
    rate(envoy_cluster_upstream_cx_length_ms_bucket{
      envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
    }[5m])
  )
)

# Query C：最近 5 分钟连接生命周期事件
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_cx_(idle_timeout|max_duration_reached|max_requests|close_notify|destroy|destroy_local|destroy_remote)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：连接持续时间与事件增量分视图。

**问题与注意事项**：

- 连接生命周期 Histogram 不是请求延迟 Histogram。
- `destroy`、`destroy_local`、`destroy_remote`、`idle_timeout`、`close_notify` 增长可能只是正常连接回收，不能单独标记为故障；销毁总数与 local/remote 方向子项不能相加。
- 连接时长单位需按实际 HELP 和 bucket 边界确认；分母为零时平均值无意义。
- 只有结合新建连接速率、Pending 和请求异常，才能判断连接复用是否不足。

### 图 12：上游连接协议分布（按需）

**用途**：观察新建连接的 HTTP/1.x、HTTP/2、HTTP/3 和 0-RTT 事件速率。

**包含指标**：

- `envoy_cluster_upstream_cx_http1_total`：累计建立的 HTTP/1.x 上游连接数，Counter。
- `envoy_cluster_upstream_cx_http2_total`：累计建立的 HTTP/2 上游连接数，Counter。
- `envoy_cluster_upstream_cx_http3_total`：累计建立的 HTTP/3 上游连接数，Counter。
- `envoy_cluster_upstream_cx_connect_with_0_rtt`：使用 0-RTT Early Data 的建连事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  rate({
    __name__=~"envoy_cluster_upstream_cx_(http1_total|http2_total|http3_total|connect_with_0_rtt)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位连接/秒或事件/秒，按指标分别命名图例。

**问题与注意事项**：

- 这些 Counter 展示的是新建连接或事件的速率，不是当前各协议连接数量。
- 不能直接用这些速率计算“当前连接协议占比”；若需要当前占比，需要相应的按协议 Active Gauge。
- HTTP/3 和 0-RTT 未启用时长期为零不一定异常。
- HTTP/2 重点理解多路复用，不能按连接数推导请求数。

---

## 第 7 类：上游数据传输与流控

### 图 13：上游数据吞吐量（核心）

**用途**：分别观察 Envoy 向上游发送请求数据和从上游接收响应数据的吞吐量。

**包含指标**：

- `envoy_cluster_upstream_cx_rx_bytes_total`：从上游累计接收的响应字节数，Counter。
- `envoy_cluster_upstream_cx_tx_bytes_total`：向上游累计发送的请求字节数，Counter。

**PromQL**：

```promql
# Query A：RX，响应方向吞吐量
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_rx_bytes_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query B：TX，请求方向吞吐量
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_tx_bytes_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
```

**展示**：单位 Byte/s，可自动换算 KiB/s、MiB/s；RX/TX 两条独立折线。

**问题与注意事项**：

- RX 是从上游接收响应，TX 是向上游发送请求，方向以 Envoy 为参照。
- 吞吐量升高可能只是 RPS、请求体大小或响应长度增加，不能直接判定网络拥塞。
- 字节量不等于 Token 数，Byte/s 不等于 Token/s，不能据此计算 TTFT、TPOT 或模型解码速度。

### 图 14：上游缓冲区占用（核心）

**用途**：观察响应读取缓冲和请求写入缓冲是否持续积压。

**包含指标**：

- `envoy_cluster_upstream_cx_rx_bytes_buffered`：当前仍在 Envoy 上游读取缓冲中的响应字节数，Gauge。
- `envoy_cluster_upstream_cx_tx_bytes_buffered`：准备发往上游但尚未完全发送的请求字节数，Gauge。

**PromQL**：

```promql
# Query A：RX Buffer
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_rx_bytes_buffered{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# Query B：TX Buffer
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_tx_bytes_buffered{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：单位 Bytes，Gauge 直接展示；总览可跨 Pod 求和，排障时增加 `pod` 分组或改用 `max`。

**问题与注意事项**：

- Buffered 是当前占用量，不是缓冲区容量上限，不能使用 `rate()` 或 `increase()`。
- 短暂峰值可能正常，重点观察是否持续升高且长期不回落。
- RX Buffer 持续升高可能表示响应已到达 Envoy，但下游消费或后续转发不及时，不等于 vLLM 不返回数据。
- TX Buffer 持续升高提示向 Endpoint 写入请求数据可能受阻，但仍需网络和后端证据。

### 图 15：响应方向流控（核心）

**用途**：观察 Envoy 暂停和恢复读取上游响应的流控事件。

**包含指标**：

- `envoy_cluster_upstream_flow_control_paused_reading_total`：暂停读取上游响应的累计事件数，Counter。
- `envoy_cluster_upstream_flow_control_resumed_reading_total`：恢复读取上游响应的累计事件数，Counter。

**PromQL**：

```promql
# Query A：Pause，最近 5 分钟平均每分钟事件数
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_paused_reading_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
) / 5

# Query B：Resume，最近 5 分钟平均每分钟事件数
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_resumed_reading_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
) / 5
```

**展示**：单位 events/min；如果删除 `/ 5`，单位必须改为次/5min。

**问题与注意事项**：

- Pause/Resume 频繁说明流控反复切换，但不必然发生请求失败。
- 不能用暂停次数减恢复次数推导当前暂停连接数。
- RX Buffer 持续升高且 Pause 频繁时，重点排查下游消费或 Envoy 向下游转发瓶颈。
- 与超时、Reset 同时出现只能说明时间关联，仍需 Access Log 和客户端行为确认。

### 图 16：请求方向背压（核心）

**用途**：观察 Envoy 向上游写入请求数据受阻，以及背压解除事件。

**包含指标**：

- `envoy_cluster_upstream_flow_control_backed_up_total`：上游写入受阻并向下游传播背压的累计事件数，Counter。
- `envoy_cluster_upstream_flow_control_drained_total`：上游写缓冲恢复到可继续处理状态、解除背压的累计事件数，Counter。

**PromQL**：

```promql
# Query A：Backed up，最近 5 分钟平均每分钟事件数
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_backed_up_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
) / 5

# Query B：Drained，最近 5 分钟平均每分钟事件数
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_drained_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
) / 5
```

**展示**：单位 events/min；适合与 TX Buffer、大 Prompt 和多模态请求联合分析。

**问题与注意事项**：

- 该组表示 Envoy 写上游受阻，不要与响应方向的 Pause/Resume 混淆。
- 普通小型文本请求中长期为零不一定异常。
- Backed up/Drained 是事件次数，不是当前处于背压状态的连接数，也不能直接当作失败请求数。
- 不能仅凭指标相关性推断上游接收慢或网络存在故障，需要结合请求体大小、TX Buffer 和网络证据。

---

## 第 8 类：上游请求处理

### 图 17：上游请求速率（核心）

**用途**：比较上游请求尝试和完成速率。

**包含指标**：

- `envoy_cluster_upstream_rq_total`：累计发起的上游请求尝试数，Counter，可能包含重试。
- `envoy_cluster_upstream_rq_completed`：累计完成的上游 HTTP 请求数，Counter，不等于成功数。

**PromQL**：

```promql
# Query A：上游请求尝试速率
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_rq_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)

# Query B：上游请求完成速率
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_rq_completed{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
```

**展示**：单位 req/s，图例明确写“上游请求尝试”和“上游请求完成”。

**问题与注意事项**：

- `rq_total` 可能包含重试，不严格等于客户端 RPS。
- `rq_completed` 可能包括非 2xx，不能用 `completed / total` 计算业务成功率。
- 不能用累计的 `total - completed` 推导当前活跃请求数，活跃并发直接看图 18。
- 两条曲线的统计时点不同，短期速率差不能直接解释为“丢失请求”。

### 图 18：当前上游请求并发（核心）

**用途**：观察 Envoy 侧当前仍在处理的上游请求数。

**包含指标**：

- `envoy_cluster_upstream_rq_active`：当前活跃上游请求数，Gauge。

**PromQL**：

```promql
# 总览：所有选中 Envoy Pod 的在途请求总量
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_rq_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# 排障：保留 pod 分组时单独使用下面的查询
sum by (envoy_cluster_name, pod) (
  envoy_cluster_upstream_rq_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)
```

**展示**：单位 requests，Gauge 直接展示；总览与按 Pod 排障查询二选一，不要在同一面板重复相加。

**问题与注意事项**：

- `rq_active` 不等于 vLLM `num_requests_running`。
- 请求可能处于连接建立后的发送、等待首个响应、vLLM Waiting、Prefill、Decode 或 SSE 输出阶段。
- 长推理和 SSE 会使较低 RPS 也形成较高并发，不能仅凭并发高判断异常。

### 图 19：连接池等待（核心，两个视图）

**用途**：分别观察当前等待连接池资源的请求数，以及进入等待流程的频率。

**包含指标**：

- `envoy_cluster_upstream_rq_pending_active`：当前等待连接池资源的请求数，Gauge。
- `envoy_cluster_upstream_rq_pending_total`：累计进入连接池等待流程的请求数，Counter。

**PromQL**：

```promql
# 视图 A：当前等待请求数
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_rq_pending_active{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }
)

# 视图 B：进入等待流程的速率
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_rq_pending_total{
    envoy_cluster_name=~"$upstream_cluster",pod=~"$pod"
  }[5m])
)
```

**展示**：视图 A 单位 requests，视图 B 单位 req/s；优先上下两个视图，平台不支持时拆成两个独立面板。

**问题与注意事项**：

- 两个指标单位不同，不应强行共用 Y 轴。
- `pending_total` 的累计值不是当前队列长度。
- Envoy Pending 不等于 vLLM Scheduler Waiting。
- `rq_active` 升高但 `pending_active` 接近零且 vLLM Waiting 升高时，更倾向于模型 Scheduler 内部排队。

### 图 20：Pending 异常事件（核心）

**用途**：观察连接池容量拒绝、等待连接失败和获取连接前取消。

**包含指标**：

- `envoy_cluster_upstream_rq_pending_overflow`：Pending 相关容量拒绝事件，Counter。
- `envoy_cluster_upstream_rq_pending_failure_eject`：等待连接期间因连接失败或远端终止而失败的事件，Counter。
- `envoy_cluster_upstream_rq_cancelled`：获取连接池连接之前被取消的请求事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(pending_overflow|pending_failure_eject|cancelled)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位次/5min，独立折线不堆叠。

**问题与注意事项**：

- `pending_overflow` 不必然只由 Pending Queue 已满导致，需联查图 4、5 的 `rq_open` 和 `rq_pending_open`。
- `pending_failure_eject` 需联查建连失败、建连超时和无健康后端。
- `rq_cancelled` 不覆盖所有客户端取消，只对应获取连接池连接之前的取消。
- 三个事件可能属于同一次故障的不同阶段，不能相加为唯一失败请求数。

### 图 21：超时与请求终止（核心）

**用途**：区分整体请求超时、单次尝试超时、单次尝试空闲超时和最大请求时长终止。

**包含指标**：

- `envoy_cluster_upstream_rq_timeout`：上游请求超时事件，Counter。
- `envoy_cluster_upstream_rq_per_try_timeout`：单次上游尝试达到 per-try 超时的事件，Counter。
- `envoy_cluster_upstream_rq_per_try_idle_timeout`：单次尝试空闲超时相关事件，类型和精确语义需按部署版本确认。
- `envoy_cluster_upstream_rq_max_duration_reached`：达到最大请求持续时间而终止的事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(timeout|per_try_timeout|per_try_idle_timeout|max_duration_reached)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位次/5min，独立折线不堆叠；`per_try_idle_timeout` 图例注明“版本待验证”。

**问题与注意事项**：

- `per_try_timeout` 后仍可能通过重试成功，不能直接视为最终请求失败。
- `per_try_idle_timeout` 在核实部署版本的 HELP/源码前，不应解释为所有 SSE 无 Token 间隔超时。
- `rq_timeout` 是请求处理阶段，`cx_connect_timeout` 是建连阶段，`cx_idle_timeout` 是连接空闲回收，三者不能混用。
- 超时增长需结合 vLLM TTFT/E2E、模型排队和网关超时配置分析。

### 图 22：上游请求重置方向（核心）

**用途**：区分收到上游远端重置和 Envoy 本地发起重置。

**包含指标**：

- `envoy_cluster_upstream_rq_rx_reset`：收到上游远端请求或流重置的事件，Counter。
- `envoy_cluster_upstream_rq_tx_reset`：Envoy 本地发起上游请求或流重置的事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(rx_reset|tx_reset)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位次/5min，图例使用“收到上游重置”和“Envoy 本地发起重置”。

**问题与注意事项**：

- `rx_reset` 与 `cx_destroy_remote_with_active_rq` 同时增加时，更值得检查上游远端或网络中断。
- `tx_reset` 与 `rq_timeout` 同时增加时，更值得检查 Envoy 超时、取消或主动终止。
- Reset 只说明方向，不能单凭指标判断哪一端存在程序 Bug。
- 最终原因仍需 Envoy Access Log、响应标志和 vLLM 日志确认。

### 图 23：重试与重试受限（核心）

**用途**：观察重试负载、重试后成功、单请求重试上限和重试预算/熔断限制。

**包含指标**：

- `envoy_cluster_upstream_rq_retry`：累计发起的重试次数，Counter。
- `envoy_cluster_upstream_rq_retry_success`：重试后成功事件，Counter。
- `envoy_cluster_upstream_rq_retry_limit_exceeded`：达到单请求可重试次数限制的事件，Counter。
- `envoy_cluster_upstream_rq_retry_overflow`：受重试熔断或 Retry Budget 限制而未获准重试的事件，Counter。

**PromQL**：

```promql
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(retry|retry_success|retry_limit_exceeded|retry_overflow)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)
```

**展示**：单位次/5min，独立折线不堆叠；与图 6 的并发重试限额状态联查。

**问题与注意事项**：

- 一次客户端请求可能发生多次重试，而 `retry_success` 不一定按相同次数增长，因此不能直接用 `retry_success / retry` 作为客户端请求重试成功率。
- `retry_limit_exceeded` 与 `retry_overflow` 分别对应单请求重试次数和重试资源限制，含义不同。
- 重试增加可能放大 vLLM 和 GPU 负载；已经开始输出部分 SSE 的请求不能简单假设可以透明重试。
- 本图与图 6 使用部分相同 Counter，是“请求视角”和“限额视角”的两种展示，不能跨图重复累计事件。

### 图 24：特殊请求与重试退避（按需）

**用途**：用于维护模式、本地拒绝、重试退避和 0-RTT 专项排障。

**包含指标**：

- `envoy_cluster_upstream_rq_maintenance_mode`：上游维护模式触发的本地拒绝/503 事件，Counter。
- `envoy_cluster_upstream_rq_retry_backoff_exponential`：指数退避重试事件，Counter。
- `envoy_cluster_upstream_rq_retry_backoff_ratelimited`：限流相关退避重试事件，Counter。
- `envoy_cluster_upstream_rq_0rtt`：0-RTT Early Data 相关请求事件，具体统计语义和类型需按部署版本确认。

**PromQL**：

```promql
# Query A：维护模式和重试退避事件
sum by (__name__, envoy_cluster_name) (
  increase({
    __name__=~"envoy_cluster_upstream_rq_(maintenance_mode|retry_backoff_exponential|retry_backoff_ratelimited)",
    envoy_cluster_name=~"$upstream_cluster",
    pod=~"$pod"
  }[5m])
)

# Query B：仅用于检查 0-RTT 原始序列；确认 Counter 语义后再决定是否使用 rate/increase
envoy_cluster_upstream_rq_0rtt{
  envoy_cluster_name=~"$upstream_cluster",
  pod=~"$pod"
}
```

**展示**：默认折叠或放在诊断区；Query A 单位次/5min，Query B 先检查原始值和 HELP，不直接设单位。

**问题与注意事项**：

- 维护模式、Backoff 和 0-RTT 不适合作为默认核心告警或核心负载指标。
- `rq_0rtt` 在未确认类型前直接套用 `increase()` 可能产生错误解释。
- 指标存在不代表对应功能已启用，长期无数据或零值需结合配置和版本判断。

---

## 3. 跨图共性问题与使用边界

1. **这些仍是 Envoy Upstream Cluster 指标**：`envoy_cluster_name` 中包含 `httproute/...`，不代表指标由 HTTPRoute CRD 自身输出。
2. **上游尝试不等于客户端请求**：重试会破坏一一对应关系，不能跨层直接比较计数并解释为“丢失请求”。
3. **完成不等于成功**：当前清单没有完整的 2xx/4xx/5xx 维度，业务成功率需结合 Envoy HTTP 统计、Access Log 或业务指标。
4. **当前清单没有上游请求延迟 Histogram**：`connect_ms` 和 `length_ms` 分别是建连和连接生命周期耗时，不能替代 TTFT、TPOT 或端到端请求延迟。
5. **连接不等于请求**：HTTP/2 多路复用时，连接事件数不等于受影响请求数。
6. **Envoy Active/Pending 不等于 vLLM Running/Waiting**：二者位于不同处理层，需要联合而不是互相替代。
7. **异常事件不能跨图重复累计**：同一 Counter 可能同时出现在限额图、连接图和请求图中；同一故障也可能同时产生超时、Reset、断连和重试。
8. **总量与子项不能相加**：如 `destroy_with_active_rq` 与 local/remote 子项可能包含，DEFAULT/HIGH 也不能相加。
9. **不同单位不能强行共轴**：0/1 状态、requests、连接数、req/s、Byte/s、Bytes、events/min 和次/5min 应分视图或使用独立坐标轴。
10. **指标相关性不等于因果**：最终故障定位仍需配置、Envoy Access Log、响应标志、AIBrix 与 vLLM 指标和日志共同确认。

## 4. 推荐 Dashboard 排障顺序

```text
请求速率与并发（图 17、18）
    ↓
连接池等待与 Pending 异常（图 19、20）
    ↓
连接、请求、Pending、Retry 限额（图 2～6）
    ↓
健康 Endpoint、建连与断连（图 1、7～10）
    ↓
吞吐、Buffer、流控与背压（图 13～16）
    ↓
超时、Reset 与 Retry（图 21～23）
    ↓
HTTP 状态、Access Log、AIBrix 与 vLLM 的最终业务结果
```

连接生命周期、协议分布和特殊请求退避（图 11、12、24）默认放入附加诊断区。
