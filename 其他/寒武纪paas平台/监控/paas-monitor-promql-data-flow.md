# PaaS 前端监控 PromQL 数据流程

## 1. 文档目的

本文梳理 PaaS Predictor 监控页面如何使用 PromQL：从 PromQL 常量、筛选变量、Monitor Server 查询，到 ECharts 最终绘图。

本文重点说明主数据流和各组件的职责边界，便于后续继续细化具体指标、接口和图表转换逻辑。

## 2. 总体流程

```text
PromQL constant
  ↓ 提供带占位符的查询模板
PredictorMonitorComponent
  ↓ 填入 namespace、Predictor UID 等固定参数
  ↓ 生成 MetricVariable[]
shared-container-monitor
  ↓ 根据监控类型分发变量配置
shared-metric-variable-select
  ↓ 查询 version、pod、container、path 等标签可选值
  ↓ emit 用户选中的筛选条件
shared-container-monitor
  ↓ 保存为 monitorVariableValues
  ↓ 分发给 hardware、service 或 llmservice 监控组件
具体图表组件
  ↓ 将筛选条件填入指标 PromQL
  ↓ 通过 QueryApi 请求 Monitor Server
Monitor Server / Prometheus
  ↓ 返回时间序列
getMatrixSeries()
  ↓ 转换为统一序列结构
getLineOption()
  ↓ 转换为 ECharts option
ChartConfig.option
  ↓ Angular [options] 绑定
ngx-echarts → ECharts → Canvas
  ↓
展示动态图表
```

整条链路包含两类 Prometheus 查询：

1. `shared-metric-variable-select` 查询“可以查谁”，例如有哪些版本、Pod 和容器。
2. 具体图表组件查询“指标是多少”，例如 CPU、内存、网络和设备利用率的时间序列。

## 3. 主要文件

### 3.1 Predictor 页面入口

```text
webapp/caip/projects/paas/src/app/pages/predictor/
  predictor-monitor/predictor-monitor.component.ts
  predictor-monitor/predictor-monitor.component.html
```

该页面负责：

- 订阅当前 Predictor 数据；
- 计算监控时间范围；
- 判断普通推理或 LLM Serving；
- 构造三组监控筛选变量；
- 将配置交给 `shared-container-monitor`。

三组变量分别是：

| 属性                       | 构造函数                         | 用途         | 变量链路                        |
| -------------------------- | -------------------------------- | ------------ | ------------------------------- |
| `metricVariables`        | `getPredictorMonitorMetrics()` | 硬件监控     | `version → pod → container` |
| `serviceMetricVariables` | `getPredictorServiceMetrics()` | 服务监控     | `version → path`             |
| `llmMetricVariables`     | `getLLMMonitorMetrics()`       | LLM 服务监控 | `version → pod`              |

### 3.2 标签筛选 PromQL

```text
webapp/caip/projects/paas/src/app/constant/container-query.constant.ts
```

其中包含：

- `podLabelsStatus`
- `podLabelsStatusWithPhase`
- `podLabelsStatusWithLLMPhase`
- `containerInfo`
- `envoySvcTotal`

这些常量是普通 TypeScript 字符串，包含 `%(name)s` 形式的占位符。

### 3.3 监控容器组件

```text
webapp/caip/projects/shared/src/lib/container-monitor/
  container-monitor.component.ts
  container-monitor.component.html
```

该组件承担中间协调职责：

- 接收三组 `MetricVariable[]`；
- 根据 `monitorType` 显示硬件、服务或 LLM 监控；
- 接收筛选组件发出的值；
- 保存 `monitorVariableValues`；
- 将筛选值传给具体图表组件。

### 3.4 筛选变量组件

```text
webapp/caip/projects/shared/src/lib/metric-variable-select/
  metric-variable-select.component.ts
```

该组件负责查询和选择标签值，不负责查询最终图表时间序列。

### 3.5 硬件图表组件

```text
webapp/caip/projects/shared/src/lib/container-monitor/components/hardware-monitor/
  hardware-monitor.component.ts
  container-hardware-monitor.component.ts
  container-hardware-monitor.component.html
```

