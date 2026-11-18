# Envoy Gateway HTTPRoute Upstream Cluster 指标分类汇总

> 来源：`envoy-aibrix-system-aibrix-eg` 在黄区 VictoriaMetrics 中实测存在 `envoy_cluster_name=~"httproute/.*"` 标签值的指标清单。  
> 范围：**133 个指标名，9 类**。保持原始名称，分类不引入清单之外的指标。  
> 说明：`envoy_cluster_name` 标识 Envoy 内部 Upstream Cluster；当值形如 `httproute/<namespace>/<HTTPRoute>/rule/<index>` 时，可以关联到生成该 Cluster 统计名称的 HTTPRoute 规则。它不代表 HTTPRoute 自身在执行数据面转发。

## 一、分类总览

| 类别 | 指标数量 | 主要作用 |
|---|---:|---|
| 1. Cluster 配置与服务发现 | 19 | 配置更新、后端发现与状态同步 |
| 2. Cluster 成员与健康状态 | 5 | Endpoint 数量及健康情况 |
| 3. 负载均衡（LB） | 16 | Subset、Zone-aware 与健康回退 |
| 4. 熔断与并发限制 | 10 | 上游连接、连接池、请求、待处理请求与重试限制 |
| 5. 异常实例检测（Outlier Detection） | 20 | 异常检测与后端剔除 |
| 6. 上游连接管理 | 29 | 建连、活跃连接、销毁、超时与协议问题 |
| 7. 上游数据传输与流控 | 8 | 收发字节、缓冲区与背压 |
| 8. 上游请求处理 | 22 | 请求量、并发、等待、超时、取消与重试 |
| 9. 特殊行为与内部重定向 | 4 | 影子请求、HTTP/3 与内部重定向 |
| **合计** | **133** | **每个指标归入唯一类别** |

## 二、逐类指标清单

### 1. Cluster 配置与服务发现（19）

关注 Cluster 的配置加载、Endpoint Assignment 更新和服务发现。用于分析新建或变更 HTTPRoute 后，后端信息是否成功同步到 Envoy。

```text
envoy_cluster_assignment_stale
envoy_cluster_assignment_timeout_received
envoy_cluster_assignment_use_cached
envoy_cluster_bind_errors
envoy_cluster_default_total_match_count
envoy_cluster_init_fetch_timeout
envoy_cluster_original_dst_host_invalid
envoy_cluster_update_attempt
envoy_cluster_update_duration_bucket
envoy_cluster_update_duration_count
envoy_cluster_update_duration_sum
envoy_cluster_update_empty
envoy_cluster_update_failure
envoy_cluster_update_no_rebuild
envoy_cluster_update_rejected
envoy_cluster_update_success
envoy_cluster_update_time
envoy_cluster_version
envoy_cluster_warming_state
```

**重点观察：** `envoy_cluster_update_failure`、`envoy_cluster_update_rejected`、`envoy_cluster_update_success`、`envoy_cluster_assignment_stale`、`envoy_cluster_warming_state`。

### 2. Cluster 成员与健康状态（5）

关注 Envoy 识别到的后端 Endpoint 数量及健康状态。Envoy 的健康判定不完全等同于 Kubernetes Pod Ready。

```text
envoy_cluster_membership_change
envoy_cluster_membership_degraded
envoy_cluster_membership_excluded
envoy_cluster_membership_healthy
envoy_cluster_membership_total
```

| 指标后缀 | 含义 |
|---|---|
| `membership_total` | 当前 Cluster 的 Endpoint 总数 |
| `membership_healthy` | 处于健康状态的 Endpoint 数量 |
| `membership_degraded` | 处于降级健康状态的 Endpoint 数量 |
| `membership_excluded` | 被排除在负载均衡候选范围之外的 Endpoint 数量 |
| `membership_change` | Endpoint 成员变更事件累计量 |

### 3. 负载均衡（Load Balancing）（16）

关注 Cluster 内部如何选择 Endpoint，包括健康异常回退、Subset LB 和 Zone-aware LB。**这不是 AiBrix 自身的 KV Cache 感知路由指标。**

