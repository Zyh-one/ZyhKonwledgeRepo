# aTrust VPN 导致公共 AI 网站无法访问的排查与解决

## 事件概述

在 Ubuntu 24.04 上启动并登录深信服 aTrust VPN 后，普通 Chrome、Codex CLI、VS Code 插件访问 ChatGPT、Gemini、OpenAI API 等公网服务出现异常。表面现象包括：

- 浏览器访问 ChatGPT、Gemini 超时或报错；
- Gemini 曾出现 `ERR_QUIC_PROTOCOL_ERROR`；
- Codex MCP 启动超时，或 Codex 无法正常连接；
- 部分国内 AI 网站也可能出现加载异常；
- 退出 aTrust 后偶尔还会被浏览器 DNS 缓存、QUIC 缓存或 Service Worker 影响，需要重启浏览器/清缓存。

最终确认：aTrust 登录后不仅创建 VPN 虚拟网卡，还会影响 DNS 与透明代理相关路由。旧的“独立 Chrome + 本地代理”方案可以绕过浏览器问题，但不能自然覆盖 Codex、VS Code 插件和普通 Chrome。

当前处理边界已收窄为：

```text
只允许处理：10.10.150.0/24 -> aTrust utun 网卡
禁止修改：公司 DNS、/etc/resolv.conf、默认路由、其他内网路由
```

公共 AI 网站问题需要在上述边界内单独排查，不得以牺牲公司内网访问为代价解决。

## 当前正式方案（2026-07-30，最终收敛版）

当前不再追求 aTrust 与普通 Chrome、Codex、VS Code 等所有应用同时协调工作，只保留两个目标：

1. aTrust 登录期间，通过独立 Chrome 和 `127.0.0.1:18787` 访问 ChatGPT、Gemini；
2. 使用结束后，通过“aTrust 快速退出”彻底停止 aTrust 后台、删除残留隧道并快速恢复普通网络。

应用菜单中的最终入口为：

```text
aTrust 启动
aTrust 专用 Chrome
aTrust 快速退出
```

最终保留的自定义文件只有：

```text
/home/cambricon/.local/bin/atrust-browser-proxy
/home/cambricon/bin/atrust-proxy-start
/home/cambricon/.local/bin/atrust-secure-chrome
/home/cambricon/.local/bin/atrust-mode-start
/home/cambricon/.local/bin/atrust-fast-exit
/usr/local/sbin/atrust-mode-start-root
/usr/local/sbin/atrust-fast-exit-root
```

路由守护、split、全局 DoH、DNS测试以及 Codex/VS Code代理包装器均已停用并删除。详细使用方式见：

```text
其他/atrust-tools/使用规范.md
```

## 已停用方案：专用路由守护 + 指定应用代理

> [!CAUTION]
> 本节记录 2026-07-30 的中间方案。相关脚本和 systemd服务已经删除，不得按本节重新安装或执行。

当时采用“专用路由守护 + 指定应用代理”的轻量方案，不使用虚拟机，也不修改系统 DNS、默认路由、防火墙或 aTrust 下发的其他路由。

```text
10.10.150.0/24
    -> atrust-route-guard.service
    -> 当前在线的 aTrust utun 接口

Codex / 指定 VS Code / aTrust 专用 Chrome
    -> 127.0.0.1:18787
    -> Cloudflare DoH 解析公共域名

*.cambricon.com
    -> 强制绕过 18787
    -> 公司 DNS 与物理网卡原链路
```

### 1. 专用路由守护

已安装：

```text
/usr/local/sbin/atrust-route-guard
/etc/systemd/system/atrust-route-guard.service
/usr/local/sbin/atrust-split-on
/usr/local/sbin/atrust-split-off
/usr/local/sbin/atrust-network-check
/home/cambricon/bin/atrust-split-on
/home/cambricon/bin/atrust-split-off
/home/cambricon/bin/atrust-split-status
```

守护服务每 2 秒检查一次当前在线的 `utun*` 接口，只维护：