- `HardwareMonitorComponent` 是公共抽象基类，负责响应输入变化、轮询和更新图表配置。
- `ContainerHardwareMonitorComponent` 提供容器指标配置并实现 `getRangeQuery()`。
- HTML 模板把每个 `ChartConfig.option` 绑定给 ECharts。

硬件指标 PromQL 位于：

```text
webapp/caip/projects/shared/src/lib/container-monitor/constant/
  container-query.constant.ts
```

## 4. 第一阶段：构造筛选变量

以 Predictor 硬件监控为例：

```ts
export const getPredictorMonitorMetrics = (predictor) => [
  {
    name: 'version',
    queryExpression: sprintf(podLabelsStatus, {
      namespace: getK8sNamespace(predictor.metadata.namespace),
      labelID: predictor.metadata.uid,
      labelVersion: `label_version_id=~".*"`,
      pod: '.*',
    }),
    queryLabel: 'label_version',
  },
  {
    name: 'pod',
    queryExpression: sprintf(podLabelsStatusWithPhase, {
      namespace: getK8sNamespace(predictor.metadata.namespace),
      labelID: predictor.metadata.uid,
      labelVersion: `label_version=~"%(version)s"`,
      pod: '.*',
    }),
    queryLabel: 'pod',
  },
  {
    name: 'container',
    queryExpression: sprintf(containerInfo, {
      namespace: getK8sNamespace(predictor.metadata.namespace),
    }),
    queryLabel: 'container',
  },
];
```

这里存在两阶段占位符替换：

```text
第一阶段：PredictorMonitorComponent
  填入 namespace、labelID 等已知业务参数

第二阶段：MetricVariableSelectComponent
  用户选择后填入 version、pod 等动态参数
```

例如，Pod 查询先保留：

```promql
label_version=~"%(version)s"
```

用户选择版本 `1.1` 后，再变成：

```promql
label_version=~"1.1"
```

## 5. 第二阶段：查询标签值并形成级联筛选

`MetricVariable` 的核心字段如下：

```ts
interface MetricVariable {
  name: string;
  queryExpression?: string;
  queryLabel?: string;
  value?: SelectOptions[];
  transformOptions?: (options: SelectOptions[]) => SelectOptions[];
  includeAll?: boolean;
}
```

字段含义：

| 字段                 | 含义                           |
| -------------------- | ------------------------------ |
| `name`             | 表单字段和最终输出字段名称     |
| `queryExpression`  | 用于限定时间序列的 PromQL      |
| `queryLabel`       | 要从匹配序列中提取的标签       |
| `value`            | 已查询或预设的下拉选项         |
| `transformOptions` | 标签值排序、去重或格式转换函数 |
| `includeAll`       | 是否加入值为`.*` 的 All 选项 |

组件初始化入口是：

```text
ngOnChanges()
  → handleVariablesChanged()
```

`handleVariablesChanged()` 会：

1. 为变量创建表单控件；
2. 监听选择变化；
3. 找到不依赖其他变量的查询；
4. 调用 `getLabelValues()` 获取第一层标签；
5. 上一级变量变化后，重新查询依赖它的下一级变量。

实际标签查询使用：

```ts
this.queryApi.postNamespacedLabelValue(
  this.namespace,
  variable.queryLabel,
  {
    matches: [queryExpression],
    start,
    end,
  }
);
```

典型级联过程：

```text
查询 label_version
  ↓ 用户选择 version
替换 Pod PromQL 中的 %(version)s
  ↓ 查询 pod 标签
用户选择 pod
  ↓ 替换容器 PromQL 中的 %(pod)s
查询 container 标签
```

当所有变量都有值时，组件发出：

```ts
this.onChange.emit({
  version: '1.1',
  pod: 'predictor-123-pod-a',
  container: 'model',
});
```

## 6. 第三阶段：父组件保存并分发筛选结果

`shared-container-monitor` 处理事件：

```ts
handleMetricVariablesChange(val: { [key: string]: string }) {
  this.cdr.markForCheck();
  this.monitorVariableValues = val;
  this.onMonitorSelectedChange.emit(val);
}
```

`monitorVariableValues` 会根据当前模式传给对应图表组件：

