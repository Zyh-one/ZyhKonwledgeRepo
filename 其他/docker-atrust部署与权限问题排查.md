# docker-aTrust 部署与 `/tmp/aTrustShell.conf` 权限问题排查方案

## 1. 目标

在 Ubuntu 宿主机中使用 `docker-atrust`，将 aTrust 客户端隔离在容器内，避免其污染宿主机的 DNS、路由和网络环境。

整体结构：

```text
Ubuntu 宿主机
└── docker-atrust 容器
    ├── aTrust 图形客户端
    ├── VNC：127.0.0.1:5901
    ├── SOCKS5：127.0.0.1:1080
    └── HTTP 代理：127.0.0.1:8888
```

学校 VPN 接入地址：

```text
https://newvpn.ict.ac.cn
```

该地址需要填写在容器内的 aTrust 客户端中，不是 VNC 地址。

---

## 2. 宿主机准备

确认 Docker 正常：

```bash
docker --version
docker info
```

确认 TUN 设备存在：

```bash
ls -l /dev/net/tun
```

如果不存在：

```bash
sudo modprobe tun
```

---

## 3. 拉取镜像

```bash
docker pull hagb/docker-atrust
```

确认镜像：

```bash
docker images | grep docker-atrust
```

现成镜像已经包含 aTrust 客户端，通常不需要再手动安装学校门户下载的 `.deb` 包。

---

## 4. 创建持久化目录

```bash
mkdir -p "$HOME/.atrust-data"
```

该目录用于保存 aTrust 配置、登录状态等数据。

---

## 5. 启动容器

```bash
docker run -d   --name atrust   --device /dev/net/tun   --cap-add NET_ADMIN   --restart unless-stopped   --tmpfs /tmp:rw,exec,nosuid,mode=1777   -e PASSWORD='AtrustVnc123'   -e URLWIN=1   -v "$HOME/.atrust-data:/root"   -p 127.0.0.1:5901:5901   -p 127.0.0.1:1080:1080   -p 127.0.0.1:8888:8888   -p 127.0.0.1:54631:54631   --sysctl net.ipv4.conf.default.route_localnet=1   hagb/docker-atrust
```

关键参数：

```text
/dev/net/tun              VPN 虚拟网卡
NET_ADMIN                 修改容器网络的权限
5901                      VNC 图形界面
1080                      SOCKS5 代理
8888                      HTTP 代理
54631                     aTrust 相关端口
/tmp tmpfs                提供标准、可写的临时目录
```

---

## 6. 通过 VNC 登录

安装 VNC 客户端：

```bash
sudo apt update
sudo apt install -y tigervnc-viewer
```

连接：

```bash
vncviewer 127.0.0.1:5901
```

部分客户端需要：

```bash
vncviewer 127.0.0.1::5901
```

进入容器桌面后，在 aTrust 中填写：

```text
https://newvpn.ict.ac.cn
```

然后按照学校原有流程完成认证。

---

## 7. 当前日志问题

容器日志持续出现：

```text
sh: 1: cannot create /tmp/aTrustShell.conf: Permission denied
```

同时还可能出现：

```text
Failed to connect to bus
UnhandledPromiseRejectionWarning
ReferenceError: err is not defined
Glib-GObject-CRITICAL
```

其中最关键的问题是：

```text
/tmp/aTrustShell.conf 无法创建或覆盖
```

后面的 DBus、Node.js 和 GLib 报错大概率是连锁异常。

---

## 8. 已确认信息

执行：

```bash
docker exec -it atrust sh -c '
id
ls -ld /tmp
touch /tmp/test-file && echo "tmp writable" || echo "tmp not writable"
'
```

结果为：

```text
uid=0(root)
drwxrwxrwt ... /tmp
tmp writable
```

这说明：

- `/tmp` 目录权限正常；
- `/tmp` 权限为标准的 `1777`；
- root 可以正常写入 `/tmp`；
- 问题不是整个 `/tmp` 不可写。

因此，问题范围缩小到：

1. `/tmp/aTrustShell.conf` 已存在且权限异常；
2. 文件属主与 aTrust 实际运行用户不一致；
3. 多个 aTrust 进程使用不同用户操作同一文件；
4. 文件可能是软链接、目录或带特殊属性；
5. aTrust 在异常情况下自身处理逻辑存在缺陷。

---

## 9. 检查目标文件

执行：

```bash
docker exec -u 0 atrust sh -c '
echo "===== file ====="
ls -la /tmp/aTrustShell.conf 2>/dev/null || echo "not exists"

echo "===== stat ====="
stat /tmp/aTrustShell.conf 2>/dev/null || true

echo "===== type/link ====="
file /tmp/aTrustShell.conf 2>/dev/null || true
readlink -f /tmp/aTrustShell.conf 2>/dev/null || true

echo "===== attributes ====="
lsattr /tmp/aTrustShell.conf 2>/dev/null || true
'
```

重点关注：

