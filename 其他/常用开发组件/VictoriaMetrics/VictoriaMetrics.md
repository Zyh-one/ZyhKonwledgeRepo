Prometheus Serve本质上偏向单节点TSDB，但是随着规模的继续增长，就会开始碰到各种问题，比单机磁盘，查询压力，此时业界就开始出现各种替代方案，VictoriaMetrics就是其中的翘楚，但是这不以为着Prometheus的完全体系，相反它已经不只是一个软件，而是某种程度上的**“云原生Metrics标准体系”**

# VictoriaMetrics 体系与数据链路

## 1. VictoriaMetrics 是什么

VictoriaMetrics 是面向时间序列数据的监控存储与查询系统。它兼容 Prometheus 的关键接口，因此现有 Exporter、指标格式、标签模型、PromQL 查询和 Grafana 通常可以继续使用。

最重要的理解是：

> VictoriaMetrics 可以替代 Prometheus Server 的运行时职责，但不需要替换 Prometheus 指标生态。

因此，看到 Prometheus 格式的 `/metrics`、PromQL、`prometheus-adapter` 或名为 `prometheus-k8s` 的 ServiceAccount，都不能单独证明集群中运行着 Prometheus Server。是否存在某个系统，应以实际 Pod、Service、控制器和查询地址为准。

## 2. 两种部署形态

### 2.1 Single 版

`vmsingle` 在一个进程中提供写入、存储和查询，结构简单，适合开发、小规模环境或单机部署。

```text
vmagent → vmsingle ← 查询客户端
```

### 2.2 Cluster 版

Cluster 版将写入、存储和查询拆开，可分别扩容，适合生产环境：

```text
vmagent → vminsert → vmstorage ← vmselect ← 查询客户端
```

黄区生产环境采用 Cluster 版。

## 3. 核心组件与职责

| 组件                          | 职责                                        | 类比 Prometheus 体系中的能力       |
| ----------------------------- | ------------------------------------------- | ---------------------------------- |
| `victoria-metrics-operator` | 根据 VM 自定义资源管理采集、存储和规则组件  | Prometheus Operator 的控制器角色   |
| `vmagent`                   | 服务发现、定时抓取、relabel、缓存并转发样本 | Prometheus Server 的发现与抓取部分 |
| `vminsert`                  | 接收写入并把数据路由到`vmstorage`         | Remote Write 接收入口              |
| `vmstorage`                 | 持久保存时间序列数据                        | Prometheus TSDB 的存储部分         |
| `vmselect`                  | 从存储节点读取数据并执行 PromQL/MetricsQL   | Prometheus 查询 API                |
| `vmalert`                   | 周期执行告警规则和 recording rules          | Prometheus Rules                   |
| `vmalertmanager`            | 告警分组、去重、抑制和通知                  | Alertmanager                       |

Cluster 版并不是“一个 VictoriaMetrics 服务”，而是一组分工明确的服务。排障时必须先判断问题属于采集、写入、存储、查询还是规则计算。

## 4. 指标与时间序列

一个 Prometheus 格式样本由指标名、标签集合、数值以及隐含或显式时间戳组成：

```text
demo_gpu_utilization_percent{
  namespace="demo",
  pod="llm-pod-0",
  container="vllm",
  gpu="0"
} 72.5
```

其中的标签可能来自三个位置：

1. 指标生产者直接输出，例如应用知道自身模型、GPU 编号或请求状态；
2. `vmagent` 在服务发现和 relabel 阶段加入，例如 Namespace、Pod、Node；
3. recording rule 或 PromQL join 在加工结果中保留或生成。

## 5. 四条核心数据链路

### 5.1 指标写入链路

```text
应用、kubelet 或 Exporter
  → 暴露 Prometheus 文本格式 /metrics
  → VMServiceScrape / VMPodScrape / VMNodeScrape 描述抓取目标
  → vmagent 发现并定时抓取
  → vminsert 接收并分发
  → vmstorage 持久化
```

自定义资源只描述“抓谁、抓哪个端口、什么路径、多久一次”；真正发起 HTTP 抓取的是 `vmagent`。

### 5.2 普通查询链路

```text
Angular 页面
  → 业务监控后端 monitor-server
  → vmselect 的 Prometheus 兼容 API
  → vmstorage
```

Grafana 也通常把 `vmselect` 配置为 Prometheus 类型数据源：

```text
Grafana → vmselect → vmstorage
```

常用兼容接口包括：

```text
/select/<tenant>/prometheus/api/v1/query
/select/<tenant>/prometheus/api/v1/query_range
```

其中 `<tenant>` 是租户或账户编号；黄区当前地址中使用 `0`。

### 5.3 规则与告警链路

```text
VMRule
  → vmalert 周期执行查询
  → vmselect → vmstorage
  ├─ recording rule 结果 → vminsert → vmstorage
  └─ 告警事件 → vmalertmanager → 通知渠道
```

recording rule 会把复杂查询的结果保存为新时间序列，便于前端复用并降低重复查询成本。

### 5.4 HPA 自定义指标链路

```text
HPA
  → Kubernetes Custom/External Metrics API
  → prometheus-adapter
  → vmselect
  → vmstorage
```

`prometheus-adapter` 的职责是把 Prometheus 兼容指标转换成 Kubernetes 能识别的自定义或外部指标。它既不采集指标，也不存储指标，并且不是普通页面查询的必经节点。

## 6. Prometheus 兼容性

VictoriaMetrics 能够融入 Prometheus 生态，主要因为它兼容：

- Prometheus exposition format，即 `/metrics` 文本格式；
- 指标名、标签和值组成的时间序列模型；
- Prometheus Remote Write；
- Prometheus 查询 HTTP API；
- PromQL，并提供兼容扩展 MetricsQL；
- Grafana 的 Prometheus 数据源；
- 常见 Exporter 和服务发现方式。

因此，“VictoriaMetrics 后端”与“Prometheus 格式指标”并不矛盾。

## 7. Kubernetes 中的采集声明

黄区各 CRD 的实际实例、选择关系和配置流转见[黄区 VictoriaMetrics CRD 资源分析](黄区VictoriaMetrics-CRD.md)。

VictoriaMetrics Operator 常用自定义资源：

| 资源                | 采集对象                           |
| ------------------- | ---------------------------------- |
| `VMServiceScrape` | 通过 Service 和 Endpoint 发现目标  |
| `VMPodScrape`     | 直接按 Pod 标签发现目标            |
| `VMNodeScrape`    | Node、kubelet、cAdvisor 等节点目标 |
| `VMStaticScrape`  | 明确列出的静态地址                 |
| `VMRule`          | 告警规则和 recording rules         |
| `VMCluster`       | Cluster 版存储查询集群声明         |
| `VMAgent`         | 采集器声明                         |

采集声明可以分布在业务 Namespace 中。核心监控服务位于 `monitoring`，不代表所有 `VMServiceScrape` 和指标生产者也必须位于该 Namespace。

某个 `VMServiceScrape` 显示 operational，只说明 Operator 已接受并生成配置，不代表它的 selector 一定能匹配 Service，也不代表目标抓取成功。还要继续核对：

```text
selector 是否匹配 Service
→ Service 是否有 Endpoint
→ 端口名和路径是否正确
→ vmagent target 是否为 UP
→ 查询端是否出现时间序列
```
