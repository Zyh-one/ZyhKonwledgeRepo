# 黄区 VictoriaMetrics CRD 资源分析

## 1. 文档范围

本文基于 2026 年 8 月 30 日对黄区生产 Kubernetes 集群的只读查询，说明 VictoriaMetrics Operator CRD 如何协调采集、存储、查询和规则组件。

本文只记录资源类型、对象名称、非敏感 `spec`、状态和对象关系，未读取 Secret 内容，也未对集群执行任何修改。

## 2. 核心理解

VictoriaMetrics CRD YAML 是提交给 Kubernetes API 的声明式配置。真正的执行过程是：

```text
用户提交 CRD YAML
  → Kubernetes API 保存期望状态
  → VictoriaMetrics Operator 监听并解析
  → 生成或更新 Deployment、StatefulSet、Service 和运行配置
  → vmagent、vminsert、vmstorage、vmselect、vmalert 等组件执行
```

因此可以把 CRD 分成两类：

1. **组件声明**：描述需要运行哪些 VictoriaMetrics 组件以及副本、存储和连接参数；
2. **任务声明**：描述 vmagent 抓取哪些目标，或 vmalert 执行哪些规则。

CRD 不是所有子模块直接共享的一份配置文件。Operator 是声明与实际工作负载之间的协调者。

## 3. 黄区实际使用情况

### 3.1 组件类 CRD

| CRD                | Namespace/名称                | 黄区状态    | 作用                               |
| ------------------ | ----------------------------- | ----------- | ---------------------------------- |
| `VMAgent`        | `monitoring/vmagent`        | operational | 生成采集器并汇总抓取声明           |
| `VMCluster`      | `monitoring/vmcluster`      | operational | 生成 vminsert、vmstorage、vmselect |
| `VMAlert`        | `monitoring/vmalert`        | operational | 生成规则计算组件                   |
| `VMAlertmanager` | `monitoring/vmalertmanager` | operational | 生成告警管理组件                   |

### 3.2 任务类 CRD

| CRD                 | 实例分布                                                                                       | 黄区用途                                 |
| ------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------- |
| `VMServiceScrape` | `monitoring`、`aibrix-system`、`envoy-gateway-system`、`llm-webui`、`serving-system` | 按 Service 发现 Exporter 和应用指标端点  |
| `VMNodeScrape`    | `kube-system`                                                                                | 抓取 kubelet、cAdvisor 和 kubelet probes |
| `VMScrapeConfig`  | `monitoring`                                                                                 | 声明自定义/静态抓取目标                  |
| `VMRule`          | 多个系统和业务 Namespace                                                                       | 声明告警规则和 recording rules           |

### 3.3 已注册但本次未发现实例的 CRD

Operator 注册了更多资源类型，包括：

```text
VMPodScrape
VMStaticScrape
VMProbe
VMSingle
VMAuth
VMUser
VMAlertmanagerConfig
```

这些 CRD 类型“存在”只说明当前 Operator 支持它们。本次实例盘点未发现对应对象，不能描述成黄区正在使用这些模块。

## 4. 组件声明如何建立数据链路

### 4.1 VMAgent：汇总所有采集任务

黄区 `monitoring/vmagent` 的关键声明：

| 字段                       | 当前值                     | 含义                                 |
| -------------------------- | -------------------------- | ------------------------------------ |
| `shardCount`             | 2                          | 抓取目标被分到两个 shard             |
| `replicaCount`           | 1                          | 每个 shard 一个副本                  |
| `scrapeInterval`         | 30s                        | 默认抓取周期                         |
| `externalLabels.cluster` | `bj-caip`                | 为写入序列统一增加集群标签           |
| `serviceScrapeSelector`  | `{}`                     | 接受匹配范围内的所有 VMServiceScrape |
| `nodeScrapeSelector`     | `{}`                     | 接受匹配范围内的所有 VMNodeScrape    |
| `scrapeConfigSelector`   | `{}`                     | 接受匹配范围内的所有 VMScrapeConfig  |
| 各类`NamespaceSelector`  | `{}`                     | 允许从多个 Namespace 汇总采集声明    |
| `remoteWrite.url`        | 指向`vminsert-vmcluster` | 将样本写入 VMCluster 的写入口        |

