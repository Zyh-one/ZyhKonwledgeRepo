# VM 采集指标汇总（按来源拆分）

本文汇总当前目录 4 份清单中的全部指标，共 **351 条“指标名－采集 job”来源记录**、**253 个唯一指标名**。与跨 job 合并同名指标的单表不同，本文按采集来源拆分；`go_*`、`process_*`、`scrape_*`、`up` 等同名指标会分别保留在对应 job 下，避免丢失采集目标归属。

每个来源表均增加“指标含义（简述）”和“主要标识标签”两列。“是否写入平台数据”列统一留空，供后续填写。

## 来源概览

| 采集 job                          |        记录数 | 来源范围                                                           |
| --------------------------------- | ------------: | ------------------------------------------------------------------ |
| `aibrix-gateway-plugins`        |            78 | AIBrix 原生、经 Gateway 暴露的 vLLM、Go/process 运行时及采集元数据 |
| `envoy-aibrix-system-aibrix-eg` |           133 | 带 HTTPRoute Upstream Cluster 标识的 Envoy Proxy 数据面指标        |
| `envoy-gateway`                 |            82 | Envoy Gateway 控制面、Go/process 运行时及采集元数据                |
| `envoy-svc-exporter-svc`        |            58 | Service Exporter 请求、Go/process 运行时及采集元数据               |
| **合计**                    | **351** | 253 个唯一指标名；跨 job 同名项按来源分别列出                      |

## 1. `aibrix-gateway-plugins`

（黄区aibrix-gateway-plugin会转发来自VLLM推理指标，我已经去除一部分“大模型监控”中的重复指标）

来源：[ `aibrix-gateway-plugins.md` ](aibrix-gateway-plugins.md)，共 **78** 条记录。该 job 混合多个语义来源，以下分为经 Gateway 暴露的 vLLM、AIBrix 原生路由/本地缓存、Go/process 运行时与采集元数据三个子表；它们仍全部属于同一个采集 job。

### 1.1 经 Gateway 暴露的 vLLM 推理引擎指标（19 项）

| 指标名                                         | 指标含义（简述）                                                                      | 主要标识标签                                                                     | 是否写入平台数据 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------- |
| `engine_sleep_state`                         | 引擎睡眠状态；数值枚举含义与状态标签待确认                                            | `cluster`、`namespace`、`job`、`pod`；状态标签待确认                     |                  |
| `iteration_tokens_total_bucket`              | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的 Histogram 桶计数            | `cluster`、`namespace`、`job`、`pod`、`le`；模型、引擎等业务标签待确认 |                  |
| `iteration_tokens_total_count`               | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的累计观测次数                 | `cluster`、`namespace`、`job`、`pod`；模型、引擎等业务标签待确认         |                  |
| `iteration_tokens_total_p50`                 | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的预导出 P50 分位数，单位Token | `cluster`、`namespace`、`job`、`pod`；模型、引擎等业务标签待确认         |                  |
| `iteration_tokens_total_p90`                 | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的预导出 P90 分位数，单位Token | `cluster`、`namespace`、`job`、`pod`；模型、引擎等业务标签待确认         |                  |
| `iteration_tokens_total_p99`                 | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的预导出 P99 分位数，单位Token | `cluster`、`namespace`、`job`、`pod`；模型、引擎等业务标签待确认         |                  |
| `iteration_tokens_total_sum`                 | 单次引擎迭代处理的 Token 数量（可含 Prefill 与 Decode）的累计总和，单位Token          | `cluster`、`namespace`、`job`、`pod`；模型、引擎等业务标签待确认         |                  |
| `http_request_duration_highr_seconds_bucket` | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的 Histogram 桶计数           | `cluster`、`namespace`、`job`、`pod`、`le`；请求维度标签待确认         |                  |
| `http_request_duration_highr_seconds_count`  | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的累计观测次数                | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_highr_seconds_p50`    | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的预导出 P50 分位数，单位秒   | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_highr_seconds_p90`    | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的预导出 P90 分位数，单位秒   | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_highr_seconds_p99`    | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的预导出 P99 分位数，单位秒   | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_highr_seconds_sum`    | 高分辨率 HTTP 请求处理耗时（具体桶边界与请求范围待确认）的累计总和，单位秒            | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_seconds_bucket`       | HTTP 请求处理耗时（计时边界与请求范围待确认）的 Histogram 桶计数                      | `cluster`、`namespace`、`job`、`pod`、`le`；请求维度标签待确认         |                  |
| `http_request_duration_seconds_count`        | HTTP 请求处理耗时（计时边界与请求范围待确认）的累计观测次数                           | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_seconds_p50`          | HTTP 请求处理耗时（计时边界与请求范围待确认）的预导出 P50 分位数，单位秒              | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_seconds_p90`          | HTTP 请求处理耗时（计时边界与请求范围待确认）的预导出 P90 分位数，单位秒              | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_seconds_p99`          | HTTP 请求处理耗时（计时边界与请求范围待确认）的预导出 P99 分位数，单位秒              | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |
| `http_request_duration_seconds_sum`          | HTTP 请求处理耗时（计时边界与请求范围待确认）的累计总和，单位秒                       | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                 |                  |

### 1.2 AIBrix 原生路由与本地缓存指标（8 项）

