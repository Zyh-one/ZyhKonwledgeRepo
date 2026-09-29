# 推理请求量 PromQL（metric 语义整合版）

本文依据 `llm-query.constant.ts` 中的业务注释，收录"推理请求量"类别的全部前端 PromQL，并已将原 [metric指标.md](./metric指标.md) 中各 metric 的类型、来源、口径与判读说明**整合到对应查询下方**——查看指标时无需再在两份文档间切换。

**抓取链路（适用于本类全部 metric）：** vLLM/HTTP metric 由模型实例自己的 `*-serving` Service 经名为 `serve` 的端口转发到 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取；`label_id`/`label_role_name` 等平台身份标签由 vmagent 从 pod 标签 relabel 注入，metric 原始样本本身不携带。Kubernetes 资源指标的来源在对应小节单独说明。

> **关于各"经典实例"**：均取自集群真实序列（2026-09-29 经 VmSelect 只读查询 `last_over_time(<metric>[30d])`，数值为该序列最后一个样本的 counter 读数）。由于各指标样本的公共部分高度一致——**抓取注入的外部标签组（14 个）在所有指标上结构完全相同，`vllm:` 系指标又共有 `model_name`/`engine` 两个内部标签**——为避免重复，仅在 1.1 完整排版一次作为基准，其余指标用「公共外部标签组（结构同 1.1）」简写，只展开**各指标特有的内部标签**。
> 另一实操提醒：同名 metric 也会经 `native-pod` 裸 pod 抓取路径出现（`job="native-pod"`，标签为 `pod_name`/`pod_ip`/`service_name`，**无 `label_id`**）。查 llm-serving 在线服务指标时务必带 `label_id` 过滤，否则裸 pod 的同源序列会混入结果。

## 1. PromQL 查询

### 1.1 `vllmRequestPerStep` — 推理请求量

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

**使用 metric：`http_requests_total`**

- **埋点位置：** vLLM 服务进程自身的 HTTP 入口（API server 中间件，处于参数校验之前）——因此被校验拒绝（400）的请求同样被计数，它是**全量到达账本**。进程内的埋点层次：HTTP 入口 → 校验中间件 → 请求输出处理（`vllm:` 请求级直方图族）→ 引擎调度器（running/waiting、KV 水位）。
- **计数时机（为什么能带 `status` 标签）：** 中间件"处于校验之前"指的是**链路位置**（最外层包裹），不是计数时刻。它在请求进入时只捕获 `handler`/`method`；**计数发生在响应带着最终 status 流回外层的那一刻**——每个请求恰好递增一次、且天然携带这次生命周期的结局。由此推论：严格说它是"HTTP 生命周期已完结的账本"，任一时刻在途（校验中/排队中/生成中）的请求**尚未入账**，http 层在途 = 引擎在途 + 校验/提交前缓冲 + 流式收尾。
- **`status` 三类取值的含义：**

| status  | 内层实际发生了什么                                                                                                                     | 典型事件归因       |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `2xx` | 请求**通过**校验和路由，handler 开始返回响应；SSE 流式在首个响应头发出时刻 status 即定格为 2xx（早于生成完成，中途断开也不改写） | 正常路径           |
| `4xx` | 被校验中间件**拒绝**：prompt 超 `max_model_len`、参数非法、模型不存在等                                                        | E1 负载/调用方问题 |
| `5xx` | handler/引擎错误（500），或过载准入拒绝（503，此时引擎无`finished_reason=error` 记录，是"根本没进引擎"的过载信号）                   | E2 容量/故障       |

- **类型/单位：** Counter，request。`increase()` 得窗口请求量；`rate()` 得请求速率。
- **语义：** HTTP 服务累计处理请求数。当前筛选 messages/completions 路由；按 `status` 分组可观察 HTTP 状态。HTTP 状态不必然等同于模型业务成功（流式中断、网关重试需结合 `vllm:request_success_total` 的 `finished_reason` 判断）。
- **流式口径注意：** SSE 流式响应的状态码在响应开始（首个 byte 前）即确定为 2xx；客户端中途断开时 HTTP 层已按 2xx 计完数，引擎侧以 `finished_reason=abort` 结束——两层账本差值是流式弃单的指纹。
- **PD 判读注意：** prefill/decode 两角色各自的 serving 进程各自计数，存在双计风险，**不能跨角色相加当总到达量**；始终按 `label_role_name` 分拆。
- **经典实例**（集群实测：服务 prediction-service-0224-143355，standalone；**本例完整列出全部标签，是后续各指标实例的排版基准**）：

