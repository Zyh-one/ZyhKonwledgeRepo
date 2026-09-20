# 推理排队 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录“推理排队”类别的全部前端 PromQL。

## 1. PromQL 查询

### 1.1 `vllmRequestConcurrencyPerStep`

推理并发度 - 运行中的请求数 + 排队中的请求数

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  avg_over_time(
    vllm:num_requests_running{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
+
sum by (
  namespace,
  label_version%(groupPod)s
) (
  avg_over_time(
    vllm:num_requests_waiting{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.2 `vllmRequestConcurrencyRunningPerStep`

推理运行并发度 - 当前正在运行的请求数

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  avg_over_time(
    vllm:num_requests_running{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.3 `vllmRequestConcurrencyWaitingPerStep`

推理排队并发度 - 当前排队的请求数

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  avg_over_time(
    vllm:num_requests_waiting{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.4 `vllmRequestWaitingRatioPerStep`

推理排队率 - 排队请求数占运行中和排队请求数总和的比例

```promql
(
  sum(
    sum_over_time(
      vllm:num_requests_waiting{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  ) by (
    namespace,
    label_version%(groupPod)s
  )
  /
  (
    sum(
      sum_over_time(
        vllm:num_requests_running{
          cluster=~"%(cluster)s",
          namespace="%(namespace)s",
          pod=~"%(pod)s",
          label_version=~"%(version)s",
          label_id="%(labelID)s"%(labelRoleName)s
        }[%(time)s:30s]
      )
    ) by (
      namespace,
      label_version%(groupPod)s
    )
    +
    sum(
      sum_over_time(
        vllm:num_requests_waiting{
          cluster=~"%(cluster)s",
          namespace="%(namespace)s",
          pod=~"%(pod)s",
          label_version=~"%(version)s",
          label_id="%(labelID)s"%(labelRoleName)s
        }[%(time)s:30s]
      )
    ) by (
      namespace,
      label_version%(groupPod)s
    )
  )
)
*
100
```

### 1.5 `vllmRequestWaitingTimeTPPerStep`

推理排队延迟 - 请求在队列中的等待时间

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:request_queue_time_seconds_bucket{
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

### 1.6 `vllmRequestWaitingTimeAvgPerStep`

推理排队延迟平均值

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:request_queue_time_seconds_sum{
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
    vllm:request_queue_time_seconds_count{
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
平均总并发 = 平均 Running + 平均 Waiting
等待并发占比 = Waiting 样本和 / (Running 样本和 + Waiting 样本和)
Queue 平均值 = rate(queue_sum) / rate(queue_count)
```

等待并发占比不是“曾经排队的请求比例”；Queue Histogram 描述已观测请求的排队时长分布。
