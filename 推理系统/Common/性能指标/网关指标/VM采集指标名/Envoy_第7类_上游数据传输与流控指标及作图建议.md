# Envoy 第 7 类指标：上游数据传输与流控（Data Transfer & Flow Control）

> 适用场景：Envoy Gateway / AiBrix / HTTPRoute 上游 Cluster / vLLM 在线推理，尤其是 SSE 流式响应。  
> 统计范围：仅针对已采集的 `envoy_cluster_name=~"httproute/.*"` 数据序列。  
> 本类共 **8 个指标**，推荐绘制 **4 张 Grafana 折线图**（每张图两条指标曲线，按 HTTPRoute/Envoy Pod 维度筛选）。

## 1. 基本概念

### 1.1 RX 与 TX 的方向

这里的方向以 **Envoy 的上游连接** 为参照：

```text
Client  ──HTTP Request──>  Envoy  ──TX──> vLLM / 上游 Endpoint
Client  <──HTTP/SSE─────  Envoy  <──RX── vLLM / 上游 Endpoint
```

- **TX（Transmit）**：Envoy 向上游发送数据，通常对应转发 HTTP 请求。
- **RX（Receive）**：Envoy 从上游接收数据，通常对应接收 HTTP 响应（包括 SSE 事件）。
- **Connection 与 Request 不同**：一条 HTTP/2 上游连接可以承载多个请求；这些指标是 Cluster/连接层聚合统计，不是单次推理请求指标。

### 1.2 三类数据

1. **累计传输字节（Counter）**：历史累计传输量，用 `rate()` 看 Byte/s。
2. **当前缓冲字节（Gauge）**：当前缓冲区中尚未被后续流程消耗的数据量，用瞬时值看 Bytes。
3. **流控事件（Counter）**：数据传输受到限制时，暂停/恢复读取的事件数，用 `increase()` 看一段时间内的次数。

## 2. 八个指标总览

| 子类 | 指标 | 类型 | 含义 | LLM 场景价值 |
|---|---|---|---|---|
| 数据传输量 | `envoy_cluster_upstream_cx_rx_bytes_total` | Counter | 从上游收到的累计字节数 | 响应方向吞吐量，优先关注 SSE |
| 数据传输量 | `envoy_cluster_upstream_cx_tx_bytes_total` | Counter | 发送到上游的累计字节数 | 请求体、Prompt 传输量 |
| 缓冲区占用 | `envoy_cluster_upstream_cx_rx_bytes_buffered` | Gauge | 上游读取方向当前缓冲字节数 | 响应数据是否积压 |
| 缓冲区占用 | `envoy_cluster_upstream_cx_tx_bytes_buffered` | Gauge | 上游写入方向当前缓冲字节数 | 请求数据是否积压 |
| 流控与背压 | `envoy_cluster_upstream_flow_control_paused_reading_total` | Counter | 因流控暂停从上游读取的次数 | 响应方向流控 |
| 流控与背压 | `envoy_cluster_upstream_flow_control_resumed_reading_total` | Counter | 因流控恢复从上游读取的次数 | 响应方向恢复 |
| 流控与背压 | `envoy_cluster_upstream_flow_control_backed_up_total` | Counter | 上游写入受阻，向下游传播背压的次数 | 请求方向流控 |
| 流控与背压 | `envoy_cluster_upstream_flow_control_drained_total` | Counter | 上游写缓冲排空到恢复条件、解除相应背压的次数 | 请求方向恢复 |

> 注意：接收/发送字节数不是 Input/Output Token 数；Buffered 是瞬时占用，不是缓冲区大小上限；流控事件不等同于请求失败。具体缓冲含义和上游协议细节应结合部署版本的 Envoy stats HELP 信息确认。

## 3. 分组分析

### 3.1 数据吞吐量（2 个）

- `rx_bytes_total`：vLLM → Envoy 的累计接收数据量。用 `rate()` 得到响应方向 Byte/s。
- `tx_bytes_total`：Envoy → vLLM 的累计发送数据量。用 `rate()` 得到请求方向 Byte/s。

