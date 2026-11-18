# Envoy 第 6 类：上游连接管理指标（Upstream Connection）

> 适用范围：Envoy Gateway 中 `envoy_cluster_name=~"httproute/.*"` 的 Upstream Cluster 指标。重点分析 Envoy → HTTPRoute 对应后端（如 vLLM Service Endpoint）的连接状态，而不是 HTTPRoute CRD 自身的运行状态。
>
> **核心结论**：第 4 类 Circuit Breaker 主要回答“资源限额是否已达到”；第 6 类 Connection 指标回答“连接实际建立、失败、复用、关闭或溢出了什么”。连接数不等于 HTTP 请求数，HTTP/2 一条连接可承载多个请求。

## 1. 分组总览（29 个指标）

| 子类 | 数量 | 主要分析问题 | 优先级 |
|---|---:|---|---|
| A. 连接数量与协议 | 5 | 有多少连接？是否反复建连？ | 高 |
| B. 连接建立与失败 | 7 | 连接是否成功？建连是否缓慢？ | 高 |
| C. 连接销毁与异常中断 | 7 | 谁关闭了连接？是否有请求未完成？ | 高 |
| D. 连接生命周期 | 6 | 连接维持多久？为何退出连接池？ | 中 |
| E. 熔断、可用性与协议异常 | 4 | 是否因资源、无健康后端或协议错误失败？ | 高 |
| **合计** | **29** | | |

## 2. 连接数量与协议（5 个）

| 指标全名 | 类型 | 解释 | 分析建议 |
|---|---|---|---|
| `envoy_cluster_upstream_cx_active` | Gauge | 当前存在的上游连接数（含可能空闲可复用的连接） | 结合 `rq_active` 区分连接和请求负载 |
| `envoy_cluster_upstream_cx_total` | Counter | 累计建立的上游连接数 | 用 `rate()` 观察新建连接速率 |
| `envoy_cluster_upstream_cx_http1_total` | Counter | 累计建立的 HTTP/1.x 上游连接数 | 查看上游连接协议分布 |
| `envoy_cluster_upstream_cx_http2_total` | Counter | 累计建立的 HTTP/2 上游连接数 | HTTP/2 可能在同一连接复用多个 Stream |
| `envoy_cluster_upstream_cx_http3_total` | Counter | 累计建立的 HTTP/3 上游连接数 | 仅协议启用时重点分析 |

**例子**：`cx_active=4`、`upstream_rq_active=100` 并不矛盾，特别是在 HTTP/2 多路复用场景。`cx_total` 快速增长但请求速率不变，可进一步查看连接时长、销毁数、建连失败等，以排查连接复用不足。

## 3. 连接建立与失败（7 个）

| 指标全名 | 类型 | 解释 | 分析建议 |
|---|---|---|---|
| `envoy_cluster_upstream_cx_connect_attempts_exceeded` | Counter | 连续连接尝试失败超过允许次数的事件 | 排查持续性后端连通问题 |
| `envoy_cluster_upstream_cx_connect_fail` | Counter | 上游连接建立失败次数 | 检查端口监听、网络、Pod 状态、Endpoint |
| `envoy_cluster_upstream_cx_connect_ms_bucket` | Histogram bucket | 连接建立耗时的分桶计数 | 可估计建连耗时分位数 |
| `envoy_cluster_upstream_cx_connect_ms_count` | Histogram count | 建连耗时观测次数 | 计算平均耗时的分母 |
| `envoy_cluster_upstream_cx_connect_ms_sum` | Histogram sum | 建连耗时观测值总和 | 计算平均耗时的分子 |
| `envoy_cluster_upstream_cx_connect_timeout` | Counter | 建立上游连接超时次数 | 与请求处理超时区别开来 |
| `envoy_cluster_upstream_cx_connect_with_0_rtt` | Counter | 支持使用 0-RTT Early Data 的连接累计数 | 特定协议场景，通常非优先项 |

**重要区分**：`cx_connect_timeout` 发生在**建连阶段**，而 `upstream_rq_timeout` 发生在**请求处理/响应等待阶段**。连接耗时 Histogram 统计的是实际新建连接，不是每个 HTTP 请求的耗时；已有连接复用时不会重新经历相同的建连流程。

## 4. 连接销毁与异常中断（7 个）

