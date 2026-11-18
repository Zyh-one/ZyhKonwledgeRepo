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
