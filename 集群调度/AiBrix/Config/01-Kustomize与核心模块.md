# Kustomize 与核心模块

[返回总览](./README.md)

## Kustomize 组织方式

`config/` 不是一组平铺的 YAML，而是一棵 Kustomize 资源树：

```text
单个 YAML
    → 描述一个或一组 Kubernetes 资源

模块 kustomization.yaml
    → 聚合同一能力的 Deployment、Service、RBAC、CRD

config/default/kustomization.yaml
    → 聚合 AIBrix 核心模块

config/overlays/*
    → 替换镜像、参数和环境配置
```

## 核心装配入口：`default/`

`config/default/kustomization.yaml` 引用以下模块：

```text
namespace  crd  rbac  manager  gateway
metadata   gpu-optimizer  kuberay-operator
webhook    internalcert
```

该入口统一设置 `aibrix-system` Namespace、`aibrix-` 名称前缀、公共标签、组件镜像与 Tag，并接入 KubeRay RBAC 和 Webhook Patch。`make deploy` 会构建该目录并应用到当前集群。

## `namespace/`

定义 AIBrix 系统命名空间。基础资源名为 `system`，加上 `default/` 的名称前缀后变为 `aibrix-system`。

Controller Manager、Gateway Plugin、Metadata Service、Redis、GPU Optimizer 和 Webhook 通常部署在该命名空间；Envoy Gateway Controller 通常位于 `envoy-gateway-system`。

## `crd/`

| 子目录 | API Group | 主要 CRD | 作用 |
| --- | --- | --- | --- |
| `autoscaling/` | `autoscaling.aibrix.ai` | `PodAutoscaler` | 描述模型工作负载的弹性伸缩需求 |
| `model/` | `model.aibrix.ai` | `ModelAdapter` | 管理 LoRA/模型适配器的加载、卸载和状态 |
| `orchestration/` | `orchestration.aibrix.ai` | `StormService`、`RoleSet`、`PodSet`、`KVCache`、Ray 相关 CRD | 描述分布式推理编排 |

顶层 `crd/kustomization.yaml` 聚合三个 API Group，各子目录也可被 Standalone 部署单独引用。CRD 通常由 `api/` 中的 Go 类型和 Kubebuilder 标记生成：

```text
api/ 下的 Go 类型
    → controller-gen
config/crd/bases/*.yaml
    → make sync-crds
config/crd/{autoscaling,model,orchestration}/
```

| 命令 | 作用 |
| --- | --- |
| `make manifests` | 生成 `bases` 中的 CRD |
| `make sync-crds` | 同步到各 API Group 目录 |
| `make manifests-all` | 生成并同步到模块目录和 Helm Chart |

`crd/kustomizeconfig.yaml` 告诉 Kustomize 如何替换 CRD Conversion Webhook 中的 Service 名称和 Namespace，仅在启用相关 Webhook 配置时需要接入。

## `rbac/`

| 子目录 | 关联组件/用户 | 作用 |
| --- | --- | --- |
| `controller-manager/` | Controller Manager | ServiceAccount、控制器权限、ClusterRoleBinding、Leader Election 权限 |
| `gateway/` | Gateway Plugin | 读取 Pod、Service、路由和模型资源 |
| `autoscaling/` | PodAutoscaler API 用户 | Viewer/Editor 辅助角色 |
| `model/` | ModelAdapter API 用户 | Viewer/Editor 辅助角色 |
| `orchestration/` | 编排 API 用户 | 各 CRD 的 Viewer/Editor 辅助角色 |

Controller Manager 和 Gateway 的 RBAC 是组件运行所需权限；按 CRD 生成的 Viewer/Editor 主要用于给普通集群用户授权。

## `manager/`

该目录定义 Controller Manager Deployment 和 Metrics Service。Manager 监听 AIBrix CR，通过 Reconcile 创建或更新 Deployment、Pod、Service 等原生资源，并维护 CR Status。

```text
用户创建 AIBrix CR
    → Controller Watch
    → Reconcile
    → 创建/更新 Kubernetes 资源
    → 更新 CR Status
```

一个 Manager 进程可包含 PodAutoscaler、ModelAdapter、StormService、RoleSet、KVCache 和 Ray 等多个控制器，具体启用范围可通过参数、Feature Gate 或 Standalone Patch 控制。