```text
10.10.150.0/24 dev <当前 utun> proto 186
```

其中 `proto 186` 在 `ip -details route` 中显示为 `proto bgp`，仅作为本工具识别和精确删除该路由的标记，不表示系统实际运行了 BGP。

守护服务明确不操作：

- DNS 与 `/etc/resolv.conf`；
- 默认路由和物理网卡；
- 防火墙；
- `198.18.*`、`10.5.*` 等 aTrust 下发的其他路由；
- `172.24.*` 与任何 CAIP、GitLab 公司网络链路。

当前验证结果：

```text
10.10.150.19 -> utun7
10.10.150.50 -> utun7
10.10.150.19:2222 -> 可连接
atrust-route-guard.service -> active
atrust-split-status -> status: healthy
```

### 2. 公司网络强制保护

以下地址是硬性回归项，任何改动前后都必须保持正常：

```text
http://bj.caip.cambricon.com:30080/auth/login
```

2026-07-30 的基线与实施后结果均为：

```text
bj.caip.cambricon.com -> 172.24.32.32 / 172.24.32.33
172.24.32.32/33      -> enp2s0 默认网关
TCP 30080             -> OPEN
HTTP                  -> 200
```

`18787` 只支持 HTTPS CONNECT；若上述 HTTP 地址误入代理会返回 `405 Method Not Allowed`。因此 `codex-atrust`、`code-atrust` 和 aTrust 专用 Chrome 已加入 `.cambricon.com` 绕过规则。普通 Chrome 未配置该代理，保持公司网络直连。

应用启动器使用的关键规则为：

```text
NO_PROXY=127.0.0.1,localhost,::1,
         10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,
         .cambricon.com,
         bj.caip.cambricon.com,
         caip.cambricon.com,
         gitlab.software.cambricon.com
```

已运行的 Codex 或 VS Code 不会自动获得新的环境变量，需要关闭对应应用后通过 `codex-atrust` 或 `code-atrust` 重新启动。

### 3. 安全启停与验证

登录 aTrust 后启用或确认守护：

```bash
sudo /usr/local/sbin/atrust-split-on
/home/cambricon/bin/atrust-split-status
/usr/local/sbin/atrust-network-check
```

正常状态应同时满足：

```text
atrust-split-status -> status: healthy
CAIP login          -> HTTP 200
公司 DNS             -> 10.3.34.10 / 172.10.80.158
默认路由             -> enp2s0
```

退出 aTrust 前可关闭守护：

```bash
sudo /usr/local/sbin/atrust-split-off
```

该命令会立即中断依赖 `10.10.150.0/24` 的 SSH、VS Code Remote-SSH 等连接。工作期间不得为了测试执行 `split-off` 或删除专用路由；只允许使用状态命令进行非中断式验证。

### 4. 回退顺序

如果实施后公司网络出现异常：

1. 执行 `sudo /usr/local/sbin/atrust-split-off`；
2. 重新执行 `/usr/local/sbin/atrust-network-check`；
3. 若仍未恢复，立即退出 aTrust；
4. 不得通过修改 DNS、`/etc/resolv.conf` 或删除其他 aTrust 路由尝试恢复。

## 重要安全约束：公司内网访问优先

> [!IMPORTANT]
> 任何 aTrust 排查或修复都必须保证公司内网正常访问。不得将全局 DNS 改为 `8.8.8.8`、`1.1.1.1` 或本地 DoH 代理；不得改写 `/etc/resolv.conf`；不得删除 aTrust 下发的其他内网路由。

允许的操作范围仅为：

```text
10.10.150.0/24 -> 当前 aTrust utun 接口
```

除上述网段的专用路由外，不应改动：

- 公司 DNS；
- `/etc/resolv.conf` 及 `systemd-resolved` 运行状态；
- 物理网卡与默认路由；
- aTrust 自身下发的其他路由；
- 公司 GitLab、CAIP 等内网服务依赖的解析与访问链路。

### 昨日公司内网访问失败事故