```text
hardware
  → shared-container-hardware-monitor

service
  → shared-container-service-monitor

llmservice
  → shared-llmservice-monitor-graph
```

硬件模式示例：

```html
<shared-container-hardware-monitor
  [monitorVariableValues]="monitorVariableValues"
  ...
></shared-container-hardware-monitor>
```

父组件不会把筛选结果转换成时间序列；它主要负责保存和原样分发。

## 7. 第四阶段：构造指标 PromQL

硬件指标首先在 constant 中定义，例如：

```ts
export const containerCpuUsage = `
  sum by(cluster,pod,container)(
    avg_over_time(
      rate(
        container_cpu_usage_seconds_total{
          cluster=~"%(cluster)s",
          namespace="%(namespace)s",
          container=~"%(container)s",
          pod=~"%(pod)s"
        }[5m]
      )[%(time)s:30s]
    )
  )
`;
```

组件通过 TypeScript `import` 得到该字符串，并在类字段初始化时放入 `ChartConfig.query`：

```ts
cpuUsageOption: ChartConfig = {
  titleTranslateKey: 'cpuUsage',
  name: ['{pod=%(pod)s,container=%(container)s}'],
  query: [containerCpuUsage],
  formatter: (value) => `${value} Core`,
  legend: {},
  option: {},
};
```

因此，运行时并不会根据名称动态查找 constant 文件。实际关系是：

```text
constant.ts 导出字符串
  → 组件 import
  → 初始化 ChartConfig.query
  → config.query.map(item => ...)
```

在下面的代码中，`item` 已经是具体 PromQL 字符串：

```ts
config.query.map((item) => {
  const expression = sprintf(item, {
    cluster: '.*',
    namespace: getK8sNamespace(this.namespace),
    time: this.step,
    ...this.monitorVariableValues,
  });
});
```

假设：

```ts
this.monitorVariableValues = {
  version: '1.1',
  pod: 'predictor-123-pod-a',
  container: 'model',
};
```

则 CPU PromQL 中的 `%(pod)s` 和 `%(container)s` 会被替换。该查询没有 `%(version)s`，因此对象中的 `version` 不参与这条 PromQL。

## 8. 第五阶段：查询时间序列

输入变化时，硬件监控基类执行：

```text
ngOnChanges()
  → reloadMonitor()
  → getLineChart()
  → getRangeQuery(config)
```

`getRangeQuery()` 使用范围查询接口：

```ts
this.queryApi.postNamespacedRange(this.namespace, {
  query: expression,
  start,
  end,
  step: this.step,
});
```

两类查询接口的区别：

| 调用                           | 目的                 | 典型结果                   |
| ------------------------------ | -------------------- | -------------------------- |
| `postNamespacedLabelValue()` | 查询可选标签值       | Pod、容器、版本名称数组    |
| `postNamespacedRange()`      | 查询一段时间内的指标 | Prometheus matrix 时间序列 |

## 9. 第六阶段：转换并保存图表配置

Monitor Server 的响应先经过：

```ts
getMatrixSeries(res.body?.data, config.name[index])
```

多个查询结果汇总为 `MatrixSeries[][]`，然后在 `getLineChart()` 中展平：

```ts
const dataFlat = data.reduce((result, item) => {
  result.push(...item);
  return result;
}, []);
```

最后转换为 ECharts option：

```ts
config.option = getLineOption(
  dataFlat,
  initLineOption(),
  config
);
```

数据没有集中保存在单独的原始数据属性中，而是分散保存在各个图表配置的 `option` 中，例如：

```text
cpuUtilizationOption.option
memoryOption.option
networkOption.option
diskOption.option
mluUtilization.option
gpuUtilization.option
```

其中真正的折线点最终位于类似下面的位置：

```ts
option.series[n].data
```

## 10. 第七阶段：Angular 和 ECharts 绘图

模板中不直接遍历时间序列，而是把完整 option 交给 `ngx-echarts`：

```html
<div
  echarts
  [options]="cpuUtilizationOption.option"
  [initOpts]="initChartOpts"
  [style.height.px]="390"
></div>
```

查询完成后调用：

```ts
this.cdr.markForCheck();
```

