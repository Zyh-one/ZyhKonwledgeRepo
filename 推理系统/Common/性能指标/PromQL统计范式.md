# 1. 统计范式

## 1.1 PromQL 的求值时刻与时间轴

一条 PromQL 描述的是：**在某一个求值时刻，如何计算这个时刻的结果**。

图表展示多长时间、生成多少个点，由前端范围查询的 `start`、`end` 和 `step` 决定，**和PromQL中的时间数据没有任何关系**。例如：

```text
start = 20:00
end   = 20:20
step  = 30s
```

相当于 VMSelect 在 20:00:00、20:00:30、20:01:00……20:20:00 分别执行一次相同的 PromQL。每次执行时，表达式中的 `[5m]`、`[30m:30s]` 等范围都相对于当前求值时刻向前计算。

因此，`[10m:30s]` 不表示图表每 10 分钟画一个点。`10m` 是内部统计窗口，`30s` 是子查询 resolution；图表描点间隔仍由外部 `step` 决定。

## 1.2 标签过滤

```promql
namespace="inference"  # = 表示精确匹配
pod=~"worker-.*"       # =~ 表示正则匹配
```

前端模板中的 `%(cluster)s`、`%(namespace)s`、`%(pod)s`、`%(container)s` 会在查询前替换成实际筛选条件。

## 1.3 Gauge：对瞬时值求时间平均

Gauge 表示当前状态，可以升高也可以降低。通用范式为：

```promql
avg_over_time(
  gauge_metric{过滤条件}[%(time)s:30s]
)
//%(time)是需要大于30s
```

计算过程如下：

1. 在当前求值时刻向前取 `%(time)s` 的范围。
2. 以 30 秒为子查询 resolution 形成一组中间结果。
3. 使用 `avg_over_time()` 计算平均值。

容器内存的实际查询为：

```promql
sum by (cluster, pod, container) (
  avg_over_time(
    container_memory_working_set_bytes{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      container=~"%(container)s",
      pod=~"%(pod)s"
    }[%(time)s:30s]
  )
)
```

采用该范式的前端指标包括：

- `containerMemoryUsage`
- `containerMluUtilization`、`containerMluMemUtilization`、`containerMluPowerConsumption`
- `containerGpuUtilization`、`containerGpuMemUtilization`、`containerGpuPowerConsumption`

## 1.4 Counter：先计算速率，再对速率求平均

Counter 是从进程或容器启动以来的**累计值**，正常情况下只增不减，重启后可能归零。它通常需要先通过 `rate()` 转换为每秒速率：

```promql
avg_over_time(
  rate(counter_metric{过滤条件}[5m])
  [%(time)s:30s]
)
```

```text
累计 Counter
  └─ rate(...[5m])：最近 5 分钟的平均每秒增长量
       └─ avg_over_time(...[time:30s])：展示窗口内的平均速率
```

`rate()` 会利用窗口内多个样本识别 Counter reset（数据中间出现重置，表示服务重启）。为了理解语义，可以把它近似看成 `(末值 - 初值) / 经过秒数`，但实际实现并不只是简单的首尾相减。

| 原始累计量                       | 原始单位 | `rate()` 后单位 | 含义                |
| -------------------------------- | -------- | ----------------- | ------------------- |
| CPU 时间                         | seconds  | seconds/second    | 平均使用的 CPU 核数 |
| 网络、磁盘、MLULink、RDMA 字节数 | bytes    | bytes/second      | 平均传输速率        |

例如：

```promql
avg_over_time(
  rate(container_cpu_usage_seconds_total{...}[5m])[30m:30s]
)
```

在 20:20 求值时，它会在 19:50～20:20 之间每 30 秒计算一次 `rate(...[5m])`，每次 `rate()` 又读取对应时刻之前 5 分钟的 Counter 样本，最后对这些速率求平均。（一次典型的计算指标过程）

采用该范式的前端指标包括：

