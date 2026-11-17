# VictoriaMetrics 中 LLM / AiBrix / NiXL 指标分类与分析

> 整理日期：2026-11-17
> 数据范围：严格限定为用户提供的 VM 指标名称列表（去重后 **168** 个唯一指标）。
> 分类规则：每个指标只归入一个类别；`_bucket` / `_count` / `_sum` / `_p50` / `_p90` / `_p99` 等后缀仍按真实名称完整列出。
> 注意：**指标名称不等于已确认的源码定义**。对 `aibrix_balanced_*`、`count:up1`、`llm_engine_metrics_query_fail` 等非标准或定制指标，本文仅给出可能的语义，需依据 `/metrics` 的 `HELP/TYPE`、VM Recording Rule 与对应源码确认。

## 一、核对结果

- 原始列表包含 **168** 行指标名称，去重后 **168** 个，`up` 仅出现一次。
- 以下 10 类中的全部条目都来自原始列表，**无额外补入的指标**；每个唯一名称恰好出现于一个类别。
- 之前讲解中出现的 `request_success_total`、`num_preemptions_total`、`nixl_num_failed_transfers_total`、`nixl_num_kv_expired_reqs`、`inter_token_latency_seconds` 和带 `vllm:` 前缀的原生指标等，**均不属于所提供的 VM 名称列表，本文件不将其作为现有指标**。
- 这一列表包含完整的 `iteration_tokens_total_*` 六名称组合，包括 `_count` 和 `_p50`。

## 二、分类概览

| 类别                            | 唯一指标数 | 主要关注点                   |
| ------------------------------- | ---------: | ---------------------------- |
| 01 请求量、Token 吞吐与请求规模 |         16 | 请求规模与 Token/s           |
| 02 请求体验与端到端延迟         |         18 | TTFT、TPOT、E2E              |
| 03 推理阶段耗时                 |         24 | Queue/Prefill/Decode/Running |
| 04 引擎运行、排队与迭代         |          9 | 负载、排队与迭代规模         |
| 05 KV Cache 与前缀缓存          |          6 | KV 容量与前缀命中            |
| 06 AiBrix Balanced 路由         |          8 | 网关路由评分和决策           |
| 07 NiXL / PD 分离传输           |         24 | KV 传输大小、描述符及耗时    |
| 08 HTTP 请求延迟                |         12 | HTTP 入口延迟                |
| 09 Go Runtime 与进程资源        |         40 | 程序资源与运行时             |
| 10 监控采集与监控端点健康       |         11 | 监控抓取及查询健康           |

## 四、逐类指标说明和原始名称清单

### 01 请求量、Token 吞吐与请求规模（16 个）

- `prompt_tokens_total` / `generation_tokens_total`：累计输入/生成 Token 量；可通过 `rate()` 计算 Token/s。
- `avg_prompt_throughput_toks_per_s` / `avg_generation_throughput_toks_per_s`：Exporter 提供的平均 Token 吞吐率，实际平滑窗口以源码为准。
- `request_prompt_tokens_*` / `request_generation_tokens_*`：按请求观测输入与输出 Token 长度的分布，适合分析长短请求混合程度。
- `*_sum` 与 Token 总计数器未必在所有版本和采样时点上完全相等。

**实际存在的指标名称：**

```text
prompt_tokens_total
generation_tokens_total
avg_prompt_throughput_toks_per_s
avg_generation_throughput_toks_per_s
request_generation_tokens_bucket
request_generation_tokens_count
request_generation_tokens_p50
request_generation_tokens_p90
request_generation_tokens_p99
request_generation_tokens_sum
request_prompt_tokens_bucket
request_prompt_tokens_count
request_prompt_tokens_p50
request_prompt_tokens_p90
request_prompt_tokens_p99
request_prompt_tokens_sum
```

### 02 请求体验与端到端延迟（18 个）