```text
envoy_cluster_lb_healthy_panic
envoy_cluster_lb_local_cluster_not_ok
envoy_cluster_lb_recalculate_zone_structures
envoy_cluster_lb_subsets_active
envoy_cluster_lb_subsets_created
envoy_cluster_lb_subsets_fallback
envoy_cluster_lb_subsets_fallback_panic
envoy_cluster_lb_subsets_removed
envoy_cluster_lb_subsets_selected
envoy_cluster_lb_zone_cluster_too_small
envoy_cluster_lb_zone_no_capacity_left
envoy_cluster_lb_zone_number_differs
envoy_cluster_lb_zone_routing_all_directly
envoy_cluster_lb_zone_routing_cross_zone
envoy_cluster_lb_zone_routing_sampled
envoy_cluster_max_host_weight
```

**子类：** `lb_healthy_*` / `lb_local_*` 为健康与回退相关，`lb_subsets_*` 为子集负载均衡，`lb_zone_*` 为区域路由，`max_host_weight` 为后端权重统计。

### 4. 熔断与并发限制（Circuit Breakers）（10）

关注 Cluster 在 DEFAULT / HIGH 两种优先级下各类资源是否触及熔断阈值。`*_open` 属于状态指标，通常 0 表示未触及限制、1 表示触及限制；**不等于发生的熔断次数**。

```text
envoy_cluster_circuit_breakers_default_cx_open
envoy_cluster_circuit_breakers_default_cx_pool_open
envoy_cluster_circuit_breakers_default_rq_open
envoy_cluster_circuit_breakers_default_rq_pending_open
envoy_cluster_circuit_breakers_default_rq_retry_open
envoy_cluster_circuit_breakers_high_cx_open
envoy_cluster_circuit_breakers_high_cx_pool_open
envoy_cluster_circuit_breakers_high_rq_open
envoy_cluster_circuit_breakers_high_rq_pending_open
envoy_cluster_circuit_breakers_high_rq_retry_open
```

| 后缀 | 限制对象 |
|---|---|
| `cx_open` | 上游连接数 |
| `cx_pool_open` | 上游连接池数量（并非连接总数） |
| `rq_open` | 并发上游请求数 |
| `rq_pending_open` | 等待连接容量的 Pending Request |
| `rq_retry_open` | 并发重试数 |

### 5. 异常实例检测（Outlier Detection）（20）

用于分析 Envoy 是否检测出持续错误的 Endpoint、是否实际剔除，以及当前剔除数量。

```text
envoy_cluster_outlier_detection_ejections_active
envoy_cluster_outlier_detection_ejections_consecutive_5xx
envoy_cluster_outlier_detection_ejections_detected_consecutive_5xx
envoy_cluster_outlier_detection_ejections_detected_consecutive_gateway_failure
envoy_cluster_outlier_detection_ejections_detected_consecutive_local_origin_failure
envoy_cluster_outlier_detection_ejections_detected_failure_percentage
envoy_cluster_outlier_detection_ejections_detected_local_origin_failure_percentage
envoy_cluster_outlier_detection_ejections_detected_local_origin_success_rate
envoy_cluster_outlier_detection_ejections_detected_success_rate
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx
envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure
envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
envoy_cluster_outlier_detection_ejections_enforced_local_origin_failure_percentage
envoy_cluster_outlier_detection_ejections_enforced_local_origin_success_rate
envoy_cluster_outlier_detection_ejections_enforced_success_rate
envoy_cluster_outlier_detection_ejections_enforced_total
envoy_cluster_outlier_detection_ejections_overflow
envoy_cluster_outlier_detection_ejections_success_rate
envoy_cluster_outlier_detection_ejections_total
```

- `detected_*`：满足某类异常检测条件；不保证已经实际剔除。
- `enforced_*`：实际执行了相应异常剔除动作。
- `ejections_active`：当前处于剔除状态的 Endpoint 数量。

### 6. 上游连接管理（Upstream Connection）（29）

关注 Envoy 与 HTTPRoute 后端 Endpoint 之间的连接创建、活跃度、持续时长、关闭和网络错误。

