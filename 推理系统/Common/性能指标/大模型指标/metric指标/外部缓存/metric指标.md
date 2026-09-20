# 外部缓存 metric 指标

本文说明“外部缓存”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

> **组织说明**：以下 metric 按前端“外部缓存”区块的显示顺序与聚合关系排列，与 [PromQL.md](./PromQL.md) 的章节顺序一一对应。该区块共 8 张图（命中次数 → 命中率 → 传输字节数×2 方向 → 传输大小分位×2 方向 → 传输大小热力图×2 方向）。其中 **“命中率”一条图聚合 2 个 metric**（命中 + 查询），**“传输大小分位”一条图聚合同一 Histogram 家族的 3 个 metric**（`_bucket` 出 4 条分位 + `_sum`/`_count` 出 1 条均值）；KV 卸载系列的两张方向图共用同一 metric，仅 `transfer_type` 标签不同。
>
> 另有“综合 Prefix 缓存命中率”图使用的 `vllm:prefix_cache_hits_total` / `vllm:prefix_cache_queries_total` 属于“缓存”区块（该图位于 `monitor.cache` 行，`externalCacheEnabled` 时显示），已在 `缓存/metric指标.md` 文档，本文不重复。
>
> **口径提醒（重要）**：`vllm:external_prefix_cache_hits_total` / `vllm:external_prefix_cache_queries_total` 单位为 **token**（vLLM 源码：`connector_prefix_cache_stats.record(num_tokens=..., num_hits=...)`，二者均按 token 计），不是命中/查询事件次数。命中率 = 命中 token 数 / 查询 token 数，是 token 级比例。
>
> **外部命中来源（按 role 区分）**：External 命中由 `self.connector`（KVConnector，V1 `MultiConnector`）驱动。同一“外部缓存命中率/命中次数”指标，在 **prefill pod** 上主要对应 `OffloadingConnector`（本 pod CPU 内存 KV 的 promote-back 命中），在 **decode pod** 上主要对应 `NixlConnector`（跨 pod 从 prefill 收到的 KV 命中）。监控面板上需按 role 区分着看。

## 1. `vllm:external_prefix_cache_hits_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计外部 KV/Prefix Cache **命中的 token 数**（vLLM 源码：`External prefix cache hits ... in terms of number of cached tokens.`）。递增点 `counter_external_prefix_cache_hits[engine_idx].inc(scheduler_stats.connector_prefix_cache_stats.hits)`，其中 `connector_prefix_cache_stats.hits` = 调度器准入时 `self.connector.get_num_new_matched_tokens(...)` 返回的外部匹配 token 数。同时服务于“外部缓存命中次数”（单值）与“外部缓存命中率”（分子）两张图。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/backend。

## 2. `vllm:external_prefix_cache_queries_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计外部 KV/Prefix Cache **查询的 token 数**，是外部命中率的分母。递增点 `counter_external_prefix_cache_queries[engine_idx].inc(scheduler_stats.connector_prefix_cache_stats.queries)`，其中 `connector_prefix_cache_stats.queries = request.num_tokens - num_new_local_computed_tokens`（本地未命中、交由 connector 查询的 token 数）。值为 0 可能表示功能未启用、无合格请求或采集缺失；窗口无查询 token 时命中率无定义。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/backend。

## 3. `vllm:kv_offload_total_bytes_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 byte，表示 KV 卸载（GPU/MLU ↔ CPU 内存）累计传输字节数。按 `transfer_type` 标签区分方向，`CPU_to_MLU`（CPU→AI 卡，promote 回填）与 `MLU_to_CPU`（AI 卡→CPU，offload 卸载）各对应一张图。`increase()` 得窗口总量；如需带宽应使用 `rate()`。双重 `total` 只是当前命名（Counter 被 prometheus 自动加 `_total`）。

**唯一标识标签：** `(cluster, namespace, pod, transfer_type)`；有 backend/target 时保留。

## 4. 单次 KV 卸载传输大小 Histogram 家族

`vllm:kv_offload_size` 是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。它服务于“传输大小分位”（两张方向图，各聚合 4 条分位 + 1 条均值）与“传输大小热力图”（两张方向图）共 4 张图，按 `transfer_type` 分方向。

### `vllm:kv_offload_size_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 transfer。它按照 `le` 记录“单次 KV 卸载传输大小小于等于该上界”的累计传输数；`le` 的单位为 byte。`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。

分位图对它使用 `rate()`（再 `histogram_quantile` 得 P99.9/P95/P90/P50），热力图对它使用 `increase()`（按大小区间映射密度）。

> **桶边界口径（重要）**：本 Histogram 的有限桶边界在 vLLM 源码 `vllm/distributed/kv_transfer/kv_connector/v1/offloading/metrics.py` 的 `TRANSFER_SIZE_BUCKETS` 中硬编码，值为 `(1e6, 5e6, 1e7, 2e7, 4e7, 6e7, 8e7, 1e8, 1.5e8, 2e8)`（即 1/5/10/20/40/60/80/100/150/200 MB），prometheus_client 自动再加 `+Inf`。黄区 VictoriaMetrics 经 vmselect 原始 `le` 标签查询返回的值与源码逐项一致，证明 VMAgent（30s 抓取，无桶处理）→ vminsert → vmstorage → vmselect / MonitorServer / 前端均不重定义桶——桶是 producer（vLLM 进程的 prometheus_client Histogram）在注册时固化的，监控链路全程透传。
>
> **当前场景失真警告**：GLM-5（大 TP、300k max_len）单次 KV offload 传输为 GB 量级，而**最大有限桶仅 200MB**，GB 级观测全部塌进 `+Inf` 桶。后果：`histogram_quantile` 算不出分位、退回返回最后一个有限桶 `le=2e8`（200MB）作为 cap 伪值，**P99.9/P95/P90/P50 分位图与 §1.7/1.8 热力图全部失真**（典型现象：P99.9 ≪ avg）；只有 `rate(_sum)/rate(_count)` 的均值与 `vllm:kv_offload_total_bytes_total` 字节总量可信。修复需在 vLLM fork 扩展 `TRANSFER_SIZE_BUCKETS` 覆盖 GB 量级（如补 5e8/1e9/2e9/5e9/1e10），重建 vLLM 镜像后 load_size/store_size/旧 size 直方图同时生效。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:kv_offload_size_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 byte，表示进程启动以来全部已观测传输的“单次 KV 卸载传输大小”累计总和。它没有 `le`，也不是平均值。

分位图中“均值”那条 query 以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单次传输大小。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type)`。

### `vllm:kv_offload_size_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 transfer，表示进程启动以来该 Histogram 记录的累计传输数。它没有 `le`，也不表示当前状态。

`_count` 是均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 无定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type)`。