| 指标名                                             | 指标含义（简述）                                                         | 主要标识标签                                                                      | 是否写入平台数据 |
| -------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ---------------- |
| `aibrix_balanced_local_prefix_cache_capacity`    | 单个 gateway-plugins 副本本地前缀哈希 LRU 索引的容量上限                 | `cluster`、`namespace`、`job`、`pod`                                      |                  |
| `aibrix_balanced_local_prefix_cache_entries`     | 单个 gateway-plugins 副本本地前缀哈希 LRU 索引的当前条目数               | `cluster`、`namespace`、`job`、`pod`                                      |                  |
| `aibrix_balanced_local_prefix_cache_usage_ratio` | 单个 gateway-plugins 副本本地前缀索引的条目容量使用率，取值 0～1         | `cluster`、`namespace`、`job`、`pod`                                      |                  |
| `aibrix_balanced_pod_scores`                     | balanced 路由候选 Pod 的平均前缀匹配得分或负载得分，按 component 区分    | `cluster`、`namespace`、`job`、`pod`、`model`、`component`            |                  |
| `aibrix_balanced_routing_decisions_total`        | 按选中 Pod 的原始前缀匹配百分比分桶累计 balanced 路由决策次数            | `cluster`、`namespace`、`job`、`pod`、`model`、`match_percent_bucket` |                  |
| `aibrix_balanced_routing_latency_seconds_bucket` | balanced 路由决策算法耗时（不含 HTTP 转发和模型执行）的 Histogram 桶计数 | `cluster`、`namespace`、`job`、`pod`、`model`、`le`                   |                  |
| `aibrix_balanced_routing_latency_seconds_count`  | balanced 路由决策算法耗时（不含 HTTP 转发和模型执行）的累计观测次数      | `cluster`、`namespace`、`job`、`pod`、`model`                           |                  |
| `aibrix_balanced_routing_latency_seconds_sum`    | balanced 路由决策算法耗时（不含 HTTP 转发和模型执行）的累计总和，单位秒  | `cluster`、`namespace`、`job`、`pod`、`model`                           |                  |

### 1.3 Go/process 运行时与采集元数据（51 项）

