http_requests_total {**cluster="bj-caip",**container="deepseekv4-flash-0-0-9",**endpoint="serve",**handler="/v1/messages",**instance="10.9.103.71:9100",**job="deepseek-v4-8r-dp2-0-0-1-serving",**label_id="7d0a22af-2f15-410f-b373-57e4368ce888",**label_name="deepseek-v4-8r-dp2",**label_role_name="standalone",**label_version="0.0.1",**label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",**method="POST",**namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",**pod="deepseek-v4-8r-dp2-0-0-1-roleset-wp2h5-standalone-6c57f8-0-1",**prometheus="monitoring/vmagent",**service="deepseek-v4-8r-dp2-0-0-1-serving",**status="2xx"**}

# 具体 metric 指标

本部分以原始 metric 为中心，说明类型、单位、标签身份、原始语义及当前 PromQL 的输出语义。`vllm:` 前缀可能来自 vLLM，也可能经过兼容层、重命名或 recording rule；最终口径应以当前服务 `/metrics` 的 HELP/TYPE 和对应版本代码为准。

## 1. 抓取与标签约定

vLLM 暴露样本，vmagent 定期写入 VictoriaMetrics，VMSelect 只在查询阶段执行 PromQL。`[%(time)s:30s]` 的 30 秒是子查询 resolution，不能据此判断抓取间隔或 vLLM 内部埋点周期。

业务实例至少由 `(cluster, namespace, pod)` 标识；仅用 `pod` 不能跨作用域唯一定位。同一 Pod 多引擎时还应保留 `engine`、`instance`。Histogram 的 `_bucket` 序列还必须包含 `le`。

## 2. `vllm:cache_config_info`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

配置型 Info/Gauge，通常以固定值 1 携带 KV Cache 或引擎配置标签。价值在标签而不在数值。

```
vllm:cache_config_info {_block_size_resolved="True",block_size="16",cache_dtype="auto",calculate_kv_scales="False",cluster="bj-caip",container="test-qwen-0-0-107",enable_prefix_caching="True",endpoint="serve",engine="0",gpu_memory_utilization="0.9",instance="10.8.159.228:8001",is_attention_free="False",job="qwen36-35b-0-0-1-serving",kv_cache_dtype_skip_layers="[]",kv_cache_memory_bytes="None",kv_offloading_backend="native",kv_offloading_size="None",kv_sharing_fast_prefill="False",label_id="02252861-093e-4474-b6dc-51e2f8898c39",label_name="qwen36-35b",label_role_name="standalone",label_version="0.0.1",label_version_id="9a5da0c1-aa36-45cb-9e8c-08d8b7c5a764",mamba_block_size="16",mamba_cache_dtype="auto",mamba_cache_mode="align",mamba_page_size_padded="None",mamba_ssm_cache_dtype="float32",namespace="ns-20a73d3287614958ac8d06fc41155c94",num_cpu_blocks="None",num_gpu_blocks="3991",num_gpu_blocks_override="None",pod="qwen36-35b-0-0-1-roleset-95r7f-standalone-sv7t9",prefix_caching_hash_algo="sha256",prometheus="monitoring/vmagent",service="qwen36-35b-0-0-1-serving",sliding_window="None",user_specified_block_size="False",user_specified_mamba_block_size="False"}
```

**唯一标识标签：** 至少使用 `(cluster, namespace, pod)`，再加实际配置或 engine 标签。

## 3. `http_requests_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 request，表示 HTTP 服务累计处理请求数。当前筛选 messages/completions 路由，用 `increase()` 得到窗口请求量；按 `status` 分组可观察 HTTP 状态。HTTP 状态不必然等同于模型业务成功，流式中断和网关重试要结合埋点判断。

```

http_requests_total {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",handler="/v1/messages",instance="10.9.103.71:9100",job="deepseek-v4-8r-dp2-0-0-1-serving",label_id="7d0a22af-2f15-410f-b373-57e4368ce888",label_name="deepseek-v4-8r-dp2",label_role_name="standalone",label_version="0.0.1",label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",method="POST",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-8r-dp2-0-0-1-roleset-wp2h5-standalone-6c57f8-0-1",prometheus="monitoring/vmagent",service="deepseek-v4-8r-dp2-0-0-1-serving",status="2xx"}
```

**唯一标识标签：** `(cluster, namespace, pod, handler, method, status)`；不存在的标签从组合中移除。