- `time_to_first_token_seconds_*`：TTFT，常用于定位首 Token 交付缓慢。
- `time_per_output_token_seconds_*`：每输出 Token 平均用时的请求分布；不要未经确认就当成逐 Token 间隔 ITL。
- `e2e_request_latency_seconds_*`：请求端到端耗时分布。
- PD 分离的用户可感知 TTFT 可能同时受排队、Prefill、KV 传输、首步 Decode 与网络影响；监控指标可能只覆盖其中一部分。

**实际存在的指标名称：**

```text
e2e_request_latency_seconds_bucket
e2e_request_latency_seconds_count
e2e_request_latency_seconds_p50
e2e_request_latency_seconds_p90
e2e_request_latency_seconds_p99
e2e_request_latency_seconds_sum
time_per_output_token_seconds_bucket
time_per_output_token_seconds_count
time_per_output_token_seconds_p50
time_per_output_token_seconds_p90
time_per_output_token_seconds_p99
time_per_output_token_seconds_sum
time_to_first_token_seconds_bucket
time_to_first_token_seconds_count
time_to_first_token_seconds_p50
time_to_first_token_seconds_p90
time_to_first_token_seconds_p99
time_to_first_token_seconds_sum
```

### 03 推理阶段耗时（24 个）

- `request_queue_time_seconds_*`：请求排队累计耗时。
- `request_prefill_time_seconds_*`：Prefill 阶段累计耗时，可能受到 Chunked Prefill、调度等因素影响。
- `request_decode_time_seconds_*`：Decode 阶段累计耗时，不等于单 Token TPOT。
- `request_inference_time_seconds_*`：推理/运行阶段耗时；准确的计时边界以引擎源码为准。
- 对比阶段延迟时，需确认统计标签、版本、状态定义及请求生命周期。

**实际存在的指标名称：**

```text
request_decode_time_seconds_bucket
request_decode_time_seconds_count
request_decode_time_seconds_p50
request_decode_time_seconds_p90
request_decode_time_seconds_p99
request_decode_time_seconds_sum
request_inference_time_seconds_bucket
request_inference_time_seconds_count
request_inference_time_seconds_p50
request_inference_time_seconds_p90
request_inference_time_seconds_p99
request_inference_time_seconds_sum
request_prefill_time_seconds_bucket
request_prefill_time_seconds_count
request_prefill_time_seconds_p50
request_prefill_time_seconds_p90
request_prefill_time_seconds_p99
request_prefill_time_seconds_sum
request_queue_time_seconds_bucket
request_queue_time_seconds_count
request_queue_time_seconds_p50
request_queue_time_seconds_p90
request_queue_time_seconds_p99
request_queue_time_seconds_sum
```

### 04 引擎运行、排队与迭代（9 个）

- `num_requests_running`：当前 Running 请求数。
- `num_requests_waiting`：当前 Waiting 请求数。
- `engine_sleep_state`：引擎睡眠状态，数值含义需要确认枚举或 HELP。
- `iteration_tokens_total_*`：单次调度/模型执行迭代处理的 Token 数量分布，可包括 Prefill 和 Decode Token；不是纯粹的输出 Token 数。
- 本清单包含 `iteration_tokens_total_count` 和 `iteration_tokens_total_p50`。

**实际存在的指标名称：**

```text
num_requests_running
num_requests_waiting
engine_sleep_state
iteration_tokens_total_bucket
iteration_tokens_total_count
iteration_tokens_total_p50
iteration_tokens_total_p90
iteration_tokens_total_p99
iteration_tokens_total_sum
```

### 05 KV Cache 与前缀缓存（6 个）

- `kv_cache_usage_perc`：KV Cache 占用比例（常见值域为 0～1，须结合实际数据核实）。
- `gpu_cache_usage_perc`：GPU 缓存使用率相关兼容/旧版名称；是否与前者同义需检查来源。
- `prefix_cache_hits_total` / `prefix_cache_queries_total`：内部前缀缓存命中与查询累计值；实际单位可能为 Token、Block 或查询操作，需核对实现。
- `external_prefix_cache_hits_total` / `external_prefix_cache_queries_total`：外部前缀缓存相关累计值；指标本身不说明使用何种外部缓存后端。
- 缓存命中率仅在 hits/queries 单位和标签口径一致时才有意义。