| 指标名                                         | 指标含义（简述）                                               | 主要标识标签                                                             | 是否写入平台数据 |
| ---------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------- |
| `go_gc_duration_seconds`                     | Go GC 停顿耗时的 Summary 分位数观测                            | `cluster`、`namespace`、`job`、`pod`、`instance`、`quantile` |                  |
| `go_gc_duration_seconds_count`               | Go GC 停顿耗时的累计观测次数                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_gc_duration_seconds_sum`                 | Go GC 停顿耗时的累计总和，单位秒                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_gc_gogc_percent`                         | 当前 Go GC 目标百分比（GOGC）                                  | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_gc_gomemlimit_bytes`                     | 当前 Go 运行时内存软限制，单位字节                             | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_goroutines`                              | 当前 Goroutine 数量                                            | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_info`                                    | Go 运行时版本信息，值恒为 1                                    | `cluster`、`namespace`、`job`、`pod`、`instance`、`version`  |                  |
| `go_memstats_alloc_bytes`                    | 当前已分配且仍在使用的堆内存字节数                             | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_alloc_bytes_total`              | 累计分配的堆内存字节数，即使对象已释放也会累计                 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_buck_hash_sys_bytes`            | Go 性能分析 bucket 哈希表占用的内存字节数                      | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_frees_total`                    | 累计释放的堆对象次数                                           | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_gc_sys_bytes`                   | Go GC 元数据占用的内存字节数                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_alloc_bytes`               | 当前堆上已分配对象的内存字节数                                 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_idle_bytes`                | 当前空闲堆 Span 占用的内存字节数                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_inuse_bytes`               | 当前正在使用的堆 Span 内存字节数                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_objects`                   | 当前堆上已分配对象的数量                                       | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_released_bytes`            | 已归还给操作系统的堆内存字节数                                 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_heap_sys_bytes`                 | Go 运行时从操作系统获取的堆内存字节数                          | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_last_gc_time_seconds`           | 最近一次 GC 完成时间的 Unix 秒时间戳                           | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_mallocs_total`                  | 累计分配堆对象的次数                                           | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_mcache_inuse_bytes`             | 当前使用的 MCache 内存字节数                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_mcache_sys_bytes`               | 从操作系统获取的 MCache 内存字节数                             | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_mspan_inuse_bytes`              | 当前使用的 MSpan 内存字节数                                    | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_mspan_sys_bytes`                | 从操作系统获取的 MSpan 内存字节数                              | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_next_gc_bytes`                  | 触发下一次 GC 的目标堆内存字节数                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_other_sys_bytes`                | 其他 Go 运行时结构占用的内存字节数                             | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_stack_inuse_bytes`              | 当前使用的 Goroutine 栈内存字节数                              | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_stack_sys_bytes`                | 从操作系统获取的栈内存字节数                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_memstats_sys_bytes`                      | Go 运行时从操作系统获取的总内存字节数                          | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_sched_gomaxprocs_threads`                | 当前 GOMAXPROCS 可并行执行 Go 代码的线程数上限                 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `go_threads`                                 | 当前 Go 进程创建的操作系统线程数                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_cpu_seconds_total`                  | 进程累计消耗的用户态和内核态 CPU 秒数                          | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_max_fds`                            | 进程允许打开的文件描述符上限                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_network_receive_bytes_total`        | 进程累计接收的网络字节数                                       | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_network_transmit_bytes_total`       | 进程累计发送的网络字节数                                       | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_open_fds`                           | 进程当前打开的文件描述符数量                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_resident_memory_bytes`              | 进程当前驻留内存（RSS）字节数                                  | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_start_time_seconds`                 | 进程启动时间的 Unix 秒时间戳                                   | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_virtual_memory_bytes`               | 进程当前虚拟内存字节数                                         | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `process_virtual_memory_max_bytes`           | 进程可使用的虚拟内存上限字节数                                 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `up`                                         | 采集目标是否可用，1 表示最近一次抓取成功，0 表示失败           | `cluster`、`job`、`instance`                                       |                  |
| `count:up1`                                  | up=1 目标数量的记录规则结果，具体聚合范围以规则定义为准        | `cluster`、`job`                                                     |                  |
| `llm_engine_metrics_query_fail`              | LLM 引擎指标查询失败相关的定制指标，具体取值语义以采集实现为准 | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `promhttp_metric_handler_requests_in_flight` | 当前正在处理的 /metrics 请求数量                               | `cluster`、`namespace`、`job`、`pod`、`instance`               |                  |
| `promhttp_metric_handler_requests_total`     | /metrics 请求累计处理次数，通常按响应码区分                    | `cluster`、`namespace`、`job`、`pod`、`instance`、`code`     |                  |
| `scrape_duration_seconds`                    | 最近一次抓取该采集目标的耗时，单位秒                           | `cluster`、`job`、`instance`                                       |                  |
| `scrape_response_size_bytes`                 | 最近一次抓取响应的字节数                                       | `cluster`、`job`、`instance`                                       |                  |
| `scrape_samples_post_metric_relabeling`      | 最近一次抓取经 metric relabeling 后保留的样本数                | `cluster`、`job`、`instance`                                       |                  |
| `scrape_samples_scraped`                     | 最近一次抓取到的样本数                                         | `cluster`、`job`、`instance`                                       |                  |
| `scrape_series_added`                        | 最近一次抓取新增序列数的近似值                                 | `cluster`、`job`、`instance`                                       |                  |
| `scrape_timeout_seconds`                     | 该采集目标配置的抓取超时时间，单位秒                           | `cluster`、`job`、`instance`                                       |                  |



## 2. `envoy-aibrix-system-aibrix-eg`

**(该部分指标，已经整理过了，但是基本所有使用HTTPRoute匹配的数据序列全为0)**

来源：[ `envoy-aibrix-system-aibrix-eg.md` ](envoy-aibrix-system-aibrix-eg.md)，共 **133** 条记录。该表仅保留源清单已筛选出的 HTTPRoute Upstream Cluster 指标。`envoy_cluster_name` 用于定位 Cluster，其 HTTPRoute 形式为 `httproute/<namespace>/<HTTPRoute名称>/rule/<序号>`；`pod` 用于区分不同 Envoy 副本的观测。

| 指标名                                                                                  | 指标含义（简述）                                               | 主要标识标签                                                                 | 是否写入平台数据 |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------- |
| `envoy_cluster_assignment_stale`                                                      | Cluster Endpoint assignment 的 stale 状态指标                  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_assignment_timeout_received`                                           | Cluster 收到 assignment 超时的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_assignment_use_cached`                                                 | Cluster 使用缓存 assignment 的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_bind_errors`                                                           | Cluster 绑定本地地址失败的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_default_total_match_count`                                             | Cluster 默认匹配规则的累计匹配次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_init_fetch_timeout`                                                    | Cluster 初始化拉取超时的累计次数                               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_original_dst_host_invalid`                                             | Original destination 目标主机无效的累计次数                    | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_attempt`                                                        | Cluster 配置更新尝试的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_duration_bucket`                                                | Cluster 配置更新耗时的 Histogram 桶计数                        | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`、`le` |                  |
| `envoy_cluster_update_duration_count`                                                 | Cluster 配置更新耗时的累计观测次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_duration_sum`                                                   | Cluster 配置更新耗时的累计总和                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_empty`                                                          | 未产生实际内容的 Cluster 更新累计次数                          | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_failure`                                                        | Cluster 配置更新失败的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_no_rebuild`                                                     | 无需重建的 Cluster 更新累计次数                                | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_rejected`                                                       | Cluster 配置更新被拒绝的累计次数                               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_success`                                                        | Cluster 配置更新成功的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_update_time`                                                           | 最近一次 Cluster 配置更新的时间相关指标                        | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_version`                                                               | Cluster 配置版本相关指标                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_warming_state`                                                         | Cluster 当前 warming 状态                                      | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_membership_change`                                                     | Cluster Endpoint 成员变化的累计次数                            | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_membership_degraded`                                                   | 当前处于 degraded 状态的 Endpoint 数量                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_membership_excluded`                                                   | 当前被排除的 Endpoint 数量                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_membership_healthy`                                                    | 当前健康的 Endpoint 数量                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_membership_total`                                                      | 当前 Endpoint 总数量                                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_healthy_panic`                                                      | 负载均衡 healthy panic 状态相关指标                            | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_local_cluster_not_ok`                                               | 本地 Cluster 状态不满足负载均衡条件的累计次数                  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_recalculate_zone_structures`                                        | 负载均衡区域结构重新计算的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_active`                                                     | 当前活跃的负载均衡 Endpoint 子集数量                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_created`                                                    | 负载均衡 Endpoint 子集累计创建次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_fallback`                                                   | 负载均衡子集回退状态相关指标                                   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_fallback_panic`                                             | 负载均衡子集 fallback panic 状态相关指标                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_removed`                                                    | 负载均衡 Endpoint 子集累计移除次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_subsets_selected`                                                   | 负载均衡 Endpoint 子集被选择的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_cluster_too_small`                                             | 区域 Cluster 规模过小的负载均衡事件累计次数                    | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_no_capacity_left`                                              | 区域无剩余容量的负载均衡事件累计次数                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_number_differs`                                                | 本地与上游区域数量不一致的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_routing_all_directly`                                          | 请求全部直接路由到单一区域的累计次数                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_routing_cross_zone`                                            | 发生跨区域路由的累计次数                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_lb_zone_routing_sampled`                                               | 区域路由决策被采样的累计次数                                   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_max_host_weight`                                                       | Cluster 内 Endpoint 的最大负载均衡权重                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_default_cx_open`                                      | DEFAULT 优先级连接数熔断状态，1 表示打开，0 表示关闭           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_default_cx_pool_open`                                 | DEFAULT 优先级连接池熔断状态，1 表示打开，0 表示关闭           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_default_rq_open`                                      | DEFAULT 优先级请求数熔断状态，1 表示打开，0 表示关闭           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_default_rq_pending_open`                              | DEFAULT 优先级Pending 请求数熔断状态，1 表示打开，0 表示关闭   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_default_rq_retry_open`                                | DEFAULT 优先级重试熔断状态，1 表示打开，0 表示关闭             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_high_cx_open`                                         | HIGH 优先级连接数熔断状态，1 表示打开，0 表示关闭              | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_high_cx_pool_open`                                    | HIGH 优先级连接池熔断状态，1 表示打开，0 表示关闭              | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_high_rq_open`                                         | HIGH 优先级请求数熔断状态，1 表示打开，0 表示关闭              | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_high_rq_pending_open`                                 | HIGH 优先级Pending 请求数熔断状态，1 表示打开，0 表示关闭      | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_circuit_breakers_high_rq_retry_open`                                   | HIGH 优先级重试熔断状态，1 表示打开，0 表示关闭                | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_active`                                    | 当前被异常点检测剔除的 Endpoint 数量                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_consecutive_5xx`                           | 因连续 5xx 异常执行 Endpoint 剔除的累计次数                    | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_5xx`                  | 检测到 consecutive 5xx 异常点剔除的累计次数                    | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_gateway_failure`      | 检测到 consecutive gateway failure 异常点剔除的累计次数        | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_consecutive_local_origin_failure` | 检测到 consecutive local origin failure 异常点剔除的累计次数   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_failure_percentage`               | 检测到 failure percentage 异常点剔除的累计次数                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_local_origin_failure_percentage`  | 检测到 local origin failure percentage 异常点剔除的累计次数    | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_local_origin_success_rate`        | 检测到 local origin success rate 异常点剔除的累计次数          | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_detected_success_rate`                     | 检测到 success rate 异常点剔除的累计次数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx`                  | 实际执行 consecutive 5xx 异常点剔除的累计次数                  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure`      | 实际执行 consecutive gateway failure 异常点剔除的累计次数      | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure` | 实际执行 consecutive local origin failure 异常点剔除的累计次数 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_failure_percentage`               | 实际执行 failure percentage 异常点剔除的累计次数               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_local_origin_failure_percentage`  | 实际执行 local origin failure percentage 异常点剔除的累计次数  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_local_origin_success_rate`        | 实际执行 local origin success rate 异常点剔除的累计次数        | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_success_rate`                     | 实际执行 success rate 异常点剔除的累计次数                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_enforced_total`                            | 实际执行 total 异常点剔除的累计次数                            | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_overflow`                                  | 因达到剔除上限而拒绝继续剔除的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_success_rate`                              | 因成功率异常而执行 Endpoint 剔除的累计次数                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_outlier_detection_ejections_total`                                     | 异常点检测执行 Endpoint 剔除的累计总次数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_active`                                                    | 当前活跃的上游连接数量                                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_close_notify`                                              | 上游连接收到 close notify 后关闭的累计次数                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_attempts_exceeded`                                 | 上游建连尝试次数超过上限的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_fail`                                              | 上游建连失败的累计次数                                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_ms_bucket`                                         | 上游 TCP 建连耗时的 Histogram 桶计数，单位毫秒                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`、`le` |                  |
| `envoy_cluster_upstream_cx_connect_ms_count`                                          | 上游 TCP 建连耗时的累计观测次数                                | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_ms_sum`                                            | 上游 TCP 建连耗时的累计总和，单位毫秒                          | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_timeout`                                           | 上游建连超时的累计次数                                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_connect_with_0_rtt`                                        | 使用 0-RTT 建立上游连接的累计次数                              | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy`                                                   | 上游连接销毁的累计总次数                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy_local`                                             | Envoy 本地主动销毁上游连接的累计次数                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy_local_with_active_rq`                              | 本地销毁仍承载活跃请求的上游连接累计次数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy_remote`                                            | 上游对端触发连接销毁的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy_remote_with_active_rq`                             | 对端销毁仍承载活跃请求的上游连接累计次数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_destroy_with_active_rq`                                    | 销毁时仍承载活跃请求的上游连接累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_http1_total`                                               | 新建 HTTP/1.x 上游连接的累计次数                               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_http2_total`                                               | 新建 HTTP/2 上游连接的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_http3_total`                                               | 新建 HTTP/3 上游连接的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_idle_timeout`                                              | 上游连接因空闲超时关闭的累计次数                               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_length_ms_bucket`                                          | 上游连接存活时长的 Histogram 桶计数，单位毫秒                  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`、`le` |                  |
| `envoy_cluster_upstream_cx_length_ms_count`                                           | 上游连接存活时长的累计观测次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_length_ms_sum`                                             | 上游连接存活时长的累计总和，单位毫秒                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_max_duration_reached`                                      | 上游连接因达到最大存活时长关闭的累计次数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_max_requests`                                              | 上游连接因达到最大请求数关闭的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_none_healthy`                                              | 因无健康 Endpoint 而无法建连的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_overflow`                                                  | 上游连接数超过限制而产生溢出的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_pool_overflow`                                             | 上游连接池容量溢出的累计次数                                   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_protocol_error`                                            | 上游连接发生协议错误的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_total`                                                     | 新建上游连接的累计总次数                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_rx_bytes_buffered`                                         | 当前接收方向仍缓存在 Envoy 中的上游响应字节数                  | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_rx_bytes_total`                                            | 从上游累计接收的响应字节数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_tx_bytes_buffered`                                         | 当前发送方向仍缓存在 Envoy 中的请求字节数                      | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_cx_tx_bytes_total`                                            | 向上游累计发送的请求字节数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_flow_control_backed_up_total`                                 | 上游写入受阻并向下游传播背压的累计事件数                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_flow_control_drained_total`                                   | 上游写缓冲排空并解除背压的累计事件数                           | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_flow_control_paused_reading_total`                            | Envoy 暂停读取上游响应的累计事件数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_flow_control_resumed_reading_total`                           | Envoy 恢复读取上游响应的累计事件数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_0rtt`                                                      | 上游 0-RTT 请求相关指标，具体类型与口径以部署版本为准          | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_active`                                                    | 当前正在处理的上游请求数量                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_cancelled`                                                 | 上游请求被取消的累计次数                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_completed`                                                 | 上游请求处理完成的累计次数，不等同于成功请求数                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_maintenance_mode`                                          | 上游处于维护模式相关请求的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_max_duration_reached`                                      | 上游请求因达到最大时长而终止的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_pending_active`                                            | 当前等待上游连接或连接池的请求数量                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_pending_failure_eject`                                     | Pending 请求因连接失败被逐出的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_pending_overflow`                                          | Pending 请求队列溢出的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_pending_total`                                             | 进入 Pending 状态的上游请求累计次数                            | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_per_try_idle_timeout`                                      | 单次上游请求尝试发生空闲超时的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_per_try_timeout`                                           | 单次上游请求尝试超时的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry`                                                     | 上游请求发生重试的累计次数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry_backoff_exponential`                                 | 上游重试触发指数退避的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry_backoff_ratelimited`                                 | 上游重试退避受到速率限制的累计次数                             | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry_limit_exceeded`                                      | 上游重试次数超过限制的累计次数                                 | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry_overflow`                                            | 上游重试预算溢出的累计次数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_retry_success`                                             | 上游重试后成功的累计次数                                       | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_rx_reset`                                                  | 上游对端重置请求的累计次数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_timeout`                                                   | 上游请求整体超时的累计次数                                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_total`                                                     | 上游请求尝试的累计总次数，可能包含重试                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_rq_tx_reset`                                                  | Envoy 本地重置上游请求的累计次数                               | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_retry_or_shadow_abandoned`                                             | Cluster 重试或 shadow 请求被放弃的累计次数                     | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_http3_broken`                                                 | 上游 HTTP/3 连接异常或不可用的累计次数                         | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_internal_redirect_failed_total`                               | 上游内部重定向失败的累计次数                                   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |
| `envoy_cluster_upstream_internal_redirect_succeeded_total`                            | 上游内部重定向成功的累计次数                                   | `cluster`、`namespace`、`job`、`pod`、`envoy_cluster_name`         |                  |

