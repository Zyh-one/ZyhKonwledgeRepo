# 推理延迟 metric 指标

本文说明“推理延迟”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

> **组织说明**：以下 7 个 Histogram 家族按前端"推理延迟"区块的显示顺序排列（从左到右、从上到下），与 [PromQL.md](./PromQL.md) 的章节顺序一一对应：TTFT → Prefill → Decode → ITL → TPOT → 推理延迟 → E2E。每个家族对应前端一张图，图的 `ChartConfig.query` 同时包含该家族的分位查询（`histogram_quantile`，对 `_bucket` 用 `rate()`）与平均值查询（`rate(_sum)/rate(_count)`）。

## 1. TTFT 首 Token 延迟 Histogram 家族

`vllm:time_to_first_token_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 2. Prefill 阶段时长 Histogram 家族

`vllm:request_prefill_time_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 3. Decode 阶段时长 Histogram 家族

`vllm:request_decode_time_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 4. ITL Token 间隔延迟 Histogram 家族

`vllm:inter_token_latency_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 5. TPOT 每输出 Token 延迟 Histogram 家族

`vllm:request_time_per_output_token_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 6. 模型推理时长 Histogram 家族

`vllm:request_inference_time_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 7. 端到端请求延迟 Histogram 家族

`vllm:e2e_request_latency_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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