在排查 aTrust 导致的公共 AI 网站访问问题时，曾执行 `atrust-dns-test apply`，导致：

```text
enp2s0 运行时 DNS -> 8.8.8.8
/etc/resolv.conf       -> /run/systemd/resolve/resolv.conf
```

这破坏了公司内网域名的解析链路，实际造成：

- `gitlab.software.cambricon.com` 返回 `DNS_PROBE_FINISHED_NXDOMAIN`；
- `caip.cambricon.com:30443` 无法访问；
- 公司 GitLab、CAIP 等内网站点在公网 DNS 下无法正确解析。

恢复过程为：

```bash
sudo resolvectl revert enp2s0
sudo ln -sfn ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
sudo resolvectl flush-caches
nmcli device reapply enp2s0
```

恢复后，`systemd-resolved` 重新使用公司 DNS：

```text
10.3.34.10
172.10.80.158
```

实际验证结果：

```text
caip.cambricon.com -> 10.99.62.11 / 10.99.62.12 / 10.99.62.13
10.99.62.11/12/13:30443 -> TCP 连接成功
https://caip.cambricon.com:30443/ -> HTTP/2 200
```

事故结论：**公共 AI 网站恢复不能通过覆盖全局 DNS 或破坏公司内网路由实现。**

## 一、现象

### 1. aTrust 连接状态

aTrust 登录后状态为：

- `status: online`
- `tunnelStatus: tunnelAvailable`
- 创建虚拟接口，例如 `utun7`
- 在线时 `utun7` 获得类似 `10.102.1.50/24` 的地址

### 2. DNS 返回异常

aTrust 在线时，即使系统 DNS 看起来仍由 `systemd-resolved` 管理，公共域名也可能被解析到明显错误的地址。例如曾出现：

```text
chatgpt.com        -> 128.121.146.101 / 185.45.7.185 等异常地址
gemini.google.com  -> 199.16.156.103 / 157.240.10.41 等异常地址
api.openai.com     -> 异常或不可达地址
```

正常情况下应类似：

```text
chatgpt.com        -> 104.18.32.47 / 172.64.155.209
api.openai.com     -> 172.66.0.243 / 162.159.140.245
gemini.google.com  -> 142.251.*.*
```

### 3. 普通 UDP DNS 会被干扰

实测中出现过：

```text
dig @8.8.8.8 chatgpt.com
```

也返回异常地址；而：

```text
dig @1.1.1.1 chatgpt.com
```

可能直接超时。

这说明问题不只是 `/etc/resolv.conf` 配置错了，而是 aTrust 对普通 UDP/53 DNS 查询存在拦截、污染或透明处理。

### 4. 路由层面也存在 aTrust 注入项

aTrust 登录后会在主路由表中加入：

```text
10.10.150.19 dev utun7
159.226.39.1 dev utun7
198.18.* dev utun7
```

其中 `198.18.*` 是透明代理/保留测试网段相关路由。它们会扩大 aTrust 对公网访问的影响范围。

用户实际只需要访问：

```text
10.10.150.*
```

尤其包括堡垒机：

```text
10.10.150.19
```

因此最终目标是：只让 `10.10.150.0/24` 走 aTrust，其余流量不受 aTrust 影响。

## 二、问题定位

### 1. 不是简单改 `/etc/resolv.conf`

`/etc/resolv.conf` 可能仍指向：

```text
/run/systemd/resolve/resolv.conf
```

或 `systemd-resolved` 的 stub 文件，但实际 DNS 查询结果仍会被 aTrust 干扰。因此不能只通过观察 `/etc/resolv.conf` 判断 DNS 是否正常。

### 2. 单独给 Chrome 代理只是绕路

此前曾实现过：

```text
aTrust 专用 Chrome
    -> 127.0.0.1:18787 本地 HTTP CONNECT 代理
    -> 代理内部使用 DoH/固定公网解析
```

这个方案能让专用 Chrome 访问 ChatGPT、Gemini、Gmail，但有明显局限：