```text
envoy_cluster_upstream_cx_active
envoy_cluster_upstream_cx_close_notify
envoy_cluster_upstream_cx_connect_attempts_exceeded
envoy_cluster_upstream_cx_connect_fail
envoy_cluster_upstream_cx_connect_ms_bucket
envoy_cluster_upstream_cx_connect_ms_count
envoy_cluster_upstream_cx_connect_ms_sum
envoy_cluster_upstream_cx_connect_timeout
envoy_cluster_upstream_cx_connect_with_0_rtt
envoy_cluster_upstream_cx_destroy
envoy_cluster_upstream_cx_destroy_local
envoy_cluster_upstream_cx_destroy_local_with_active_rq
envoy_cluster_upstream_cx_destroy_remote
envoy_cluster_upstream_cx_destroy_remote_with_active_rq
envoy_cluster_upstream_cx_destroy_with_active_rq
envoy_cluster_upstream_cx_http1_total
envoy_cluster_upstream_cx_http2_total
envoy_cluster_upstream_cx_http3_total
envoy_cluster_upstream_cx_idle_timeout
envoy_cluster_upstream_cx_length_ms_bucket
envoy_cluster_upstream_cx_length_ms_count
envoy_cluster_upstream_cx_length_ms_sum
envoy_cluster_upstream_cx_max_duration_reached
envoy_cluster_upstream_cx_max_requests
envoy_cluster_upstream_cx_none_healthy
envoy_cluster_upstream_cx_overflow
envoy_cluster_upstream_cx_pool_overflow
envoy_cluster_upstream_cx_protocol_error
envoy_cluster_upstream_cx_total
```

| 子类 | 代表指标 |
|---|---|
| 连接数量 | `upstream_cx_active`、`upstream_cx_total` |
| 建连失败与超时 | `upstream_cx_connect_fail`、`upstream_cx_connect_timeout` |
| 建连耗时 | `upstream_cx_connect_ms_{bucket,count,sum}` |
| 销毁及中断 | `upstream_cx_destroy_*` |
| 连接生命周期 | `upstream_cx_length_ms_*`、`upstream_cx_idle_timeout` |
| 协议与异常 | `upstream_cx_http{1,2,3}_total`、`upstream_cx_protocol_error` |
| 资源溢出 | `upstream_cx_overflow`、`upstream_cx_pool_overflow` |

**流式推理特别关注：** `envoy_cluster_upstream_cx_destroy_with_active_rq`，表示销毁连接时仍有活跃请求；需要结合请求超时、取消和重置指标判断是否影响 SSE 响应。

### 7. 上游数据传输与流控（8）

从 Envoy 的视角，`rx` 表示从上游接收，`tx` 表示向上游发送。用于分析网络传输、缓冲积压和背压，不直接代表 Token 数。

```text
envoy_cluster_upstream_cx_rx_bytes_buffered
envoy_cluster_upstream_cx_rx_bytes_total
envoy_cluster_upstream_cx_tx_bytes_buffered
envoy_cluster_upstream_cx_tx_bytes_total
envoy_cluster_upstream_flow_control_backed_up_total
envoy_cluster_upstream_flow_control_drained_total
envoy_cluster_upstream_flow_control_paused_reading_total
envoy_cluster_upstream_flow_control_resumed_reading_total
```

| 指标 | 含义 |
|---|---|
| `upstream_cx_rx_bytes_total` | Envoy 从上游接收的累计字节数 |
| `upstream_cx_tx_bytes_total` | Envoy 向上游发送的累计字节数 |
| `upstream_cx_rx_bytes_buffered` | 当前上游接收缓冲区占用 |
| `upstream_cx_tx_bytes_buffered` | 当前上游发送缓冲区占用 |
| `upstream_flow_control_*` | 上游读写流控、背压及恢复事件 |

### 8. 上游请求处理（Upstream Request）（22）

与在线推理请求链路直接相关：请求量、活跃数、连接池侧等待、超时、取消、重试和重置。

