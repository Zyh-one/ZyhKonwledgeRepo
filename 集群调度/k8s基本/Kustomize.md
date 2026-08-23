
Kustomize：YAML 配置管理工具（对 Kubernetes YAML 进行加载、组合、修改和生成）；感觉和Helm有点儿像

解决问题：同一套 Kubernetes YAML，在不同环境、不同部署需求下，如何复用并做少量修改，而不是复制很多份 YAML。

Kustomize 有特定的配置语法

* resources：把这些 Kubernetes YAML 加载进来。
* patches：修改已有资源
* images：修改镜像
* namespace：统一设置Namespace
* namePrefix：修改资源名称，添加统一前缀
* configMapGenerator：
* secretGenerator：

关于kustomize的了解，到这儿就行：**Kustomize 是一个按照自身配置语法，对 Kubernetes YAML 进行组合、覆盖、修改，最终生成部署 YAML 的工具。**

后续在实际生产环境中，结合ai分析

示例
