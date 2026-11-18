# `aibrix-gateway-plugins` 指标名清单

共 **168** 个指标名，按照 [VM_Metrics_分类与分析.md](VM_Metrics_分类与分析.md) 的分类及类内顺序排列。第二列填写“是”或“否”，表示是否需要将该指标写入平台数据。

| 指标名                                             | 是否写入平台数据 |
| -------------------------------------------------- | ---------------- |
| `prompt_tokens_total`                            | 否               |
| `generation_tokens_total`                        | 否               |
| `avg_prompt_throughput_toks_per_s`               | 否               |
| `avg_generation_throughput_toks_per_s`           | 否               |
| `request_generation_tokens_bucket`               | 否               |
| `request_generation_tokens_count`                |                  |
| `request_generation_tokens_p50`                  |                  |
| `request_generation_tokens_p90`                  |                  |
| `request_generation_tokens_p99`                  |                  |
| `request_generation_tokens_sum`                  |                  |
| `request_prompt_tokens_bucket`                   | 否               |
| `request_prompt_tokens_count`                    |                  |
| `request_prompt_tokens_p50`                      |                  |
| `request_prompt_tokens_p90`                      |                  |
| `request_prompt_tokens_p99`                      |                  |
| `request_prompt_tokens_sum`                      |                  |
| `e2e_request_latency_seconds_bucket`             | 否               |
| `e2e_request_latency_seconds_count`              |                  |
| `e2e_request_latency_seconds_p50`                |                  |
| `e2e_request_latency_seconds_p90`                |                  |
| `e2e_request_latency_seconds_p99`                |                  |
| `e2e_request_latency_seconds_sum`                |                  |
| `time_per_output_token_seconds_bucket`           | 否               |
| `time_per_output_token_seconds_count`            |                  |
| `time_per_output_token_seconds_p50`              |                  |
| `time_per_output_token_seconds_p90`              |                  |
| `time_per_output_token_seconds_p99`              |                  |
| `time_per_output_token_seconds_sum`              |                  |
| `time_to_first_token_seconds_bucket`             | 否               |
| `time_to_first_token_seconds_count`              |                  |
| `time_to_first_token_seconds_p50`                |                  |
| `time_to_first_token_seconds_p90`                |                  |
| `time_to_first_token_seconds_p99`                |                  |
| `time_to_first_token_seconds_sum`                |                  |
| `request_decode_time_seconds_bucket`             | 否（考虑）       |
| `request_decode_time_seconds_count`              |                  |
| `request_decode_time_seconds_p50`                |                  |
| `request_decode_time_seconds_p90`                |                  |
| `request_decode_time_seconds_p99`                |                  |
| `request_decode_time_seconds_sum`                |                  |
| `request_inference_time_seconds_bucket`          | 否（考虑）       |
| `request_inference_time_seconds_count`           |                  |
| `request_inference_time_seconds_p50`             |                  |
| `request_inference_time_seconds_p90`             |                  |
| `request_inference_time_seconds_p99`             |                  |
| `request_inference_time_seconds_sum`             |                  |
| `request_prefill_time_seconds_bucket`            |                  |
| `request_prefill_time_seconds_count`             | 否（考虑）       |
| `request_prefill_time_seconds_p50`               |                  |
| `request_prefill_time_seconds_p90`               |                  |
| `request_prefill_time_seconds_p99`               |                  |
| `request_prefill_time_seconds_sum`               |                  |
| `request_queue_time_seconds_bucket`              | 否（考虑）       |
| `request_queue_time_seconds_count`               |                  |
| `request_queue_time_seconds_p50`                 |                  |
| `request_queue_time_seconds_p90`                 |                  |
| `request_queue_time_seconds_p99`                 |                  |
| `request_queue_time_seconds_sum`                 |                  |
| `num_requests_running`                           | 是               |
| `num_requests_waiting`                           | 是               |
| `engine_sleep_state`                             | 是               |
| `iteration_tokens_total_bucket`                  | 是               |
| `iteration_tokens_total_count`                   |                  |
| `iteration_tokens_total_p50`                     |                  |
| `iteration_tokens_total_p90`                     |                  |
| `iteration_tokens_total_p99`                     |                  |
| `iteration_tokens_total_sum`                     |                  |
| `gpu_cache_usage_perc`                           |                  |
| `kv_cache_usage_perc`                            |                  |
| `prefix_cache_hits_total`                        |                  |
| `prefix_cache_queries_total`                     |                  |
| `external_prefix_cache_hits_total`               |                  |
| `external_prefix_cache_queries_total`            |                  |
| `aibrix_balanced_local_prefix_cache_capacity`    | 是               |
| `aibrix_balanced_local_prefix_cache_entries`     | 是               |
| `aibrix_balanced_local_prefix_cache_usage_ratio` | 是               |
| `aibrix_balanced_pod_scores`                     | 是               |
| `aibrix_balanced_routing_decisions_total`        | 是               |
| `aibrix_balanced_routing_latency_seconds_bucket` | 是               |
| `aibrix_balanced_routing_latency_seconds_count`  |                  |
| `aibrix_balanced_routing_latency_seconds_sum`    |                  |
| `nixl_bytes_transferred_bucket`                  |                  |
| `nixl_bytes_transferred_count`                   |                  |
| `nixl_bytes_transferred_p50`                     |                  |
| `nixl_bytes_transferred_p90`                     |                  |
| `nixl_bytes_transferred_p99`                     |                  |
| `nixl_bytes_transferred_sum`                     |                  |
| `nixl_num_descriptors_bucket`                    |                  |
| `nixl_num_descriptors_count`                     |                  |
| `nixl_num_descriptors_p50`                       |                  |
| `nixl_num_descriptors_p90`                       |                  |
| `nixl_num_descriptors_p99`                       |                  |
| `nixl_num_descriptors_sum`                       |                  |
| `nixl_post_time_seconds_bucket`                  |                  |
| `nixl_post_time_seconds_count`                   |                  |
| `nixl_post_time_seconds_p50`                     |                  |
| `nixl_post_time_seconds_p90`                     |                  |
| `nixl_post_time_seconds_p99`                     |                  |
| `nixl_post_time_seconds_sum`                     |                  |
| `nixl_xfer_time_seconds_bucket`                  |                  |
| `nixl_xfer_time_seconds_count`                   |                  |
| `nixl_xfer_time_seconds_p50`                     |                  |
| `nixl_xfer_time_seconds_p90`                     |                  |
| `nixl_xfer_time_seconds_p99`                     |                  |
| `nixl_xfer_time_seconds_sum`                     |                  |
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