```text
envoy_cluster_upstream_rq_0rtt
envoy_cluster_upstream_rq_active
envoy_cluster_upstream_rq_cancelled
envoy_cluster_upstream_rq_completed
envoy_cluster_upstream_rq_maintenance_mode
envoy_cluster_upstream_rq_max_duration_reached
envoy_cluster_upstream_rq_pending_active
envoy_cluster_upstream_rq_pending_failure_eject
envoy_cluster_upstream_rq_pending_overflow
envoy_cluster_upstream_rq_pending_total
envoy_cluster_upstream_rq_per_try_idle_timeout
envoy_cluster_upstream_rq_per_try_timeout
envoy_cluster_upstream_rq_retry
envoy_cluster_upstream_rq_retry_backoff_exponential
envoy_cluster_upstream_rq_retry_backoff_ratelimited
envoy_cluster_upstream_rq_retry_limit_exceeded
envoy_cluster_upstream_rq_retry_overflow
envoy_cluster_upstream_rq_retry_success
envoy_cluster_upstream_rq_rx_reset
envoy_cluster_upstream_rq_timeout
envoy_cluster_upstream_rq_total
envoy_cluster_upstream_rq_tx_reset
```

| 子类 | 代表指标 |
|---|---|
| 请求总量/完成 | `upstream_rq_total`、`upstream_rq_completed` |
| 当前并发 | `upstream_rq_active` |
| 连接池侧等待 | `upstream_rq_pending_active`、`upstream_rq_pending_overflow` |
| 取消、超时与重置 | `upstream_rq_cancelled`、`upstream_rq_timeout`、`upstream_rq_rx_reset`、`upstream_rq_tx_reset` |
| 重试 | `upstream_rq_retry`、`upstream_rq_retry_success`、`upstream_rq_retry_overflow` |

**两个边界：**

1. `upstream_rq_pending_active` 是 Envoy 连接池侧的等待，**不等于 vLLM Scheduler Waiting Queue**。
2. `upstream_rq_total` 是上游请求统计，遇到重试等行为时，可能不同于客户端请求数。

### 9. 特殊行为与内部重定向（4）

```text
envoy_cluster_retry_or_shadow_abandoned
envoy_cluster_upstream_http3_broken
envoy_cluster_upstream_internal_redirect_failed_total
envoy_cluster_upstream_internal_redirect_succeeded_total
```

- `retry_or_shadow_abandoned`：重试或影子请求被放弃的事件。
- `upstream_http3_broken`：上游 HTTP/3 不可用相关事件。
- `upstream_internal_redirect_{failed,succeeded}_total`：内部重定向失败/成功次数；**并非 HTTPRoute 的 URLRewrite**。

## 三、AiBrix 在线服务重点监控指标（从上述 133 个中选取）

| 指标 | 关注的问题 |
|---|---|
| `envoy_cluster_membership_healthy` | 当前可用的后端 Endpoint 数量 |
| `envoy_cluster_upstream_rq_total` | 上游请求速率 |
| `envoy_cluster_upstream_rq_active` | 当前上游请求并发 |
| `envoy_cluster_upstream_rq_pending_active` | Envoy 连接池等待压力 |
| `envoy_cluster_upstream_rq_timeout` | 上游请求超时 |
| `envoy_cluster_upstream_rq_retry` | 上游请求重试 |
| `envoy_cluster_upstream_cx_connect_fail` | 后端连接失败 |
| `envoy_cluster_upstream_cx_destroy_with_active_rq` | 连接销毁时请求仍活跃 |
| `envoy_cluster_upstream_cx_rx_bytes_total` | 上游响应传输量 |
| `envoy_cluster_outlier_detection_ejections_active` | 当前异常剔除的 Endpoint 数量 |

### 使用边界

- 这 **133 个**指标是给定的 HTTPRoute 关联 Upstream Cluster 指标清单，**不是 Envoy Gateway 的所有指标**。
- 此清单未包含 HTTP 状态码维度（如上游 5xx）和上游请求延迟 Histogram 等指标，不能单靠它们还原请求成功率或 TTFT、TPOT、E2E 延迟。
- 具体指标是否为 Counter、Gauge 或 Histogram，应结合 Envoy 版本的指标定义确认；其中 `_bucket/_count/_sum` 为 Histogram 序列。
- 请求链路分析应结合 AiBrix Gateway 与 vLLM 指标交叉验证；不要把 Envoy 上游连接池排队误认为 vLLM 内部推理排队。

## 四、数量检查

19 + 5 + 16 + 10 + 20 + 29 + 8 + 22 + 4 = **133**。