- `containerCpuUsage`
- `containerNetworkTransmitBytes`、`containerNetworkReceiveBytes`
- `containerMluLinkReadBytes`、`containerMluLinkWriteBytes`
- `containerRdmaReceivedBytes`、`containerRdmaTransmittedBytes`
- `containerDiskReadBytes`、`containerDiskWriteBytes`

这些变量名中的 `Bytes` 表示底层 Counter 累计的是字节；经过 `rate()` 后，PromQL 实际输出单位是 `bytes/s`。

## 1.5 `sum by`：按目标标签聚合

时间函数解决“一个时间范围如何计算”，`sum by` 解决“多条时间序列如何合并”。

```promql
sum by (cluster, pod, container) (...)
```

它将 `cluster`、`pod`、`container` 相同的序列相加，并丢弃其他标签。例如底层指标可能按 CPU、网卡或文件系统设备形成多条序列，前端只需要容器维度时，就通过该操作完成折叠。

网络指标较特殊：当前实现只支持 Pod，查询没有使用 `container` 过滤条件，因为 containerd 不一定为 sandbox container 添加该标签。因此不能仅凭前端变量名，把网络数据理解成严格的单容器数据。

## 1.6 指标间计算：CPU 使用量除以 Limit

`containerCpuUtilization` 不是原始 metric，而是两个 metric 的派生结果：

```promql
sum by (cluster, pod, container) (
  avg_over_time(
    rate(container_cpu_usage_seconds_total{...}[5m])
    [%(time)s:30s]
  )
)
/
sum by (cluster, pod, container) (
  kube_pod_container_resource_limits{resource="cpu", ...}
)
* 100
```

```text
容器平均使用的 CPU 核数 / 容器配置的 CPU Limit × 100%
```

例如 CPU Limit 为 16 核，最近一段时间平均使用 8 核，则利用率为 50%。这里的利用率相对于容器 Limit，而不是整台 Node 的 CPU 容量。容器未配置 Limit，或者分子、分母标签不能匹配时，查询可能得不到结果。

## 1.7 设备指标与容器的归属映射

部分 metric 原生带有 `namespace`、`pod`、`container` 标签；另一些只描述硬件设备，需要借助关联指标映射到容器。

### 1.7.1 MLU Gauge 映射

```promql
avg_over_time(
  mlu_utilization{cluster=~"%(cluster)s"}[%(time)s:30s]
)
*
on (uuid, type, vf)
group_right
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
```

这里的乘法主要用于向量匹配和标签补充：

```text
设备指标（uuid/type/vf → 指标值）
          ×
归属指标（uuid/type/vf → namespace/pod/container）
          ↓
带容器归属信息的 MLU 指标
```

一张mlu板卡(uuid+vf标识)，可能会多个container进行使用，故使用group_right

### 1.7.2 MLULink Counter 映射

```promql
avg_over_time(
  rate(mlu_mlulink_cntr_read_byte_total{...}[5m])
  [%(time)s:30s]
)
*
on (uuid, type)
group_left(namespace, pod, container)
mlu_container{...}
```

`mlu_mlulink_cntr_read_byte_total`对应mlu板卡上的mlulink，一张板卡上的mlulink有着8条link链路，一个container通过uuid关联一张唯一mlu板卡，同时该container可能使用该mlu板卡上的多条mlulink链路，故使用group_left

它先把累计字节转换为 `bytes/s`，再按 `uuid`、`type` 找到容器，并从右侧带入 `namespace`、`pod`、`container` 标签。

### 1.7.3 RDMA device 映射

```promql
sum by (cluster, node, pod, container, device) (
  rdma_container{...}
)
*
on (cluster, node, device)
group_left()
sum by (cluster, node, device) (
  avg_over_time(
    rate(node_infiniband_port_data_received_bytes_total{...}[5m])
    [%(time)s:30s]
  )
)
```

一个infiniband协议对应的网卡是通过(cluster,node,device)进行标识，其中device是比较关键的，一台机器可能有多张网卡，一台机器上可能存在多个container共享一张网卡，所以使用group_left