| 指标全名 | 类型 | 解释 | 分析建议 |
|---|---|---|---|
| `envoy_cluster_upstream_cx_destroy` | Counter | 累计销毁的上游连接数 | 正常关闭也计入，不能单独当故障率 |
| `envoy_cluster_upstream_cx_destroy_local` | Counter | 由 Envoy 本地一侧关闭的连接数 | 排查代理超时、关闭策略、下游取消 |
| `envoy_cluster_upstream_cx_destroy_local_with_active_rq` | Counter | Envoy 本地关闭时有活跃请求的连接数 | 重点结合请求取消、超时、重置分析 |
| `envoy_cluster_upstream_cx_destroy_remote` | Counter | 由上游远端一侧关闭的连接数 | 排查后端主动断连、进程/网络事件 |
| `envoy_cluster_upstream_cx_destroy_remote_with_active_rq` | Counter | 上游远端关闭时有活跃请求的连接数 | 长时流式推理中尤其值得关注 |
| `envoy_cluster_upstream_cx_destroy_with_active_rq` | Counter | 关闭时存在一个或多个活跃请求的连接数 | 比一般的 `cx_destroy` 更接近异常请求中断 |
| `envoy_cluster_upstream_cx_close_notify` | Counter | 连接通过协议层关闭通知进行关闭的次数（如 `Connection: close`、`GOAWAY`） | 协议允许的关闭行为，不一定异常 |

**流式推理举例**：vLLM 正在持续返回 SSE Token 时，上游连接被关闭，可能增加 `cx_destroy_with_active_rq`；若由服务端侧关闭，还可能增加 `cx_destroy_remote_with_active_rq`。但这两者都**按连接事件计数，不是受影响请求数**；HTTP/2 一条连接可承载多个活跃 Stream。应结合第 8 类的 `upstream_rq_rx_reset`、`upstream_rq_tx_reset`、`upstream_rq_cancelled`、`upstream_rq_timeout` 以及应用日志综合定位。

## 5. 连接生命周期（6 个）

| 指标全名 | 类型 | 解释 | 分析建议 |
|---|---|---|---|
| `envoy_cluster_upstream_cx_idle_timeout` | Counter | 因上游连接空闲超时而关闭的次数 | 不等于活跃 HTTP Stream 的空闲超时 |
| `envoy_cluster_upstream_cx_length_ms_bucket` | Histogram bucket | 连接持续时间的分桶计数 | 判断是否存在大量短连接 |
| `envoy_cluster_upstream_cx_length_ms_count` | Histogram count | 连接持续时间观测次数 | 计算平均连接时长的分母 |
| `envoy_cluster_upstream_cx_length_ms_sum` | Histogram sum | 连接持续时间观测值总和 | 计算平均连接时长的分子 |
| `envoy_cluster_upstream_cx_max_duration_reached` | Counter | 连接达到最大持续时间限制的次数 | 检查连接生命周期配置 |
| `envoy_cluster_upstream_cx_max_requests` | Counter | 连接达到允许承载的最大请求数而关闭/停止复用的次数 | 与 Cluster 级并发 `max_requests` 熔断不同 |

**注意**：Connection Idle Timeout ≠ HTTP Request Timeout ≠ HTTP Stream Idle Timeout。`cx_length_ms_*` 的 `_ms` 反映原始 Envoy 统计命名；若导出的 Histogram 进行单位转换，以实际 `/stats/prometheus` 的 `HELP` / bucket 边界为准。

## 6. 熔断、可用性与协议异常（4 个）

| 指标全名 | 类型 | 解释 | 联动指标 |
|---|---|---|---|
| `envoy_cluster_upstream_cx_none_healthy` | Counter | 因没有可用健康后端而无法获得上游连接的事件 | `membership_healthy`、`lb_healthy_panic` |
| `envoy_cluster_upstream_cx_overflow` | Counter | 上游连接数熔断限制的溢出事件 | 第 4 类 `cx_open`、本类 `cx_active` |
| `envoy_cluster_upstream_cx_pool_overflow` | Counter | 上游连接池数量限制的溢出事件 | 第 4 类 `cx_pool_open` |
| `envoy_cluster_upstream_cx_protocol_error` | Counter | 上游连接出现协议错误的事件 | Envoy 日志、响应标志与后端协议配置 |

其中 `cx_open`/`cx_pool_open` 是**是否达到阈值的 Gauge 状态**，而 `cx_overflow`/`cx_pool_overflow` 是**实际溢出事件的 Counter**。前者为 1 并不代表所有新请求都会失败，因为已存在的连接可能继续复用。

## 7. VictoriaMetrics / PromQL 查询示例

查询前先确认 `envoy_cluster_name=~"httproute/.*"` 匹配到目标 Cluster，并在多 Envoy Pod 情况下保留 `pod` 标签。

### 7.1 当前活跃连接数

```promql
envoy_cluster_upstream_cx_active{envoy_cluster_name=~"httproute/.*"}
```

### 7.2 最近五分钟新建连接速率（连接/秒）

```promql
sum by (pod, envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_total{envoy_cluster_name=~"httproute/.*"}[5m])
)
```

### 7.3 最近五分钟连接建立失败及超时

