# AIBrix `config/` 阅读指南

## 定位

AIBrix 的 `config/` 是 Kubernetes 部署配置的主要源目录，使用 Kustomize 组织 CRD、控制器、Gateway 数据面、RBAC、辅助服务、外部依赖和环境定制配置。

`config/` 并不包含生产集群的全部基础设施。Kubernetes、CNI/CSI、GPU 驱动、镜像仓库、真实 vLLM/SGLang 工作负载以及部分可观测性配置，可能由平台预先提供，或位于项目的其他目录。

## 整体结构

```text
Kubernetes 集群
├── 外部依赖：Envoy Gateway、KubeRay
├── API 层：autoscaling、model、orchestration CRD
├── 控制面：Controller Manager、Webhook、RBAC、TLS
├── Gateway 数据面：Envoy Proxy、Gateway Plugin
├── 辅助服务：Metadata Service、Redis、GPU Optimizer
└── 装配层：default、overlays、standalone、test、samples
```

## 文档导航

| 文档 | 适合了解的问题 |
| --- | --- |
| [Kustomize 与核心模块](./01-Kustomize与核心模块.md) | 配置如何被组织；`default`、CRD、RBAC 和 Manager 如何配合 |
| [Gateway 与外部依赖](./02-Gateway与外部依赖.md) | 请求如何经 Envoy 和 Gateway Plugin 转发；依赖如何安装 |
| [辅助服务与扩展能力](./03-辅助服务与扩展能力.md) | Metadata、Redis、GPU Optimizer、Job、Webhook、证书和监控的作用 |
| [部署变体与安装流程](./04-部署变体与安装流程.md) | Overlay、Standalone、Test、Samples 的区别，以及完整安装顺序 |

## 建议阅读方式

1. 先从 `config/default/kustomization.yaml` 确认默认部署包含哪些模块。
2. 沿 `resources` 递归查看感兴趣的模块。
3. 需要特定环境或单一控制器时，再查看 `overlays/` 或 `standalone/`。
4. 使用以下命令预览渲染结果，不修改集群：

```bash
kustomize build config/default
# 或
kubectl kustomize config/default
```
