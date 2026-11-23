# `envoy-aibrix-system-aibrix-eg` 指标名清单

共 **133** 个指标名，按照 [Envoy_HTTPRoute_Cluster_Metrics_分类汇总.md](Envoy_HTTPRoute_Cluster_Metrics_分类汇总.md) 的分类及类内顺序排列，仅保留黄区 VM 实测具有 `envoy_cluster_name=~"httproute/..."` 标签值的指标。第二列填写“是”或“否”，表示是否需要将该指标写入平台数据。

| 指标名                                                                                  | 是否写入平台数据 |
| --------------------------------------------------------------------------------------- | ---------------- |
| `envoy_cluster_assignment_stale`                                                      |                  |
| `envoy_cluster_assignment_timeout_received`                                           |                  |
| `envoy_cluster_assignment_use_cached`                                                 |                  |
| `envoy_cluster_bind_errors`                                                           |                  |
| `envoy_cluster_default_total_match_count`                                             |                  |
| `envoy_cluster_init_fetch_timeout`                                                    |                  |
| `envoy_cluster_original_dst_host_invalid`                                             |                  |
| `envoy_cluster_update_attempt`                                                        |                  |
| `envoy_cluster_update_duration_bucket`                                                |                  |
| `envoy_cluster_update_duration_count`                                                 |                  |
| `envoy_cluster_update_duration_sum`                                                   |                  |
| `envoy_cluster_update_empty`                                                          |                  |
| `envoy_cluster_update_failure`                                                        |                  |
| `envoy_cluster_update_no_rebuild`                                                     |                  |
| `envoy_cluster_update_rejected`                                                       |                  |
| `envoy_cluster_update_success`                                                        |                  |
| `envoy_cluster_update_time`                                                           |                  |
| `envoy_cluster_version`                                                               |                  |
| `envoy_cluster_warming_state`                                                         |                  |
| `envoy_cluster_membership_change`                                                     |                  |
| `envoy_cluster_membership_degraded`                                                   | 是               |
| `envoy_cluster_membership_excluded`                                                   | 是               |
| `envoy_cluster_membership_healthy`                                                    | 是               |
| `envoy_cluster_membership_total`                                                      | 是               |
| `envoy_cluster_lb_healthy_panic`                                                      | 是               |
| `envoy_cluster_lb_local_cluster_not_ok`                                               |                  |
| `envoy_cluster_lb_recalculate_zone_structures`                                        |                  |
| `envoy_cluster_lb_subsets_active`                                                     |                  |
| `envoy_cluster_lb_subsets_created`                                                    |                  |
| `envoy_cluster_lb_subsets_fallback`                                                   |                  |
| `envoy_cluster_lb_subsets_fallback_panic`                                             |                  |
| `envoy_cluster_lb_subsets_removed`                                                    |                  |
| `envoy_cluster_lb_subsets_selected`                                                   |                  |
| `envoy_cluster_lb_zone_cluster_too_small`                                             |                  |
| `envoy_cluster_lb_zone_no_capacity_left`                                              |                  |
| `envoy_cluster_lb_zone_number_differs`                                                |                  |
| `envoy_cluster_lb_zone_routing_all_directly`                                          |                  |
| `envoy_cluster_lb_zone_routing_cross_zone`                                            |                  |
| `envoy_cluster_lb_zone_routing_sampled`                                               |                  |
| `envoy_cluster_max_host_weight`                                                       |                  |
| `envoy_cluster_circuit_breakers_default_cx_open`                                      |                  |
| `envoy_cluster_circuit_breakers_default_cx_pool_open`                                 |                  |
| `envoy_cluster_circuit_breakers_default_rq_open`                                      |                  |
| `envoy_cluster_circuit_breakers_default_rq_pending_open`                              |                  |
| `envoy_cluster_circuit_breakers_default_rq_retry_open`                                |                  |
| `envoy_cluster_circuit_breakers_high_cx_open`                                         |                  |
| `envoy_cluster_circuit_breakers_high_cx_pool_open`                                    |                  |
| `envoy_cluster_circuit_breakers_high_rq_open`                                         |                  |
| `envoy_cluster_circuit_breakers_high_rq_pending_open`                                 |                  |
| `envoy_cluster_circuit_breakers_high_rq_retry_open`                                   |                  |
| `envoy_cluster_outlier_detection_ejections_active`                                    |                  |
| `envoy_cluster_outlier_detection_ejections_consecutive_5xx`                           |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_5xx`                  |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_gateway_failure`      |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_local_origin_failure` |                  |
| `envoy_cluster_outlier_detection_ejections_detected_failure_percentage`               |                  |
| `envoy_cluster_outlier_detection_ejections_detected_local_origin_failure_percentage`  |                  |
| `envoy_cluster_outlier_detection_ejections_detected_local_origin_success_rate`        |                  |
| `envoy_cluster_outlier_detection_ejections_detected_success_rate`                     |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx`                  |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure`      |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure` |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_failure_percentage`               |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_local_origin_failure_percentage`  |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_local_origin_success_rate`        |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_success_rate`                     |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_total`                            |                  |
| `envoy_cluster_outlier_detection_ejections_overflow`                                  |                  |
| `envoy_cluster_outlier_detection_ejections_success_rate`                              |                  |
| `envoy_cluster_outlier_detection_ejections_total`                                     |                  |
| `envoy_cluster_upstream_cx_active`                                                    |                  |
| `envoy_cluster_upstream_cx_close_notify`                                              |                  |
| `envoy_cluster_upstream_cx_connect_attempts_exceeded`                                 |                  |
| `envoy_cluster_upstream_cx_connect_fail`                                              |                  |
| `envoy_cluster_upstream_cx_connect_ms_bucket`                                         |                  |
| `envoy_cluster_upstream_cx_connect_ms_count`                                          |                  |
| `envoy_cluster_upstream_cx_connect_ms_sum`                                            |                  |
| `envoy_cluster_upstream_cx_connect_timeout`                                           |                  |
| `envoy_cluster_upstream_cx_connect_with_0_rtt`                                        |                  |
| `envoy_cluster_upstream_cx_destroy`                                                   |                  |
| `envoy_cluster_upstream_cx_destroy_local`                                             |                  |
| `envoy_cluster_upstream_cx_destroy_local_with_active_rq`                              |                  |
| `envoy_cluster_upstream_cx_destroy_remote`                                            |                  |
| `envoy_cluster_upstream_cx_destroy_remote_with_active_rq`                             |                  |
| `envoy_cluster_upstream_cx_destroy_with_active_rq`                                    |                  |
| `envoy_cluster_upstream_cx_http1_total`                                               |                  |
| `envoy_cluster_upstream_cx_http2_total`                                               |                  |
| `envoy_cluster_upstream_cx_http3_total`                                               |                  |
| `envoy_cluster_upstream_cx_idle_timeout`                                              |                  |
| `envoy_cluster_upstream_cx_length_ms_bucket`                                          |                  |
| `envoy_cluster_upstream_cx_length_ms_count`                                           |                  |
| `envoy_cluster_upstream_cx_length_ms_sum`                                             |                  |
| `envoy_cluster_upstream_cx_max_duration_reached`                                      |                  |
| `envoy_cluster_upstream_cx_max_requests`                                              |                  |
| `envoy_cluster_upstream_cx_none_healthy`                                              |                  |
| `envoy_cluster_upstream_cx_overflow`                                                  |                  |
| `envoy_cluster_upstream_cx_pool_overflow`                                             |                  |
| `envoy_cluster_upstream_cx_protocol_error`                                            |                  |
| `envoy_cluster_upstream_cx_total`                                                     |                  |
| `envoy_cluster_upstream_cx_rx_bytes_buffered`                                         |                  |
| `envoy_cluster_upstream_cx_rx_bytes_total`                                            |                  |
| `envoy_cluster_upstream_cx_tx_bytes_buffered`                                         |                  |
| `envoy_cluster_upstream_cx_tx_bytes_total`                                            |                  |
| `envoy_cluster_upstream_flow_control_backed_up_total`                                 |                  |
| `envoy_cluster_upstream_flow_control_drained_total`                                   |                  |
| `envoy_cluster_upstream_flow_control_paused_reading_total`                            |                  |
| `envoy_cluster_upstream_flow_control_resumed_reading_total`                           |                  |
| `envoy_cluster_upstream_rq_0rtt`                                                      |                  |
| `envoy_cluster_upstream_rq_active`                                                    |                  |
| `envoy_cluster_upstream_rq_cancelled`                                                 |                  |
| `envoy_cluster_upstream_rq_completed`                                                 |                  |
| `envoy_cluster_upstream_rq_maintenance_mode`                                          |                  |
| `envoy_cluster_upstream_rq_max_duration_reached`                                      |                  |
| `envoy_cluster_upstream_rq_pending_active`                                            |                  |
| `envoy_cluster_upstream_rq_pending_failure_eject`                                     |                  |
| `envoy_cluster_upstream_rq_pending_overflow`                                          |                  |
| `envoy_cluster_upstream_rq_pending_total`                                             |                  |
| `envoy_cluster_upstream_rq_per_try_idle_timeout`                                      |                  |
| `envoy_cluster_upstream_rq_per_try_timeout`                                           |                  |
| `envoy_cluster_upstream_rq_retry`                                                     |                  |
| `envoy_cluster_upstream_rq_retry_backoff_exponential`                                 |                  |
| `envoy_cluster_upstream_rq_retry_backoff_ratelimited`                                 |                  |
| `envoy_cluster_upstream_rq_retry_limit_exceeded`                                      |                  |
| `envoy_cluster_upstream_rq_retry_overflow`                                            |                  |
| `envoy_cluster_upstream_rq_retry_success`                                             |                  |
| `envoy_cluster_upstream_rq_rx_reset`                                                  |                  |
| `envoy_cluster_upstream_rq_timeout`                                                   |                  |
| `envoy_cluster_upstream_rq_total`                                                     |                  |
| `envoy_cluster_upstream_rq_tx_reset`                                                  |                  |
| `envoy_cluster_retry_or_shadow_abandoned`                                             |                  |
| `envoy_cluster_upstream_http3_broken`                                                 |                  |
| `envoy_cluster_upstream_internal_redirect_failed_total`                               |                  |
| `envoy_cluster_upstream_internal_redirect_succeeded_total`                            |                  |

## 图表归并说明

以下 4 个指标都是描述 Cluster Endpoint 当前数量的 Gauge，单位统一为“个”，对应**一张“上游 Endpoint 成员与健康状态”数据图**，在图中分别展示 Endpoint 总数、健康、降级和排除数量：

- `envoy_cluster_membership_total`
- `envoy_cluster_membership_healthy`
- `envoy_cluster_membership_degraded`
- `envoy_cluster_membership_excluded`

图中使用 4 条独立折线，不堆叠、不使用 `rate()` 或 `increase()`。`healthy`、`degraded`、`excluded` 不一定是互斥状态，三者之和不必然等于 `total`。多个 Envoy Gateway 副本上报同一 Cluster 时，通常按 `envoy_cluster_name` 取 `max` 去重，不直接求和。

### 第 4 类：熔断与并发限制（5 张数据图）

第 4 类指标按以下 5 个资源维度分别形成数据图。每张图联合展示“限额状态 → 实际负载 → 溢出或相关事件”，不能仅凭 `*_open=1` 判断请求已经失败。表中的 `<default|high>` 表示按实际路由优先级选择 DEFAULT 或 HIGH 指标，不是指标名的一部分，两种优先级不能相加。

| 数据图 | 限额状态 Gauge | 实际负载 Gauge | 溢出及辅助分析指标 |
| ------ | -------------- | -------------- | ------------------ |
| 1. 上游连接数限制 | `envoy_cluster_circuit_breakers_<default\|high>_cx_open` | `envoy_cluster_upstream_cx_active` | `envoy_cluster_upstream_cx_overflow`；辅以 `upstream_cx_connect_fail`、`upstream_cx_connect_timeout` |
| 2. 上游连接池数量限制 | `envoy_cluster_circuit_breakers_<default\|high>_cx_pool_open` | 当前清单没有直接的连接池数量 Gauge，可辅助观察 `envoy_cluster_upstream_cx_active` | `envoy_cluster_upstream_cx_pool_overflow`；不能把连接池数量解释为 TCP 连接数 |
| 3. 上游并发请求限制 | `envoy_cluster_circuit_breakers_<default\|high>_rq_open` | `envoy_cluster_upstream_rq_active` | 当前清单没有直接的并发请求 Overflow 指标，需结合 `upstream_rq_timeout`、`upstream_rq_cancelled`、响应状态及 Access Log |
| 4. Pending Request 限制 | `envoy_cluster_circuit_breakers_<default\|high>_rq_pending_open` | `envoy_cluster_upstream_rq_pending_active` | `envoy_cluster_upstream_rq_pending_overflow`；辅以 `upstream_rq_pending_failure_eject`、`upstream_rq_timeout` |
| 5. 上游重试限制 | `envoy_cluster_circuit_breakers_<default\|high>_rq_retry_open` | 当前清单没有 Active Retry Gauge | `envoy_cluster_upstream_rq_retry`、`upstream_rq_retry_overflow`、`upstream_rq_retry_success`、`upstream_rq_retry_limit_exceeded` |

统一展示与聚合规则：

- 所有查询继续按 `envoy_cluster_name=~"httproute/<业务namespace>/<HTTPRoute名称>/rule/[0-9]+"` 限定到目标 HTTPRoute 的 Upstream Cluster。
- `*_open` 是 0/1 状态 Gauge，表示采样时是否达到限额，不是熔断次数或失败请求数；跨 Envoy 副本取 `max`，观察历史窗口可使用 `max_over_time()`，不能使用 `rate()` 或 `increase()`。
- `*_active` 是当前资源数量 Gauge，不使用 `rate()` 或 `increase()`；展示全部 Envoy 副本的实际总负载时可求和，排查单副本异常时保留 `pod` 标签。
- `*_overflow`、`upstream_rq_retry*` 等 Counter 先分别计算 `increase()` 或 `rate()`，再按需要跨 Envoy 副本求和。
- 状态值、资源数量和事件增量的单位不同，不能强行共用同一 Y 轴；每张数据图应分层展示或使用适当的独立坐标轴。
- `open=0` 不能证明窗口内从未达到限额，`open=1` 也不代表现存请求全部失败；最终业务影响仍需结合超时、取消、重置、响应状态和 Access Log 判断。

### 第 6 类：上游连接管理（6 张数据图）

第 6 类指标描述请求匹配到 Upstream Cluster 后，Envoy 能否建立并稳定复用到后端 Endpoint 的连接。建议形成 **4 张核心图和 2 张按需图**，不要把 29 个指标全部堆在一张图中。

| 数据图 | 主要指标 | 含义和分析思路 | 建议 |
| ------ | -------- | -------------- | ---- |
| 1. 上游连接负载与新建速率 | `envoy_cluster_upstream_cx_active`、`envoy_cluster_upstream_cx_total`；辅以 `envoy_cluster_upstream_rq_active` | `cx_active` 是当前连接数 Gauge，`cx_total` 用 `rate()` 观察新建连接速率；结合请求并发判断是否存在频繁建连。HTTP/2 一条连接可承载多个请求，连接数不等于请求数 | 核心 |
| 2. 上游建连失败与建连耗时 | `envoy_cluster_upstream_cx_connect_fail`、`envoy_cluster_upstream_cx_connect_timeout`、`envoy_cluster_upstream_cx_connect_attempts_exceeded`、`envoy_cluster_upstream_cx_connect_ms_{bucket,count,sum}` | 前三个 Counter 用 `increase()` 观察失败和超时，Histogram 观察平均、P90/P99 建连耗时；结合 Pending 和请求超时判断是否影响转发。建连耗时不是每个 HTTP 请求的耗时，复用连接不会重新建连 | 核心 |
| 3. 活跃请求期间的连接中断 | `envoy_cluster_upstream_cx_destroy_with_active_rq`、`envoy_cluster_upstream_cx_destroy_local_with_active_rq`、`envoy_cluster_upstream_cx_destroy_remote_with_active_rq`；辅以 `upstream_rq_rx_reset`、`upstream_rq_tx_reset`、`upstream_rq_cancelled`、`upstream_rq_timeout` | 重点分析 SSE 流式响应是否中断，以及关闭来自 Envoy 本地还是上游远端。总数与 local/remote 拆分不能直接相加；这些指标按连接事件计数，不是受影响请求数 | 核心 |
| 4. 上游连接可用性与协议异常 | `envoy_cluster_upstream_cx_none_healthy`、`envoy_cluster_upstream_cx_protocol_error`；辅以 `envoy_cluster_membership_healthy`、`envoy_cluster_upstream_cx_overflow`、`envoy_cluster_upstream_cx_pool_overflow` | `none_healthy` 增长且健康 Endpoint 为零，指向无健康后端；健康 Endpoint 存在但建连失败时检查 Pod、端口和网络。协议错误结合 Envoy 日志检查，Overflow 联查第 4 类熔断状态，无需重复制作熔断图 | 核心 |
| 5. 连接生命周期与复用异常 | `envoy_cluster_upstream_cx_length_ms_{bucket,count,sum}`、`envoy_cluster_upstream_cx_idle_timeout`、`envoy_cluster_upstream_cx_max_duration_reached`、`envoy_cluster_upstream_cx_max_requests`、`envoy_cluster_upstream_cx_close_notify`、`envoy_cluster_upstream_cx_destroy` | Histogram 分析连接持续时间，Counter 分析空闲、最大存活时间、最大请求数和正常关闭事件，用于解释短连接和频繁重建。正常关闭和生命周期回收不必然是故障，需结合建连速率、Pending 和请求异常判断 | 按需 |
| 6. 上游连接协议分布 | `envoy_cluster_upstream_cx_http1_total`、`envoy_cluster_upstream_cx_http2_total`、`envoy_cluster_upstream_cx_http3_total`、`envoy_cluster_upstream_cx_connect_with_0_rtt` | Counter 使用 `rate()` 或 `increase()` 观察新建连接的协议分布，不将累计值当作当前连接数。协议长期固定时价值较低；HTTP/2 重点理解多路复用，HTTP/3 和 0-RTT 仅在启用时关注 | 按需 |

第 6 类统一展示与聚合规则：

- `cx_active` 等 Gauge 直接展示当前值或窗口峰值；连接建立、失败、销毁和超时等 Counter 使用 `rate()` 或 `increase()`。
- 展示全部 Envoy Pod 的实际总连接数时可以对 `cx_active` 求和；Counter 先按副本分别计算增量或速率再求和，排障时保留 `pod` 标签。
- 平均建连耗时应使用 `sum(rate(connect_ms_sum[5m])) / sum(rate(connect_ms_count[5m]))`，不能平均各 Pod 的平均值；分位数先按 `le` 聚合 Bucket 再使用 `histogram_quantile()`。
- 建连失败或无健康后端应与 Pending、连接溢出和请求超时联查；活跃请求期间断连应与请求重置、取消、超时及 SSE 中断联查。
- `cx_destroy`、`idle_timeout`、`close_notify` 等增长可能只是正常连接回收，不能单独标记为请求故障。

### 第 7 类：上游数据传输与流控（4 张数据图）

第 7 类的 8 个指标天然形成 4 组，分别回答“传输了多少、当前积压多少、响应方向是否触发流控、请求方向是否触发背压”。TX 表示 Envoy 向上游 Endpoint 发送请求数据，RX 表示 Envoy 从上游接收响应数据。

| 数据图 | 主要指标 | 含义和分析思路 |
| ------ | -------- | -------------- |
| 1. 上游数据吞吐量（RX / TX） | `envoy_cluster_upstream_cx_rx_bytes_total`、`envoy_cluster_upstream_cx_tx_bytes_total` | Counter 使用 `rate()` 转换为 Byte/s，跨 Envoy Pod 求和可表示 Cluster 总吞吐量。吞吐升高可能只是 RPS、请求体或响应长度增加，不能直接判定拥塞；字节量和 Byte/s 不等于 Token 数和 Token/s |
| 2. 上游缓冲区占用（RX / TX Buffer） | `envoy_cluster_upstream_cx_rx_bytes_buffered`、`envoy_cluster_upstream_cx_tx_bytes_buffered` | Gauge 直接展示瞬时 Bytes，不使用 `rate()` 或 `increase()`。重点观察持续升高和长期不回落；RX 积压可能表示下游消费或转发不及时，TX 积压可能表示向上游写入请求数据受阻 |
| 3. 响应方向流控（Pause / Resume） | `envoy_cluster_upstream_flow_control_paused_reading_total`、`envoy_cluster_upstream_flow_control_resumed_reading_total` | Counter 使用 `increase()` 观察暂停和恢复读取上游响应的事件；`increase(...[5m]) / 5` 表示最近 5 分钟平均 events/min。重点分析 SSE 下游消费受阻导致的背压，不能用暂停减恢复推导当前暂停连接数 |
| 4. 请求方向背压（Backed up / Drained） | `envoy_cluster_upstream_flow_control_backed_up_total`、`envoy_cluster_upstream_flow_control_drained_total` | Counter 使用 `increase()` 观察向上游写入受阻及恢复事件，适合大 Prompt、多模态请求、上游接收缓慢或网络写入受限分析。普通小型文本请求中长期为零不一定异常，优先级低于响应方向流控 |

第 7 类统一展示与联合分析规则：

- RX 吞吐高、RX Buffer 低且 Pause 很少，通常只说明响应传输活跃；RX Buffer 持续升高且 Pause 频繁时，重点排查下游消费或 Envoy 向下游转发瓶颈，不直接归因于 vLLM 推理变慢。
- TX Buffer 持续升高且 Backed Up 频繁时，重点检查请求体大小、上游接收能力及 Envoy 到上游的网络写入。
- 流控事件与 `upstream_rq_timeout`、`upstream_rq_rx_reset`、`upstream_rq_tx_reset` 或 `upstream_cx_destroy_with_active_rq` 同时增加，只能说明时间关联，仍需结合 Access Log 和客户端行为确认实际影响。
- Buffer 总览可以跨 Envoy Pod 求和，排查单副本热点时保留 `pod` 或查看最大值；流控 Counter 分别计算各 Pod 增量后再按需要求和。
- 默认查看一个具体 `envoy_cluster_name`，避免所有 HTTPRoute 和 Envoy Pod 的曲线混在一起；变量名建议使用 `$upstream_cluster`，避免与 VictoriaMetrics 自身的 `cluster` 标签混淆。

### 第 8 类：上游请求处理（7 张核心数据图 + 1 张按需诊断图）

第 8 类是请求级监控的核心类别，建议按照“**上游请求速率 → 活跃并发 → 连接池等待 → 超时 / Reset → Retry → 最终业务结果**”的生命周期组织图表，不要把 22 个指标简单堆叠在少数几张图中。推荐落地为 **7 张核心数据图和 1 张按需诊断图**；其中连接池等待图应分为“当前等待数量”和“进入等待速率”两个视图，如果平台不支持这种布局，就拆成两张独立面板。

| 数据图 | 主要指标 | 图形与单位 | 含义和分析思路 | 建议 |
| ------ | -------- | ---------- | -------------- | ---- |
| 1. 上游请求速率 | `envoy_cluster_upstream_rq_total`、`envoy_cluster_upstream_rq_completed` | Counter 使用 `rate()`，单位 req/s，两条独立折线 | 比较上游请求尝试和完成速率。`total` 可能包含重试，不严格等于客户端 RPS；`completed` 只表示完成，可能包含非 2xx，不能用 `completed / total` 计算业务成功率，也不能用累计的 `total - completed` 推导当前并发 | 核心 |
| 2. 当前上游请求并发 | `envoy_cluster_upstream_rq_active` | Gauge 直接展示，单位 requests | 观察 Envoy 侧当前在途上游请求；总览可跨 Envoy Pod 求和，定位热点时保留 `pod`。请求可能仍在 vLLM Waiting、Prefill、Decode 或 SSE 输出阶段，因此不等于 vLLM `num_requests_running` | 核心 |
| 3. 连接池等待 | `envoy_cluster_upstream_rq_pending_active`、`envoy_cluster_upstream_rq_pending_total` | 分上下两个视图：Gauge 当前值单位 requests；Counter 使用 `rate()`，单位 req/s | 分别观察当前等待连接池资源的请求数和进入等待流程的频率，不强行共用 Y 轴。`pending_total` 的累计值不是当前队列长度，Envoy Pending 也不等于 vLLM Scheduler Waiting | 核心 |
| 4. Pending 异常事件 | `envoy_cluster_upstream_rq_pending_overflow`、`envoy_cluster_upstream_rq_pending_failure_eject`、`envoy_cluster_upstream_rq_cancelled` | Counter 使用 `increase()`，单位次/窗口，独立折线不堆叠 | 分别观察容量拒绝、等待连接失败和获取连接前取消。`pending_overflow` 联查第 4 类 `rq_open`、`rq_pending_open`；`pending_failure_eject` 联查第 6 类建连失败和无健康后端；`rq_cancelled` 不覆盖所有客户端取消 | 核心 |
| 5. 超时与请求终止 | `envoy_cluster_upstream_rq_timeout`、`envoy_cluster_upstream_rq_per_try_timeout`、`envoy_cluster_upstream_rq_per_try_idle_timeout`、`envoy_cluster_upstream_rq_max_duration_reached` | Counter 使用 `increase()`，单位次/窗口 | 区分整体请求超时、单次尝试超时、单次尝试空闲超时和最大请求时长。单次尝试超时后仍可能通过重试成功，不能直接视为最终失败；`per_try_idle_timeout` 的精确语义按部署版本确认；请求超时不同于第 6 类的建连超时 | 核心 |
| 6. 上游请求重置方向 | `envoy_cluster_upstream_rq_rx_reset`、`envoy_cluster_upstream_rq_tx_reset` | Counter 使用 `increase()`，单位次/窗口 | 区分收到上游远端重置和 Envoy 本地发起重置。`rx_reset` 联查上游远端断连和网络，`tx_reset` 联查 Envoy 超时、取消或主动终止；Reset 只说明方向，不能直接归责某一方存在程序问题 | 核心 |
| 7. 重试与重试受限 | `envoy_cluster_upstream_rq_retry`、`envoy_cluster_upstream_rq_retry_success`、`envoy_cluster_upstream_rq_retry_limit_exceeded`、`envoy_cluster_upstream_rq_retry_overflow` | Counter 使用 `increase()`，单位次/窗口，独立折线不堆叠 | 观察重试负载、重试后成功及单请求重试上限、Retry Budget 或重试熔断限制。一次客户端请求可能重试多次，不能直接用 `retry_success / retry` 作为按客户端请求计算的重试成功率；重试增加时联查 vLLM 请求量和 GPU 负载，防止放大重复推理工作 | 核心 |
| 8. 特殊请求与重试退避 | `envoy_cluster_upstream_rq_maintenance_mode`、`envoy_cluster_upstream_rq_retry_backoff_exponential`、`envoy_cluster_upstream_rq_retry_backoff_ratelimited`、`envoy_cluster_upstream_rq_0rtt` | 按事件类型选择 `increase()`；`rq_0rtt` 先核实类型和语义 | 分别用于维护模式本地拒绝、指数或限流退避以及 0-RTT 专项排障，不占默认核心布局 | 按需 |

第 8 类统一展示与聚合规则：

- 所有查询通过 `envoy_cluster_name=~"$upstream_cluster"` 限定到一个具体 HTTPRoute Upstream Cluster，并用 `pod=~"$pod"` 支持筛选 Envoy 实例；默认不要把所有 HTTPRoute 和 Pod 的曲线混在一起。
- `rq_total`、`rq_completed`、`pending_total` 等负载类 Counter 使用 `rate()`；超时、重置、Pending 异常和重试等稀疏事件使用 `increase([5m])` 展示最近 5 分钟事件数。`increase()` 因窗口外推出现小数属于正常现象。
- `rq_active`、`pending_active` 是 Gauge，直接展示瞬时值，不使用 `rate()` 或 `increase()`。跨 Envoy Pod 汇总 Counter 时先分别计算速率或增量再求和；总览实际并发可对 Gauge 求和，排障时保留 `pod` 或查看单副本峰值。
- 所有面板采用独立折线，不堆叠。超时、Reset、Pending 异常和 Retry 等 Counter 可能记录同一次故障中的不同事件，不能直接相加为唯一失败请求数，也不要把没有数据直接解释为真实零值。
- 当前 133 项清单没有上游请求延迟 Histogram 和按 2xx/4xx/5xx 细分的请求指标，不能仅靠第 8 类还原完整延迟和业务成功率；最终结果应结合 Envoy Access Log、HTTP 状态、响应标志、AIBrix 与 vLLM 指标判断。

典型联查路径：

- `rq_active` 升高、`pending_active` 接近零且 vLLM Waiting 升高：更倾向于模型 Scheduler 内部排队，而不是 Envoy 连接池拥塞。
- `pending_overflow` 增加并联查第 4 类 `rq_open` 或 `rq_pending_open`：检查并发请求或 Pending Queue 限额是否导致容量拒绝。
- `rq_rx_reset` 与第 6 类 `cx_destroy_remote_with_active_rq` 同时增加：优先检查上游远端或网络中断。
- `rq_tx_reset` 与 `rq_timeout` 同时增加：优先检查 Envoy 超时、取消或主动终止。
- `rq_retry` 与 `retry_overflow` 同时增加：检查 Retry Policy、Circuit Breaker 和 Retry Budget，并评估对 vLLM 和 GPU 的重复负载。
