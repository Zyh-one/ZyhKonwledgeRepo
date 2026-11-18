# Envoy Cluster 指标分析（第 4 类）：熔断与并发限制

> **适用范围**：Envoy Gateway 中 `envoy_cluster_name=~"httproute/.*"` 的上游 Cluster，重点面向 Envoy → HTTPRoute 后端 Service / vLLM 的请求转发链路。
>
> **核心结论**：本类 10 个指标均是 **状态型 Gauge**，可以理解为五种资源限制的“开关”或“满额信号”，**不是**请求失败次数，也**不是**当前资源的实际数量。诊断问题时必须结合 `upstream_*_overflow` 等事件 Counter 和 `upstream_*_active` 等实际负载 Gauge。

## 1. 熔断器在 Envoy 中的含义

Envoy Circuit Breaker 是针对 **Upstream Cluster** 的资源限额机制，主要保护代理及其上游，限制上游连接数、连接池数、并发请求数、Pending Request 和并发重试数。

与“服务连续报错后自动隔离异常实例”的思路不同，此处的熔断器重点是 **资源达到配置阈值后限制新增资源分配**。异常实例检测属于另一个模块：Outlier Detection。

- **DEFAULT**、**HIGH**：Envoy 的两种路由优先级；不是告警等级，也不是 K8s Pod Priority。需要以实际路由优先级判断哪个维度更有用。
- **`*_open = 0`**：采样时对应限制尚未达到满额状态。
- **`*_open = 1`**：采样时对应限制达到阈值，后续对应资源申请可能被限制。**不代表所有现存请求失败**。
- **注意**：这些状态可能短暂变化。采集间隔较长时可能漏采短时的 `1`，因此要与累计溢出事件共同观察。

## 2. 10 个指标完整清单

| 资源维度 | DEFAULT 优先级 | HIGH 优先级 | 对应限制配置 | 核心含义 |
|---|---|---|---|---|
| 上游连接数 | `envoy_cluster_circuit_breakers_default_cx_open` | `envoy_cluster_circuit_breakers_high_cx_open` | `max_connections` | 连接数限额是否达到 |
| 上游连接池数 | `envoy_cluster_circuit_breakers_default_cx_pool_open` | `envoy_cluster_circuit_breakers_high_cx_pool_open` | `max_connection_pools` | 连接池数量限额是否达到 |
| 并发上游请求数 | `envoy_cluster_circuit_breakers_default_rq_open` | `envoy_cluster_circuit_breakers_high_rq_open` | `max_requests` | 并发请求限额是否达到 |
| 等待连接的请求数 | `envoy_cluster_circuit_breakers_default_rq_pending_open` | `envoy_cluster_circuit_breakers_high_rq_pending_open` | `max_pending_requests` | Pending Request 限额是否达到 |
| 并发重试数 | `envoy_cluster_circuit_breakers_default_rq_retry_open` | `envoy_cluster_circuit_breakers_high_rq_retry_open` | `max_retries` | 并发重试限额是否达到 |

**清单核对**：5 个资源维度 × 2 种优先级 = **10 个**，与此前提供的第 4 类指标完全一致。

## 3. 逐组分析：状态指标与关联指标

### 3.1 `cx_open`：上游连接数限额

- **监控对象**：Cluster 的上游连接资源，而非客户端到 Envoy 的 Downstream 连接。
- **状态含义**：`cx_open=1` 表示达到连接数限制；已有连接可能仍可复用。
- **重要区别**：连接数不等于请求数；HTTP/2 一条连接可以复用多个并发 Stream。
- **实际连接数**：`envoy_cluster_upstream_cx_active`（Gauge）。
- **连接溢出事件**：`envoy_cluster_upstream_cx_overflow`（Counter）。
- **连接失败辅助项**：`envoy_cluster_upstream_cx_connect_fail`、`envoy_cluster_upstream_cx_connect_timeout`（Counter）。

**诊断逻辑**：`cx_open=1` + `cx_overflow` 增长，更支持“连接限额妨碍新连接创建”；若 `cx_connect_fail` 增长而熔断状态正常，则更应排查网络、端点或服务可达性。

### 3.2 `cx_pool_open`：上游连接池数量限额

- **监控对象**：Connection Pool 的数量，而非实际 TCP 连接数。
- **状态含义**：`cx_pool_open=1` 表示池数量达到限制，新建池可能需要先回收空闲池，回收不了时可能溢出。
- **事件佐证**：`envoy_cluster_upstream_cx_pool_overflow`（Counter）。
- **优先级**：一般低于连接数和请求并发限制，除非已经发现连接池数量或溢出异常。

