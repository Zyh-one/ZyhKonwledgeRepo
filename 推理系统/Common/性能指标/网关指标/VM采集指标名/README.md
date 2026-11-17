# VM 采集指标名清单

本目录保存北京时间 **2026-11-17** 从黄区 VictoriaMetrics 按采集 `job` 获取的最近 **15 分钟**指标名快照。

这里只整理指标名，不包含数据序列、样本值、标签组合、指标解读或 PromQL。平台代码当前实际使用的指标见[网关指标分类总结](../指标总结.md)。

| 采集 job | 指标名数 |
| --- | ---: |
| [`aibrix-gateway-plugins`](aibrix-gateway-plugins.md) | 168 |
| [`envoy-aibrix-system-aibrix-eg`](envoy-aibrix-system-aibrix-eg.md) | 542 |
| [`envoy-gateway`](envoy-gateway.md) | 82 |
| [`envoy-svc-exporter-svc`](envoy-svc-exporter-svc.md) | 58 |
| **合计** | **850** |

说明：

- 清单保留 VM 返回的全部名称，包括 `go_*`、`process_*`、`scrape_*`、`up` 和 `count:up1`，便于与接口返回逐项核对；它们不都属于网关业务指标。
- `aibrix-gateway-plugins` 清单也保留经 gateway 暴露的推理引擎指标，不能将整个 job 的名称都理解为 AIBrix 路由器原生指标。
- 本目录是上述时间窗的实测快照，不声称覆盖 VM 保留期内的历史指标，也不包含其他业务 job。
- `aibrix_prefix_cache_indexer_status` 在该时间窗内未返回，因此未人工补入清单。
