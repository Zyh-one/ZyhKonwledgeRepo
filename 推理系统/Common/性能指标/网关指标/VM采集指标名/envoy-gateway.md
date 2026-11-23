# `envoy-gateway` 指标名清单

共 **82** 个指标名。以下名称按字典序排列，仅列指标名，不含数据序列、样本值、标签组合或 PromQL。

```text
certwatcher_read_certificate_errors_total
certwatcher_read_certificate_total
controller_runtime_active_workers
controller_runtime_max_concurrent_reconciles
controller_runtime_reconcile_errors_total
controller_runtime_reconcile_panics_total
controller_runtime_reconcile_time_seconds_bucket
controller_runtime_reconcile_time_seconds_count
controller_runtime_reconcile_time_seconds_sum
controller_runtime_reconcile_total
controller_runtime_terminal_reconcile_errors_total
controller_runtime_webhook_panics_total
count:up1
go_gc_duration_seconds
go_gc_duration_seconds_count
go_gc_duration_seconds_sum
go_gc_gogc_percent
go_gc_gomemlimit_bytes
go_goroutines
go_info
go_memstats_alloc_bytes
go_memstats_alloc_bytes_total
go_memstats_buck_hash_sys_bytes
go_memstats_frees_total
go_memstats_gc_sys_bytes
go_memstats_heap_alloc_bytes
go_memstats_heap_idle_bytes
go_memstats_heap_inuse_bytes
go_memstats_heap_objects
go_memstats_heap_released_bytes
go_memstats_heap_sys_bytes
go_memstats_last_gc_time_seconds
go_memstats_mallocs_total
go_memstats_mcache_inuse_bytes
go_memstats_mcache_sys_bytes
go_memstats_mspan_inuse_bytes
go_memstats_mspan_sys_bytes
go_memstats_next_gc_bytes
go_memstats_other_sys_bytes
go_memstats_stack_inuse_bytes
go_memstats_stack_sys_bytes
go_memstats_sys_bytes
go_sched_gomaxprocs_threads
go_threads
leader_election_master_status
process_cpu_seconds_total
process_max_fds
process_network_receive_bytes_total
process_network_transmit_bytes_total
process_open_fds
process_resident_memory_bytes
process_start_time_seconds
process_virtual_memory_bytes
process_virtual_memory_max_bytes
resource_apply_duration_seconds_bucket
resource_apply_duration_seconds_count
resource_apply_duration_seconds_sum
resource_apply_total
resource_delete_duration_seconds_bucket
resource_delete_duration_seconds_count
resource_delete_duration_seconds_sum
resource_delete_total
rest_client_requests_total
scrape_duration_seconds
scrape_response_size_bytes
scrape_samples_post_metric_relabeling
scrape_samples_scraped
scrape_series_added
scrape_timeout_seconds
status_update_duration_seconds_bucket
status_update_duration_seconds_count
status_update_duration_seconds_sum
status_update_total
up
wasm_cache_entries
watchable_depth
watchable_subscribe_duration_seconds_bucket
watchable_subscribe_duration_seconds_count
watchable_subscribe_duration_seconds_sum
watchable_subscribe_total
xds_snapshot_create_total
xds_snapshot_update_total
```

## 第 7 类上游数据传输与流控：4 张数据图的含义和分析思路

> 本节说明的是 `envoy-aibrix-system-aibrix-eg` 中 HTTPRoute Upstream Cluster 的第 7 类指标，不属于上方 `envoy-gateway` job 的 82 个控制面指标。所有查询应通过 `envoy_cluster_name=~"httproute/<业务namespace>/<HTTPRoute名称>/rule/[0-9]+"` 限定到目标 HTTPRoute 对应的 Upstream Cluster。

方向以 Envoy 的上游连接为参照：TX 表示 Envoy 向 vLLM 等上游 Endpoint 发送请求数据，RX 表示 Envoy 从上游接收响应数据。4 张图分别回答“传输了多少、当前积压多少、响应方向是否触发流控、请求方向是否触发背压”。

### 图 1：上游数据吞吐量（RX / TX）

- `envoy_cluster_upstream_cx_rx_bytes_total`：从上游累计接收的响应字节数。
- `envoy_cluster_upstream_cx_tx_bytes_total`：向上游累计发送的请求字节数。

