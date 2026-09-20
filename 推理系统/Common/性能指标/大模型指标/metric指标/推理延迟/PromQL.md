# 推理延迟 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录"推理延迟"类别的全部前端 PromQL。

> **组织说明**：前端"推理延迟"区块的 7 张图按从左到右、从上到下的显示顺序排列（对应 `llmservice-monitor-graph.component.html` 的 `monitor.inferenceLatency` 区块）。**每张图对应一个 `ChartConfig`，其 `query` 数组同时包含分位查询（`histogram_quantile`）与平均值查询**——前端用 `%(tp)s` 把分位查询实例化为 P999/P95/P90/P50 四条曲线，再加一条 AVG 曲线，共 5 条线绘于同一图。因此下文每节把这两条 PromQL 归在同一标题下。

## 1. PromQL 查询

### 1.1 TTFT 首字延迟

TTFT 首字延迟（Queue + Prefill，从请求入队到首 Token 产出的耗时）。对应前端图 `monitor.ttftLatency`，config `vllmTTFTTPPerStepConfig`。

**分位延迟** `vllmTTFTTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:time_to_first_token_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmTTFTAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:time_to_first_token_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:time_to_first_token_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.2 Prefill 延迟

Prefill 阶段延迟（Prompt 处理/KV 计算阶段耗时，不含排队）。对应前端图 `monitor.prefillLatency`，config `vllmPrefillTimeTPPerStepConfig`。

**分位延迟** `vllmPrefillTimeTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_prefill_time_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmPrefillTimeAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_prefill_time_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_prefill_time_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.3 Decode 延迟

Decode 阶段延迟（生成阶段总耗时，不含 Prefill 与排队）。对应前端图 `monitor.decodeLatency`，config `vllmDecodeTimeTPPerStepConfig`。

**分位延迟** `vllmDecodeTimeTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_decode_time_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmDecodeTimeAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_decode_time_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_decode_time_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.4 ITL 输出间隔延迟

ITL（Inter-Token Latency，Decode 阶段相邻 Token 间的产出间隔）。对应前端图 `monitor.itlLatency`，config `vllmITLTPPerStepConfig`。

**分位延迟** `vllmITLTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:inter_token_latency_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmITLAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:inter_token_latency_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:inter_token_latency_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.5 TPOT 每输出 Token 延迟

TPOT（Time Per Output Token，每生成一个 Token 的平均耗时）。对应前端图 `monitor.tpotLatency`，config `vllmTPOTTPPerStepConfig`。注意末尾 `* 1000`，将秒换算为毫秒展示。

**分位延迟** `vllmTPOTTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_time_per_output_token_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
*
1000
```

**平均延迟** `vllmTPOTAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_time_per_output_token_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_time_per_output_token_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
*
1000
```

### 1.6 推理延迟

推理延迟（Prefill + Decode，模型内部推理执行时间，不含排队与首 Token 之后的网络传输）。对应前端图 `monitor.inferenceLatencyDetail`，config `vllmInferenceTPPerStepConfig`。

**分位延迟** `vllmInferenceTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_inference_time_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmInferenceAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_inference_time_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_inference_time_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.7 端到端延迟

端到端延迟（Queue + Prefill + Decode，请求从入队到生成完成的完整耗时）。对应前端图 `monitor.e2eLatency`，config `vllmE2ELatencyTPPerStepConfig`。

**分位延迟** `vllmE2ELatencyTPPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:e2e_request_latency_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

**平均延迟** `vllmE2ELatencyAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:e2e_request_latency_seconds_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:e2e_request_latency_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

## 2. 查询关系

```text
请求 → Queue → Prefill → 首 Token → Decode → 完成
               └──── TTFT ────┘
       └────────── E2E ────────────┘
```

这些是业务近似关系。不同 Histogram 的 P99 来自不同样本集合，不能直接相加。

> **前端展示说明**：上述 7 张图在前端"推理延迟"区块的排列顺序为 TTFT → Prefill → Decode → ITL → TPOT → 推理延迟 → E2E（从左到右、从上到下）。每张图的 `ChartConfig.query` 同时包含分位查询与平均值查询，前端将分位查询按 P999/P95/P90/P50 渲染为 4 条曲线、平均值查询渲染为 1 条 AVG 曲线，共 5 条线。各查询共用 `[%(time)s:30s]` 子查询窗口与 `%(groupPod)s` 分组维度，区别仅在Histogram 指标名与是否 `* 1000`。