简化关系：

```text
VMServiceScrape ─┐
VMNodeScrape ────┼→ VMAgent → vmagent → vminsert
VMScrapeConfig ──┘
```

`VMAgent` 决定“哪些采集声明归我处理”和“数据写到哪里”；具体抓取目标、端口、路径和 relabel 规则由各 Scrape CRD 提供。

### 4.2 VMCluster：声明存储查询集群

黄区 `monitoring/vmcluster` 的关键声明：

| 子模块        | 副本数 | 关键配置                                            |
| ------------- | -----: | --------------------------------------------------- |
| `vminsert`  |      2 | 接收 vmagent Remote Write，单序列最多 80 个标签     |
| `vmstorage` |      2 | 每个实例使用 40 Gi 本地持久卷，数据目录`/vm-data` |
| `vmselect`  |      4 | 提供 Prometheus 兼容查询接口                        |

集群保留周期为 `2232h`，约 93 天；`replicationFactor` 为 1。副本数表示组件横向实例数，但复制因子为 1 表示不能仅凭两个 vmstorage 就认定同一份数据保存了两份副本。

Operator 根据一个 `VMCluster` 对象生成并连接三个子模块：

```text
vmagent → vminsert → vmstorage ← vmselect ← monitor-server/Grafana
```

### 4.3 VMAlert：读取规则并计算

黄区 `monitoring/vmalert` 的关键声明：

| 字段                      | 当前值               | 含义                                       |
| ------------------------- | -------------------- | ------------------------------------------ |
| `replicaCount`          | 1                    | 一个规则计算实例                           |
| `evaluationInterval`    | 10s                  | 每 10 秒计算一次规则                       |
| `datasource.url`        | 指向`vmselect`     | 从 VictoriaMetrics 查询原始序列            |
| `remoteWrite.url`       | 指向`vminsert`     | 将 recording rule 结果写回存储             |
| `ruleNamespaceSelector` | 仅匹配`monitoring` | 当前 VMAlert 只选择 monitoring 中的 VMRule |

```text
monitoring/VMRule
  → VMAlert
  → vmalert
  → vmselect 查询输入数据
  └→ vminsert 写回 recording rule 结果
```

集群中也存在位于 `aibrix-system`、`envoy-gateway-system`、`llm-webui` 和 `serving-system` 的 VMRule，但这些对象状态未显示已被当前 VMAlert 应用。结合 `ruleNamespaceSelector`，可合理推断它们当前未被这个 `monitoring/vmalert` 选中；是否由其他机制消费尚待进一步确认。

当前 VMAlert 的 `spec.notifier` 未显式配置，因此仅凭该 CRD 不能确认告警事件发送到哪个 Alertmanager。

### 4.4 VMAlertmanager：声明告警管理组件

黄区 `monitoring/vmalertmanager` 声明一个副本、40 Gi 本地持久卷，并引用名为 `vmalertmanager-config` 的配置 Secret 和邮件模板。

这里只能确认 Operator 根据 CRD 创建告警管理工作负载；由于未读取 Secret 内容，具体接收器、邮件地址、路由和抑制规则不在本文确认范围内。

## 5. 三个代表性 VMServiceScrape

### 5.1 GPU Exporter

`monitoring/gpu-exporter`：

- 按 `app=gpu-exporter` 选择 Service；
- 抓取 `metrics` 端口的 `/metrics`；
- 周期为 30 秒；
- 将 Endpoint 所在节点名写入 `node` 标签；
- 对驱动版本标签进行整理，并删除部分冗余标签。

它展示了 VMServiceScrape 的完整职责：目标发现、抓取端点和标签加工。

### 5.2 LLM Serving

`monitoring/llm-serving-metrics`：

- 跨所有 Namespace 发现目标；
- Service 需同时满足 `type=predictor` 和存在 LLMServing 标签；
- 只保留名称匹配 `*-serving` 的 Service；
- 抓取 `serve` 端口的 `/metrics`；
- 将 Pod 的业务标签转成 `label_name`、`label_id`、`label_version` 和 `label_version_id`。

这解释了 PaaS 为什么能按 Predictor、版本和 Pod 查询 LLM 指标：一部分业务标签在 vmagent 抓取前由 relabel 规则注入时间序列。