**诊断逻辑**：不能将 `cx_pool_open=1` 直接解释为“所有连接已满”或“vLLM 无法处理新请求”。

### 3.3 `rq_open`：并发上游请求数限额

- **监控对象**：发往某个 Upstream Cluster 的并发请求资源。
- **状态含义**：`rq_open=1` 表示请求并发资源达到阈值。
- **当前请求量**：`envoy_cluster_upstream_rq_active`（Gauge）。
- **溢出佐证**：某些 Envoy 版本会提供请求并发溢出计数器（如 `upstream_rq_active_overflow`）；**该名称不在本次已给出的 133 项清单中，不可假设现网一定存在**。
- **LLM 关联**：长时间运行的推理或 SSE Streaming 会使在途请求持续存在，较低 RPS 也可能有较高并发。

**诊断逻辑**：`rq_open=1` + `rq_active` 持续较高，说明请求资源可能接近容量；要确认实际是否拒绝请求，仍需对应溢出事件、Envoy Access Log 和响应状态。

### 3.4 `rq_pending_open`：等待上游连接的请求数限额

- **监控对象**：Envoy 上游连接池中等待可用连接或容量的 Pending Request。
- **状态含义**：`rq_pending_open=1` 表示 Pending Request 数量达到限制。
- **实际排队**：`envoy_cluster_upstream_rq_pending_active`（Gauge）。
- **溢出事件**：`envoy_cluster_upstream_rq_pending_overflow`（Counter）。
- **极易混淆**：Envoy Pending Request **不是** vLLM Scheduler 的 Waiting Queue。Envoy Pending 为零时，vLLM 内部仍可能严重排队。

**诊断逻辑**：`rq_pending_open=1` + `rq_pending_overflow` 增长，对上游连接池等待容量不足提供更强证据。

### 3.5 `rq_retry_open`：并发重试限额

- **监控对象**：Cluster 当前正在发生的并发重试数量。
- **状态含义**：`rq_retry_open=1` 表示并发重试资源达到阈值。
- **重试事件**：`envoy_cluster_upstream_rq_retry`（Counter）。
- **重试受限**：`envoy_cluster_upstream_rq_retry_overflow`（Counter）。
- **重试成功**：`envoy_cluster_upstream_rq_retry_success`（Counter）。
- **区分配置**：`max_retries` 是并发重试资源限制，**不是单条请求允许重试的次数**；每条请求的重试次数由 Retry Policy 等配置控制。
- **LLM 风险**：对已开始推理、尤其已经返回部分 SSE 内容的请求，不能简单假设 Envoy 能透明地重新发送并成功接续。

**诊断逻辑**：`rq_retry_open=1` + `rq_retry_overflow` 增长提示重试资源受到限制；同时检查 `rq_retry` 是否异常增加，以识别重试风暴。

## 4. 联合分析：三个层面的证据

| 层面 | 指标类型 | 能回答什么 | 局限 |
|---|---|---|---|
| **限制状态** | `circuit_breakers_*_open`，Gauge | 此刻是否达到限额？ | 不说明已经拒绝多少次申请；可能漏采瞬时状态 |
| **实际负载** | `upstream_cx_active`、`upstream_rq_active`、`upstream_rq_pending_active`，Gauge | 当前连接、在途请求和等待请求有多少？ | 接近限额不等于已发生拒绝 |
| **拒绝/溢出事件** | `upstream_cx_overflow`、`upstream_cx_pool_overflow`、`upstream_rq_pending_overflow`、`upstream_rq_retry_overflow` 等 Counter | 最近是否出现限额溢出事件？ | 需用 `increase()` / `rate()` 看时间窗口内增量；计数器可能在进程重启时归零 |

### 推荐判断顺序

1. 先看对应 `*_open` 是否出现 `1`（是否达到限制）。
2. 再看相关 `*_active` 是否接近高位（实际资源负载）。
3. 最后看对应 `*_overflow` 的增量，并结合 Envoy Access Log / 5xx / 请求超时，判断是否影响实际转发。

**切勿推导**：`open=1` ⇒ “一定有请求失败”；`open=0` ⇒ “这段时间从未发生过熔断”。这两种结论都不可靠。

## 5. VictoriaMetrics / PromQL 示例

以下查询仅使用你已提供清单中的指标；除指定名称的查询外，均按 `envoy_cluster_name=~"httproute/.*"` 限定到 HTTPRoute 关联的上游 Cluster。

### 5.1 查看全部 10 个开关