Angular 随后检查 `[options]` 绑定，把新的配置传给 ECharts。ECharts 在宿主 `<div>` 内动态创建 `<canvas>`，并完成坐标轴、折线、图例和 Tooltip 的绘制。

`canvas` 是浏览器原生 HTML5 绘图元素，不是 TypeScript 内置组件，也不负责查询数据。在当前工程中，它由 ECharts 创建和控制。

```text
ChartConfig.option
  → Angular [options]
  → ngx-echarts
  → ECharts setOption()
  → Canvas 绘制
```

## 11. 动态变化机制

图表动态变化主要来自两类事件。

### 11.1 筛选条件变化

```text
用户修改 version、pod 或 container
  → MetricVariableSelectComponent emit 新值
  → monitorVariableValues 更新
  → 图表组件 ngOnChanges()
  → 停止旧轮询并重新查询
  → option 更新
  → ECharts 重绘
```

### 11.2 定时轮询

`getLineChart()` 使用 `poll()` 定期执行 `getRangeQuery()`，从而获取新时间序列并覆盖对应 `config.option`。

组件销毁或重新加载时通过 `stopPolling$` 停止旧轮询，避免重复请求和资源泄漏。

## 12. 常见排查入口

### 12.1 筛选项缺失或错误

重点检查：

- `MetricVariable.queryExpression`
- `MetricVariable.queryLabel`
- `postNamespacedLabelValue()` 返回值
- `transformOptions`
- `%(version)s`、`%(pod)s` 等依赖变量是否被替换

### 12.2 图表没有数据

重点检查：

- `monitorVariableValues` 是否为空；
- `ChartConfig.query` 是否包含正确 PromQL；
- `sprintf()` 后的最终表达式；
- `start`、`end`、`step` 是否合理；
- `postNamespacedRange()` 的响应；
- `getMatrixSeries()` 是否得到序列。

### 12.3 请求正确但显示异常

重点检查：

- `getMatrixSeries()` 的转换结果；
- `getLineOption()` 输出；
- `config.option.series`；
- HTML 的 `[options]` 是否绑定到正确的配置；
- 图表容器是否具有有效高度；
- `markForCheck()` 是否执行。

### 12.4 修改或新增普通折线图

通常需要修改四处：

1. 在 constant 中定义指标 PromQL；
2. 在组件中 import 该常量；
3. 创建 `ChartConfig` 并加入 `getChartOpts()`；
4. 在 HTML 中增加 `[options]="xxxOption.option"` 图表容器。

## 13. 核心概念速查

| 概念                           | 作用                             |
| ------------------------------ | -------------------------------- |
| PromQL constant                | 带占位符的查询字符串模板         |
| `MetricVariable[]`           | 标签筛选配置                     |
| `queryExpression`            | 筛选标签值使用的 PromQL          |
| `queryLabel`                 | 从匹配序列中提取的标签名         |
| `monitorVariableValues`      | 用户最终选定的筛选条件           |
| `ChartConfig.query`          | 图表实际使用的指标 PromQL        |
| `ChartConfig.option`         | 交给 ECharts 的最终图表配置      |
| `postNamespacedLabelValue()` | 查询标签可选值                   |
| `postNamespacedRange()`      | 查询指标时间序列                 |
| `getMatrixSeries()`          | 将 Prometheus 响应转换为统一序列 |
| `getLineOption()`            | 将序列转换为 ECharts option      |
| `echarts` 指令               | 将 Angular 配置交给 ECharts      |
| Canvas                         | ECharts 使用的浏览器绘图画布     |

## 14. 后续可继续细化的方向

- `QueryApi` 对应的 Monitor Server HTTP 路由和请求体；
- Monitor Server 如何转发或代理 Prometheus 查询；
- `sprintf()` 对缺失占位符的具体处理方式；
- `getMatrixSeries()` 的输入输出字段映射；
- `getLineOption()` 如何生成图例、坐标轴、单位和 Tooltip；
- `poll()` 的首次执行、刷新周期和取消机制；
- Service 与 LLM Service 的 PromQL、数据转换和展示差异；
- `OnPush`、`markForCheck()` 与 ECharts option 更新的关系；
- 新增一种指标或新建一种图表的完整实践。