## 3. `envoy-gateway`

来源：[ `envoy-gateway.md` ](envoy-gateway.md)，共 **82** 条记录。该 job 主要反映 Envoy Gateway 控制面自身的 Reconcile、资源写入、状态更新、订阅与 xDS Snapshot 活动，不表示业务 Upstream Cluster 的请求转发情况。

| 指标名                                                 | 指标含义（简述）                                        | 主要标识标签                                                                               | 是否写入平台数据 |
| ------------------------------------------------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------- |
| `certwatcher_read_certificate_errors_total`          | 证书监听组件读取证书失败的累计次数                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `certwatcher_read_certificate_total`                 | 证书监听组件读取证书的累计次数                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `controller_runtime_active_workers`                  | 当前正在执行 Reconcile 的 Worker 数量                   | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_max_concurrent_reconciles`       | 各 Controller 允许的最大并发 Reconcile 数量             | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_reconcile_errors_total`          | Controller Reconcile 返回错误的累计次数                 | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_reconcile_panics_total`          | Controller Reconcile 发生 panic 的累计次数              | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_reconcile_time_seconds_bucket`   | Controller Reconcile 耗时的 Histogram 桶计数            | `cluster`、`namespace`、`job`、`pod`、`instance`、`le`、`controller`         |                  |
| `controller_runtime_reconcile_time_seconds_count`    | Controller Reconcile 耗时的累计观测次数                 | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_reconcile_time_seconds_sum`      | Controller Reconcile 耗时的累计总和，单位秒             | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_reconcile_total`                 | Controller Reconcile 累计执行次数                       | `cluster`、`namespace`、`job`、`pod`、`instance`、`result`、`controller`     |                  |
| `controller_runtime_terminal_reconcile_errors_total` | Controller 发生终止性 Reconcile 错误的累计次数          | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `controller_runtime_webhook_panics_total`            | Controller Runtime Webhook 发生 panic 的累计次数        | `cluster`、`namespace`、`job`、`pod`、`instance`、`controller`                 |                  |
| `count:up1`                                          | up=1 目标数量的记录规则结果，具体聚合范围以规则定义为准 | `cluster`、`job`                                                                       |                  |
| `go_gc_duration_seconds`                             | Go GC 停顿耗时的 Summary 分位数观测                     | `cluster`、`namespace`、`job`、`pod`、`instance`、`quantile`                   |                  |
| `go_gc_duration_seconds_count`                       | Go GC 停顿耗时的累计观测次数                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_gc_duration_seconds_sum`                         | Go GC 停顿耗时的累计总和，单位秒                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_gc_gogc_percent`                                 | 当前 Go GC 目标百分比（GOGC）                           | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_gc_gomemlimit_bytes`                             | 当前 Go 运行时内存软限制，单位字节                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_goroutines`                                      | 当前 Goroutine 数量                                     | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_info`                                            | Go 运行时版本信息，值恒为 1                             | `cluster`、`namespace`、`job`、`pod`、`instance`、`version`                    |                  |
| `go_memstats_alloc_bytes`                            | 当前已分配且仍在使用的堆内存字节数                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_alloc_bytes_total`                      | 累计分配的堆内存字节数，即使对象已释放也会累计          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_buck_hash_sys_bytes`                    | Go 性能分析 bucket 哈希表占用的内存字节数               | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_frees_total`                            | 累计释放的堆对象次数                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_gc_sys_bytes`                           | Go GC 元数据占用的内存字节数                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_alloc_bytes`                       | 当前堆上已分配对象的内存字节数                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_idle_bytes`                        | 当前空闲堆 Span 占用的内存字节数                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_inuse_bytes`                       | 当前正在使用的堆 Span 内存字节数                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_objects`                           | 当前堆上已分配对象的数量                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_released_bytes`                    | 已归还给操作系统的堆内存字节数                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_heap_sys_bytes`                         | Go 运行时从操作系统获取的堆内存字节数                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_last_gc_time_seconds`                   | 最近一次 GC 完成时间的 Unix 秒时间戳                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_mallocs_total`                          | 累计分配堆对象的次数                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_mcache_inuse_bytes`                     | 当前使用的 MCache 内存字节数                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_mcache_sys_bytes`                       | 从操作系统获取的 MCache 内存字节数                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_mspan_inuse_bytes`                      | 当前使用的 MSpan 内存字节数                             | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_mspan_sys_bytes`                        | 从操作系统获取的 MSpan 内存字节数                       | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_next_gc_bytes`                          | 触发下一次 GC 的目标堆内存字节数                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_other_sys_bytes`                        | 其他 Go 运行时结构占用的内存字节数                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_stack_inuse_bytes`                      | 当前使用的 Goroutine 栈内存字节数                       | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_stack_sys_bytes`                        | 从操作系统获取的栈内存字节数                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_memstats_sys_bytes`                              | Go 运行时从操作系统获取的总内存字节数                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_sched_gomaxprocs_threads`                        | 当前 GOMAXPROCS 可并行执行 Go 代码的线程数上限          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `go_threads`                                         | 当前 Go 进程创建的操作系统线程数                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `leader_election_master_status`                      | 当前实例是否为 Leader，1 表示是，0 表示否               | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_cpu_seconds_total`                          | 进程累计消耗的用户态和内核态 CPU 秒数                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_max_fds`                                    | 进程允许打开的文件描述符上限                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_network_receive_bytes_total`                | 进程累计接收的网络字节数                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_network_transmit_bytes_total`               | 进程累计发送的网络字节数                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_open_fds`                                   | 进程当前打开的文件描述符数量                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_resident_memory_bytes`                      | 进程当前驻留内存（RSS）字节数                           | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_start_time_seconds`                         | 进程启动时间的 Unix 秒时间戳                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_virtual_memory_bytes`                       | 进程当前虚拟内存字节数                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `process_virtual_memory_max_bytes`                   | 进程可使用的虚拟内存上限字节数                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_apply_duration_seconds_bucket`             | 资源 Apply 操作耗时的 Histogram 桶计数                  | `cluster`、`namespace`、`job`、`pod`、`instance`、`le`                         |                  |
| `resource_apply_duration_seconds_count`              | 资源 Apply 操作耗时的累计观测次数                       | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_apply_duration_seconds_sum`                | 资源 Apply 操作耗时的累计总和，单位秒                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_apply_total`                               | Kubernetes 资源 Apply 操作的累计次数                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_delete_duration_seconds_bucket`            | 资源 Delete 操作耗时的 Histogram 桶计数                 | `cluster`、`namespace`、`job`、`pod`、`instance`、`le`                         |                  |
| `resource_delete_duration_seconds_count`             | 资源 Delete 操作耗时的累计观测次数                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_delete_duration_seconds_sum`               | 资源 Delete 操作耗时的累计总和，单位秒                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `resource_delete_total`                              | Kubernetes 资源 Delete 操作的累计次数                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `rest_client_requests_total`                         | Kubernetes REST Client 请求的累计次数                   | `cluster`、`namespace`、`job`、`pod`、`instance`、`code`、`method`、`host` |                  |
| `scrape_duration_seconds`                            | 最近一次抓取该采集目标的耗时，单位秒                    | `cluster`、`job`、`instance`                                                         |                  |
| `scrape_response_size_bytes`                         | 最近一次抓取响应的字节数                                | `cluster`、`job`、`instance`                                                         |                  |
| `scrape_samples_post_metric_relabeling`              | 最近一次抓取经 metric relabeling 后保留的样本数         | `cluster`、`job`、`instance`                                                         |                  |
| `scrape_samples_scraped`                             | 最近一次抓取到的样本数                                  | `cluster`、`job`、`instance`                                                         |                  |
| `scrape_series_added`                                | 最近一次抓取新增序列数的近似值                          | `cluster`、`job`、`instance`                                                         |                  |
| `scrape_timeout_seconds`                             | 该采集目标配置的抓取超时时间，单位秒                    | `cluster`、`job`、`instance`                                                         |                  |
| `status_update_duration_seconds_bucket`              | 资源状态更新耗时的 Histogram 桶计数                     | `cluster`、`namespace`、`job`、`pod`、`instance`、`le`                         |                  |
| `status_update_duration_seconds_count`               | 资源状态更新耗时的累计观测次数                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `status_update_duration_seconds_sum`                 | 资源状态更新耗时的累计总和，单位秒                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `status_update_total`                                | 资源状态更新操作的累计次数                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `up`                                                 | 采集目标是否可用，1 表示最近一次抓取成功，0 表示失败    | `cluster`、`job`、`instance`                                                         |                  |
| `wasm_cache_entries`                                 | 当前 WASM 模块缓存条目数量                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `watchable_depth`                                    | Watchable 当前待处理消息或事件深度                      | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `watchable_subscribe_duration_seconds_bucket`        | Watchable 订阅耗时的 Histogram 桶计数                   | `cluster`、`namespace`、`job`、`pod`、`instance`、`le`                         |                  |
| `watchable_subscribe_duration_seconds_count`         | Watchable 订阅耗时的累计观测次数                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `watchable_subscribe_duration_seconds_sum`           | Watchable 订阅耗时的累计总和，单位秒                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `watchable_subscribe_total`                          | Watchable 订阅操作的累计次数                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `xds_snapshot_create_total`                          | xDS Snapshot 累计创建次数                               | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |
| `xds_snapshot_update_total`                          | xDS Snapshot 累计更新次数                               | `cluster`、`namespace`、`job`、`pod`、`instance`                                 |                  |

