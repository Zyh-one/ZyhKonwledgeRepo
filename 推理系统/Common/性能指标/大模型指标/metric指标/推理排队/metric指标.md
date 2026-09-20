# 推理排队 metric 指标

本文说明“推理排队”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

## 1. `vllm:num_requests_running`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，单位为 request，表示正在引擎中执行的请求数。窗口平均值是平均运行并发，不是完成请求数。升高表示同时服务更多请求，但是否改善吞吐需结合 Token/s、Queue 和时延。

```
vllm:num_requests_running {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",engine="0",instance="10.9.52.78:9100",job="deepseek-v4-8r-dp2-0-0-1-serving",label_id="7d0a22af-2f15-410f-b373-57e4368ce888",label_name="deepseek-v4-8r-dp2",label_role_name="standalone",label_version="0.0.1",label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",model_name="dsv4-flash",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-8r-dp2-0-0-1-roleset-bxq8d-standalone-6c57f8-0-0",prometheus="monitoring/vmagent",service="deepseek-v4-8r-dp2-0-0-1-serving"}
```

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`。

## 2. `vllm:num_requests_waiting`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Gauge，单位为 request，表示已进入调度系统但尚未运行的请求数。持续升高不回落通常说明负载超过服务能力，或资源/KV Cache/调度条件阻塞。

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`。

## 3. 请求排队时长 Histogram 家族

`vllm:request_queue_time_seconds` 只是本组 Histogram 的逻辑家族名，不是黄区实际暴露的 metric。

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
