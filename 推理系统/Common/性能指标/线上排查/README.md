# 线上排查（指标变化分析）工作目录

本目录是**在线推理服务指标变化分析的唯一工作目录**：所有线上服务的指标异动排查、判读结论与案例记录统一存放于此。

## 目录内容

| 文件 | 用途 |
|---|---|
| [指标变化事件词典与组合签名.md](./指标变化事件词典与组合签名.md) | 核心方法文档：指标变化 → 背后事件 → 含义的判读词典与签名速查表 |
| [案例_prediction-service-0924-202926.md](./案例_prediction-service-0924-202926.md) | 实战样例：PD 架构 1M 上下文服务的完整排查闭环 |
| `案例_<服务名>_<日期>.md` | 后续新排查案例按此命名存放 |

## 上游参考（口径依据，不在本目录重复维护）

- [../大模型指标/metric指标.md](../大模型指标/metric指标.md) — 每个原始 metric 的类型、单位、标签身份与口径勘误（如 prefix cache 的 token 口径）
- [../大模型指标/PromQL分析.md](../大模型指标/PromQL分析.md) — 前端每张图的 PromQL 范式与统计语义
- [../稳定推理服务验证.md](../稳定推理服务验证.md) — 十层判稳模型：Queue/TTFT/Prefill/Decode/KV/Prefix/硬件/错误/恢复/长跑
- [../PromQL统计范式.md](../PromQL统计范式.md) — increase/rate/avg_over_time/histogram_quantile 的通用规则
- `~/ZyhKonwledgeRepo/其他/寒武纪paas平台/监控/VmSelect-PromQL查询LLM服务指标方法.md` — VmSelect 只读查询操作方法（SSH 跳板、端点、时间窗/step 策略）

## 工作约定

1. **先排假象，再定事件**：counter 归零、avg 断点、分位插值、子查询平滑、PD 单侧截断——见词典第五节清单。
2. **三类事件归因**：负载事件 E1 / 容量事件 E2 / 状态事件 E3，用签名表对号入座，再用佐证指标定案。
3. **时间一律北京时间（UTC+8）**：所有排查报告、案例记录、尖峰时刻标注均换算为北京时间并注明；查询参数仍用 Unix 秒。
4. **PD 双角色拆分**：prefill/decode 两侧同名指标语义不同，永远按 `label_role_name` 分拆看，不做聚合；单看任一侧 E2E 都会低估。
5. **只读边界**：排查全程仅 `kubectl get/describe` + VmSelect HTTP GET，不做任何变更。
6. **案例记录要素**：服务名/namespace/label_id/角色/状态/时间窗与 step/指标事实（min/avg/max + 趋势）/现象→签名→事件对账表/结论与建议。