```text
http_requests_total{
  # ══ metric 内部标签（vLLM 服务进程 HTTP 入口埋点自带）══
  handler="/v1/messages",          # 命中的 API 路由
  method="POST",                   # HTTP 方法
  status="2xx",                    # 状态码组（2xx/4xx/5xx）
  # ══ 以下均为抓取链路注入的外部标签（非 metric 内部）══
  cluster="bj-caip",
  namespace="ns-10d099c9e7bb41b88fb6f2397d36bdb4",
  pod="prediction-service-0224-143355-0-0-1-roleset-gp94g-standal2bzh4",
  container="m25-0-0-1",
  service="prediction-service-0224-143355-0-0-1-serving",
  endpoint="serve",
  job="prediction-service-0224-143355-0-0-1-serving",
  instance="10.9.253.9:12121",
  prometheus="monitoring/vmagent",
  label_id="471b58f8-20d9-485d-a145-68c9b7bbb3f3",
  label_name="prediction-service-0224-143355",
  label_role_name="standalone",
  label_version="0.0.1",
  label_version_id="3fdd2144-f1aa-4f33-b09e-15b6da113d20",
} 33                              # counter 读数（该序列最后一个样本）
```

- **内部标签只有 `handler`/`method`/`status` 三个**——"进了哪个路由、什么方法、什么状态码组"就是它全部的自带维度；服务身份（`label_id`）、角色（`label_role_name`）、pod 等维度全靠抓取链路注入。序列唯一性 = 全部标签组合；同一 pod 的每个 (handler, method, status) 组合各一条序列。

### 1.2 `vllmSuccessRequestPerStep` — 成功推理量

> 业务注释原文："服务在指定时间窗口内实际成功的推理请求数"（措辞偏宽松，实际口径见下）。

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

**使用 metric：`vllm:request_success_total`**

- **类型/单位：** Counter，request。
- **源码口径：** vLLM 源码里该 counter 实际名为 `vllm:request_success`（定义见 `vllm/v1/metrics/loggers.py` 约 713-722 行），prometheus_client 自动给 Counter 加 `_total` 后缀，故暴露为 `vllm:request_success_total`。其 `documentation="Count of successfully processed requests."`，`labelnames=["model_name", "engine", "finished_reason"]`；其中 `engine` 为引擎实例序号。
- **语义要点：** 这里的 "success" 指"**被引擎处理完成**"（走完了处理流程、未被准入阶段拒绝），并不等价于业务成功。该 counter 对每个 `FinishReason` 值都建一条带 label 的序列（源码 `for reason in FinishReason: ...labels(model_name, str(idx), str(reason))`），因此它实际是**按 `finished_reason` 分桶的"完成处理请求总量"**。
- **与 1.2 查询的关系：** 本查询**不过滤** `finished_reason`，即对 5 种 reason 全部求和——"成功推理量"面板实际显示的是完成处理总量，包含 `abort`/`error`/`repetition`。

**`finished_reason` 各取值含义（来源：vLLM `FinishReason` 枚举，`vllm/v1/engine/__init__.py`）：**

| 值             | 枚举         | 含义                                                                    | 平台层面归类 |
| -------------- | ------------ | ----------------------------------------------------------------------- | ------------ |
| `stop`       | STOP=0       | 命中停止字符串（stop string）而被发出，正常生成完成                     | 正常结束 ✅  |
| `length`     | LENGTH=1     | `max_tokens` 被耗尽，或达到 `max_model_len` 上限而截断              | 正常结束 ✅  |
| `abort`      | ABORT=2      | 被客户端主动取消（client disconnect / abort），**流式中断归此类** | 非成功 ❌    |
| `error`      | ERROR=3      | 引擎侧可重试的请求级内部错误（如 KV load 失败）；恒转换为 HTTP 500      | 非成功 ❌    |
| `repetition` | REPETITION=4 | 检测到重复 token 模式（hallucination 退化）                             | 非成功 ❌    |

