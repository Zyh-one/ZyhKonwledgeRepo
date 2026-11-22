# LLM / AI Infra 10 篇核心论文

**注意：本压缩包是下载工具包，不含论文 PDF。** 在具备互联网访问能力的电脑上运行 `python download_papers.py` 后，脚本会将 10 篇原版论文下载到 `papers/` 并自动生成 `LLM_AI_Infra_10_Papers.zip`。

## 使用方法

1. 安装 Python 3.9+（无需第三方依赖）。
2. 在本文件所在目录执行 `python download_papers.py`。
3. 程序会检查 PDF 文件头、排除网页伪装文件，并报告失败项。若失败，重新运行可重试。

| 序号 | 论文 | 官方 PDF 来源 |
|---|---|---|
| 01 | Attention Is All You Need | https://arxiv.org/pdf/1706.03762 |
| 02 | FlashAttention | https://arxiv.org/pdf/2205.14135 |
| 03 | FlashAttention-2 | https://arxiv.org/pdf/2307.08691 |
| 04 | Efficient Memory Management for LLM Serving with PagedAttention (vLLM) | https://arxiv.org/pdf/2309.06180 |
| 05 | Orca: A Distributed Serving System for Transformer-Based Generative Models | https://www.usenix.org/system/files/osdi22-yu.pdf |
| 06 | SGLang: Efficient Execution of Structured Language Model Programs | https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf |
| 07 | Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | https://arxiv.org/pdf/2403.02310 |
| 08 | DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving | https://arxiv.org/pdf/2401.09670 |
| 09 | Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism | https://arxiv.org/pdf/1909.08053 |
| 10 | DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model | https://arxiv.org/pdf/2405.04434 |

每篇论文按最初的 10 篇列表编号，保留英文原文 PDF。