## 4. `vllm:request_success_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 request，表示被埋点记为成功完成的请求累计数。`finished_reason` 描述停止原因。当前所谓“成功率”实际是 stop/length 正常结束原因占比。

```
http_requests_total {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",handler="/v1/messages",instance="10.9.103.71:9100",job="deepseek-v4-8r-dp2-0-0-1-serving",label_id="7d0a22af-2f15-410f-b373-57e4368ce888",label_name="deepseek-v4-8r-dp2",label_role_name="standalone",label_version="0.0.1",label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",method="POST",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-8r-dp2-0-0-1-roleset-wp2h5-standalone-6c57f8-0-1",prometheus="monitoring/vmagent",service="deepseek-v4-8r-dp2-0-0-1-serving",status="2xx"}
```

**唯一标识标签：** `(cluster, namespace, pod, finished_reason)`，并保留 engine/model。

## 5. `vllm:num_requests_running`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，单位为 request，表示正在引擎中执行的请求数。窗口平均值是平均运行并发，不是完成请求数。升高表示同时服务更多请求，但是否改善吞吐需结合 Token/s、Queue 和时延。

```
vllm:num_requests_running {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",engine="0",instance="10.9.52.78:9100",job="deepseek-v4-8r-dp2-0-0-1-serving",label_id="7d0a22af-2f15-410f-b373-57e4368ce888",label_name="deepseek-v4-8r-dp2",label_role_name="standalone",label_version="0.0.1",label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",model_name="dsv4-flash",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-8r-dp2-0-0-1-roleset-bxq8d-standalone-6c57f8-0-0",prometheus="monitoring/vmagent",service="deepseek-v4-8r-dp2-0-0-1-serving"}
```

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`。

## 6. `vllm:num_requests_waiting`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，单位为 request，表示已进入调度系统但尚未运行的请求数。持续升高不回落通常说明负载超过服务能力，或资源/KV Cache/调度条件阻塞。

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`。

## 7. 请求排队时长 Histogram 家族

`vllm:request_queue_time_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

用于 Queue 分位数、平均值和排队分布分析。它与当前等待并发 Gauge 不同。

### `vllm:request_queue_time_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“排队时长小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

```promql
vllm:request_queue_time_seconds_bucket{cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",engine="0",instance="10.8.154.53:9100",job="deepseek-v4-dp2tp4-0-0-1-serving",label_id="fec724d9-5ac1-472f-87db-3da734ece1db",label_name="deepseek-v4-dp2tp4",label_role_name="standalone",label_version="0.0.1",label_version_id="013049a4-5e62-4307-a196-e0c66cb875ba",le="+Inf",model_name="dsv4-flash",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-dp2tp4-0-0-1-roleset-22t4h-standalone-54b9d4-0-0",prometheus="monitoring/vmagent",service="deepseek-v4-dp2tp4-0-0-1-serving"}
```

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_queue_time_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“排队时长”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均排队时长。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_queue_time_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 8. 单请求 Prompt Token 数 Histogram 家族

`vllm:request_prompt_tokens` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

用于输入长度分位数、平均值和热力图；它描述请求长度分布，不是窗口 Token 吞吐。

### `vllm:request_prompt_tokens_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“单请求 Prompt Token 数小于等于该上界”的累计请求数；`le` 的单位为 token。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

```promql
vllm:request_prompt_tokens_bucket {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",engine="0",instance="10.8.154.53:9100",job="deepseek-v4-dp2tp4-0-0-1-serving",label_id="fec724d9-5ac1-472f-87db-3da734ece1db",label_name="deepseek-v4-dp2tp4",label_role_name="standalone",label_version="0.0.1",label_version_id="013049a4-5e62-4307-a196-e0c66cb875ba",le="+Inf",model_name="dsv4-flash",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-dp2tp4-0-0-1-roleset-22t4h-standalone-54b9d4-0-0",prometheus="monitoring/vmagent",service="deepseek-v4-dp2tp4-0-0-1-serving"}
```

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_prompt_tokens_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 token，表示进程启动以来全部已观测请求的“单请求 Prompt Token 数”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单请求 Prompt Token 数。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_prompt_tokens_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 9. 单请求 Generation Token 数 Histogram 家族

`vllm:request_generation_tokens` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

用于输出长度分位数、平均值和热力图；受 EOS、stop、max_tokens、取消和异常结束影响。