### 5.3 Envoy Service Exporter

`envoy-gateway-system/envoy-svc-exporter-monitoring`：

- 按 `app=envoy-svc-exporter` 选择 Service；
- 抓取 `http` 端口；
- 周期为 30 秒；
- 允许跨 Namespace 选择目标。

该对象最终被 `monitoring/vmagent` 汇总并转换为真实抓取配置。

## 6. VMNodeScrape 与 VMScrapeConfig

### 6.1 VMNodeScrape

黄区 `kube-system` 中存在三个节点采集声明：

| 名称                 | 路径                  | 用途                            |
| -------------------- | --------------------- | ------------------------------- |
| `kubelet`          | kubelet 默认指标路径  | kubelet 运行指标                |
| `kubelet-cadvisor` | `/metrics/cadvisor` | Container CPU、内存、网络等指标 |
| `kubelet-probes`   | `/metrics/probes`   | 探针执行指标                    |

三者都通过 HTTPS 访问节点 `10250` 端口，默认周期为 30 秒，并使用 metric relabel 丢弃部分不需要的高成本或冗余指标。

### 6.2 VMScrapeConfig

`monitoring/native-pod-metrics` 使用静态目标列表抓取 `/metrics`，并通过 relabel 生成 `pod_name`、`pod_ip`、`service_name` 等标签。

它适用于无法通过标准 Service/Pod 选择器发现、需要直接声明地址或自定义发现规则的场景。文档不记录实际内部 IP。

## 7. operational 状态的边界

Scrape CRD 的状态中出现：

```text
reason: ConfigParsedAndApplied
updateStatus: operational
```

它能证明：

- Operator/vmagent 已解析并接受这份配置；
- 当前 CRD 已进入生成的采集配置。

它不能单独证明：

- selector 一定匹配到了 Service；
- Service 一定存在可用 Endpoint；
- `/metrics` 能成功访问；
- 目标当前为 UP；
- VictoriaMetrics 中一定存在对应时间序列。

完整验证仍需继续检查：

```text
CRD 已应用
  → selector 匹配 Service/Node
  → Endpoint 和端口存在
  → vmagent target 为 UP
  → vmselect 能查询到样本
```

## 8. 黄区 CRD 协调关系总图

```text
VMServiceScrape / VMNodeScrape / VMScrapeConfig
                    │ 被选择并转换
                    ▼
VMAgent ───────→ vmagent
                    │ remote write
                    ▼
VMCluster ─────→ vminsert → vmstorage ← vmselect
                                         ▲
                                         │ datasource
monitoring/VMRule → VMAlert → vmalert ───┘
                              │ recording rule write
                              └──────────→ vminsert

VMAlertmanager → vmalertmanager
```

这张图中，CRD 描述期望状态，Operator 负责把期望状态转换成实际组件和配置，组件再完成真正的数据采集、存储、查询和规则计算。

## 9. 结论与可信等级

| 结论                                                        | 等级     |
| ----------------------------------------------------------- | -------- |
| 黄区使用 VMAgent、VMCluster、VMAlert、VMAlertmanager        | 已确认   |
| vmagent 汇总跨 Namespace Scrape CRD，并写入 vminsert        | 已确认   |
| VMCluster 生成 2 个 vminsert、2 个 vmstorage、4 个 vmselect | 已确认   |
| 当前 VMAlert 只选择 monitoring Namespace 中的 VMRule        | 已确认   |
| 业务 Namespace 中状态空白的 VMRule 未被当前 VMAlert 消费    | 合理推断 |
| 当前告警通知最终发送到哪个接收器                            | 尚待确认 |
| operational 等于指标目标抓取成功                            | 不成立   |

## 10. 本次只读查询范围

本次使用的查询类型包括：

```text
kubectl api-resources
kubectl get <VictoriaMetrics CRD> -A
kubectl get <指定 CRD> -o json/yaml
```

查询范围仅覆盖 VictoriaMetrics Operator API 资源及指定 CRD 的非敏感配置。未执行 `apply`、`patch`、`delete`、`exec`、`port-forward` 等操作，未读取或解码任何 Secret。