**实际存在的指标名称：**

```text
gpu_cache_usage_perc
kv_cache_usage_perc
prefix_cache_hits_total
prefix_cache_queries_total
external_prefix_cache_hits_total
external_prefix_cache_queries_total
```

### 06 AiBrix Balanced 路由（8 个）

- `aibrix_balanced_local_prefix_cache_capacity`：推测为路由端本地前缀索引容量上限。
- `aibrix_balanced_local_prefix_cache_entries`：推测为当前前缀索引条目数。
- `aibrix_balanced_local_prefix_cache_usage_ratio`：推测为本地前缀索引容量使用比率；不应视为 GPU KV Cache 占用率。
- `aibrix_balanced_pod_scores`：推测为候选 Pod 的路由评分；**不能由名称判定高分还是低分优先**。
- `aibrix_balanced_routing_decisions_total`：推测统计路由决策次数，需根据标签确定目标 Pod、决策结果维度。
- `aibrix_balanced_routing_latency_seconds_*`：路由决策算法耗时分布；未必包含 HTTP 转发或模型执行。
- **上述语义为名称推断，非已核实的官方定义。**

**实际存在的指标名称：**

```text
aibrix_balanced_local_prefix_cache_capacity
aibrix_balanced_local_prefix_cache_entries
aibrix_balanced_local_prefix_cache_usage_ratio
aibrix_balanced_pod_scores
aibrix_balanced_routing_decisions_total
aibrix_balanced_routing_latency_seconds_bucket
aibrix_balanced_routing_latency_seconds_count
aibrix_balanced_routing_latency_seconds_sum
```

### 07 NiXL / PD 分离传输（24 个）

- `nixl_bytes_transferred_*`：每次传输的数据量分布；`_sum` 的速率可估算由此指标记录的字节吞吐。
- `nixl_num_descriptors_*`：一次传输包含的内存描述符数量分布。
- `nixl_post_time_seconds_*`：传输任务提交（Post）阶段耗时分布。
- `nixl_xfer_time_seconds_*`：传输操作耗时分布；是否包含 Post 阶段取决于版本的计时边界，**不可默认与 Post Time 相加**。
- 多 Rank/Pod 汇聚时注意标签去重与重复上报。

**实际存在的指标名称：**

```text
nixl_bytes_transferred_bucket
nixl_bytes_transferred_count
nixl_bytes_transferred_p50
nixl_bytes_transferred_p90
nixl_bytes_transferred_p99
nixl_bytes_transferred_sum
nixl_num_descriptors_bucket
nixl_num_descriptors_count
nixl_num_descriptors_p50
nixl_num_descriptors_p90
nixl_num_descriptors_p99
nixl_num_descriptors_sum
nixl_post_time_seconds_bucket
nixl_post_time_seconds_count
nixl_post_time_seconds_p50
nixl_post_time_seconds_p90
nixl_post_time_seconds_p99
nixl_post_time_seconds_sum
nixl_xfer_time_seconds_bucket
nixl_xfer_time_seconds_count
nixl_xfer_time_seconds_p50
nixl_xfer_time_seconds_p90
nixl_xfer_time_seconds_p99
nixl_xfer_time_seconds_sum
```

### 08 HTTP 请求延迟（12 个）

- `http_request_duration_seconds_*`：HTTP 请求处理耗时分布。
- `http_request_duration_highr_seconds_*`：通常指更细分桶的 High Resolution HTTP 耗时分布；具体桶边界和包含的请求类型以实际 Exporter 为准。
- HTTP 耗时是否覆盖流式输出全过程，由 Middleware/Handler 的计时边界决定；不要直接与引擎 E2E 等同。

**实际存在的指标名称：**

