# OCI 组装镜像方式概述

## 1. 核心结论

本项目的 `webapp-caip` 没有使用传统的 `Dockerfile + docker build`，而是先生成前端静态文件和 Go Web Server，再使用 `skopeo`、`umoci` 和 `manifest-tool` 直接组装、发布符合 OCI 标准的容器镜像。

这种方式可以称为：

- 无 Dockerfile 镜像构建；
- OCI Image Layout 直接组装；
- Dockerless 或 daemonless 镜像构建。

它是符合容器标准的正规方式，但普及程度低于 Dockerfile、BuildKit 或 Kaniko，通常用于需要精确控制镜像内容、极简运行环境或多架构发布的工程化场景。

## 2. 整体构建流程

```text
Angular/Nx 源代码                  Go 源代码
        │                             │
        │ yarn nx build               │ go build
        ▼                             ▼
各前端项目的 dist 产物           web-server 二进制
        │                             │
        └───────────┬─────────────────┘
                    ▼
             整理构建上下文
         dist/www + dist/server
                    │
                    │ skopeo 拉取基础镜像
                    ▼
             OCI Image Layout
                    │
                    │ umoci insert/config
                    ▼
       写入静态文件、服务程序和启动配置
                    │
                    │ skopeo copy
                    ▼
              发布单架构镜像
                    │
                    │ manifest-tool
                    ▼
            发布多架构 webapp-caip
```

## 3. 各阶段的职责

### 3.1 编译前端项目

Nx 一次构建 `paas`、`console`、`label`、`llm` 和 `cair` 等前端项目，然后统一整理到 `dist/www`。

因此，`webapp-caip` 是一个包含多个前端站点静态产物的共享镜像，而不是只包含 Paas 页面。

### 3.2 编译静态文件服务器

项目把 Go 编写的 Web Server 编译为 Linux 可执行文件，并关闭 CGO，使其能够在极简的 distroless 基础镜像中运行。

这个程序负责：

- 监听 HTTP 端口；
- 从指定目录提供前端静态文件；
- 支持单页应用的入口回退；
- 提供健康检查；
- 在运行时读取配置和系统信息。

### 3.3 准备 OCI 基础镜像

`skopeo` 将远程 distroless 基础镜像复制为本地 OCI Image Layout。这里得到的不是正在运行的容器，而是一套可以继续修改的标准镜像目录结构。

### 3.4 组装镜像文件系统

`umoci` 向 OCI 镜像中写入：

```text
/usr/bin/web-server   Go Web Server
/var/www/             各前端项目的静态文件
```

同时将镜像入口程序配置为：

```text
/usr/bin/web-server
```

`umoci insert` 属于构建期写入，会形成镜像文件系统内容，并不是 Kubernetes 运行时挂载。

### 3.5 发布镜像

`skopeo copy` 将本地 OCI 镜像复制到目标镜像仓库。每个 CPU 架构先发布独立镜像，最后由 `manifest-tool` 生成统一的多架构清单，使同一个镜像标签可以同时支持 amd64 和 arm64。

## 4. 静态文件与挂载文件的区别

前端 `dist` 产物已经写入镜像：

```text
dist/www/  →  镜像内 /var/www/
```

镜像内部大致为：

```text
/var/www/
├── paas/
├── console/
├── label/
├── llm/
├── cair/
└── dp/
```

部署不同前端服务时，可以复用同一个镜像，通过启动参数选择不同静态文件根目录。例如 Paas 使用 `/var/www/paas`。

运行时挂载只用于需要随环境变化或独立维护的内容：

| 内容 | 来源 | 是否写入镜像 |
|---|---|---|
| Go Web Server | 构建产物 | 是 |
| 前端静态文件 | `dist/www` | 是 |
| Web 环境配置 | Kubernetes ConfigMap | 否，运行时挂载 |
| 用户文档 | 宿主机目录 | 否，运行时挂载 |

如果卷被挂载到镜像已有的目录，该挂载点下原有的镜像内容会在容器运行期间被遮蔽，但镜像本身并没有被修改。

## 5. 与传统 Dockerfile 构建的对比

| 方面 | OCI 直接组装 | Dockerfile 构建 |
|---|---|---|
| 构建描述 | Makefile 调用多个 OCI 工具 | Dockerfile 声明步骤 |
| 是否需要 Docker daemon | 不需要 | 传统方式通常需要，BuildKit 可独立运行 |
| 镜像内容控制 | 精确 | 较直观且生态成熟 |
| 可读性 | 需要了解 skopeo、umoci | 团队更容易理解 |
| 构建缓存 | 依赖外部构建流程设计 | BuildKit 支持较成熟 |
| 多架构 | 单独组装后合并 Manifest | buildx 等工具可直接处理 |
| 常见场景 | 基础设施、极简镜像、定制流水线 | 大多数应用项目 |

## 6. 这种方式的优势与代价

优势：

- 不依赖 Docker daemon；
- 可以使用不带 Shell 和包管理器的 distroless 镜像；
- 镜像内容少，运行时攻击面较小；
- 可以精确控制文件路径、入口程序和架构信息；
- 适合集中构建多个前端项目和发布多架构镜像。

代价：

- 相比 Dockerfile，理解和维护门槛更高；
- 构建过程分散在 Makefile 和多个工具中；
- 调试 distroless 容器不方便，因为通常没有 Shell；
- 缓存、SBOM、签名和供应链能力需要在流水线中另外设计；
- 若构建脚本没有保持确定性，同一源码仍可能产生不同镜像元数据。

## 7. 本项目运行时模型

镜像构建阶段才会运行 Yarn 和 Nx。正式环境容器启动时不再编译前端，也不会通过 Yarn 启动 Angular 开发服务器。

运行时链路为：

```text
Kubernetes 创建 Pod
        │
        ▼
启动 /usr/bin/web-server
        │
        ├── 读取挂载的环境配置
        ├── 监听 80 端口
        └── 提供 /var/www/paas 下的静态文件
```

因此要区分：

- **构建期**：Yarn/Nx 编译前端，Go 编译服务器，OCI 工具组装镜像；
- **运行期**：Go Web Server 直接提供已经编译好的静态文件；
- **部署期配置**：Kubernetes 通过参数和卷挂载决定站点目录、环境配置和外部文档。

## 8. 一句话总结

本项目把“编译产物生成”和“容器镜像组装”明确分开：先在镜像外完成 Angular 与 Go 的编译，再以 distroless 为基础，通过 OCI 工具把必要文件直接写成标准镜像，最后使用同一个 `webapp-caip` 镜像和不同启动参数运行多个前端站点。
