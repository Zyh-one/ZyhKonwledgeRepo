# 周报分析

多日维度的在线服务质量统计与分析报告。本 README 承载各报告共用的**统计口径**与**复算 PromQL**，具体报告按服务一文档。

- [glm52-8-pd每日统计报告_2026-09-14至09-18.md](./glm52-8-pd每日统计报告_2026-09-14至09-18.md)
- [glm52-pd每日统计报告_2026-09-14至09-18.md](./glm52-pd每日统计报告_2026-09-14至09-18.md)

## 统计口径（PD 分离 · 客户端视角）

两个服务的报告共用以下口径。核心问题：PD 分离架构下，prefill/decode 任一单角色指标都不代表客户端真实体验，必须跨角色组合。

- **数据源**：VmSelect 直连引擎抓取路径（`label_id` + `label_role_name` 过滤），**非网关转发路径**——网关路径 decode 侧严重漏计（实测 decode 完成数只有真实值 1/4 左右），已弃用。
- **统计窗口**：每日 9:30–18:30（北京时间，UTC+8）= instant 查询取 E = 当日 18:30 北京（10:30 UTC）的 unix 秒，`[9h]` increase；increase() 自动处理 counter 重启归零。
- **到达请求数** = prefill 角色 `http_requests_total`（`handler=~".*(messages|completions|responses).*"`）。prefill 是服务入口，网关把每个客户端请求恰好转发给 prefill 一次，故它是全量到达账本（含被校验拒绝的 4xx）。
- **成功请求数** = decode 角色 `vllm:request_success_total` 的 `finished_reason=~"stop|length"`（模型完整生成出结果）。`abort`=客户端取消、`error`=引擎错误、`repetition`=退化，均非成功。
- **输入/输出分布**：输入取 prefill 侧 `vllm:request_prompt_tokens` 直方图；输出取 decode 侧 `vllm:request_generation_tokens` 直方图。
- **客户端 TTFT/E2E（avg）** ≈ prefill 侧 + KV 传输 + decode 侧。各阶段 **avg 近似可加**；**分位数不可跨阶段相加**（不同直方图样本集），故 p95/p99 按阶段单列。KV 传输按每请求 2 次 NIXL 传输计（实测 `nixl_xfer_time` 计数/请求数稳定为 2.0）。
- **TPOT/ITL** 为 decode 侧指标——所有输出 token 都出自 decode，客户端感知与引擎侧一致。
- **请求生命周期**（两角色互补）：

```
到达 → [P:排队] → [P:prefill计算] → [KV经NIXL传输×2] → [D:排队] → [D:逐token生成] → 完成
```

### 统计假象与注意

- **输入 p99=200000**：直方图最大桶边界假象（超长 prompt 落入 +Inf 桶），只能解读为"p99 ≈ 200k 或以上"，非精确值。
- **"到达−完成"差额**：正常 260–400/日（入口拒绝 + 窗口边缘在途请求）；大幅超出时用小时级下钻定位（如 glm52-8-pd 9/14 的下午积压）。
- **CR 接替**：服务 CR 删除重建后 label_id 变化，重建日的数据来自新 label_id（如 9/18 的 glm52-pd-2），横比时注意切换初期效应。

## 复算 PromQL

公共标签串：`L = cluster="bj-caip", label_id="<服务label_id>"`；`LP`/`LD` 分别追加 `label_role_name="prefill"`/`"decode"`。

```promql
# 到达请求数（prefill 是入口）
sum(increase(http_requests_total{LP, handler=~".*(messages|completions|responses).*"}[9h]))

# 成功请求数（decode 侧正常结束）
sum(increase(vllm:request_success_total{LD, finished_reason=~"stop|length"}[9h]))

# avg 类（avg 可跨阶段相加得客户端视角）
sum(increase(vllm:time_to_first_token_seconds_sum{LP}[9h])) / sum(increase(vllm:time_to_first_token_seconds_count{LP}[9h]))

# p95 类（不可跨阶段相加，按角色单看）
histogram_quantile(0.95, sum by (le)(increase(vllm:request_prompt_tokens_bucket{LP}[9h])))

# 每小时到达分布（query_range，step=3600，start=E-32400+3600，end=E）
sum(increase(http_requests_total{LP, handler=~".*(messages|completions|responses).*"}[1h]))
```

## 交叉校验方法（各报告数据可信度）

- 小时到达之和 = 全天到达（逐日对账）
- 到达 → prefill 完成 → decode 完成三级漏斗自洽（decode 完成数 = E2E 计数）
- http 双路径计数互证（label_id 直连路径 vs 网关转发路径，误差 <1/千）

指标语义与判读方法论详见 [../../Common/性能指标/大模型指标/metric指标/推理请求量/PromQL.md](../../Common/性能指标/大模型指标/metric指标/推理请求量/PromQL.md) 与 [../../Common/性能指标/线上排查/指标变化事件词典与组合签名.md](../../Common/性能指标/线上排查/指标变化事件词典与组合签名.md)。