- 普通 Chrome 仍受影响；
- Codex CLI 仍受影响；
- VS Code 插件仍受影响；
- 需要维护独立浏览器 Profile；
- 本质是“应用级绕过”，不是系统级隔离。

因此该方案现在标记为过时方案，仅保留为备用。

### 3. 历史判断：同时处理路由与 DNS（已停用）

> [!WARNING]
> 本节记录早期排查结论，不再作为实施建议。尤其不得启用全局 DoH，也不得删除 aTrust 下发的其他路由。

最终需要同时处理：

```text
路由隔离：
只让 10.10.150.0/24 走 aTrust utun 网卡

DNS 隔离：
公网域名不再走会被 aTrust 干扰的 UDP DNS，而是走本机 DoH 代理
```

只改路由不够，因为 DNS 污染仍会让浏览器/Codex 拿到错误 IP。

只改 DNS 也不够，因为 aTrust 注入的 `198.18.*` 路由仍可能影响公网访问。

## 三、历史方案：系统级 aTrust split（已停用）

> [!CAUTION]
> 本节方案会修改全局 DNS，并删除 aTrust 下的非 `10.10.150.*` 路由，曾间接导致公司 GitLab、CAIP 等内网服务不可访问。仅作历史记录，禁止按本节操作。

### 1. 目标效果

启用后：

```text
10.10.150.0/24  -> aTrust utun7
公网流量         -> enp2s0 默认网关
公网 DNS         -> 127.0.0.1 本机 DoH 代理
```

不做的事情：

- 不修改普通网卡 IP；
- 不修改默认网关；
- 不持久修改 NetworkManager 配置；
- 不修改 aTrust 客户端配置；
- 不要求使用独立 Chrome；
- 不要求 Codex 单独配置代理。

### 2. 已创建的工具

```text
/home/cambricon/bin/atrust-split-on
/home/cambricon/bin/atrust-split-off
/home/cambricon/bin/atrust-split-status
/home/cambricon/bin/atrust-doh-dns-proxy
/etc/systemd/system/atrust-doh-dns-proxy.service
```

### 3. 工作原理

`atrust-split-on` 会：

1. 自动识别当前 aTrust 虚拟网卡，例如 `utun7`；
2. 保存启用前的 DNS 运行态到：

   ```text
   /run/atrust-split.state
   ```
3. 启动本机 DoH DNS 服务：

   ```text
   atrust-doh-dns-proxy.service
   127.0.0.1:53 -> Cloudflare DoH
   ```
4. 将系统 DNS 临时切到：

   ```text
   127.0.0.1
   ```
5. 删除 aTrust 注入到 `utun*` 上的非 `10.10.150.*` 路由，尤其是 `198.18.*`；
6. 添加/保留：

   ```text
   10.10.150.0/24 dev utun*
   ```

`atrust-split-off` 会：

1. 删除本工具添加的 `10.10.150.0/24` 路由；
2. 恢复本次 split 启用前记录下来的 aTrust 原始路由；
3. 恢复启用前的 DNS 运行态；
4. 停止本机 DoH DNS 服务；
5. 删除 `/run/atrust-split.*` 状态文件。

## 四、历史使用方法（禁止执行）

> [!CAUTION]
> 以下命令仅用于说明旧方案，不得在当前系统执行。

### 1. 登录 aTrust

先正常打开并登录 aTrust，确认隧道已连接。

### 2. 启用隔离

```bash
sudo /home/cambricon/bin/atrust-split-on
```

成功时会看到类似：

```text
aTrust split 已启用。
公网 DNS: 127.0.0.1 -> Cloudflare DoH
aTrust 路由: 仅保留 10.10.150.0/24 -> utun7
公网出口: enp2s0 保持默认路由
```

### 3. 查看状态

```bash
/home/cambricon/bin/atrust-split-status
```

重点确认：

```text
10.10.150.19 dev utun7
10.10.150.50 dev utun7
104.18.32.47 via 192.168.82.1 dev enp2s0
DNS Servers: 127.0.0.1
```