> `stop`/`length` 属于"模型按预期完成生成"（即便 `length` 是被截断，也产出了有效输出）；`abort`/`error`/`repetition` 则代表请求未产出有效结果。

- **经典实例**（集群实测：服务 prediction-service-0224-143355，standalone，MiniMax-M2.5）：

```text
vllm:request_success_total{
  model_name="MiniMax-M2.5",       # 共有内部标签（vllm: 系指标一致，后同）
  engine="0",
  finished_reason="stop",          # ★ 本指标特有内部标签：结束原因桶
  # ── 公共外部标签组（结构同 1.1，值为本服务，略）──
} 36703                           # finished_reason=stop 的累计条数
```

- **内部标签只有 `model_name`/`engine`/`finished_reason` 三个**；不带 `handler`/`method`/`status`（那是 HTTP 层专属），HTTP 状态层面的成功/失败要回 `http_requests_total` 查。序列唯一性 = 全部标签组合；源码初始化时对每个 `FinishReason` 各建一条序列，同一 (pod, engine) 固定拆出 5 条（值可为 0），这就是 1.2/1.3 查询能按 `finished_reason` 过滤的原因。

### 1.3 `vllmRequestSuccessRatioPerStep` — 推理成功率

> 业务注释原文："成功完成的请求数占所有结束请求数的比例"。

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

**使用 metric：`vllm:request_success_total`（同 1.2，仅多了分子侧的 `finished_reason` 过滤）**

- **口径（重要）：** 分子 `finished_reason=~"stop|length"`，分母为所有 `finished_reason`（5 种之和）。所以**平台所谓"成功率" = (stop+length) / (stop+length+abort+error+repetition) × 100**，即把 `stop`/`length` 视为正常结束、其余视为非成功。这与 vLLM 自身把 5 种都计入 "successfully processed" 不同，是平台层面对"业务成功"的重新定义（各取值含义见 1.2 的 FinishReason 表）。
- **判读注意：** 分母不含 HTTP 层被拒的请求（400/503 等根本没进引擎），因此该比率掉了但 4xx/5xx 为零时，怀疑方向是流式中断（abort）或引擎内部错误（error），而非入口拒绝；反之 4xx 在涨时请求根本没到引擎。

### 1.4 `vllmHttpRequestStatusPerStep` — Http 请求状态数量（4xx/5xx 错误数量）

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

**使用 metric：`http_requests_total`（同 1.1）**

- 按 `status` 标签分组（`%(status)s` 分别取 `4xx`/`5xx` 各查一次），是**入口拒绝/超时/过载的探测器**：4xx = 校验拒绝（超长/参数）或客户端断开，5xx/503/504 = 引擎错误或网关超时切断。metric 完整口径与样本见 1.1。