### `vllm:request_generation_tokens_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“单请求实际生成 Token 数小于等于该上界”的累计请求数；`le` 的单位为 token。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_generation_tokens_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 token，表示进程启动以来全部已观测请求的“单请求实际生成 Token 数”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单请求实际生成 Token 数。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_generation_tokens_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 10. `vllm:prompt_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计输入 Token。`increase()` 得窗口总量，`rate()` 得输入 Token/s。Prefix Cache 命中时它统计全部逻辑 Token 还是实际计算部分取决于埋点；不能默认等于 Prefill 实际计算 Token。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/model。

## 11. `vllm:generation_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计输出 Token。`increase()` 得窗口总量，`rate()` 得输出 Token/s。输入和输出 Token 的计算成本不同，两者之和不是单一效率指标。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/model。

## 12. `kube_pod_container_resource_requests`

**黄区暴露来源：** `monitoring/Service kube-state-metrics` 的 `https-main` 端点；由 `monitoring/VMServiceScrape kube-state-metrics` 抓取。

kube-state-metrics 的 Gauge，表示容器声明的 Kubernetes Resource Request，不是实际使用量。当前取加速卡 Request 作为每卡 Token/s 分母。同一 Pod 可能有多个容器或资源序列，应精确限定 `resource` 并按 Pod 汇总。

**唯一标识标签：** `(cluster, namespace, pod, container, resource, unit)`；有 `uid` 时可区分同名重建 Pod。

## 13. TTFT 首 Token 延迟 Histogram 家族

`vllm:time_to_first_token_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

通常覆盖 Queue、Prefill 及部分调度/序列化开销，不包含到达 vLLM 前的网络与网关耗时。

### `vllm:time_to_first_token_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“服务端首 Token 延迟小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:time_to_first_token_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“服务端首 Token 延迟”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均服务端首 Token 延迟。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:time_to_first_token_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 14. 模型推理时长 Histogram 家族

`vllm:request_inference_time_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

当前业务注释近似解释为 Prefill + Decode，实际计时边界以埋点代码为准。

### `vllm:request_inference_time_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“请求的模型内部推理时长小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_inference_time_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“请求的模型内部推理时长”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均请求的模型内部推理时长。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_inference_time_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 15. ITL Token 间隔延迟 Histogram 家族

`vllm:inter_token_latency_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

一个请求通常贡献多次观测，长输出请求会贡献更多样本，因此它按 Token 间隔而非请求加权。

### `vllm:inter_token_latency_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 interval。它按照 `le` 记录“相邻输出 Token 的时间间隔小于等于该上界”的累计Token 间隔数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:inter_token_latency_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测Token 间隔的“相邻输出 Token 的时间间隔”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均相邻输出 Token 的时间间隔。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:inter_token_latency_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 interval，表示进程启动以来该 Histogram 记录的累计Token 间隔数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 16. TPOT 每输出 Token 延迟 Histogram 家族

`vllm:request_time_per_output_token_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

当前 PromQL 最后乘以 1000，展示单位为 ms/token。TPOT 是请求级观测，与逐 Token 间隔的 ITL 不同。

### `vllm:request_time_per_output_token_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“请求级每输出 Token 平均耗时小于等于该上界”的累计请求数；`le` 的单位为 seconds/token。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_time_per_output_token_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds/token，表示进程启动以来全部已观测请求的“请求级每输出 Token 平均耗时”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均请求级每输出 Token 平均耗时。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_time_per_output_token_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 17. 端到端请求延迟 Histogram 家族

`vllm:e2e_request_latency_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

通常覆盖 Queue、Prefill 和 Decode，但不包含客户端与上游网关之前的耗时。

### `vllm:e2e_request_latency_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“服务端从接收请求到完成的时长小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:e2e_request_latency_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“服务端从接收请求到完成的时长”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均服务端从接收请求到完成的时长。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:e2e_request_latency_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 18. `vllm:prefix_cache_hits_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 hit，累计本地 Prefix Cache 命中事件。命中次数不等于节省 Token 数，应结合 Prefill KV computed Token 与 TTFT。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/cache 层级。

## 19. `vllm:prefix_cache_queries_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 query，累计本地 Prefix Cache 查询事件，是本地命中率分母。一次事件按请求、Prefix 还是缓存块计数需由埋点确认；窗口无查询时命中率无定义。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/cache 层级。

## 20. `vllm:external_prefix_cache_hits_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 hit，累计外部 KV/Prefix Cache 命中事件。它与本地 hit 是否互斥，决定两者能否直接相加计算综合命中率。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/backend。

