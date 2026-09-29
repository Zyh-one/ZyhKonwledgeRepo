# 排查案例：prediction-service-0924-202926（PD + 1M 上下文服务）

> 词典与签名表见 [指标变化事件词典与组合签名.md](./指标变化事件词典与组合签名.md)，本文按其方法完成一次完整闭环，作为后续案例的记录模板。时间均为**北京时间（UTC+8）**，括注 UTC。

## 1. 服务事实

| 项 | 值 |
|---|---|
| 服务名 / kind | prediction-service-0924-202926 / llmserving |
| namespace | ns-e23f5b20fb9b42d3ac674f9691a0b9b1 |
| label_id | 4f0059c1-42d8-4f15-a939-9274b17bfc06 |
| 角色 | prefill + decode（PD 分离），每角色 2 pod × 8 MLU590（TP16），volcano 调度 |
| 模型 | GLM-5.3-W4A8，1M 上下文 |
| prefill 关键 env | MAX_NUM_BATCHED_TOKENS=16384，MAX_NUM_SEQS=16 |
| decode 关键 env | MAX_NUM_BATCHED_TOKENS=128，MAX_NUM_SEQS=32 |
| 配置来源 | 模型包 glm53-1m-16384（包名内嵌 16384；同集群 glm52 包用 8192/4）——api/ 平台代码零注入，可在创建时经 modelPkg.Envs 覆盖 |
| 状态 / 活跃窗口 | Expired；2026-09-24 20:46 ~ 09-25 05:48（北京） |
| 分析窗口 | 2026-09-24 20:30 ~ 23:30（北京）= 12:30~15:30 UTC，step 60s（重点时段 1m 粒度） |
| 负载画像 | 平均输入 18.0 万 token/请求，p99 99.5 万（贴 1M 上限）；突发 49 req/min、5.5M token/min |

## 2. 现象 → 签名 → 事件对账表

| 观测现象（北京时间） | 签名 | 事件定性 |
|---|---|---|
| prefill running 恒 0/1（30s 粒度），MAX_NUM_SEQS=16 并未触顶 | 非签名，是形态 | 16384 chunk 预算 < 18万 prompt → ⌈prompt/16384⌉=11~61 chunk，每 step 1 chunk 1 请求 → 串行 prefill |
| 20:53~20:55 waiting 尖 42 + queue avg 77s + TTFT avg 95.8s（≈77.1+15.6 对账成立）+ prefill avg 平 | **S1** | E1 突发（49 req/min × 5.5M token ≈ prefiller 5.5万 token/s 吞吐上限 → ~100s 积压）；后回基线 = **S13 型可恢复** |
| 21:05 / 20:53 / 22:27 prefill p99 尖 216/114/113s，avg 3.3s 平 | **S2** | E1 个别近 1M prompt × attention 平方复杂度（长尾指纹：avg 平 p99 尖） |
| decode running 随到达爬至 32 顶格，waiting max 仅 8.5 | **S6 前兆** | decode 槽位按 Little 定律 L=λW 累积；avg 生成 127s 决定占槽时长；未恶化为 TPOT↑，非故障 |
| decode E2E max 1410s + TPOT 平 | **S7** | 长输出驱动（E1），非 decode 降速 |
| 桶 0（20:46 起）TTFT 偏高 + prefix 命中率低 → 回升 | 预热 | E3 冷启动，正常升温 |
| 全程无 KV→100%、无 preemptions、无 NIXL failed/expired、无重启、无 4xx/5xx | — | 排除 S8/S10/S11/S12 |

**最终结论**：所有"疑惑曲线"全部落在 E1（负载事件）；服务自身无容量/状态故障，负载处于可持续吞吐边界内（过载可自行消化，S13）。

## 3. 根因链（配置 → 行为）

```
模型包 glm53-1m-16384 的 MAX_NUM_BATCHED_TOKENS=16384（prefill chunk 预算）
  + 负载 avg 18万 / p99 99.5万 token prompt
  → chunk 数 11~61/请求，每 step 推进 1 chunk
  → prefill running 恒 1（非 MAX_NUM_SEQS 卡死）+ 突发时 waiting 尖峰 + queue 主导 TTFT
  + 近 1M prompt × attention 平方复杂度
  → prefill 计算时长 p99 长尾尖峰（avg 不动）
```

调优方向（如复建同类服务）：prefill MAX_NUM_BATCHED_TOKENS 提至 32768/65536 或增加 prefill 副本；输入长度本身不可再降。

## 4. 本案例的方法论沉淀

1. 5m `avg_over_time` 曾把 prefill running=1 抹成 0.07——**子查询平滑假象**的实证，细 step（30s/1m）复核后才见真形态。
2. TTFT ≈ queue + prefill 的 avg 级对账（95.8 ≈ 77.1 + 15.6）是区分排队/计算主导的最快手段。
3. Little 定律双向使用：由 queue 时长反推积压量（~100s ≈ 5.5M token ÷ 5.5万/s），验证"过载幅度"而非仅报数值。
4. 跨模型包参数对比（glm52-8 包 8192/4 vs glm53-1m 包 16384/16）是定位配置来源的关键证据，比读平台代码更快收敛。
