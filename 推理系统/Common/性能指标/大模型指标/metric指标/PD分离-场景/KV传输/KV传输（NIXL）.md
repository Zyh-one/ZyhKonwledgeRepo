# KV 传输（NIXL）PromQL 与 metric 指标

> 传输流程（交接全流程、计时边界、Descriptor 映射、失败分层）见同目录《KV传输流程》，其图解原始资料归档于 `PD_NIXL_对话整理/`；本文聚焦本部署分支源码核实后的指标口径与 PromQL，冲突处以本文为准。

> **角色分布总述（重要）**：PD 分离 + NixlConnector pull 模式下，**RDMA READ 由 decode（D）实例发起并轮询完成**（`pull_worker.py` 的 `start_load_kv` → `_read_blocks` → `make_prepped_xfer("READ", ...)`），因此 **4 个直方图家族（传输耗时/提交耗时/字节数/描述符数）的观测只发生在 decode 实例**，prefill 侧序列存在但计数恒 0。**KV 租约由 prefill（P）实例持有并回收**（`base_worker.py` `_reap_expired_send_leases`），因此 **`kv_expired` 与 `notifications_after_expiry` 只在 prefill 实例非零**（vLLM 源码 documentation 明确 "tracked on the P instance"）。failed_* 两类计数器在传输层异常时双侧均可能出现。线上健康态下 4 个直方图 `_count` 完全一致（每次成功传输在 4 个家族各记 1 次观测），可互相校验。

## 0. 占位符说明

PromQL 模板中的 sprintf 占位符由前端变量注入：

| 占位符                 | 含义                                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| `%(cluster)s`        | 集群名（探针时常取 `.*`）                                                                              |
| `%(namespace)s`      | 指定 namespace                                                                                           |
| `%(pod)s`            | pod 过滤，`.*` 或具体 pod 名                                                                           |
| `%(version)s`        | `label_version` 正则（如 `0.0.1`）                                                                   |
| `%(labelID)s`        | `label_id`（应用 ID，UUID）。**探针用 `=` 精确匹配，图表用 `=~` 正则**                       |
| `%(labelRoleName)s`  | 选中角色时展开 `,label_role_name=~"prefill\|decode"`，未选时为空                                        |
| `%(time)s:30s`       | 子查询窗口，外层 `%(time)s` = 当前 step（如 `[1m:30s]`），内层固定 30s 分辨率                        |
| `%(tp)s`             | 分位数，取 `0.999` / `0.95` / `0.90` / `0.5`（图例 P999/P95/P90/P50）                            |
| `%(labelServiceBy)s` | `groupByService` 时展开 `,label_id`（按服务聚合），否则为空                                          |
| `%(labelVersionBy)s` | 有 version 变量时展开 `,label_version`；无 version 但有 role 变量时展开 `,label_role_name`；否则为空 |
| `%(groupPod)s`       | pod 过滤非 `.*` 时展开 `,pod`（曲线按 pod 细分），否则为空                                           |

## 1. PromQL 查询（按图显示顺序）

### 1.1 区块开关探针 `vllmNixlXferTimeCountPerStep`（非图表）

NIXL KV 传输活动探测——用于判断是否启用 NixlConnector（基于传输次数计数，每次传输均累加）。不是展示图：`container-monitor.component.ts` 用它查询时间范围，**任一序列存在且有点位值 > 0** 时 `nixlEnabled = true`，整个"KV 传输（NIXL）"区块才渲染。注意它用 `label_id="..."` 精确匹配，而图表查询用 `label_id=~"..."`。