## 4. `envoy-svc-exporter-svc`

来源：[ `envoy-svc-exporter-svc.md` ](envoy-svc-exporter-svc.md)，共 **58** 条记录。该 job 包含 Service Exporter 的请求观测以及导出器自身的运行时和采集元数据。`envoy_svc_*` 与不带 `svc` 的请求指标属于不同导出名称，不应在查询时混为同一序列。

| 指标名                                         | 指标含义（简述）                                                                | 主要标识标签                                                                                                   | 是否写入平台数据 |
| ---------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------- |
| `count:up1`                                  | up=1 目标数量的记录规则结果，具体聚合范围以规则定义为准                         | `cluster`、`job`                                                                                           |                  |
| `envoy_request_duration_seconds_bucket`      | Service Exporter 请求耗时（非 svc 命名，具体统计范围待确认）的 Histogram 桶计数 | `cluster`、`namespace`、`job`、`pod`、`le`；请求维度标签待确认                                       |                  |
| `envoy_request_duration_seconds_count`       | Service Exporter 请求耗时（非 svc 命名，具体统计范围待确认）的累计观测次数      | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                                               |                  |
| `envoy_request_duration_seconds_sum`         | Service Exporter 请求耗时（非 svc 命名，具体统计范围待确认）的累计总和，单位秒  | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                                               |                  |
| `envoy_requests_total`                       | Service Exporter 请求累计次数；非 svc 命名，具体统计范围与请求标签待确认        | `cluster`、`namespace`、`job`、`pod`；请求维度标签待确认                                               |                  |
| `envoy_svc_request_duration_seconds_bucket`  | 服务级请求处理耗时的 Histogram 桶计数                                           | `cluster`、`namespace`、`label_id`、`label_version`、`path`、`le`                                  |                  |
| `envoy_svc_request_duration_seconds_count`   | 服务级请求处理耗时的累计观测次数                                                | `cluster`、`namespace`、`label_id`、`label_version`、`path`                                          |                  |
| `envoy_svc_request_duration_seconds_sum`     | 服务级请求处理耗时的累计总和，单位秒                                            | `cluster`、`namespace`、`label_id`、`label_version`、`path`                                          |                  |
| `envoy_svc_requests_total`                   | 服务级请求累计次数，可按路径、响应状态和 response flag 拆分                     | `cluster`、`namespace`、`pod`、`label_id`、`label_version`、`path`、`status`、`response_flags` |                  |
| `go_gc_duration_seconds`                     | Go GC 停顿耗时的 Summary 分位数观测                                             | `cluster`、`namespace`、`job`、`pod`、`instance`、`quantile`                                       |                  |
| `go_gc_duration_seconds_count`               | Go GC 停顿耗时的累计观测次数                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_gc_duration_seconds_sum`                 | Go GC 停顿耗时的累计总和，单位秒                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_gc_gogc_percent`                         | 当前 Go GC 目标百分比（GOGC）                                                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_gc_gomemlimit_bytes`                     | 当前 Go 运行时内存软限制，单位字节                                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_goroutines`                              | 当前 Goroutine 数量                                                             | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_info`                                    | Go 运行时版本信息，值恒为 1                                                     | `cluster`、`namespace`、`job`、`pod`、`instance`、`version`                                        |                  |
| `go_memstats_alloc_bytes`                    | 当前已分配且仍在使用的堆内存字节数                                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_alloc_bytes_total`              | 累计分配的堆内存字节数，即使对象已释放也会累计                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_buck_hash_sys_bytes`            | Go 性能分析 bucket 哈希表占用的内存字节数                                       | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_frees_total`                    | 累计释放的堆对象次数                                                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_gc_sys_bytes`                   | Go GC 元数据占用的内存字节数                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_alloc_bytes`               | 当前堆上已分配对象的内存字节数                                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_idle_bytes`                | 当前空闲堆 Span 占用的内存字节数                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_inuse_bytes`               | 当前正在使用的堆 Span 内存字节数                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_objects`                   | 当前堆上已分配对象的数量                                                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_released_bytes`            | 已归还给操作系统的堆内存字节数                                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_heap_sys_bytes`                 | Go 运行时从操作系统获取的堆内存字节数                                           | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_last_gc_time_seconds`           | 最近一次 GC 完成时间的 Unix 秒时间戳                                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_mallocs_total`                  | 累计分配堆对象的次数                                                            | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_mcache_inuse_bytes`             | 当前使用的 MCache 内存字节数                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_mcache_sys_bytes`               | 从操作系统获取的 MCache 内存字节数                                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_mspan_inuse_bytes`              | 当前使用的 MSpan 内存字节数                                                     | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_mspan_sys_bytes`                | 从操作系统获取的 MSpan 内存字节数                                               | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_next_gc_bytes`                  | 触发下一次 GC 的目标堆内存字节数                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_other_sys_bytes`                | 其他 Go 运行时结构占用的内存字节数                                              | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_stack_inuse_bytes`              | 当前使用的 Goroutine 栈内存字节数                                               | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_stack_sys_bytes`                | 从操作系统获取的栈内存字节数                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_memstats_sys_bytes`                      | Go 运行时从操作系统获取的总内存字节数                                           | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_sched_gomaxprocs_threads`                | 当前 GOMAXPROCS 可并行执行 Go 代码的线程数上限                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `go_threads`                                 | 当前 Go 进程创建的操作系统线程数                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_cpu_seconds_total`                  | 进程累计消耗的用户态和内核态 CPU 秒数                                           | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_max_fds`                            | 进程允许打开的文件描述符上限                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_network_receive_bytes_total`        | 进程累计接收的网络字节数                                                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_network_transmit_bytes_total`       | 进程累计发送的网络字节数                                                        | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_open_fds`                           | 进程当前打开的文件描述符数量                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_resident_memory_bytes`              | 进程当前驻留内存（RSS）字节数                                                   | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_start_time_seconds`                 | 进程启动时间的 Unix 秒时间戳                                                    | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_virtual_memory_bytes`               | 进程当前虚拟内存字节数                                                          | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `process_virtual_memory_max_bytes`           | 进程可使用的虚拟内存上限字节数                                                  | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `promhttp_metric_handler_requests_in_flight` | 当前正在处理的 /metrics 请求数量                                                | `cluster`、`namespace`、`job`、`pod`、`instance`                                                     |                  |
| `promhttp_metric_handler_requests_total`     | /metrics 请求累计处理次数，通常按响应码区分                                     | `cluster`、`namespace`、`job`、`pod`、`instance`、`code`                                           |                  |
| `scrape_duration_seconds`                    | 最近一次抓取该采集目标的耗时，单位秒                                            | `cluster`、`job`、`instance`                                                                             |                  |
| `scrape_response_size_bytes`                 | 最近一次抓取响应的字节数                                                        | `cluster`、`job`、`instance`                                                                             |                  |
| `scrape_samples_post_metric_relabeling`      | 最近一次抓取经 metric relabeling 后保留的样本数                                 | `cluster`、`job`、`instance`                                                                             |                  |
| `scrape_samples_scraped`                     | 最近一次抓取到的样本数                                                          | `cluster`、`job`、`instance`                                                                             |                  |
| `scrape_series_added`                        | 最近一次抓取新增序列数的近似值                                                  | `cluster`、`job`、`instance`                                                                             |                  |
| `scrape_timeout_seconds`                     | 该采集目标配置的抓取超时时间，单位秒                                            | `cluster`、`job`、`instance`                                                                             |                  |
| `up`                                         | 采集目标是否可用，1 表示最近一次抓取成功，0 表示失败                            | `cluster`、`job`、`instance`                                                                             |                  |

## 标签与统计口径说明

- “主要标识标签”只列定位采集目标或业务对象的常用维度，不声称穷举实际序列的全部标签；具体标签名和取值仍以 VM 中的原始序列为准。
- Histogram 的 `_bucket` 序列另带 `le`；`_count`、`_sum` 不带 `le`。Go GC Summary 的分位数序列带 `quantile`。预导出的 `_p50`、`_p90`、`_p99` 不应通过求和或平均推导整体分位数。
- `cluster` 表示 VM 序列所属集群标签，`namespace`、`pod`、`instance` 和 `job` 用于定位采集目标；`envoy_cluster_name` 才是 HTTPRoute Upstream Cluster 的业务定位标签。
- `go_*` 与 `process_*` 描述被采集进程自身，不等同于容器或 Pod 的 CPU、working set 等资源指标。
- `label_id` 在带该标签的 LLMServing 相关序列中表示平台 LLMServing/Predictor 业务 ID，不是 Router ID 或 Kubernetes UID。