**分析要点**：吞吐量受 RPS、请求体大小、响应内容长度、HTTP 协议开销影响。RX 高可能仅说明推理响应多，**不能单独判定拥塞**。

### 3.2 Buffer 占用（2 个）

- `rx_bytes_buffered`：从上游接收但还在 Envoy 上游读取缓冲中的字节。持续增长可能说明后续处理/下游转发未及时消耗。
- `tx_bytes_buffered`：准备发往上游但尚未完全发送的字节。持续增长可能说明上游写入受阻。

**分析要点**：一次短暂峰值可能正常；持续高位或不断增长更值得排查。Buffer 指标与流控指标、请求异常指标结合看，不能直接等同网络拥塞。

### 3.3 响应方向流控（2 个）

- `paused_reading_total`：Envoy 暂停读取上游连接的事件累计次数。
- `resumed_reading_total`：Envoy 恢复读取上游连接的事件累计次数。

典型示意：`vLLM → Envoy → Client`，当下游消费受阻，背压可能传播到 Envoy 的上游读取，暂停后再恢复。

**分析要点**：成对的暂停/恢复频繁发生，说明流控切换频繁；单独出现暂停也未必是故障。**不要直接用暂停次数减恢复次数作为当前暂停连接数**。

### 3.4 请求方向背压（2 个）

- `backed_up_total`：上游写缓冲积压，导致 Envoy 暂停读取下游数据的累计事件数。
- `drained_total`：上游写缓冲恢复到可继续处理的状态，Envoy 恢复读取下游数据的累计事件数。

典型示意：`Client → Envoy → vLLM`，大的请求体可能遇到上游发送速度低于下游到达速度而触发背压。

**分析要点**：这对指标重点是 **Envoy 写上游受阻**，不要和响应方向的 `paused_reading/resumed_reading` 混淆。

## 4. Grafana 作图建议：4 张图

建议设置 Grafana 变量：

- `$cluster`：`envoy_cluster_name`，值为 HTTPRoute 对应的 Cluster 名称，可支持 `.*` 全选。
- `$pod`：Envoy Proxy Pod 名称，可支持 `.*` 全选。
- 查询中的 `=~"$cluster"`、`=~"$pod"` 为 Grafana 正则变量占位符；在 VMUI 单独执行时改成实际标签选择条件。

建议按同一个 `envoy_cluster_name` 选择查看，必要时保留 `pod` 用于定位不同 Envoy 实例。多个 HTTPRoute 混合时，每个 Cluster 将各有 RX/TX 两条系列，线条可能过多。

### 图 1：上游数据吞吐量（RX / TX）

**图形**：Time series，单位 **Byte/s**（可自动显示 KiB/s、MiB/s）。

```promql
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_rx_bytes_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
)
```

```promql
sum by (envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_tx_bytes_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
)
```

图例分别命名 `RX - {{envoy_cluster_name}}`、`TX - {{envoy_cluster_name}}`。

**看什么**：响应吞吐、请求吞吐变化；若 RX/TX 同时大幅变化，先核对 RPS 与模型响应长度，不要直接归因网络瓶颈。

### 图 2：上游缓冲区占用（RX / TX Buffer）

**图形**：Time series，单位 **Bytes**。

```promql
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_rx_bytes_buffered{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }
)
```

```promql
sum by (envoy_cluster_name) (
  envoy_cluster_upstream_cx_tx_bytes_buffered{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }
)
```

**看什么**：是否长期积压，峰值是否与吞吐量变化或超时、重置同步出现。按故障 Pod 排查时，建议把 `pod` 加到 `sum by` 分组中。

### 图 3：响应方向流控（Pause / Resume）

**图形**：Time series，单位 **events/min**。采用过去 5 分钟平均每分钟发生次数，趋势更平稳。

```promql
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_paused_reading_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
) / 5
```

```promql
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_resumed_reading_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
) / 5
```