`node-exporter` 提供 InfiniBand 端口真实收发 Counter，`rdma_container` 提供 device 与容器的归属关系，二者通过 `cluster`、`node`、`device` 完成匹配。

## 1.8 Counter：统计窗口内的增量

当图表关心“这段时间一共发生了多少次或处理了多少 Token”时，使用：

```promql
sum by (...) (
  increase(counter_metric{...}[%(time)s:30s])
)
```

`increase()` 把 Counter 在当前查询窗口内的增长量转换为总量，并能处理进程重启造成的 Counter reset。结果单位仍是原 Counter 的单位，例如 request、token 或 byte；它不是每秒速率。

`[%(time)s:30s]` 中，`%(time)s` 是统计窗口，30 秒是子查询 resolution，不代表 vmagent 的抓取间隔。请求量、Token 消耗量、缓存命中次数、抢占次数和 KV 卸载字节数均采用这一范式。

## 1.9 Gauge：窗口平均与并发状态组合

运行请求数、等待请求数和 KV Cache 利用率都是 Gauge：

```promql
sum by (...) (
  avg_over_time(gauge_metric{...}[%(time)s:30s])
)
```

总并发度再把 Running 与 Waiting 在相同标签维度下相加。只有两侧保留的标签能够一对一匹配，PromQL 加法才会产生结果。

## 1.10 Histogram：分位数

```promql
histogram_quantile(
  %(tp)s,
  sum by (..., le) (
    rate(histogram_metric_bucket{...}[%(time)s:30s])
  )
)
```

`rate(_bucket)` 计算各累计桶每秒新增的观测数量，`sum by (..., le)` 在保留桶上界 `le` 的前提下合并实例，`histogram_quantile()` 再估算 P50、P90、P99。结果是桶内插值，不是原始样本的精确排序值；聚合前不能丢弃 `le`。

### 1.10.1 `le` 是累计桶上界

假设 `request_queue_time_seconds_bucket` 在某个查询窗口内得到以下累计观测数：

| `le` | 累计请求数 | 对应含义 |
| --- | ---: | --- |
| `0.1` | 20 | 排队时间小于等于 0.1 秒的请求共有 20 个 |
| `0.2` | 50 | 排队时间小于等于 0.2 秒的请求共有 50 个 |
| `0.5` | 80 | 排队时间小于等于 0.5 秒的请求共有 80 个 |
| `1` | 95 | 排队时间小于等于 1 秒的请求共有 95 个 |
| `+Inf` | 100 | 所有请求共有 100 个 |

每个 bucket 都包含前面的 bucket，不能把 `le="0.5"` 理解为只有 0.2～0.5 秒的请求。各非累计区间的请求数需要用相邻累计值相减：

```text
(0.0, 0.1]：20
(0.1, 0.2]：50 - 20 = 30
(0.2, 0.5]：80 - 50 = 30
(0.5, 1.0]：95 - 80 = 15
(1.0, +Inf)：100 - 95 = 5
```

这也是 `sum by (..., le)` 必须保留 `le` 的原因：`histogram_quantile()` 需要每个桶的上界和累计计数，才能判断目标分位点落在哪个区间。

### 1.10.2 P90 的定位与线性插值

`histogram_quantile(0.9, ...)` 首先根据 `+Inf` 桶得到总观测数 100，然后计算 P90 的目标 rank：

```text
rank = 0.9 × 100 = 90
```

累计到 `le="0.5"` 时只有 80 个请求，累计到 `le="1"` 时已有 95 个请求，因此第 90 个请求位于 `(0.5, 1.0]` 桶内。这个桶自身包含：

```text
95 - 80 = 15 个请求
```

但经典 Histogram 只保存桶计数，不知道这 15 个请求在 0.5～1.0 秒之间的真实位置。Prometheus 因而假设它们在桶内均匀分布，并做线性插值：