## 21. `vllm:external_prefix_cache_queries_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 query，累计外部 KV/Prefix Cache 查询事件，是外部命中率分母。值为 0 可能表示功能未启用、没有合格请求或采集缺失。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/backend。

## 22. `vllm:kv_cache_usage_perc`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，通常为 0～1，表示 KV Cache 已用容量比例；当前乘 100 展示百分比。必须用裸样本确认不是 0～100，避免重复换算。它是容量利用率，不是命中率。

**唯一标识标签：** `(cluster, namespace, pod, engine)`。

## 23. Prefill 阶段时长 Histogram 家族

`vllm:request_prefill_time_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

受输入长度、实际计算 KV Token、Prefix Cache 命中、Batch 形态和设备效率影响。

### `vllm:request_prefill_time_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“请求 Prefill 阶段耗时小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_prefill_time_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“请求 Prefill 阶段耗时”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均请求 Prefill 阶段耗时。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_prefill_time_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 24. Decode 阶段时长 Histogram 家族

`vllm:request_decode_time_seconds` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

同时受输出长度与单 Token 生成速度影响，应结合 Generation Tokens、TPOT/ITL 分析。

### `vllm:request_decode_time_seconds_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“请求 Decode 阶段累计耗时小于等于该上界”的累计请求数；`le` 的单位为 seconds。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_decode_time_seconds_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 seconds，表示进程启动以来全部已观测请求的“请求 Decode 阶段累计耗时”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均请求 Decode 阶段累计耗时。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_decode_time_seconds_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 25. `vllm:num_preemptions_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 preemption，表示调度器累计抢占次数。窗口增量大于 0 表示请求因 KV Cache 或调度资源压力被移出运行态；swap、recompute 等具体方式取决于引擎。

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`，有 reason 时保留。

## 26. Prefill 实际计算 KV Token 数 Histogram 家族

`vllm:request_prefill_kv_computed_tokens` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

不含被缓存直接复用的部分；与 Prompt Token 对比可观察 Prefix Cache 减少的实际计算量。

### `vllm:request_prefill_kv_computed_tokens_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“单请求 Prefill 阶段实际计算的 KV Token 数小于等于该上界”的累计请求数；`le` 的单位为 token。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_prefill_kv_computed_tokens_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 token，表示进程启动以来全部已观测请求的“单请求 Prefill 阶段实际计算的 KV Token 数”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单请求 Prefill 阶段实际计算的 KV Token 数。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_prefill_kv_computed_tokens_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 27. `vllm:spec_decode_num_accepted_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计被主模型接受的草稿 Token，是接受率分子。接受数量增加不等于同等比例加速，还取决于验证开销。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/speculator。

## 28. `vllm:spec_decode_num_draft_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计草稿模型提出的 Token，是接受率分母。窗口无 draft token 时接受率无定义；它必须与 accepted Counter 保留相同聚合维度。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/speculator。

## 29. `vllm:kv_offload_total_bytes_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 byte，表示 KV 卸载累计传输字节数。按 `transfer_type` 区分方向，`increase()` 得窗口总量；如需带宽应使用 `rate()`。双重 `total` 只是当前命名。

**唯一标识标签：** `(cluster, namespace, pod, transfer_type)`；有 backend/target 时保留。

## 30. 单次 KV 卸载传输大小 Histogram 家族

`vllm:kv_offload_size` 是本文用于称呼一组 Histogram 的逻辑家族名，**不是黄区实际暴露的 metric**。实际暴露并被前端查询的是下面三个带后缀的 Counter。

按 transfer_type 区分方向。它描述单次大小，不是窗口传输总量或 bytes/s 带宽。

### `vllm:kv_offload_size_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 transfer。它按照 `le` 记录“单次 KV 卸载传输大小小于等于该上界”的累计传输数；`le` 的单位为 byte。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:kv_offload_size_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 byte，表示进程启动以来全部已观测传输的“单次 KV 卸载传输大小”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单次 KV 卸载传输大小。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type)`。

### `vllm:kv_offload_size_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 transfer，表示进程启动以来该 Histogram 记录的累计传输数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, transfer_type)`。

## 31. 组合分析原则

- 吞吐下降：同时检查请求量、输入/输出 Token/s、请求长度和并发。
- TTFT 上升：拆分 Queue 与 Prefill。
- TPOT/ITL 上升：结合 Decode、运行并发、输出长度和抢占。
- KV Cache 高水位：结合 Waiting、Preemption、Prefix Cache 与 Offload。

不同 Histogram 的 P99 来自不同样本集合，不能直接相加或相减。