公网域名应解析为正常地址：

```text
chatgpt.com        -> 172.64.155.209 / 104.18.32.47
gemini.google.com  -> 142.251.*.*
api.openai.com     -> 172.66.0.243 / 162.159.140.245
```

### 4. 关闭隔离并恢复

```bash
sudo /home/cambricon/bin/atrust-split-off
```

如果已经退出 aTrust，也可以执行该命令，用于停止本机 DoH 服务并恢复 DNS 运行态。

### 5. 日常推荐流程

```text
1. 登录 aTrust
2. 执行 sudo /home/cambricon/bin/atrust-split-on
3. 正常使用普通 Chrome / Codex / VS Code
4. 不需要 aTrust 时，执行 sudo /home/cambricon/bin/atrust-split-off
5. 退出 aTrust
```

## 五、历史验证结果

启用 split 后已验证：

```text
10.10.150.19 -> utun7
10.10.150.50 -> utun7
104.18.32.47 -> enp2s0
8.8.8.8      -> enp2s0
```

DNS 已恢复正常：

```text
chatgpt.com        -> 172.64.155.209
gemini.google.com  -> 142.251.xxx.2
api.openai.com     -> 172.66.0.243 / 162.159.140.245
```

连通性验证：

```text
gemini.google.com  HTTP/2 200
chatgpt.com        HTTP/2 403
api.openai.com     HTTP/2 421
10.10.150.19:2222  OPEN
```

说明：

- `chatgpt.com` 在 `curl` 中返回 `403` 通常是 Cloudflare 浏览器挑战，不代表网络失败；
- `api.openai.com` 返回 `421` 表示已连到真实 OpenAI/Cloudflare 入口，不是 DNS 污染超时；
- 浏览器中应以页面能否正常打开为准；
- 若浏览器仍异常，优先完全退出 Chrome 后重开，要时清理浏览器 DNS/QUIC 缓存。

## 六、过时方案：aTrust 专用 Chrome

> 状态：已过时，仅作为备用方案保留。

历史上创建过：

```text
/home/cambricon/.local/bin/atrust-secure-chrome
/home/cambricon/.local/bin/atrust-browser-proxy
/home/cambricon/.local/share/applications/atrust-secure-chrome.desktop
/home/cambricon/.local/share/atrust-secure-chrome/profile
```

该方案曾经用于：

```text
aTrust 专用 Chrome
    -> 127.0.0.1:18787 HTTP CONNECT 代理
    -> 代理内部使用安全 DNS
    -> ChatGPT / Gemini / Gmail
```

现在不推荐作为主方案，原因：

- 只能解决专用 Chrome；
- 不能自然解决普通 Chrome；
- 不能自然解决 Codex CLI；
- 不能自然解决 VS Code 插件；
- 需要单独登录 Google/Gmail/ChatGPT/Gemini 账号；
- 维护成本高于系统级隔离。

若系统级 split 临时不可用，可短期使用它应急。

## 七、注意事项与防范

### 1. 该工具目前只处理 `10.10.150.0/24`

本次按要求只围绕：

```text
10.10.150.*
```

如果后续需要访问：

```text
10.10.162.22
```

或其他内网段，不要手动乱加路由，应先把目标网段明确加入脚本白名单。

### 2. 不要同时使用多个修复方案

当前 `atrust-split-on/off/status` 已收窄为只处理 `10.10.150.0/24` 路由。使用前应确认脚本不包含 DNS、DoH、默认路由或其他网段修改。

允许使用的工具是：

```text
atrust-split-on/off/status
```

这些命令仅管理 `10.10.150.0/24` 专用路由，**不承担 ChatGPT、Gemini 或 Codex 的 DNS/代理修复**。不必再依赖：

```text
aTrust 专用 Chrome
codex-atrust
code-atrust
```

这些可以作为备用，但不要把多个方案混在一起排查，否则容易把代理、DNS 缓存、浏览器缓存混成一团。

### 3. aTrust 重新登录后可能需要重新建立专用路由