```text
分位数所在桶的下界 lower          = 0.5
分位数所在桶的上界 upper          = 1.0
进入该桶前的累计数 countBefore   = 80
该桶的非累计观测数 countInBucket = 95 - 80 = 15

P90 = lower
      + (upper - lower)
        × (rank - countBefore) / countInBucket

    = 0.5 + (1.0 - 0.5) × (90 - 80) / 15
    ≈ 0.833 秒
```

因此结果约为 0.833 秒。它不表示系统真的观测到一个 0.833 秒的请求，而是根据桶边界和累计计数估算出：约 90% 的请求排队时间不超过 0.833 秒。

同一组桶计算 P50 时，`rank=50`，恰好落在 `le="0.2"` 的累计边界上，结果为 0.2 秒。P99 的 `rank=99` 落入最高的 `+Inf` 桶；经典 Histogram 无法在无穷区间内插值，因此 `histogram_quantile()` 返回倒数第二个有限桶的上界，即 1 秒。最高有限桶设置得过低时，高分位数会失去区分度。

### 1.10.3 插值误差来自桶宽

线性插值隐含“桶内均匀分布”假设。如果 `(0.5, 1.0]` 中的请求实际都集中在 0.51 秒附近，估算出的 0.833 秒会偏高；如果都集中在 0.99 秒附近，则会偏低。

因此，分位数精度由桶边界决定：目标区间的桶越窄，插值误差通常越小。调整 bucket 时应在关键 SLO 附近设置更密的边界。例如关注 TTFT 是否小于 1 秒，就应避免让 1 秒落在跨度很大的桶中。


延迟 Histogram 的结果通常为秒，Token 数量和传输大小 Histogram 分别为 token 和 byte。当前 TPOT 查询额外乘以 1000，前端结果为毫秒。

## 1.11 Histogram：平均值

```promql
sum by (...) (rate(histogram_metric_sum{...}[%(time)s:30s]))
/
sum by (...) (rate(histogram_metric_count{...}[%(time)s:30s]))
```

分子是观测值总和的增长速率，分母是观测次数的增长速率，相除得到每次观测的平均值。应先分别聚合再相除；不能先计算各 Pod 平均值后简单平均。窗口内没有新观测时分母为 0，结果可能为空或 `NaN`。

## 1.12 两个 Counter 的比率

```promql
sum by (...) (increase(numerator_total{...}[%(time)s:30s]))
/
sum by (...) (increase(denominator_total{...}[%(time)s:30s]))
* 100
```

该范式表达窗口内事件数之比。分子与分母必须来自相同统计范围、采用相同聚合标签，且业务定义上分子应属于分母。分母为 0 时结果不可解释。

## 1.13 Gauge 样本占比不等于请求事件占比

当前“推理排队率”实际计算：

```text
等待并发样本之和 /（运行并发样本之和 + 等待并发样本之和）× 100%
```

采样间隔稳定时，它近似表示窗口内“请求槽位时间”处于等待状态的比例。因此更准确的名称是**等待并发占比**，不是“有多少请求曾排过队”的事件占比。

## 1.14 Histogram 热力图

热力图对 `_bucket` 使用 `increase()` 并保留 `le`。Histogram bucket 是累计桶：`le="1024"` 包含所有小于等于 1024 的观测。若前端需要非累计区间，必须由组件转换或用相邻累计桶相减。

## 1.15 跨 metric 关联与按卡归一化

每卡每秒 Token 的目标语义为：

```text
Pod Token/s / Pod 申请的加速卡数 = Token/(card·s)
```

当前查询用 `on(pod)` 关联宽泛的 `resource=~".*(cambricon|nvidia).*"`，依赖每个 Pod 只匹配一条卡资源序列。更稳妥的实现应先把右侧按 `(cluster, namespace, pod)` 汇总，精确限定实际 MLU/GPU resource 名，再使用 `on(cluster, namespace, pod)`。否则可能错误匹配、many-to-many 或重复计算。

该指标按申请卡数归一化，不是按实际忙碌卡数归一化。
