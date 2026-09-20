# 缓存 metric 指标

本文说明“缓存”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

> **组织说明**：以下 metric 按前端“缓存”区块的显示顺序排列（综合 Prefix 缓存命中率 → Prefix 缓存命中次数 → Prefix 缓存命中率 → KV 缓存利用率），与 [PromQL.md](./PromQL.md) 的章节顺序一一对应。**“综合 Prefix 缓存命中率”一条图集成 3 个 metric**（外部命中 + 本地命中 + 本地查询），故合入同一标题；其余各图均为单 metric，各自独立成节。另有配置探针 `vllm:cache_config_info` 单列于首节。Prefill 实际计算 KV Token 数的 Histogram 家族不属于本区块（服务于“Token 消耗”区块），见 `Token 消耗/metric指标.md`。
>
> **口径提醒（重要）**：`vllm:prefix_cache_hits_total` / `vllm:prefix_cache_queries_total` 虽名含 “hits/queries”，但 vLLM 源码 documentation 明确为 “**in terms of number of cached tokens / queried tokens**”——即单位是 **token**，不是命中事件次数。命中率 = 命中 token 数 / 查询 token 数，是 token 级比例。

## 1. 配置探针 `vllm:cache_config_info`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

配置型 Info/Gauge，通常以固定值 1 携带 KV Cache 或引擎配置标签。价值在标签而不在数值，用于判定 Pod 是否为 vLLM 并读取 KV Cache 配置。

```
vllm:cache_config_info {_block_size_resolved="True",block_size="16",cache_dtype="auto",calculate_kv_scales="False",cluster="bj-caip",container="test-qwen-0-0-107",enable_prefix_caching="True",endpoint="serve",engine="0",gpu_memory_utilization="0.9",instance="10.8.159.228:8001",is_attention_free="False",job="qwen36-35b-0-0-1-serving",kv_cache_dtype_skip_layers="[]",kv_cache_memory_bytes="None",kv_offloading_backend="native",kv_offloading_size="None",kv_sharing_fast_prefill="False",label_id="02252861-093e-4474-b6dc-51e2f8898c39",label_name="qwen36-35b",label_role_name="standalone",label_version="0.0.1",label_version_id="9a5da0c1-aa36-45cb-9e8c-08d8b7c5a764",mamba_block_size="16",mamba_cache_dtype="auto",mamba_cache_mode="align",mamba_page_size_padded="None",mamba_ssm_cache_dtype="float32",namespace="ns-20a73d3287614958ac8d06fc41155c94",num_cpu_blocks="None",num_gpu_blocks="3991",num_gpu_blocks_override="None",pod="qwen36-35b-0-0-1-roleset-95r7f-standalone-sv7t9",prefix_caching_hash_algo="sha256",prometheus="monitoring/vmagent",service="qwen36-35b-0-0-1-serving",sliding_window="None",user_specified_block_size="False",user_specified_mamba_block_size="False"}
```

**唯一标识标签：** 至少使用 `(cluster, namespace, pod)`，再加实际配置或 engine 标签。

## 2. 综合 Prefix 缓存命中率图集成的 metric

前端“综合 Prefix 缓存命中率”图（`vllmPrefixCacheOverallHitsRatePerStep`）一条 PromQL 集成以下 3 个 Counter：分子 = 外部 KV 复用命中 + 本地 Prefix 命中，分母 = 本地查询。它们也分别服务于“命中次数”“命中率”两张图。

### `vllm:external_prefix_cache_hits_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计外部 KV 复用（KV connector 跨实例缓存共享）**命中的缓存 token 数**（vLLM 源码 documentation：`External prefix cache hits ... in terms of number of cached tokens.`）。仅参与“综合命中率”分子；它本身也是“外部缓存”区块各图的主 metric，详见 `外部缓存/metric指标.md`。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/cache 层级。

### `vllm:prefix_cache_hits_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计本地 Prefix Cache **命中的缓存 token 数**（vLLM 源码 documentation：`Prefix cache hits, in terms of number of cached tokens.`）。递增点 `counter_prefix_cache_hits[engine_idx].inc(scheduler_stats.prefix_cache_stats.hits)`。同时服务于本区块的“综合命中率”（分子）、“命中次数”（单值）、“命中率”（分子）三张图。**“命中次数”图展示的是命中 token 数，不是命中事件次数**；它与节省的算力相关，但不等于节省的 Prefill 计算量（后者见 `Token 消耗/metric指标.md` 的 Prefill KV computed 家族）。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/cache 层级。

### `vllm:prefix_cache_queries_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计本地 Prefix Cache **查询的 token 数**（vLLM 源码 documentation：`Prefix cache queries, in terms of number of queried tokens.`），是本地/综合命中率的分母。递增点 `counter_prefix_cache_queries[engine_idx].inc(scheduler_stats.prefix_cache_stats.queries)`。窗口无查询 token 时命中率无定义。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/cache 层级。

## 3. `vllm:kv_cache_usage_perc`（KV 缓存利用率图）

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，通常为 0～1，表示 KV Cache 已用容量比例；当前乘 100 展示百分比。必须用裸样本确认不是 0～100，避免重复换算。它是容量利用率，不是命中率。

**唯一标识标签：** `(cluster, namespace, pod, engine)`。
