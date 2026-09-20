# 大模型性能指标 PromQL 分析

前端指标由原始 vLLM/HTTP metric、时间统计、标签聚合和跨 metric 计算组成。通用规则见 [PromQL 统计范式](../PromQL统计范式.md)，本文只说明每组查询采用什么范式，以及最终得到什么业务量。

原始PromQL语句

```TypeScript
export const vllmConfigInfo = `
vllm:cache_config_info{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  label_id="%(labelID)s"%(labelRoleName)s
}
`;

// 推理请求量
export const vllmRequestPerStep = `
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
`;

// 成功推理量 - 服务在指定时间窗口内实际成功的推理请求数
export const vllmSuccessRequestPerStep = `
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
`;

// 推理并发度 - 运行中的请求数 + 排队中的请求数
export const vllmRequestConcurrencyPerStep = `
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
`;

// 推理运行并发度 - 当前正在运行的请求数
export const vllmRequestConcurrencyRunningPerStep = `
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
`;

// 推理排队并发度 - 当前排队的请求数
export const vllmRequestConcurrencyWaitingPerStep = `
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
`;

// 推理排队率 - 排队请求数占运行中和排队请求数总和的比例
export const vllmRequestWaitingRatioPerStep = `
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
* 100
`;

// 推理排队延迟 - 请求在队列中的等待时间
export const vllmRequestWaitingTimeTPPerStep = `
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
`;

// 推理排队延迟平均值
export const vllmRequestWaitingTimeAvgPerStep = `
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
`;

// 推理成功率 - 成功完成的请求数占所有结束请求数的比例
export const vllmRequestSuccessRatioPerStep = `
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
* 100
`;

// 输入 Token 数量分位 - 每个推理请求的 Prompt Token 数量分布
export const vllmRequestPromptTokenPerStep = `
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
`;

// 输入 Token 数量平均值
export const vllmRequestPromptTokenAvgPerStep = `
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
`;

// 输出 Token 数量分位 - 每个推理请求的 Generation Token 数量分布
export const vllmRequestGenerationTokenPerStep = `
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
`;

// 输出 Token 数量平均值
export const vllmRequestGenerationTokenAvgPerStep = `
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
`;

// 输入 Token 消耗量 - 实际处理的所有 Prompt Token 总数（即用户提示词）
export const vllmPromptTokenPerStep = `
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
`;

// 输入 Token 消耗量每卡每秒 - 实际处理的所有 Prompt Token 总数（即用户提示词）
export const vllmPromptTokenPerCardPerSecondPerStep = `
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
  on (pod)
  group_left()
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
`;

// 输出 Token 消耗量 - 实际生成的所有 Generation Token 总数（即模型回答）
export const vllmGenerationTokenPerStep = `
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
`;

// 输出 Token 消耗量每卡每秒 - 实际处理的所有 Generation Token 总数（即模型回答）
export const vllmGenerationTokenPerCardPerSecondPerStep = `
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
  on (pod)
  group_left()
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
`;

// Token 消耗总量 - 包含输入和输出的 Token 总数
export const vllmTokenPerStep = `
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
`;

// TTFT 首字延迟 - 首字延迟（Queue+Prefill）
export const vllmTTFTTPPerStep = `
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
`;

// TTFT 首字延迟平均值
export const vllmTTFTAvgPerStep = `
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
`;

// 推理延迟 - 推理延迟（Prefill + Decode，模型内部推理执行时间）
export const vllmInferenceTPPerStep = `
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
`;

// 推理延迟平均值
export const vllmInferenceAvgPerStep = `
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
`;

// ITL 输出间隔延迟 - Token 间延迟（Decode）
export const vllmITLTPPerStep = `
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
`;

// ITL 输出间隔延迟平均值
export const vllmITLAvgPerStep = `
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
`;

// TPOT 每输出 Token 延迟
export const vllmTPOTTPPerStep = `
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
* 1000
`;

// TPOT 每输出 Token 延迟平均值
export const vllmTPOTAvgPerStep = `
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
* 1000
`;

// 端到端延迟 - 端到端延迟（Queue+Prefill+Decode）
export const vllmE2ELatencyTPPerStep = `
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
`;

// 端到端延迟平均值
export const vllmE2ELatencyAvgPerStep = `
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
`;

// 综合 Prefix 缓存命中率 - 外部 KV 复用命中与本地 Prefix 缓存命中之和占查询总数的比例
export const vllmPrefixCacheOverallHitsRatePerStep = `
(
  sum by (
    namespace,
    label_version%(groupPod)s
  ) (
    increase(
      vllm:external_prefix_cache_hits_total{
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
    increase(
      vllm:prefix_cache_hits_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
* 100
`;

// Prefix 缓存命中次数 - KV 复用命中次数
export const vllmPrefixCacheHitsPerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_hits_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
`;

// Prefix 缓存命中率 - KV 复用命中率
export const vllmPrefixCacheHitsRatePerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_hits_total{
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
    vllm:prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
* 100
`;

// KV 缓存利用率
export const vllmKVUsagePercPerStep = `
avg by (
  namespace,
  label_version,
  engine%(groupPod)s
) (
  avg_over_time(
    vllm:kv_cache_usage_perc{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
* 100
`;

// Prefill 延迟 - Prefill 阶段延迟
export const vllmPrefillTimeTPPerStep = `
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
`;

// Prefill 延迟平均值
export const vllmPrefillTimeAvgPerStep = `
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
`;

// Decode 延迟 - Decode 阶段延迟
export const vllmDecodeTimeTPPerStep = `
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
`;

// Decode 延迟平均值
export const vllmDecodeTimeAvgPerStep = `
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
`;

// Http 请求状态数量 - 4xx 和 5xx 错误数量
export const vllmHttpRequestStatusPerStep = `
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
`;

// Prompt Token 数量分布热力图 - 用于展示请求 Prompt Token 的原始分布情况 (Heatmap)
export const vllmRequestPromptTokenBucketPerStep = `
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
`;

// Generation Token 数量分布热力图 - 用于展示请求 Generation Token 的原始分布情况 (Heatmap)
export const vllmRequestGenerationTokenBucketPerStep = `
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
`;

// 抢占请求数
export const vllmNumPreemptionsTotalPerStep = `
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
`;

// Prefill 计算的 KV Token 数量分位 - 记录每个请求在 Prefill 阶段实际计算的 KV 缓存 Token 数量（不含缓存命中部分）
export const vllmRequestPrefillKVComputedTokensPerStep = `
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
        label_id="%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
`;

// Prefill 计算的 KV Token 数量平均值
export const vllmRequestPrefillKVComputedTokensAvgPerStep = `
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
    vllm:request_prefill_kv_computed_tokens_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
`;

// Prefill 计算的 KV Token 数量分布热力图 - 用于展示 Prefill 阶段实际计算的 KV Token 分布 (Heatmap)
export const vllmRequestPrefillKVComputedTokensBucketPerStep = `
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
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
`;

// 投机采样接受率 - MTP 草稿模型预测 Token 被主模型接受的比例
export const vllmSpecDecodeAcceptanceRatePerStep = `
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
* 100
`;

// KV 卸载传输字节数 - 统计 KV 卸载的字节总数，按 transferType 参数区分传输方向
export const vllmKVOffloadTotalBytesPerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:kv_offload_total_bytes_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="%(transferType)s"
    }[%(time)s:30s]
  )
)
`;

// KV 卸载传输大小分位 - 每次 KV 卸载传输的数据大小分布，按 transferType 参数区分传输方向
export const vllmKVOffloadSizeTPPerStep = `
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:kv_offload_size_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s,
        transfer_type="%(transferType)s"
      }[%(time)s:30s]
    )
  )
)
`;

// KV 卸载传输大小平均值，按 transferType 参数区分传输方向
export const vllmKVOffloadSizeAvgPerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:kv_offload_size_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="%(transferType)s"
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:kv_offload_size_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="%(transferType)s"
    }[%(time)s:30s]
  )
)
`;

// KV 卸载传输大小分布热力图 - 用于展示 KV 卸载每次传输大小的原始分布情况 (Heatmap)，按 transferType 参数区分传输方向
export const vllmKVOffloadSizeBucketPerStep = `
sum by (
  namespace,
  label_version,
  le%(groupPod)s
) (
  increase(
    vllm:kv_offload_size_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="%(transferType)s"
    }[%(time)s:30s]
  )
)
`;

// External Prefix 缓存命中次数 - 外部 KV 复用命中次数
export const vllmExternalPrefixCacheHitsPerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:external_prefix_cache_hits_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
`;

// External Prefix 缓存命中率 - 外部 KV 复用命中率
export const vllmExternalPrefixCacheHitsRatePerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:external_prefix_cache_hits_total{
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
    vllm:external_prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
* 100
`;

// External Prefix 缓存查询次数 - 用于判断是否开启外部缓存功能
export const vllmExternalPrefixCacheQueriesPerStep = `
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:external_prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
`;
```

## 1. 公共筛选与聚合维度

查询普遍通过 `cluster`、`namespace`、`pod`、`label_version`、`label_id` 和可选角色标签筛选，并至少按 `namespace`、`label_version` 聚合。`%(groupPod)s` 决定是否保留 Pod，`%(tp)s` 是分位参数，`%(time)s` 是每个图表点向前读取的统计窗口。

这些模板参数不是原始 metric。`[%(time)s:30s]` 中的 30 秒是子查询 resolution，不是 vLLM 内部窗口或 vmagent 抓取间隔。`vllmConfigInfo` 只选择 `vllm:cache_config_info` 的配置标签，不做时间聚合。

## 2. 窗口增量：请求、Token 与事件总量

以下查询对 Counter 使用 `increase()`：

- `vllmRequestPerStep`：HTTP messages/completions 请求量。
- `vllmSuccessRequestPerStep`：成功完成请求量。
- `vllmPromptTokenPerStep`、`vllmGenerationTokenPerStep`、`vllmTokenPerStep`：输入、输出及总 Token 增量。
- `vllmPrefixCacheHitsPerStep`、`vllmExternalPrefixCacheHitsPerStep`、`vllmExternalPrefixCacheQueriesPerStep`：缓存事件次数。
- `vllmHttpRequestStatusPerStep`：按 HTTP status 分组的请求数。
- `vllmNumPreemptionsTotalPerStep`：抢占次数。
- `vllmKVOffloadTotalBytesPerStep`：按 transfer_type 筛选的 KV 卸载总字节数。

结果是窗口总量，不是每秒速率。比较不同长度窗口时应使用 `rate()`，或除以窗口秒数。

## 3. Gauge：并发度与 KV Cache 利用率

Running 和 Waiting 查询分别对运行、等待请求数执行 `avg_over_time()`；总并发度再把两者相加。因此图中是窗口平均并发，不是求值时刻瞬时值。

KV Cache 查询对 `vllm:kv_cache_usage_perc` 求窗口平均，保留 `engine` 后乘以 100。只有裸值确实为 0～1 时，结果才是百分数。

## 4. 等待并发占比

`vllmRequestWaitingRatioPerStep` 计算 Waiting 样本值之和除以 Running 与 Waiting 样本值之和。它表示等待并发在总并发中的时间加权占比，不能回答“有多少请求曾进入队列”。两者都为 0 时结果没有定义。

## 5. Histogram 分位数与平均值

以下 TP 查询采用 `rate(_bucket)`、按 `le` 聚合，再执行 `histogram_quantile()`：

- Queue、TTFT、Inference、ITL、TPOT、E2E、Prefill、Decode。
- 单请求 Prompt Token、Generation Token、Prefill KV computed Token。
- 单次 KV offload size。

TPOT 额外乘 1000，单位由 seconds/token 变为 ms/token。跨 Pod 聚合得到合并后全部观测的分位数，不是各 Pod 分位数的平均值。

对应 Avg 查询均以 `rate(_sum) / rate(_count)` 求观测次数加权平均。窗口无新观测时平均值没有定义。

## 6. Histogram 热力图

Prompt Token、Generation Token、Prefill KV computed Token 和 KV offload size 的 Bucket 查询对 `_bucket` 使用 `increase()` 并保留 `le`。结果仍是累计桶；前端是否转换为非累计区间需要结合热力图组件确认。

## 7. 比率指标

本地/外部 Prefix Cache 命中率和投机解码接受率都以窗口内分子 Counter 增量除以分母增量。

综合 Prefix 命中率把 external hit 与 local hit 相加后除以 local query。只有两个 hit 互斥且属于同一 query 口径时才成立；否则会重复计数或超过 100%。已有 external query Counter 时，应先确认产品定义再决定综合分母。

“推理成功率”的分母仍是 `request_success_total`，分子只筛选 `finished_reason=~"stop|length"`。因此它实际是“正常结束原因占比”，不是成功请求占全部请求的比例。真正的成功率需要覆盖成功与失败的统一完成请求 Counter。

## 8. 每卡每秒 Token

两个 PerCardPerSecond 查询先用 `rate()` 得到 Pod Token/s，再除以 Kubernetes 资源请求中的申请卡数，目标单位为 `token/(card·s)`。当前只按 `pod` 关联且 resource 正则宽泛，建议改为精确卡资源名，并用 `on(cluster, namespace, pod)` 关联按 Pod 汇总后的卡数。

## 9. 主要关系

```text
请求到达 → Queue → Prefill ──首 Token──→ Decode ──后续 Token──→ 完成

TTFT ≈ Queue + Prefill + 其他首包开销
Inference ≈ Prefill + Decode（以埋点边界为准）
E2E ≈ Queue + Inference + 其他处理开销
```

这些是业务近似关系，不能要求不同 Histogram 的 Avg 或 P99 严格相加；“各阶段 P99 之和”不等于“端到端 P99”。

`request_*_tokens` Histogram 描述单请求长度分布，`*_tokens_total` Counter 描述窗口 Token 总量。