### 1.5 `vllmNumPreemptionsTotalPerStep` — 抢占请求数

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
  }
)
```

**使用 metric：`vllm:num_preemptions_total`**

- **类型/单位：** Counter，preemption，调度器累计抢占次数。窗口增量 > 0 即代表该段时间发生过"KV block 池耗尽 → 强制回退"。
- **核心触发原因只有一个：KV cache block 池不够了**——调度器在某个 step 要给 running 请求续命（分配下一个 token 的 KV block）时拿不到空闲 block、又无法靠驱逐已完成请求腾出空间，只能把一部分 running 请求踢出运行态、释放它们的 block 给剩下的请求。抢占的诱因都收敛到"KV 需求超过池容量"这一个点，常见场景：
  - **高并发 + 长输出**：多请求同时 decode，序列持续生长累积占用直到池满；
  - **长上下文输入**：单个长 prompt 准入时就吃掉大量 block，挤压其他 running 请求；
  - **突发流量**：瞬时涌入大量请求，调度器乐观准入后 KV 不够被迫抢占回退；
  - **prefix cache 未命中**：请求间无共享前缀，每请求独立占 block，等效 KV 需求放大；
  - **配置偏激进**：`max_num_seqs` 偏大或 KV cache 预算偏小（如 `--gpu-memory-utilization`/`--max-model-len`/`--block-size` 设置），常态性抢占。
- **被踢出请求的去向**取决于引擎抢占模式：**RECOMPUTE**（默认，丢弃 KV、回 waiting 队列、重调度时重算 prefill）或 **SWAP**（KV 换出到 CPU、重调度时 swap 回 GPU / KVOffload）。RECOMPUTE 模式下抢占表现为被踢请求重走 prefill，ITL 出现长尖。
- **经典实例**（集群实测：服务 glm-47-gpu，standalone，glm-4.7；value=10 表示该实例累计发生过 10 次抢占）：

```text
vllm:num_preemptions_total{
  model_name="glm-4.7",
  engine="0",
  # ── 公共外部标签组（结构同 1.1，值为本服务，略）──
} 10                              # 该实例累计 10 次抢占
```

  无特有内部标签——只有共有的 `model_name`/`engine`，即本指标在引擎粒度上只有一条序列。

- 一个细节：实测序列的 `container="glm-47-gpu-0-0-2"` 与 `pod="...-0-0-1-..."` 尾缀不同——同一 pod 内 serving 容器名独立编号，对齐实例身份时以 `pod`/`label_id` 为准，别拿 `container` 尾缀去配对。

### 1.6 `vllmSpecDecodeAcceptanceRatePerStep` — 投机采样接受率

> 业务注释原文："MTP 草稿模型预测 Token 被主模型接受的比例"。

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
  }
)
*
100
```

**使用 metric（两个）：**

- **分子 `vllm:spec_decode_num_accepted_tokens_total`**：Counter，token，累计被主模型接受的草稿 Token。接受数量增加不等于同等比例加速，还取决于验证开销。
- **分母 `vllm:spec_decode_num_draft_tokens_total`**：Counter，token，累计草稿模型提出的 Token。窗口无 draft token 时接受率无定义（未开启投机解码时两 counter 均无数据）；它必须与 accepted Counter 保留相同聚合维度。
- **共同内部标签为 `model_name`/`engine`**（集群实测确认；早期写的 `speculator` 标签未在实测序列中出现），无其他特有内部标签。
- **经典实例**（集群实测：服务 qwen3-5-122b-a10b，standalone，Qwen3.5-122B-A10B——两 counter 同 pod 同引擎同刻，可直接相除）：

```text
vllm:spec_decode_num_accepted_tokens_total{
  model_name="Qwen3.5-122B-A10B",
  engine="0",
  # ── 公共外部标签组（结构同 1.1，值为本服务，略）──
} 8235336                         # 累计被主模型接受的草稿 token 数

vllm:spec_decode_num_draft_tokens_total{
  model_name="Qwen3.5-122B-A10B",
  engine="0",
  # ── 公共外部标签组（同上，略）──
} 12261436                        # 累计草稿 token 数
```

  两序列除 metric 名外标签完全一致，直接相除即接受率：8235336 / 12261436 ≈ **67.2%**。

- **判读注意：** 接受率↓ → 草稿质量退化（模型行为事件），影响的是有效吞吐而非延迟语义。

## 2. 查询关系

```text
HTTP 请求进入量（全量到达，含被拒） → vLLM 完成处理量（5 种 finished_reason 分桶）
                                          ├→ 正常结束原因占比（stop+length / 全部 reason）
                                          └→ 按 HTTP status 观察入口拒绝/超时/错误
调度器 KV block 池耗尽事件           → 窗口抢占请求数
accepted/draft token                → 投机采样接受率
```

当前所谓"推理成功率"实际是 `request_success_total` 中 `finished_reason=stop|length` 的占比，不是真正的成功请求/全部请求（分母不含 HTTP 层被拒请求）。

各 metric 的完整原始语义（含样本与源码口径）已并入上文对应小节；原 [metric指标.md](./metric指标.md) 保留作为单 metric 视角的对照文档。