- 文件是否存在；
- 文件属主和属组；
- 权限是否允许写入；
- 是否为软链接；
- 是否为目录或特殊文件；
- 是否存在 immutable 属性。

---

## 10. 检查 aTrust 实际运行用户

执行：

```bash
docker exec -it atrust sh -c '
ps -eo user,uid,pid,ppid,cmd |
grep -Ei "atrust|sangfor|electron|node" |
grep -v grep
'
```

需要确认：

- aTrust GUI 由哪个用户启动；
- Node.js 进程由哪个用户启动；
- 后台服务是否由 root 启动；
- 是否存在多个不同用户同时操作 `/tmp/aTrustShell.conf`。

可能的冲突模式：

```text
root 进程创建文件
        ↓
普通用户进程尝试覆盖
        ↓
Permission denied
```

---

## 11. 临时修复方案

先删除旧文件：

```bash
docker exec -u 0 atrust rm -f /tmp/aTrustShell.conf
```

创建一个所有用户可写的普通文件：

```bash
docker exec -u 0 atrust sh -c '
touch /tmp/aTrustShell.conf
chmod 666 /tmp/aTrustShell.conf
ls -l /tmp/aTrustShell.conf
'
```

重启容器：

```bash
docker restart atrust
```

只查看重启后的新日志：

```bash
sleep 5
docker logs --since 15s atrust
```

不要直接执行：

```bash
docker logs atrust
```

否则旧日志仍会显示，容易误判为问题没有变化。

---

## 12. 按实际用户修复属主

如果 aTrust 实际由某个普通用户运行，应让该用户拥有文件。

假设实际 UID 为 `1000`：

```bash
docker exec -u 0 atrust sh -c '
rm -f /tmp/aTrustShell.conf
touch /tmp/aTrustShell.conf
chown 1000:1000 /tmp/aTrustShell.conf
chmod 666 /tmp/aTrustShell.conf
'
```

然后：

```bash
docker restart atrust
sleep 5
docker logs --since 15s atrust
```

UID 必须以 `ps` 输出为准，不要直接猜。

---

## 13. 监控文件由谁创建

先删除文件：

```bash
docker exec -u 0 atrust rm -f /tmp/aTrustShell.conf
```

持续观察：

```bash
docker exec -it atrust sh -c '
while true; do
    date
    ls -ln /tmp/aTrustShell.conf 2>/dev/null || echo "not exists"
    sleep 0.5
done
'
```

一旦文件出现，通过数字 UID/GID 可以判断由哪个用户创建。

---

## 14. 检查只读根文件系统

```bash
docker inspect atrust   --format 'ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}}'
```

正常应为：

```text
ReadonlyRootfs=false
```

---

## 15. 代理测试

登录成功后，使用 SOCKS5 测试内网：

```bash
curl --socks5-hostname 127.0.0.1:1080   -I http://内网地址
```

建议使用：

```text
--socks5-hostname
```

这样域名解析也会通过 SOCKS5 代理完成。

使用 HTTP 代理测试：

```bash
curl -x http://127.0.0.1:8888   -I http://内网地址
```

临时设置当前终端代理：

```bash
export http_proxy=http://127.0.0.1:8888
export https_proxy=http://127.0.0.1:8888
```

使用结束后取消：

```bash
unset http_proxy
unset https_proxy
```

不要直接将这些代理变量写入 `~/.zshrc`，否则 Codex、GitHub、npm 等外网流量也可能被送入 aTrust 容器。

---

## 16. 日常管理命令

启动：

```bash
docker start atrust
```

停止：

```bash
docker stop atrust
```

重启：

```bash
docker restart atrust
```

查看状态：

```bash
docker ps -a --filter name=atrust
```

查看最近日志：

```bash
docker logs --tail 100 atrust
```

只看最近 30 秒：

```bash
docker logs --since 30s atrust
```

删除容器：

```bash
docker rm -f atrust
```

保留：

```text
$HOME/.atrust-data
```

即可在重新创建容器后继续复用部分配置。

---

## 17. 当前结论

当前问题不是 Docker 容器整体无法运行，也不是 `/tmp` 整体不可写。

更可能的根因是：

```text
aTrust 多进程或多用户操作同一个临时文件
                   ↓
aTrustShell.conf 被某个用户创建
                   ↓
另一个用户无法覆盖或重建
                   ↓
Permission denied
                   ↓
引发 DBus、Node.js、GTK/GLib 连锁异常
```

下一步最重要的两项检查是：

```bash
docker exec -u 0 atrust sh -c '
ls -la /tmp/aTrustShell.conf 2>/dev/null
stat /tmp/aTrustShell.conf 2>/dev/null
file /tmp/aTrustShell.conf 2>/dev/null
lsattr /tmp/aTrustShell.conf 2>/dev/null
'
```

以及：

```bash
docker exec -it atrust sh -c '
ps -eo user,uid,pid,ppid,cmd |
grep -Ei "atrust|sangfor|electron|node" |
grep -v grep
'
```

根据这两组输出，可以进一步确定最终修复方式。
