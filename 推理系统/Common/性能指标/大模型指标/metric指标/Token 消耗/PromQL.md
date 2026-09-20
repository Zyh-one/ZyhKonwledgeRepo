# Token 消耗 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录“Token 消耗”类别的全部前端 PromQL。

> **组织说明**：前端"Token 消耗"区块共 11 张图，按从左到右、从上到下的显示顺序排列（对应 `llmservice-monitor-graph.component.html` 的 `monitor.tokenConsumption` 区块）。**分布类图（输入/Prefill KV/输出 Token 数量分布）的 `ChartConfig.query` 同时包含分位查询（`histogram_quantile`，实例化为 P999/P95/P90/P50）与平均值查询**，故合入同一标题；热力图与各消耗量/每卡每秒图为单查询，各自独立成节。

## 1. PromQL 查询

### 1.1 输入 Token 数量分位（每请求）

每个推理请求的 Prompt Token 数量分布。对应前端图 `monitor.promptTokenDistribution`，config `vllmRequestPromptTokenPerStepConfig`。

**分位** `vllmRequestPromptTokenPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_prompt_tokens_bucket{
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

**平均值** `vllmRequestPromptTokenAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_prompt_tokens_sum{
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
    vllm:request_prompt_tokens_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.2 输入 Token 分布热力图

请求 Prompt Token 的原始分布情况（Heatmap）。对应前端图 `monitor.promptTokenHeatmap`，config `vllmRequestPromptTokenHeatmapConfig`。

```promql
sum by (
  namespace,
  label_version,
  le%(groupPod)s
) (
  increase(
    vllm:request_prompt_tokens_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.3 Prefill 计算的 KV Token 数量分位（每请求）

记录每个请求在 Prefill 阶段**实际计算的 KV 缓存 Token 数量（不含缓存命中部分）**的分布。对应前端图 `monitor.prefillKVComputedTokensDistribution`，config `vllmRequestPrefillKVComputedTokensPerStepConfig`。

> 注：该家族的 PromQL 模板中**不带 `%(labelRoleName)s` 占位符**（与输入/输出 Token 家族不同），label 选择器以 `label_id="%(labelID)s"` 结尾，下同。

**分位** `vllmRequestPrefillKVComputedTokensPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_prefill_kv_computed_tokens_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"
      }[%(time)s:30s]
    )
  )
)
```

**平均值** `vllmRequestPrefillKVComputedTokensAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_prefill_kv_computed_tokens_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_prefill_kv_computed_tokens_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"
    }[%(time)s:30s]
  )
)
```

### 1.4 Prefill 计算的 KV Token 分布热力图

Prefill 阶段实际计算的 KV Token 的原始分布情况（Heatmap）。对应前端图 `monitor.prefillKVComputedTokensHeatmap`，config `vllmRequestPrefillKVComputedTokensHeatmapConfig`。

```promql
sum by (
  namespace,
  label_version,
  le%(groupPod)s
) (
  increase(
    vllm:request_prefill_kv_computed_tokens_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"
    }[%(time)s:30s]
  )
)
```

### 1.5 消耗输入 Token 量

实际处理的所有 Prompt Token 总数（即用户提示词）。对应前端图 `monitor.promptTokenThroughput`，config `vllmPromptTokenPerStepConfig`。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prompt_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.6 每卡每秒消耗输入 Token 量

实际处理的 Prompt Token 总数按申请卡数归一化的速率（Token/(card·s)）。对应前端图 `monitor.promptTokenPerCardPerSecond`，config `vllmPromptTokenPerCardPerSecondPerStepConfig`。

```promql
sum(
  rate(
    vllm:prompt_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
  /
  on (pod) group_left()
  kube_pod_container_resource_requests{
    cluster=~"%(cluster)s",
    namespace="%(namespace)s",
    pod=~"%(pod)s",
    resource=~".*(cambricon|nvidia).*"
  }
) by (
  namespace,
  label_version%(groupPod)s
)
```

### 1.7 输出 Token 数量分位（每请求）

每个推理请求的 Generation Token 数量分布。对应前端图 `monitor.generationTokenDistribution`，config `vllmRequestGenerationTokenPerStepConfig`。

**分位** `vllmRequestGenerationTokenPerStep`（`%(tp)s` 实例化为 0.999/0.95/0.90/0.5）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_generation_tokens_bucket{
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

**平均值** `vllmRequestGenerationTokenAvgPerStep`：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_generation_tokens_sum{
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
    vllm:request_generation_tokens_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.8 输出 Token 分布热力图

请求 Generation Token 的原始分布情况（Heatmap）。对应前端图 `monitor.generationTokenHeatmap`，config `vllmRequestGenerationTokenHeatmapConfig`。

```promql
sum by (
  namespace,
  label_version,
  le%(groupPod)s
) (
  increase(
    vllm:request_generation_tokens_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.9 消耗输出 Token 量

实际生成的所有 Generation Token 总数（即模型回答）。对应前端图 `monitor.generationTokenThroughput`，config `vllmDecodeTokenPerStepConfig`。

> 注：该图 config 名为 `vllmDecodeTokenPerStepConfig`，但其 `query` 实际引用的常量是 `vllmGenerationTokenPerStep`（与下图标语义一致，仅命名沿用 Decode 旧称）。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:generation_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.10 每卡每秒消耗输出 Token 量

实际生成的 Generation Token 总数按申请卡数归一化的速率（Token/(card·s)）。对应前端图 `monitor.generationTokenPerCardPerSecond`，config `vllmGenerationTokenPerCardPerSecondPerStepConfig`。

```promql
sum(
  rate(
    vllm:generation_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
  /
  on (pod) group_left()
  kube_pod_container_resource_requests{
    cluster=~"%(cluster)s",
    namespace="%(namespace)s",
    pod=~"%(pod)s",
    resource=~".*(cambricon|nvidia).*"
  }
) by (
  namespace,
  label_version%(groupPod)s
)
```

### 1.11 消耗 Token 量

包含输入和输出的 Token 总数。对应前端图 `monitor.tokenThroughput`，config `vllmTokenPerStepConfig`。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prompt_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
  +
  increase(
    vllm:generation_tokens_total{
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
request_*_tokens Histogram           → 单请求长度分布（分位/热力图）
request_prefill_kv_computed_tokens   → 单请求 Prefill 实际计算 KV 长度（不含缓存命中）
*_tokens_total Counter               → 窗口 Token 总量（increase）或 Token/s（rate）
Token/s ÷ 申请卡数                    → Token/(card·s)
prompt_total + generation_total      → 消耗 Token 总量
```

输入与输出 Token 的计算成本不同，总 Token/s 不应单独作为统一算力效率。Prefill 计算的 KV Token 是 Prompt Token 中"实际进入计算"的子集，与 `prompt_tokens_total`（逻辑总量）口径不同，不可直接相减比较。