aTrust 断开重连后，`utun` 接口编号可能改变。登录成功后可重新执行：

```bash
sudo /home/cambricon/bin/atrust-split-on
```

然后只检查 `10.10.150.0/24` 的路由决策：

```bash
/home/cambricon/bin/atrust-split-status
```

### 4. 退出 aTrust 前建议先关闭 split

推荐顺序：

```bash
sudo /home/cambricon/bin/atrust-split-off
```

然后再退出 aTrust。

这样只删除工具创建的 `10.10.150.0/24` 专用路由，不应修改 DNS 或其他路由。

### 5. 浏览器缓存可能造成假故障

即使系统网络已经恢复，Chrome 仍可能因为缓存导致页面短时间异常。可尝试：

- 完全退出 Chrome 后重开；
- 打开 `chrome://net-internals/#dns` 清理 DNS 缓存；
- 打开 `chrome://net-internals/#sockets` 关闭空闲 socket；
- 必要时关闭并重新打开 VS Code / Codex。

### 6. 不要修改 `/etc/resolv.conf` 或全局 DNS

Ubuntu 24.04 中 `/etc/resolv.conf` 由 `systemd-resolved` 管理。手工修改该文件或通过 `resolvectl` 覆盖全局 DNS，都可能再次破坏公司 GitLab、CAIP 等内网域名解析。当前专用路由工具不应调用 `resolvectl`。

## 八、维护与排查命令

> [!NOTE]
> DoH 服务、公网 DNS 与公网 HTTPS 命令仅用于只读观察历史问题，不得据此修改系统 DNS。

### 查看 split 状态

```bash
/home/cambricon/bin/atrust-split-status
```

### 查看本机 DoH DNS 服务

```bash
systemctl status atrust-doh-dns-proxy.service
```

### 查看 DNS 配置

```bash
resolvectl status
resolvectl dns
resolvectl domain
```

### 查看关键路由

```bash
ip route get 10.10.150.19
ip route get 10.10.150.50
ip route get 104.18.32.47
ip route show dev utun7
```

### 验证公网域名解析

```bash
getent ahostsv4 chatgpt.com
getent ahostsv4 gemini.google.com
getent ahostsv4 api.openai.com
```

### 验证公网 HTTPS

```bash
curl -I --max-time 15 https://chatgpt.com/
curl -I --max-time 15 https://gemini.google.com/
curl -I --max-time 15 https://api.openai.com/
```

### 验证堡垒机端口

```bash
timeout 5 bash -lc '</dev/tcp/10.10.150.19/2222' && echo OPEN || echo FAILED
```

## 九、回退方式

### 1. 正常关闭 split

```bash
sudo /home/cambricon/bin/atrust-split-off
```

### 2. 如需删除隔离工具

先关闭 split：

```bash
sudo /home/cambricon/bin/atrust-split-off
```

再删除文件：

```text
/home/cambricon/bin/atrust-split-on
/home/cambricon/bin/atrust-split-off
/home/cambricon/bin/atrust-split-status
/home/cambricon/bin/atrust-doh-dns-proxy
/home/cambricon/.local/share/atrust-split/
/etc/systemd/system/atrust-doh-dns-proxy.service
```

删除 systemd 服务后执行：

```bash
sudo systemctl daemon-reload
```

## 十、经验总结

1. VPN 导致解析异常时，不能只看 `/etc/resolv.conf`；应同时对比系统解析、指定 DNS 查询结果和实际连接 IP。
2. aTrust 的影响不只是默认路由，也包括 DNS 与透明代理相关路由。
3. 只修浏览器不够，Codex 和 VS Code 插件也需要系统级 DNS/路由环境恢复。
4. 公共 AI 网站恢复必须服从“公司内网访问优先”约束，不得修改全局 DNS、`/etc/resolv.conf`、默认路由或其他内网路由。
5. 当前工具只允许处理 `10.10.150.0/24`，后续新增内网段必须明确授权并独立验证，不得影响现有公司内网访问。
