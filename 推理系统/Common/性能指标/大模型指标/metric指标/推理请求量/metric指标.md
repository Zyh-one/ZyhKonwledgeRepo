# 推理请求量 metric 指标

本文说明“推理请求量”类别 PromQL 实际使用的全部 metric。对应查询见 [PromQL.md](./PromQL.md)。

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取。Kubernetes 资源指标的来源在对应小节单独说明。

## 1. `http_requests_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 request，表示 HTTP 服务累计处理请求数。当前筛选 messages/completions 路由，用 `increase()` 得到窗口请求量；按 `status` 分组可观察 HTTP 状态。HTTP 状态不必然等同于模型业务成功，流式中断和网关重试要结合埋点判断。

```

http_requests_total {cluster="bj-caip",container="deepseekv4-flash-0-0-9",endpoint="serve",handler="/v1/messages",instance="10.9.103.71:9100",job="deepseek-v4-8r-dp2-0-0-1-serving",label_id="7d0a22af-2f15-410f-b373-57e4368ce888",label_name="deepseek-v4-8r-dp2",label_role_name="standalone",label_version="0.0.1",label_version_id="ea647c65-61f4-436b-841e-356ea56b202c",method="POST",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="deepseek-v4-8r-dp2-0-0-1-roleset-wp2h5-standalone-6c57f8-0-1",prometheus="monitoring/vmagent",service="deepseek-v4-8r-dp2-0-0-1-serving",status="2xx"}
```

**唯一标识标签：** `(cluster, namespace, pod, handler, method, status)`；不存在的标签从组合中移除。

## 2. `vllm:request_success_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 request。vLLM 源码里该 counter 实际名为 `vllm:request_success`（定义见 `vllm/v1/metrics/loggers.py` 约 713-722 行），prometheus_client 会自动给 Counter 加 `_total` 后缀，故暴露为 `vllm:request_success_total`。其 `documentation=”Count of successfully processed requests.”`，`labelnames = [“model_name”, “engine”, “finished_reason”]`；其中 `engine` 为引擎实例序号，`finished_reason` 取自 `vllm/v1/engine/__init__.py` 的 `FinishReason` 枚举（共 5 个值）。需要特别注意：**这里的 “success” 指”被引擎处理完成”（即走完了处理流程、未被准入阶段拒绝），并不等价于业务成功**。该 counter 对每个 `FinishReason` 值都建一条带 label 的序列（源码 `for reason in FinishReason: ...labels(model_name, str(idx), str(reason))`），因此 `vllm:request_success_total` 实际是按 `finished_reason` 分桶的”完成处理请求总量”。

### `finished_reason` 各取值含义（来源：vLLM `FinishReason` 枚举文档串）

| 值             | 枚举         | 含义                                                               | 平台层面归类 |
| -------------- | ------------ | ------------------------------------------------------------------ | ------------ |
| `stop`       | STOP=0       | 命中停止字符串（stop string）而被发出，正常生成完成                | 正常结束 ✅  |
| `length`     | LENGTH=1     | `max_tokens` 被耗尽，或达到 `max_model_len` 上限而截断         | 正常结束 ✅  |
| `abort`      | ABORT=2      | 被客户端主动取消（client disconnect / abort）                      | 非成功 ❌    |
| `error`      | ERROR=3      | 引擎侧可重试的请求级内部错误（如 KV load 失败）；恒转换为 HTTP 500 | 非成功 ❌    |
| `repetition` | REPETITION=4 | 检测到重复 token 模式（hallucination 退化）                        | 非成功 ❌    |

> `stop`/`length` 属于”模型按预期完成生成”（即便 `length` 是被截断，也产出了有效输出）；`abort`/`error`/`repetition` 则代表请求未产出有效结果。

### 与平台 PromQL 的对应关系