这 **168 个原始指标名并不等于 168 种独立业务含义**。该 job 的清单混合了 AIBrix 原生指标、经 gateway 暴露的推理引擎指标、Go/process 运行时指标和采集元数据，不能全部理解为 AIBrix 路由器业务指标。

其中有 **16 组推理观测指标**，每组都使用 `_bucket`、`_count`、`_sum`、`_p50`、`_p90`、`_p99` 六个名称描述同一个观测对象，共占 96 个名称。前三个是 Histogram 的组成部分，后三个是额外导出的分位数形式；分析时可归为一个语义指标族，但它们仍是不同的 Prometheus 指标名。

仅按这些明确的后缀归并，不强行合并其他名称相近的指标，结果如下：

| 来源分类                      |  原始指标名数 | 归并后的名称族/观测组数 |
| ----------------------------- | ------------: | ----------------------: |
| AIBrix 原生指标               |             8 |                       6 |
| 经 gateway 暴露的推理引擎指标 |           110 |                      30 |
| Go runtime                    |            31 |                      29 |
| process                       |             9 |                       9 |
| promhttp                      |             2 |                       2 |
| scrape、up、recording rule    |             8 |                       8 |
| **合计**                | **168** |            **84** |

这里的 **84** 是按名称结构得到的观测组数量，不是 Prometheus 官方元数据中的 Metric Family 数量。`entries`、`capacity`、`usage_ratio` 等名称虽然属于同一业务分类，但语义各自独立，不应继续强行合并。
