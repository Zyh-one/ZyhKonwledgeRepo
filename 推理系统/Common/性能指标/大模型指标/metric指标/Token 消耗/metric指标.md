# Token 消耗 metric 指标

本文说明“Token 消耗”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

> **组织说明**：以下 metric 家族按前端"Token 消耗"区块的显示顺序排列（从左到右、从上到下），与 [PromQL.md](./PromQL.md) 的章节顺序一一对应：输入 Token 分布 → Prefill KV 计算分布 → 消耗输入 Token → 每卡每秒 → 输出 Token 分布 → 消耗输出 Token。Histogram 家族（带 `_bucket`/`_sum`/`_count`）服务于"分布/分位/热力图"类图；Counter/Gauge 服务于"消耗量/每卡每秒"类图。

## 1. 单请求 Prompt Token 数 Histogram 家族

`vllm:request_prompt_tokens` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 2. 单请求 Prefill 计算的 KV Token 数 Histogram 家族

`vllm:request_prefill_kv_computed_tokens` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。该家族记录的是 Prefill 阶段**实际进入计算的 KV Token 数**（不含缓存命中部分），与 `prompt_tokens_total` 的逻辑总量口径不同。

> 注：该家族对应 PromQL 模板中**不带 `%(labelRoleName)s` 占位符**（label 选择器以 `label_id` 结尾），与输入/输出 Token 家族略有差异。

### `vllm:request_prefill_kv_computed_tokens_bucket`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Bucket Counter，metric 值的单位为 request。它按照 `le` 记录“单请求 Prefill 阶段实际计算的 KV Token 数小于等于该上界”的累计请求数；`le` 的单位为 token。

`le` 是累计桶上界，`le="+Inf"` 包含全部观测，其值通常与相同标签维度的 `_count` 相等。当前分位数查询对它使用 `rate()`，热力图查询对它使用 `increase()`。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name, le)`；若某些标签在裸样本中不存在，应从组合中移除。

### `vllm:request_prefill_kv_computed_tokens_sum`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Sum Counter，单位为 token，表示进程启动以来全部已观测请求的“单请求 Prefill 阶段实际计算的 KV Token 数”累计总和。它没有 `le`，也不是平均值。

当前平均值查询以 `rate(_sum) / rate(_count)` 计算窗口内新增观测的加权平均单请求 Prefill 实际计算 KV Token 数。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

### `vllm:request_prefill_kv_computed_tokens_count`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Histogram 的 Count Counter，单位为 request，表示进程启动以来该 Histogram 记录的累计请求数。它没有 `le`，也不表示当前状态。

`_count` 是平均值计算的分母。窗口内 `rate(_count)=0` 时没有新增观测，`rate(_sum)/rate(_count)` 没有定义。

**唯一标识标签：** `(cluster, namespace, pod, engine, model_name)`。

## 3. `vllm:prompt_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计输入 Token。`increase()` 得窗口总量，`rate()` 得输入 Token/s。Prefix Cache 命中时它统计全部逻辑 Token 还是实际计算部分取决于埋点；不能默认等于 Prefill 实际计算 Token（后者见 §2 家族）。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/model。

## 4. `kube_pod_container_resource_requests`

**黄区暴露来源：** `monitoring/Service kube-state-metrics` 的 `https-main` 端点；由 `monitoring/VMServiceScrape kube-state-metrics` 抓取。

kube-state-metrics 的 Gauge，表示容器声明的 Kubernetes Resource Request，不是实际使用量。当前取加速卡 Request 作为每卡 Token/s 分母。同一 Pod 可能有多个容器或资源序列，应精确限定 `resource` 并按 Pod 汇总。

**唯一标识标签：** `(cluster, namespace, pod, container, resource, unit)`；有 `uid` 时可区分同名重建 Pod。

## 5. 单请求 Generation Token 数 Histogram 家族

`vllm:request_generation_tokens` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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

## 6. `vllm:generation_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计输出 Token。`increase()` 得窗口总量，`rate()` 得输出 Token/s。输入和输出 Token 的计算成本不同，两者之和不是单一效率指标。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/model。