```promql
{__name__=~"envoy_cluster_circuit_breakers_(default|high)_(cx|cx_pool|rq|rq_pending|rq_retry)_open",
 envoy_cluster_name=~"httproute/.*"}
```

### 5.2 查看最近 5 分钟采样到的开关状态是否曾达到 1

```promql
max by (__name__, envoy_cluster_name, pod) (
  max_over_time(
    {__name__=~"envoy_cluster_circuit_breakers_default_.*_open",
     envoy_cluster_name=~"httproute/.*"}[5m]
  )
)
```

> 只有采集到的 `1` 才会被报告；这无法排除抓取间隔内发生的短时熔断。

### 5.3 查看实际活跃连接及请求数

```promql
{__name__=~"envoy_cluster_upstream_(cx_active|rq_active|rq_pending_active)",
 envoy_cluster_name=~"httproute/.*"}
```

### 5.4 查看最近 5 分钟的溢出事件

```promql
sum by (__name__, envoy_cluster_name) (
  increase(
    {__name__=~"envoy_cluster_upstream_(cx_overflow|cx_pool_overflow|rq_pending_overflow|rq_retry_overflow)",
     envoy_cluster_name=~"httproute/.*"}[5m]
  )
)
```

> 若同一 Cluster 有多个 Envoy Pod，此处 `sum by` 汇总的是各 Envoy 实例的事件增量；排查具体故障 Pod 时保留 `pod` 分组。

### 5.5 定位单条 HTTPRoute 的并发请求限制

```promql
envoy_cluster_circuit_breakers_default_rq_open{
  envoy_cluster_name="httproute/ns-e23f5b20fb9b42d3ac674f9691a0b9b1/coderunner-go-router-serving/rule/0"
}
```

同一 Cluster 的在途请求：

```promql
envoy_cluster_upstream_rq_active{
  envoy_cluster_name="httproute/ns-e23f5b20fb9b42d3ac674f9691a0b9b1/coderunner-go-router-serving/rule/0"
}
```

## 6. 在 AiBrix + vLLM 中的分析优先级

| 资源限制 | 建议 | 主要原因 |
|---|---|---|
| `rq_open` | **重点** | LLM 推理和 SSE 请求持续时间长，并发容易累积 |
| `rq_pending_open` | **重点** | 关联 Envoy 上游连接池等待容量，而不是 vLLM 内部排队 |
| `cx_open` | **重点** | 反映上游连接数是否接近资源上限 |
| `rq_retry_open` | 次重点 | 重试放大可能加重模型负载，尤其需检查失败与重试行为 |
| `cx_pool_open` | 按需 | 主要用于连接池数量异常或溢出排查 |

### 三层监控不要混淆

- **Envoy**：连接、连接池、Pending Request、上游并发、重试和网络故障。
- **AiBrix**：模型实例选择、负载感知、路由决策及相关策略。
- **vLLM**：内部 Waiting / Running Request、KV Cache、Prefill / Decode、TTFT / TPOT。

HTTPRoute 相关的 Cluster 指标属于 **Envoy 向业务后端转发请求的代理层**，不能直接代替模型推理内部指标。

## 7. 排障速查

| 现象 | 优先查看 | 后续检查 |
|---|---|---|
| 新连接受限 | `cx_open` | `cx_active` + `cx_overflow` + 连接失败/超时 |
| 连接池创建受限 | `cx_pool_open` | `cx_pool_overflow` + 实际 Cluster 连接池配置 |
| 请求并发接近限额 | `rq_open` | `rq_active` + 日志 + 可用的并发溢出指标 |
| Envoy 等待连接的请求堆积 | `rq_pending_open` | `rq_pending_active` + `rq_pending_overflow` |
| 重试增加或受限 | `rq_retry_open` | `rq_retry` + `rq_retry_overflow` + `rq_retry_success` |

## 8. 最终结论

第 4 类 10 个指标**非常贴近请求转发，但本质都是限额状态信号**：

> **Gauge 状态（是否满额）→ Active 负载（占用多少）→ Overflow Counter（是否触发拒绝）→ 请求日志和业务指标（是否造成实际失败）**。

这条链路比单独盯着某个 `*_open` 指标更能解释 Envoy → vLLM 的请求转发瓶颈。

---

**参考资料**：Envoy 官方文档中的 *Upstream Cluster Statistics*、*Circuit Breaking*、*Cluster Circuit Breakers*。具体指标是否导出、默认阈值及个别熔断细节，需以当前 Envoy 版本和实际 `/config_dump` 为准。