```text
http_request_duration_highr_seconds_bucket
http_request_duration_highr_seconds_count
http_request_duration_highr_seconds_p50
http_request_duration_highr_seconds_p90
http_request_duration_highr_seconds_p99
http_request_duration_highr_seconds_sum
http_request_duration_seconds_bucket
http_request_duration_seconds_count
http_request_duration_seconds_p50
http_request_duration_seconds_p90
http_request_duration_seconds_p99
http_request_duration_seconds_sum
```

### 09 Go Runtime 与进程资源（40 个）

**Go GC 与调度**

- `go_gc_duration_seconds`、`go_gc_duration_seconds_count`、`go_gc_duration_seconds_sum`：GC 暂停时间相关统计；首个无后缀序列如何表示需查看 TYPE。
- `go_gc_gogc_percent`、`go_gc_gomemlimit_bytes`：GC 参数与内存限制。
- `go_goroutines`、`go_threads`、`go_sched_gomaxprocs_threads`、`go_info`：协程、线程、并行度及 Go 版本信息。

**Go Heap 和内部内存**

- `go_memstats_alloc_bytes`、`go_memstats_heap_alloc_bytes`：当前分配/存活对象相关堆内存。
- `go_memstats_alloc_bytes_total`、`go_memstats_mallocs_total`、`go_memstats_frees_total`：累计分配字节、分配对象数、释放对象数。
- `go_memstats_heap_idle_bytes`、`go_memstats_heap_inuse_bytes`、`go_memstats_heap_released_bytes`、`go_memstats_heap_sys_bytes`、`go_memstats_heap_objects`：Heap 空闲、使用、释放、系统保留容量与对象数量。
- `go_memstats_gc_sys_bytes`、`go_memstats_last_gc_time_seconds`、`go_memstats_next_gc_bytes`：GC 内存、最近 GC 时间及下次 GC 阈值。
- `go_memstats_mcache_inuse_bytes`、`go_memstats_mcache_sys_bytes`、`go_memstats_mspan_inuse_bytes`、`go_memstats_mspan_sys_bytes`：分配器内部 MCache/MSpan 资源。
- `go_memstats_stack_inuse_bytes`、`go_memstats_stack_sys_bytes`：栈内存使用/申请。
- `go_memstats_buck_hash_sys_bytes`、`go_memstats_other_sys_bytes`、`go_memstats_sys_bytes`：Hash 元数据、其他 Runtime 内存及总内存。

**进程资源**

- `process_cpu_seconds_total`：累计进程 CPU 时间。
- `process_resident_memory_bytes`：进程 RSS 常驻内存。
- `process_virtual_memory_bytes`、`process_virtual_memory_max_bytes`：虚拟地址空间占用/上限相关统计。
- `process_open_fds`、`process_max_fds`：文件描述符占用与限额。
- `process_network_receive_bytes_total`、`process_network_transmit_bytes_total`：进程网络收发字节累计（以 Exporter 支持情况为准）。
- `process_start_time_seconds`：进程启动时间（Unix 秒）。

**实际存在的指标名称：**

```text
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
process_cpu_seconds_total
process_max_fds
process_network_receive_bytes_total
process_network_transmit_bytes_total
process_open_fds
process_resident_memory_bytes
process_start_time_seconds
process_virtual_memory_bytes
process_virtual_memory_max_bytes
```

### 10 监控采集与监控端点健康（11 个）

- `up`：最近一次抓取成功通常为 1，失败通常为 0；不等于业务可用性。
- `count:up1`：命名疑似自定义 Recording Rule，需检查 VM/Prometheus Rule 配置。
- `scrape_duration_seconds`：抓取耗时；`scrape_timeout_seconds`：抓取超时阈值。
- `scrape_response_size_bytes`：抓取响应大小；`scrape_samples_scraped`：原始样本数；`scrape_samples_post_metric_relabeling`：重标记后样本数；`scrape_series_added`：抓取新增的序列数。
- `promhttp_metric_handler_requests_in_flight`、`promhttp_metric_handler_requests_total`：Prometheus Metrics HTTP Handler 的并发请求与累计请求。
- `llm_engine_metrics_query_fail`：可能是引擎指标查询失败状态或计数；需确认 TYPE 后再决定使用比较表达式还是 `rate()`。