两者都是 Counter，使用 `rate()` 转换为 Byte/s；展示整个 Cluster 的总吞吐量时，可以分别计算各 Envoy Pod 的速率后再求和。RX 用于观察 SSE 等响应方向的传输量，TX 用于观察 Prompt、Request Body 等请求方向的传输量。

吞吐量升高可能只是 RPS、请求体大小或响应长度增加，不能直接判定网络拥塞。字节量不等于 Token 数，Byte/s 也不等于 Input/Output Token/s，不能据此计算 TTFT、TPOT 或模型解码速度。

### 图 2：上游缓冲区占用（RX / TX Buffer）

- `envoy_cluster_upstream_cx_rx_bytes_buffered`：从上游接收后，当前仍在 Envoy 读取缓冲中的字节数。
- `envoy_cluster_upstream_cx_tx_bytes_buffered`：准备发往上游，但当前尚未完全发送的字节数。

两者都是 Gauge，直接展示瞬时 Bytes，不使用 `rate()` 或 `increase()`。短暂峰值可能正常，重点观察是否持续升高、长期不回落，以及是否与流控、请求超时或重置同时出现。平台总览可以跨 Envoy Pod 求和；排查单副本热点时应保留 `pod` 或按 Cluster 查看最大值。

RX Buffer 持续升高并不表示 vLLM 不返回数据，反而可能是响应已经到达 Envoy，但后续转发或下游客户端消费不及时。TX Buffer 持续升高则提示向 Endpoint 写入请求数据可能受阻。

### 图 3：响应方向流控（Pause / Resume）

- `envoy_cluster_upstream_flow_control_paused_reading_total`：Envoy 因流控暂停读取上游响应的累计事件数。
- `envoy_cluster_upstream_flow_control_resumed_reading_total`：Envoy 恢复读取上游响应的累计事件数。

两者都是 Counter，使用 `increase()` 观察窗口内事件增量；`increase(...[5m]) / 5` 表示最近 5 分钟平均每分钟事件数，单位为 events/min。删除 `/ 5` 后，含义则是最近 5 分钟累计事件数，不能仍标成每分钟次数。

典型链路是“vLLM 返回响应 → 下游客户端消费或 Envoy 向下游发送受阻 → 背压传播到上游读取 → Envoy 暂停读取”。Pause/Resume 频繁说明流控反复切换，但不必然发生请求故障；不能用暂停次数减恢复次数推导当前暂停连接数。若 RX Buffer 持续升高、Pause 频繁，并伴随活跃请求增加、超时或重置，再进一步检查 Downstream 发送能力、SSE 客户端读取能力和 Access Log。

### 图 4：请求方向背压（Backed up / Drained）

- `envoy_cluster_upstream_flow_control_backed_up_total`：Envoy 向上游写入请求数据受阻，背压向下游传播的累计事件数。
- `envoy_cluster_upstream_flow_control_drained_total`：上游写缓冲排空到恢复条件、解除相应背压的累计事件数。

两者同样使用 `increase()` 展示事件增量，窗口和单位规则与图 3 一致。该图用于分析“客户端请求体到达较快 → Envoy 向上游写入受阻 → TX Buffer 增加 → Envoy 减缓读取下游数据”的过程，适合大 Prompt、多模态大请求体、上游接收缓慢或上游网络写入受限的场景。普通小型文本请求中，这组指标长期为零可能没有异常，因此优先级低于响应方向流控。

### 联合分析原则

- RX 吞吐高、RX Buffer 低且 Pause 很少：通常只说明响应传输活跃，暂未见明显积压。
- RX Buffer 持续升高且 Pause 频繁：重点排查下游消费或 Envoy 向下游转发瓶颈，不直接归因于 vLLM 推理变慢。
- TX Buffer 持续升高且 Backed Up 频繁：重点排查请求体大小、上游接收能力及 Envoy 到上游的网络写入。
- 流控事件与 `upstream_rq_timeout`、`upstream_rq_rx_reset`、`upstream_rq_tx_reset` 或 `upstream_cx_destroy_with_active_rq` 同时增加：说明传输异常与请求异常存在时间关联，但仍需结合请求日志确认，不能只凭相关性推断因果。
- 默认查看一个具体 HTTPRoute Cluster，避免所有路由和 Envoy Pod 的曲线混在一起；变量名建议使用 `$upstream_cluster`，避免与 VictoriaMetrics 自身的 `cluster` 标签混淆。
