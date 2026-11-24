# `aibrix-gateway-plugins` 指标名清单

共 **78** 个指标名，按照 [VM_Metrics_分类与分析.md](VM_Metrics_分类与分析.md) 的分类及类内顺序排列。第二列填写“是”或“否”，表示是否需要将该指标写入平台数据。

| 指标名                                             | 是否写入平台数据 |
| -------------------------------------------------- | ---------------- |
| `engine_sleep_state`                             | 是               |
| `iteration_tokens_total_bucket`                  | 是               |
| `iteration_tokens_total_count`                   |                  |
| `iteration_tokens_total_p50`                     |                  |
| `iteration_tokens_total_p90`                     |                  |
| `iteration_tokens_total_p99`                     |                  |
| `iteration_tokens_total_sum`                     |                  |
| `aibrix_balanced_local_prefix_cache_capacity`    | 是               |
| `aibrix_balanced_local_prefix_cache_entries`     | 是               |
| `aibrix_balanced_local_prefix_cache_usage_ratio` | 是               |
| `aibrix_balanced_pod_scores`                     | 是               |
| `aibrix_balanced_routing_decisions_total`        | 是               |
| `aibrix_balanced_routing_latency_seconds_bucket` | 是               |
| `aibrix_balanced_routing_latency_seconds_count`  |                  |
| `aibrix_balanced_routing_latency_seconds_sum`    |                  |
| `http_request_duration_highr_seconds_bucket`     |                  |
| `http_request_duration_highr_seconds_count`      |                  |
| `http_request_duration_highr_seconds_p50`        |                  |
| `http_request_duration_highr_seconds_p90`        |                  |
| `http_request_duration_highr_seconds_p99`        |                  |
| `http_request_duration_highr_seconds_sum`        |                  |
| `http_request_duration_seconds_bucket`           |                  |
| `http_request_duration_seconds_count`            |                  |
| `http_request_duration_seconds_p50`              |                  |
| `http_request_duration_seconds_p90`              |                  |
| `http_request_duration_seconds_p99`              |                  |
| `http_request_duration_seconds_sum`              |                  |
| `go_gc_duration_seconds`                         | 否               |
| `go_gc_duration_seconds_count`                   | 否               |
| `go_gc_duration_seconds_sum`                     | 否               |
| `go_gc_gogc_percent`                             | 否               |
| `go_gc_gomemlimit_bytes`                         | 否               |
| `go_goroutines`                                  | 否               |
| `go_info`                                        | 否               |
| `go_memstats_alloc_bytes`                        | 否               |
| `go_memstats_alloc_bytes_total`                  | 否               |
| `go_memstats_buck_hash_sys_bytes`                | 否               |
| `go_memstats_frees_total`                        | 否               |
| `go_memstats_gc_sys_bytes`                       | 否               |
| `go_memstats_heap_alloc_bytes`                   | 否               |
| `go_memstats_heap_idle_bytes`                    | 否               |
| `go_memstats_heap_inuse_bytes`                   | 否               |
| `go_memstats_heap_objects`                       | 否               |
| `go_memstats_heap_released_bytes`                | 否               |
| `go_memstats_heap_sys_bytes`                     | 否               |
| `go_memstats_last_gc_time_seconds`               | 否               |
| `go_memstats_mallocs_total`                      | 否               |
| `go_memstats_mcache_inuse_bytes`                 | 否               |
| `go_memstats_mcache_sys_bytes`                   | 否               |
| `go_memstats_mspan_inuse_bytes`                  | 否               |
| `go_memstats_mspan_sys_bytes`                    | 否               |
| `go_memstats_next_gc_bytes`                      | 否               |
| `go_memstats_other_sys_bytes`                    | 否               |
| `go_memstats_stack_inuse_bytes`                  | 否               |
| `go_memstats_stack_sys_bytes`                    | 否               |
| `go_memstats_sys_bytes`                          | 否               |
| `go_sched_gomaxprocs_threads`                    | 否               |
| `go_threads`                                     | 否               |
| `process_cpu_seconds_total`                      | 否               |
| `process_max_fds`                                | 否               |
| `process_network_receive_bytes_total`            | 否               |
| `process_network_transmit_bytes_total`           | 否               |
| `process_open_fds`                               | 否               |
| `process_resident_memory_bytes`                  | 否               |
| `process_start_time_seconds`                     | 否               |
| `process_virtual_memory_bytes`                   | 否               |
| `process_virtual_memory_max_bytes`               | 否               |
| `up`                                             | 否               |
| `count:up1`                                      | 否               |
| `llm_engine_metrics_query_fail`                  | 否               |
| `promhttp_metric_handler_requests_in_flight`     | 否               |
| `promhttp_metric_handler_requests_total`         | 否               |
| `scrape_duration_seconds`                        | 否               |
| `scrape_response_size_bytes`                     | 否               |
| `scrape_samples_post_metric_relabeling`          | 否               |
| `scrape_samples_scraped`                         | 否               |
| `scrape_series_added`                            | 否               |
| `scrape_timeout_seconds`                         | 否               |

## 指标名归并说明

这 **78 个原始指标名并不等于 78 种独立业务含义**。该 job 的清单混合了 AIBrix 原生指标、经 gateway 暴露的推理引擎指标、Go/process 运行时指标和采集元数据，不能全部理解为 AIBrix 路由器业务指标。

剩余指标中有 **3 组推理观测指标**：`iteration_tokens_total`、`http_request_duration_highr_seconds` 和 `http_request_duration_seconds`。每组都使用 `_bucket`、`_count`、`_sum`、`_p50`、`_p90`、`_p99` 六个名称描述同一个观测对象，共占 18 个名称。前三个是 Histogram 的组成部分，后三个是额外导出的分位数形式；分析时可归为一个语义指标族，但它们仍是不同的 Prometheus 指标名。

仅按这些明确的后缀归并，不强行合并其他名称相近的指标，结果如下：

| 来源分类 | 原始指标名数 | 归并后的名称族/观测组数 |
| --- | ---: | ---: |
| AIBrix 原生指标 | 8 | 6 |
| 经 gateway 暴露的推理引擎指标 | 19 | 4 |
| Go runtime | 31 | 29 |
| process | 9 | 9 |
| promhttp | 2 | 2 |
| scrape、up、recording rule | 9 | 9 |
| **合计** | **78** | **59** |

这里的 **59** 是按名称结构得到的观测组数量，不是 Prometheus 官方元数据中的 Metric Family 数量。`entries`、`capacity`、`usage_ratio` 等名称虽然属于同一业务分类，但语义各自独立，不应继续强行合并。