**实际存在的指标名称：**

```text
up
count:up1
llm_engine_metrics_query_fail
promhttp_metric_handler_requests_in_flight
promhttp_metric_handler_requests_total
scrape_duration_seconds
scrape_response_size_bytes
scrape_samples_post_metric_relabeling
scrape_samples_scraped
scrape_series_added
scrape_timeout_seconds
```

## 五、推荐的 PromQL（所有指标名称均来自本清单）

> 查询前请加上真实的 `job` / `namespace` / `pod` 等标签，避免跨服务重复聚合；不同标签下的时序也要先确认来源与统计口径。

**输入 / 输出 Token/s：**

```promql
sum(rate(prompt_tokens_total[5m]))
sum(rate(generation_tokens_total[5m]))
```

**5 分钟 Queue 平均时长（秒）：**

```promql
sum(rate(request_queue_time_seconds_sum[5m]))
/
sum(rate(request_queue_time_seconds_count[5m]))
```

**5 分钟 Queue P90（秒）：**

```promql
histogram_quantile(
  0.90,
  sum by (le) (rate(request_queue_time_seconds_bucket[5m]))
)
```

**5 分钟 NiXL 传输 P90（秒）：**

```promql
histogram_quantile(
  0.90,
  sum by (le) (rate(nixl_xfer_time_seconds_bucket[5m]))
)
```

**NiXL 数据字节速率（由事件直方图估算）：**

```promql
sum(rate(nixl_bytes_transferred_sum[5m]))
```

**内部前缀缓存命中比率（仅在命中/查询单位一致时）：**

```promql
sum(rate(prefix_cache_hits_total[5m]))
/
sum(rate(prefix_cache_queries_total[5m]))
```

**Balanced 决策次数（10 分钟）：**

```promql
sum(increase(aibrix_balanced_routing_decisions_total[10m]))
```

**当前采集失败目标：**

```promql
up == 0
```

## 六、联动排查路线

1. **TTFT 增长** → `time_to_first_token_seconds_p90`、`request_queue_time_seconds_p90`、`request_prefill_time_seconds_p90`。
2. **排队增长** → `num_requests_waiting`、`num_requests_running`、`kv_cache_usage_perc`。
3. **Prefill 变慢** → `request_prefill_time_seconds_p90`、`request_prompt_tokens_p90`、`avg_prompt_throughput_toks_per_s`、`prefix_cache_hits_total` / `prefix_cache_queries_total`。
4. **PD 传输瓶颈** → `nixl_xfer_time_seconds_p90`、`nixl_post_time_seconds_p90`、`nixl_bytes_transferred_sum`、`nixl_num_descriptors_p90`。
5. **路由异常** → `aibrix_balanced_routing_latency_seconds_bucket`、`aibrix_balanced_routing_decisions_total`、`aibrix_balanced_pod_scores`。
6. **监控异常** → `up`、`scrape_duration_seconds`、`scrape_samples_scraped`、`llm_engine_metrics_query_fail`。

## 七、核实非标准指标定义的方法

可以查看原始 Exporter 的 `/metrics` 中 `# HELP` / `# TYPE` 文本，或检查 VM 的 Recording Rule 与 Relabel 配置。对于 `aibrix_balanced_*` 指标，优先查找记录这些指标的 Go 源码和具体标签。仅有名称无法可靠推断 Score 的优先方向、`cache_entries` 的计数对象、`count:up1` 的 Rule 含义。

---

*本文件中的每一个指标名均从给定的 VM 清单核对而来；概念性术语（如 TTFT/ITL、GPU、Prefill/Decode）不视为新增监控指标。*