```promql
sum by (
  namespace%(labelServiceBy)s,
  label_version%(groupPod)s
) (
  increase(
    vllm:nixl_xfer_time_seconds_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.2 `vllmNixlXferTimeTPPerStep` — NIXL 传输延迟

每次跨进程 KV 块传输的**端到端 RDMA 拷贝耗时**分布，从请求提交开始到后端报告完成为止，**包含提交步骤与实际数据搬运**。分位图：同一模板代入 `%(tp)s` = 0.999 / 0.95 / 0.90 / 0.5 渲染 4 条分位线，叠加 1 条均值线，共 5 条序列（图例 `{version=…, tp=P999/P95/P90/P50}` + `{version=…, avg=AVG}`）。数值格式化为秒（4 位小数）。

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace%(labelServiceBy)s%(labelVersionBy)s,
    le%(groupPod)s
  ) (
    rate(
      vllm:nixl_xfer_time_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id=~"%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

均值线（同图第 5 条序列）：

```promql
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_xfer_time_seconds_sum{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
/
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_xfer_time_seconds_count{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
```

**底层 metric：`vllm:nixl_xfer_time_seconds`（Histogram 家族）**

**观测触发时机（完整链路）**：在**传输完成被轮询发现的那一刻**生成（只有decode才有）

1. **传输发起**：D（decode）侧调度器把携带远端 KV 的请求排入执行，connector worker 调 `start_load_kv` → `_read_blocks` → `make_prepped_xfer("READ", ...)` 向 NIXL 后端提交 RDMA READ（此刻 NIXL 开始计时）；
2. **完成轮询**：每个 engine step 检查在途传输的 `check_xfer_state(handle)`：`PROC`（搬运中）则继续等；既非 `PROC` 也非 `DONE` 则走失败路径（`_log_failure` → failed_transfers 计数）；`DONE` 则调 `get_xfer_telemetry(handle)` 向 NIXL 取回该次传输的遥测数据；
3. **遥测落账**：`record_transfer()` 把遥测的 4 个字段换算后 append 进 `NixlKVConnectorStats` 的内存累积列表（时间 µs→s）——`transfer_duration`（即本 metric 的观测值）、`post_duration`、`bytes_transferred`、`num_descriptors`，随后释放传输句柄；

**观测值含义**：`transfer_duration` = 从传输提交（post）到 NIXL 后端报告完成的总耗时——**包含提交步骤与实际数据搬运**。因此它与 1.3 的 `post_time`（仅提交到 NIC 队列的同步耗时）是包含关系：`xfer_time − post_time ≈ 纯 RDMA 数据搬运时间`。单次观测对应一个 prefill 请求的 KV 块集合从 P 到 D 的完整搬运（一次成功传输），桶边界见 2.1。

**标签粒度与 MLU 对应关系**：NIXL 传输实际发生在 **MLU 卡（TP rank）级别**——每个 TP rank 有独立的 worker、KV 基址注册与传输描述符，每张卡的 KV 分片是独立传输、独立观测。但 metric 自有标签**只有 `["model_name", "engine"]`，没有 MLU 序号标签**：各 rank 遥测先聚合（`aggregate()`）再按 `engine` 落账。因此 `engine`（数据并行 engine 序号）是最细粒度：

- **TP=1** 时 engine 进程即单卡，`engine` 序号 ↔ MLU 序号一一对应，可直接按卡定位（本例 decode 的 engine 0-7 即 8 张 MLU，连续编号分布在 2 个 pod 上）；
- **TP>1** 时一个 engine 聚合 TP 组内全部卡的观测，**无法按卡拆分**，且 `_count` 计的是 rank 级传输数（一次请求的 KV 传输会记 `tp_size` 次观测），不是请求数；
- 样本上其余标签均非 vLLM 添加：`pod/container/instance/endpoint/job/service` 来自 VMServiceScrape 服务发现，`label_id/label_name/label_role_name/label_version*` 等为平台注入；
- **前端 PromQL（`sum by(namespace, label_version, ...)`）把 `engine` 聚合掉了**——要按 MLU 定位传输异常，需绕过前端直接用 `by(engine)` 查询。

### 1.3 `vllmNixlPostTimeTPPerStep` — NIXL 提交延迟

将传输请求**提交到 RDMA 后端所耗时间**的分位分布，衡量把工作提交到 NIC 队列（描述符设置等）的同步开销，发生在异步数据搬运之前。序列构成与 1.2 相同（4 分位 + 均值，秒）。

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace%(labelServiceBy)s%(labelVersionBy)s,
    le%(groupPod)s
  ) (
    rate(
      vllm:nixl_post_time_seconds_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id=~"%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

均值线：

```promql
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_post_time_seconds_sum{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
/
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_post_time_seconds_count{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
```

### 1.4 `vllmNixlBytesTransferredTPPerStep` — NIXL 传输字节数分位（每次传输）

每次 NIXL KV 块传输搬运**字节数**的分位分布，衡量 P 与 D 实例之间单次跨进程 KV Cache 传输的负载大小。序列构成与 1.2 相同（4 分位 + 均值）。

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace%(labelServiceBy)s%(labelVersionBy)s,
    le%(groupPod)s
  ) (
    rate(
      vllm:nixl_bytes_transferred_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id=~"%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

均值线：

```promql
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_bytes_transferred_sum{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
/
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_bytes_transferred_count{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
```

### 1.5 `vllmNixlBytesTransferredBucketPerStep` — NIXL 传输字节数热力图

通过热力图展示窗口内每次传输搬运字节数的**分布密度**：对 `_bucket` 做 `increase` 增量后按 `le` 桶展开，颜色深浅代表落入各字节区间的传输数量集中程度；颜色越深表示越多传输落入该区间，用于识别典型传输负载规模及检测异常偏大或碎片化传输。单条查询，按 `le` 维度渲染为行。

```promql
sum by (
  namespace%(labelServiceBy)s%(labelVersionBy)s,
  le%(groupPod)s
) (
  increase(
    vllm:nixl_bytes_transferred_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id=~"%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.6 `vllmNixlNumDescriptorsTPPerStep` — NIXL 描述符数量分位（每次传输）

每次 NIXL KV 块传输提交的**内存描述符（scatter-gather 段）数量**的分位分布。描述符越多说明 KV Cache 分配越碎片化或越大，过高的数量会增加描述符注册开销。序列构成与 1.2 相同（4 分位 + 均值）。

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace%(labelServiceBy)s%(labelVersionBy)s,
    le%(groupPod)s
  ) (
    rate(
      vllm:nixl_num_descriptors_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id=~"%(labelID)s"%(labelRoleName)s
      }[%(time)s:30s]
    )
  )
)
```

均值线：

```promql
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_num_descriptors_sum{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
/
sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
  rate(vllm:nixl_num_descriptors_count{cluster=~"%(cluster)s",namespace="%(namespace)s",pod=~"%(pod)s",label_version=~"%(version)s",label_id=~"%(labelID)s"%(labelRoleName)s}[%(time)s:30s])
)
```

### 1.7 `vllmNixlNumFailedTransfersPerStep` — NIXL 失败传输次数

窗口内**失败的 NIXL KV 块传输次数**增量，反映跨进程 KV Cache 传输的可靠性问题。一次传输对应一个预填充请求的 KV Cache 在 P 与 D 之间的搬运；失败意味着该请求的 KV 需要重传或在 D 上重算。单序列计数图。

```promql
sum by (
  namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s
) (
  increase(
    vllm:nixl_num_failed_transfers_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id=~"%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.8 `vllmNixlNumFailedNotificationsPerStep` — NIXL 失败通知次数

窗口内 NIXL KV 块传输过程中**失败的完成通知（send_notif）次数**增量。非零值表明 P 与 D 之间的完成通知未被对端成功接收/处理，传输完成事件可能丢失。单序列计数图。

```promql
sum by (
  namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s
) (
  increase(
    vllm:nixl_num_failed_notifications_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id=~"%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.9 `vllmNixlNumKvExpiredReqsPerStep` — NIXL 过期请求数

窗口内 **Prefiller 上 KV 块在 Decoder 读取前过期失效的请求数量**增量，仅在 P 实例统计。预填充请求完成时其 KV 块被持有一个租约时长等待 D 读取；若租约到期仍未被 D 消费（D 排队过长或调度滞后），P 侧回收块并计数。非零代表 PD 之间调度/容量失配，是可操作的弹性伸缩信号（autoscaler 信号）而非单纯传输故障。单序列计数图。

```promql
sum by (
  namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s
) (
  increase(
    vllm:nixl_num_kv_expired_reqs_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id=~"%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

## 2. Metric 指标

vLLM/HTTP metric 在黄区由模型实例的 `*-serving` Service 经 `serve` 端口暴露 Predictor Pod 的 `/metrics`，由 `monitoring/VMServiceScrape llm-serving-metrics` 抓取（与"缓存"等区块同源）。NIXL 各 metric 由 vLLM 的 `NixlPromMetrics` 按 engine 建立（`create_metric_per_engine`），**每个 vLLM engine 一条独立序列**（`engine` 标签区分）。

> **口径提醒（重要）**：
>
> 1. 4 个直方图家族（`xfer_time` / `post_time` / `bytes_transferred` / `num_descriptors`）在**每次成功传输**时各记 1 次观测（`stats.py` `observe()` 中 zip 遍历），因此 4 个家族的 `_count` 应完全一致，等于成功传输总次数，可互相校验。
> 2. 观测点在 **D（decode）实例**：`pull_worker` 发起 `make_prepped_xfer("READ")`，传输 DONE 后 `get_xfer_telemetry(handle)` 取回遥测数据写入 `record_transfer`。P 实例序列存在但计数恒 0——**看这 4 个家族的数值要过滤/关注 decode 序列，不要被 prefill 的 0 值序列稀释聚合**（`sum` 聚合不受影响，但 `avg`/按实例分组时需注意）。
> 3. 计数器在 Prometheus 输出侧带 `_total` 后缀，查询时用 `vllm:nixl_num_failed_transfers_total` 等全名。
> 4. **标签分层**：vLLM 自有标签仅 `model_name` + `engine`（无 MLU 序号标签，`engine` 是最细粒度，TP=1 时即 MLU 序号，TP>1 时为 TP 组聚合，详见 1.2 的"标签粒度与 MLU 对应关系"）；`pod/container/instance/endpoint/job/service` 为抓取侧服务发现添加；`label_id/label_name/label_role_name/label_version*` 为平台注入。

### 2.1 `vllm:nixl_xfer_time_seconds`（Histogram）

**黄区暴露来源：** 模型实例自己的 `*-serving` Service，通过名为 `serve` 的端口将请求转发到 Predictor Pod 的 `/metrics`；由 `monitoring/VMServiceScrape llm-serving-metrics` 跨 Namespace 发现并抓取。

直方图，单位秒，观测**每次 NIXL KV Cache 传输的端到端耗时**（从请求提交到后端报告完成，含提交步骤与实际数据搬运）。vLLM 源码 documentation：`Histogram of transfer duration for NIXL KV Cache transfers.` 内部记录单位为 µs，导出前 `/1e6` 换算为秒。桶边界（12 个，来自 `buckets[1:]`）：

```text
0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 5.0 (+Inf)
```

原始样本（decode engine，已传 516 次）：

```text
vllm:nixl_xfer_time_seconds_count{cluster="bj-caip",container="glm5-0427-0-0-1079",endpoint="serve",engine="0",instance="10.9.249.53:7921",job="glm52-8-pd-1026-0-0-1-serving",label_id="0dec8455-1f4f-4bee-88b9-c8abc51ad172",label_name="glm52-8-pd-1026",label_role_name="decode",label_version="0.0.1",label_version_id="1642f904-49fb-4263-a43e-170b6b719697",model_name="glm5",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod="glm52-8-pd-1026-0-0-1-roleset-8jzh9-decode-66c8cd-0-0",prometheus="monitoring/vmagent",service="glm52-8-pd-1026-0-0-1-serving"} 516
```

**唯一标识标签：** vLLM 侧仅 `(model_name, engine)`；含抓取侧即 `(cluster, namespace, pod, engine)`，辅以 `label_id`（服务主键）与 `label_role_name`（角色）。**`engine` 无独立 MLU 序号标签可替代——TP=1 时 engine 即 MLU 序号，TP>1 时为组内聚合（见 1.2）**。

**实测参考（glm52-8-pd-1026，3P + 2D×4engine = 11 实例，运行约 18.9h）：** decode 侧 8 个 engine 全部非零（单 engine 500~834 次），prefill 3 实例全 0；总传输 5476 次，xfer 中位约 0.5–0.75s（单次平均 6.8GiB 的量级下）。

### 2.2 `vllm:nixl_post_time_seconds`（Histogram）

**黄区暴露来源：** 同 2.1。

直方图，单位秒，观测**每次传输把请求提交到 RDMA 后端（NIC 队列、描述符设置）的耗时**，是异步数据搬运开始前的同步开销。vLLM 源码 documentation：`Histogram of transfer post time for NIXL KV Cache transfers.` 桶边界（13 个，全桶）：

```text
0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 5.0 (+Inf)
```

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** 与 xfer_time 同批 decode 观测，绝大部分落在 5ms 以内（最小桶 1ms~5ms 区间占绝对多数）；post 与 xfer 的差值即纯数据搬运时间。

### 2.3 `vllm:nixl_bytes_transferred`（Histogram）

**黄区暴露来源：** 同 2.1。

直方图，单位字节，观测**每次传输搬运的字节数**。vLLM 源码 documentation：`Histogram of bytes transferred per NIXL KV Cache transfers.` 桶边界为 4 倍等比（源码 `2**(10+i) for i in range(1,25,2)`，源码注释 "uniform 2kb to 16gb range" 与实际不符，实际 12 个桶）：

```text
2048(2KiB), 8192(8KiB), 32KiB, 128KiB, 512KiB, 2MiB, 8MiB, 32MiB, 128MiB,
512MiB, 2GiB, 8GiB (2^33) (+Inf)
```

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** `_count` 5476（与 xfer_time 一致），`_sum` 40076185319424 字节 ≈ 40.1 TB（36.4 TiB），平均单次 ≈ 7.32 GB（6.82 GiB）；单次 6.8GiB 意味着 P50 分位落在 2GiB~8GiB 桶内，与 0.5~0.75s 的中位传输耗时对应（有效带宽约 9~14 GB/s 量级）。

### 2.4 `vllm:nixl_num_descriptors`（Histogram）

**黄区暴露来源：** 同 2.1。

直方图，无量纲，观测**每次传输提交的内存描述符（scatter-gather 段）数量**。vLLM 源码 documentation：`Histogram of number of descriptors per NIXL KV Cache transfers.` 桶边界（14 个）：

```text
10, 20, 30, 50, 75, 100, 200, 400, 1000, 2000, 4000, 10000, 20000, 50000 (+Inf)
```

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** `_count` 5476（一致），`_sum` 243772828，平均单次 ≈ 44503 个描述符（P50 落在 20000~50000 桶）。描述符数与传输字节数同向增长：碎片化的物理块分布会推高描述符数、增加注册开销；若字节数不变而描述符数显著上升，说明 KV 块分配碎片化加剧。

### 2.5 `vllm:nixl_num_failed_transfers`（Counter）

**黄区暴露来源：** 同 2.1。

Counter（查询名 `vllm:nixl_num_failed_transfers_total`），累计**失败的 NIXL KV Cache 传输次数**。vLLM 源码 documentation：`Number of failed NIXL KV Cache transfers.` 递增点：`base_worker.py` `_log_failure` → `record_failed_transfer`（`make_prepped_xfer` 抛异常等传输建立/执行失败路径）。

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** 健康态双侧恒 0。非零时优先看失败发生的角色与对应时段的 xfer_time 是否同步恶化（RDMA 链路/内存注册问题）。

### 2.6 `vllm:nixl_num_failed_notifications`（Counter）

**黄区暴露来源：** 同 2.1。

Counter（查询名 `vllm:nixl_num_failed_notifications_total`），累计**失败的完成通知（send_notif）次数**。vLLM 源码 documentation：`Number of failed NIXL KV Cache notifications.` 与 2.5 同在 `_log_failure` 路径记录，区别在于失败对象是通知发送而非数据搬运本身。

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** 健康态双侧恒 0。

### 2.7 `vllm:nixl_num_kv_expired_reqs`（Counter）

**黄区暴露来源：** 同 2.1。

Counter（查询名 `vllm:nixl_num_kv_expired_reqs_total`），累计**KV 块在 D 读取前租约到期而被 P 回收的请求数**。vLLM 源码 documentation：`Number of requests that had their KV expire. NOTE: This metric is tracked on the P instance.` 递增点：`base_worker.py:2184` `_reap_expired_send_leases`——P 侧周期扫描 `_reqs_to_send` 中租约（`expiration_time`）已过的请求，释放 KV 块并计数；D 侧通过 "HB:" 心跳为仍在排队的请求续租。

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** 仅 prefill 侧非零（glm52-8-pd-1026 全程 8406，decode 恒 0），**超过同窗口成功传输总次数 5476**——说明过期事件可按"请求"计而一次传输消费多个请求的 KV，或存在 D 侧长期未消费的排队请求；该值持续大于传输量是 P/D 失配（D 消费能力不足或租约时长偏短）的直接信号。

### 2.8 `vllm:nixl_num_notifications_after_expiry`（Counter，前端未直接展示）

**黄区暴露来源：** 同 2.1。

Counter（查询名 `vllm:nixl_num_notifications_after_expiry_total`），累计**针对已不再追踪（通常因 KV 租约过期）的请求到达的完成通知数**。vLLM 源码 documentation：`Number of completion notifications for requests that were no longer tracked, usually because their KV lease expired. The KV blocks may have been reused before the transfer finished. Counted per notification (one per remote rank), not per request.` 递增点：`pull_worker.py:388` `_get_new_notifs`——收到远端拉取完成通知时请求已不在 `_reqs_to_send`/`_reqs_to_process` 集合，说明 KV 块可能在传输完成前已被复用。

**唯一标识标签：** `(cluster, namespace, pod, engine)`，辅以 `label_id` 与 `label_role_name`。

**实测参考：** 仅 prefill 侧非零（1136）。它不在前端 8 张图中，但排查 kv_expired 高值时应同查：**计数按通知（每远端 rank 一条）而非按请求**，8406 过期请求对应 1136 条过期后通知，意味着多数过期块的 KV 已被复用而未被实际读取。

## 3. 查询关系与排查解读

```text
NIXL 活动探针（xfer_time_count > 0）→ 区块渲染
传输执行（D 侧观测）→ 传输延迟 / 提交延迟 / 字节数(分位+热力图) / 描述符数
传输可靠性（双侧）→ 失败传输次数 / 失败通知次数
调度/租约健康（P 侧）→ 过期请求数 (+ notifications_after_expiry，前端未展示)
```

**对账关系：**

- 4 个直方图家族 `_count` 必须一致 = 成功传输次数；不一致说明抓取缺失或序列被过滤。
- `_sum / _count` 即每传输平均值（字节：40.1TB / 5476 ≈ 6.82GiB；描述符：243772828 / 5476 ≈ 44503）。
- `kv_expired`（P 侧按请求计）与传输次数（D 侧按传输计）**口径不同**，二者比值反映"产出被消费"的效率：本例 8406/5476 > 1，说明大量 prefill 产出的 KV 未被及时消费即过期。

**解读要点：**

- **传输延迟分位 vs 均值**：P999 远高于 P50 属正常长尾；若 P50 本身抬升且字节数分位同步上移，是负载变大；字节数不变而耗时上升则是带宽/链路退化（可算有效带宽 = bytes_sum / xfer_time_sum）。
- **提交延迟**：正常应在毫秒级；与传输延迟的差值为纯搬运时间。提交耗时突增 + 描述符数突增 → 描述符注册开销过大（KV 块碎片化）。
- **热力图**：颜色集中于 2GiB~8GiB 桶为大批量整体传输；若向低字节桶扩散（碎片化）且描述符数同步升高，说明 KV 块分配零散。
- **失败传输/失败通知非零**：传输层异常，结合发生角色与时段定位（RDMA 链路、内存注册、对端处理）。
- **过期请求数持续非零**：P/D 容量或调度失配。优先动作（只读排查视角）：看 D 侧 running/waiting 并发是否饱和、P 侧 kv_cache_usage_perc 是否高企、D 侧 TTFT 是否恶化；租约时长参数是否匹配 D 的最长排队时间。
- **角色过滤**：所有查询可加 `label_role_name=~"decode"`（直方图类）或 `=~"prefill"`（租约类）聚焦有效侧；直方图家族在 prefill 侧的 0 值序列属正常现象，不代表异常。

### 3.1 计时边界分层（xfer_time 在完整交接中的位置）

```text
T_xfer    ≈ T_post + T_后端搬运与完成检测
T_handoff ≈ T_准备/等待 + T_xfer + T_就绪/状态同步
```

- `T_后端搬运与完成检测` 含后端排队、真实数据搬运、进度推进，**不能把 xfer_time 视作纯网络时间**。
- 第二式是**解释性分层**，不能拿 Histogram 直接相加（多 rank、多次传输相互重叠）。xfer_time 不含交接前的调度等待与 KV 元数据准备，也不含完成通知与 P 侧资源释放——decode 侧 TTFT 与 xfer_time 的差值主要落在这些环节。
- 时间轴图解见 `PD_NIXL_对话整理/images/nixl_timeline.svg`。

### 3.2 失败计数器口径（本分支源码核实）

`record_failed_transfer` 与 `record_failed_notification` 是**两个独立计数器，调用点分离**：

- `record_failed_transfer`：`push_worker.py:703`、`base_worker.py:2290`（`_handle_failed_transfer`）。
- `record_failed_notification`：`pull_worker.py:240`（传输完成后通知远端 rank 失败）、`pull_worker.py:301`（全量前缀命中场景的通知发送失败）。
- 特例：`pull_worker.py:138` 对已知失效远端 engine 走 `_handle_failed_transfer(record_failed_transfer=False)`，**不计入** failed_transfers。

**版本口径警告**：部分上游 vLLM 版本把 handshake / 传输 / 通知失败**综合计入** failed_transfers（见 `PD_NIXL_对话整理/README.md` §5.1 的警告）；本部署分支已核实分开计数，排查时两者各自独立解读，**不要再相加当作"总失败数"**。失败事件分层图解见 `PD_NIXL_对话整理/images/failure_layers.svg`。

### 3.3 诊断 PromQL 示例

窗口可按需替换 `[5m]`；`label_id` 换成目标服务 ID。

```promql
# decode 侧失败传输 / 失败通知增量（5m）
sum(increase(vllm:nixl_num_failed_transfers_total{label_id="<服务ID>",label_role_name="decode"}[5m]))
sum(increase(vllm:nixl_num_failed_notifications_total{label_id="<服务ID>",label_role_name="decode"}[5m]))

# prefill 侧 KV 租约过期增量（5m）
sum(increase(vllm:nixl_num_kv_expired_reqs_total{label_id="<服务ID>",label_role_name="prefill"}[5m]))

# 每 Pod 平均传输 / 提交耗时（秒）
sum by (pod) (rate(vllm:nixl_xfer_time_seconds_sum{label_id="<服务ID>",label_role_name="decode"}[5m]))
  / sum by (pod) (rate(vllm:nixl_xfer_time_seconds_count{label_id="<服务ID>",label_role_name="decode"}[5m]))
sum by (pod) (rate(vllm:nixl_post_time_seconds_sum{label_id="<服务ID>",label_role_name="decode"}[5m]))
  / sum by (pod) (rate(vllm:nixl_post_time_seconds_count{label_id="<服务ID>",label_role_name="decode"}[5m]))

# 每 Pod 平均描述符数
sum by (pod) (rate(vllm:nixl_num_descriptors_sum{label_id="<服务ID>",label_role_name="decode"}[5m]))
  / sum by (pod) (rate(vllm:nixl_num_descriptors_count{label_id="<服务ID>",label_role_name="decode"}[5m]))

# NIXL 吞吐（MiB/s；为应用层观测值，非网卡物理吞吐）
sum(rate(vllm:nixl_bytes_transferred_sum{label_id="<服务ID>",label_role_name="decode"}[5m])) / 1024 / 1024
```

### 3.4 建议故障判断顺序

```text
TTFT / 成功率 → Queue / Prefill Time → NIXL xfer / post / bytes / descriptors
→ failed / notifications / expired → decode ITL / TPOT、KV usage、日志
```

先看用户可感知面（延迟、成功率），再逐层下钻到传输链路，最后回到 decode 生成侧与日志交叉验证。

### 3.5 常见误区

- **描述符数升高 ≠ KV 体积变大**：descriptors 是段数（≈ 块数 × 层数），bytes 才是体积；同体积可对应不同段数，二者要联看。
- **KV offload bytes ≠ PD 传输字节**：offload 是缓存卸载/加载指标；跨实例搬运看 `nixl_bytes_transferred`。
- **failed_transfers 非零 ≠ 用户请求失败**：可能仅是通知失败或已重试成功，须结合日志与 HTTP 状态码。
- **传输次数 ≠ 请求数**：观测单位是"次传输"，TP>1 时每请求每 rank 各记一次（`_count` ≈ 请求数 × tp_size），TP=1 时才约等于迁移请求数（见 §1.2 标签粒度）。
- **P 侧直方图恒 0 ≠ 异常**：观测只发生在 decode 侧（见开头角色分布总述）。