```promql
sum by (__name__, pod, envoy_cluster_name) (
  increase({__name__=~"envoy_cluster_upstream_cx_(connect_fail|connect_timeout|connect_attempts_exceeded)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

### 7.4 最近五分钟活跃请求期间断连事件

```promql
sum by (__name__, pod, envoy_cluster_name) (
  increase({__name__=~"envoy_cluster_upstream_cx_destroy_(local_with_active_rq|remote_with_active_rq|with_active_rq)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

> `destroy_with_active_rq` 与两个 local/remote 子项之间可能有包含关系，**不要直接相加**，否则可能重复计数。

### 7.5 最近五分钟连接熔断、无健康后端、协议错误

```promql
sum by (__name__, pod, envoy_cluster_name) (
  increase({__name__=~"envoy_cluster_upstream_cx_(none_healthy|overflow|pool_overflow|protocol_error)",
            envoy_cluster_name=~"httproute/.*"}[5m])
)
```

### 7.6 平均建连耗时

```promql
sum by (pod, envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_connect_ms_sum{envoy_cluster_name=~"httproute/.*"}[5m])
)
/
sum by (pod, envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_connect_ms_count{envoy_cluster_name=~"httproute/.*"}[5m])
)
```

> 平均值单位应依据实际导出格式核实；分母为 0 时结果无意义。直方图可以补充 P90/P99，需先确认 `_bucket` 的单位及 `le`。

## 8. 推荐故障分析路径

| 现象 | 先看 | 接着结合 | 初步排查方向 |
|---|---|---|---|
| 请求返回 503，无法连接后端 | `cx_connect_fail`、`cx_none_healthy` | `membership_healthy`、Envoy 响应标志 | 后端端点不可用、拒绝连接、服务发现 |
| 连接建立缓慢 | `cx_connect_ms_*`、`cx_connect_timeout` | 网络 RTT、Pod/Node 资源 | 建连和网络问题 |
| 请求期间 SSE 中断 | `cx_destroy_with_active_rq` | `destroy_local/remote_with_active_rq`、`rq_rx_reset`/`rq_tx_reset` | 后端主动断连、代理超时、取消、网络重置 |
| 连接频繁重建 | `cx_total`、`cx_destroy`、`cx_length_ms_*` | `cx_idle_timeout`、HTTP 协议 | 连接池复用、空闲策略、网络稳定性 |
| 第 4 类熔断开关触发 | `cx_active`、`cx_overflow`、`cx_pool_overflow` | `default/high_cx_open`、`default/high_cx_pool_open` | 连接资源限制、连接池限制 |
| HTTP 请求并发高，但连接不多 | `cx_active` | `upstream_rq_active`、HTTP/2 | 多路复用，不应直接当异常 |

## 9. 推荐优先保留的核心指标

- **连接负载**：`upstream_cx_active`、`upstream_cx_total`
- **连接故障**：`upstream_cx_connect_fail`、`upstream_cx_connect_timeout`、`upstream_cx_connect_ms_*`
- **请求期间断连**：`upstream_cx_destroy_with_active_rq`、`upstream_cx_destroy_local_with_active_rq`、`upstream_cx_destroy_remote_with_active_rq`
- **不可用/熔断**：`upstream_cx_none_healthy`、`upstream_cx_overflow`、`upstream_cx_pool_overflow`
- **协议异常**：`upstream_cx_protocol_error`

上面省略了统一前缀 `envoy_cluster_`。其他指标保留在完整字典中，按需进行专项排查。

## 10. 边界与注意事项

1. **Cluster 粒度，不是 HTTPRoute 资源自身执行监控**：`envoy_cluster_name` 可以关联 `httproute/.../rule/0`，但实际指标是 Envoy 内部上游 Cluster 统计。
2. **通常按 Envoy Proxy 实例分别维护**：在 VM 中不要忽略 `pod` 造成误判。
3. **连接不等于请求**：不能把 `cx_active` 当成 vLLM 并发请求数，更不能当作 `vllm:num_requests_running`。
4. **正常关闭也会计数**：`cx_destroy`、`cx_idle_timeout`、`cx_close_notify` 增长并不必然是故障。
5. **Counter 和 Gauge 使用方式不同**：Counter 通常用 `rate`/`increase`；Gauge 看当前值或时间窗口内的峰值。
6. **流式响应需要联合第 8 类请求指标**：尤其是 `upstream_rq_timeout`、`upstream_rq_rx_reset`、`upstream_rq_tx_reset`、`upstream_rq_cancelled`。
7. **准确类型和单位以部署版本为准**：检查 Envoy `/stats/prometheus` 或 VictoriaMetrics 指标 HELP；指标存在不意味着对应功能一定启用。

---

**一句话总结**：第 6 类回答的是 Envoy 将 HTTPRoute 对应请求交给上游时，连接**是否能建起来、能否稳定复用、是否在请求执行期间被断开，以及是否被连接类资源限制拒绝**。