- **成功推理量 `vllmSuccessRequestPerStep`**（[llm-query.constant.ts:7](#)）：`increase(vllm:request_success_total{...}[%(time)s:30s])`，**不过滤** `finished_reason`，即对 5 种 reason 全部求和。因此该量实为”完成处理请求总量”，其注释”成功推理量/实际成功的推理请求数”措辞偏宽松——它包含 `abort`/`error`/`repetition`。
- **推理成功率 `vllmRequestSuccessRatioPerStep`**（[llm-query.constant.ts:62](#)）：分子 `finished_reason=~”stop|length”`，分母为所有 `finished_reason`（即上述 5 种之和），结果 ×100。所以**平台所谓”成功率” = (stop+length) / (stop+length+abort+error+repetition) × 100**，即把 `stop`/`length` 视为正常结束、其余视为非成功。这与 vLLM 自身把 5 种都计入”successfully processed”不同，是平台层面对”业务成功”的重新定义。

```
# 典型样本（vLLM 原生 label 为 model_name/engine/finished_reason，叠加抓取注入的 K8s/平台 label）
vllm:request_success_total{cluster=”bj-caip”,container=”deepseekv4-flash-0-0-9”,endpoint=”serve”,engine=”0”,finished_reason=”stop”,instance=”10.9.103.71:9100”,job=”deepseek-v4-8r-dp2-0-0-1-serving”,label_id=”7d0a22af-2f15-410f-b373-57e4368ce888”,label_name=”deepseek-v4-8r-dp2”,label_role_name=”standalone”,label_version=”0.0.1”,label_version_id=”ea647c65-61f4-436b-841e-356ea56b202c”,model_name=”deepseek-v4-8r-dp2”,namespace=”ns-e23f5b20fb9b42d3ac674f9691a0b9b1”,pod=”deepseek-v4-8r-dp2-0-0-1-roleset-wp2h5-standalone-6c57f8-0-1”,prometheus=”monitoring/vmagent”,service=”deepseek-v4-8r-dp2-0-0-1-serving”} 12345
```

> 注：原先此处的样本块是从 `http_requests_total` 误粘贴而来（metric 名写成了 `http_requests_total`，且带 `handler`/`method`/`status` 等 HTTP 层 label），与 `vllm:request_success_total` 的真实 label 集不符，已更正。`vllm:request_success_total` 不带 `handler`/`method`/`status`，而带 `model_name`/`engine`/`finished_reason`。`status` 层面的成功/失败应查 `http_requests_total`。

**唯一标识标签：** `(cluster, namespace, pod, model_name, engine, finished_reason)`，并保留平台标签 `label_id`/`label_version` 等。注意按 `finished_reason` 分桶后，同一 (pod,engine) 会拆成 5 条序列。

## 3. `vllm:num_preemptions_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 preemption，表示调度器累计抢占次数。**核心触发原因只有一个：KV cache block 池不够了**——调度器在某个 step 要给 running 请求续命（分配下一个 token 的 KV block）时拿不到空闲 block、又无法靠驱逐已完成请求腾出空间，只能把一部分 running 请求踢出运行态、释放它们的 block 给剩下的请求。

窗口增量 > 0 即代表该段时间内发生过这种"KV block 池耗尽 → 强制回退"。

抢占的诱因都收敛到"KV 需求超过池容量"这一个点，常见场景：

- **高并发 + 长输出**：多请求同时 decode，序列持续生长累积占用直到池满；
- **长上下文输入**：单个长 prompt 准入时就吃掉大量 block，挤压其他 running 请求；
- **突发流量**：瞬时涌入大量请求，调度器乐观准入后 KV 不够被迫抢占回退；
- **prefix cache 未命中**：请求间无共享前缀，每请求独立占 block，等效 KV 需求放大；
- **配置偏激进**：`max_num_seqs` 偏大或 KV cache 预算偏小（如 `--gpu-memory-utilization`/`--max-model-len`/`--block-size` 设置），常态性抢占。

被踢出请求的去向取决于引擎抢占模式：**RECOMPUTE**（默认，丢弃 KV、回 waiting 队列、重调度时重算 prefill）或 **SWAP**（KV 换出到 CPU、重调度时 swap 回 GPU）--- KVOffload；

**唯一标识标签：** `(cluster, namespace, pod)`；多引擎时增加 `engine`，有 reason 时保留。

## 4. `vllm:spec_decode_num_accepted_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计被主模型接受的草稿 Token，是接受率分子。接受数量增加不等于同等比例加速，还取决于验证开销。

**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/speculator。

## 5. `vllm:spec_decode_num_draft_tokens_total`

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

Counter，单位为 token，累计草稿模型提出的 Token，是接受率分母。窗口无 draft token 时接受率无定义；它必须与 accepted Counter 保留相同聚合维度。


**唯一标识标签：** `(cluster, namespace, pod)`，并保留 engine/speculator。