**看什么**：Envoy 是否频繁暂停/恢复读取 vLLM 响应；若频繁出现，可进一步检查 Downstream 发送缓冲、客户端读取能力和请求异常。

> 如果希望展示“最近 5 分钟累计事件数”，直接移除 `/ 5` 并将单位改为 `events / 5min`。不要把 `increase(...[5m])` 的结果直接标成每分钟次数。

### 图 4：请求方向背压（Backed up / Drained）

**图形**：Time series，单位 **events/min**。

```promql
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_backed_up_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
) / 5
```

```promql
sum by (envoy_cluster_name) (
  increase(envoy_cluster_upstream_flow_control_drained_total{
    envoy_cluster_name=~"$cluster",pod=~"$pod"
  }[5m])
) / 5
```

**看什么**：Envoy 向 vLLM 发送请求数据是否频繁受阻，以及背压是否及时解除。大 Prompt、多模态请求可重点观察。

### 建议面板布局

```text
┌───────────────────────────────┬───────────────────────────────┐
│ ① 上游数据吞吐量              │ ② 上游缓冲区占用              │
│    RX / TX · Byte/s           │    RX / TX · Bytes            │
├───────────────────────────────┼───────────────────────────────┤
│ ③ 响应方向流控                │ ④ 请求方向背压                │
│    Paused / Resumed · 次/min  │    Backed up / Drained · 次/min│
└───────────────────────────────┴───────────────────────────────┘
```

## 5. 联合排障思路

| 观察组合 | 初步分析方向 | 进一步核实 |
|---|---|---|
| RX 吞吐升高，RX Buffer 不高 | 数据传输增加，未见明显接收缓冲积压 | RPS、响应长度、vLLM Output Token 数 |
| RX Buffer 持续升高，Pause 频繁 | 响应方向可能受到下游消费/处理能力限制 | Downstream 指标、SSE 客户端、连接与请求重置 |
| TX Buffer 持续升高，Backed up 频繁 | 向上游发送请求体受阻，可能有背压 | 后端接收性能、网络、HTTP 请求体大小 |
| Pause/Resume 持续频繁 | 流控反复切换 | 水位线、下游发送速率、相关超时 |
| Flow Control 上升且 `upstream_rq_timeout` / Reset 增加 | 存在时间关联的潜在传输问题 | 结合请求日志确认，**不能仅凭相关性推断因果** |

结合其他类别的关键指标：

- 第 6 类：`envoy_cluster_upstream_cx_connect_fail`、`envoy_cluster_upstream_cx_destroy_with_active_rq`。
- 第 8 类：`envoy_cluster_upstream_rq_active`、`envoy_cluster_upstream_rq_timeout`、`envoy_cluster_upstream_rq_rx_reset`、`envoy_cluster_upstream_rq_tx_reset`。
- vLLM：TTFT、TPOT、Waiting/Running Requests、Token 吞吐。**Envoy Byte/s 不等于 vLLM Token/s**。

## 6. 监控优先级建议

| 子类 | 推荐级别 | 理由 |
|---|---|---|
| RX 吞吐 | 高 | 直接反映 SSE 响应方向的网络输出量 |
| TX 吞吐 | 中 | 辅助分析 Prompt / Request Body 的传输量 |
| RX Buffer | 高 | 关注响应方向的积压 |
| TX Buffer | 中 | 关注请求方向的积压 |
| Pause / Resume | 高 | 响应方向的流控事件 |
| Backed up / Drained | 中 | 请求方向的背压事件 |

## 7. 一句话总结

**用 4 张图分别回答：传输了多少数据、当前积压多少数据、响应方向是否触发流控、请求方向是否触发背压。** 第 7 类定位的是 Envoy 网络数据传输，不是模型推理本身的速度；最终应结合第 6 类连接事件、第 8 类请求事件和 vLLM 指标分析。

## 参考资料

- Envoy 官方 Cluster statistics：https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats
- Envoy 官方 Flow control：https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/flow_control
