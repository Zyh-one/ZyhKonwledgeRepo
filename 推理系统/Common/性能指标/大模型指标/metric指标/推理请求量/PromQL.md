# 推理请求量 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录“推理请求量”类别的全部前端 PromQL。

## 1. PromQL 查询

### 1.1 `vllmRequestPerStep`

推理请求量

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    http_requests_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      handler=~".*(messages|completions).*"
    }[%(time)s:30s]
  )
)
```

### 1.2 `vllmSuccessRequestPerStep`

成功推理量 - 服务在指定时间窗口内实际成功的推理请求数

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:request_success_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.3 `vllmRequestSuccessRatioPerStep`

推理成功率 - 成功完成的请求数占所有结束请求数的比例

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:request_success_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      finished_reason=~"stop|length"
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:request_success_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
*
100
```

### 1.4 `vllmHttpRequestStatusPerStep`

Http 请求状态数量 - 4xx 和 5xx 错误数量

```promql
sum by (
  namespace,
  label_version,
  status%(groupPod)s
) (
  increase(
    http_requests_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      handler=~".*(messages|completions).*",
      status="%(status)s"
    }[%(time)s:30s]
  )
)
```

### 1.5 `vllmNumPreemptionsTotalPerStep`

抢占请求数

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:num_preemptions_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.6 `vllmSpecDecodeAcceptanceRatePerStep`

投机采样接受率 - MTP 草稿模型预测 Token 被主模型接受的比例

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:spec_decode_num_accepted_tokens_total{
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
  increase(
    vllm:spec_decode_num_draft_tokens_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
*
100
```

## 2. 查询关系

```text
HTTP 请求进入量 → vLLM 成功完成量 → 正常结束原因占比
                    └→ 按 HTTP status 观察错误数量
调度抢占事件     → 窗口抢占请求数
accepted/draft  → 投机采样接受率
```

当前所谓“推理成功率”实际是 `request_success_total` 中 `finished_reason=stop|length` 的占比，不是真正的成功请求/全部请求。
