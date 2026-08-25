# 1. Git 开发流程规范

> 适用于采用**线性历史策略**的 GitLab 项目。

## 1. 领取 Issue

在 GitLab 中确认：

- 开发目标
- 验收标准

## 2. 同步主分支

```bash
git switch master
git fetch origin
git pull --ff-only origin master
```

本地 `master` 始终与 `origin/master` 保持一致

`--ff-only`：

## 3. 创建功能分支

```bash
git switch -c <功能分支名>
```

示例：

```bash
git switch -c zhangyihao/feat-smart-routing
```

## 4. 开发并提交

```bash
git status
git add <相关文件>
git commit -m "feat(webapp): add PD routing strategy"
```

提交应保持：

- 单次提交目标清晰
- 不混入无关修改
- 提交信息符合团队规范

## 6. 推送功能分支

```bash
#首次推送
git push -u origin <功能分支名>
#后续推送
git push
```

远程仓库创建功能分支，目的为在gitlab申请MR

## 7. 创建 Merge Request

进入gitlab相关项目的指定分支，创建MR

MR 中应包含：

- 关联 Issue
- 修改内容

创建 MR 后，等待 CI/CD 和 Code Review。

## 8. 处理 Review 意见

处理来自gitlab mr的revire意见(comment)

修改后继续提交并推送：

```bash
git add <相关文件>
git commit -m "fix(webapp): address review comments"
git push
```

不需要重新创建 MR。

## 9. 合并前 Rebase

**Rebase**十分重要，维护“线性历史”的核心操作，rebase内部细节可咨询AI

当 `master` 有新提交（在review期间）时：

```
  master:  A ---> B ---> C
            \
  feature:   ---> X  (你的基点还在 A)
```

如图所示，feature分支出现“滞后”的现象，这是使用rebase的**根本原因**

使用方法：本地执行rebase操作，重新推送；补充：rebase可能会出现Merge conflict

```bash
git fetch origin
git rebase origin/master
```

出现冲突时：

```bash
git status
# 手动修改冲突文件
git add <冲突文件>
git rebase --continue
```

Rebase 完成后重新验证代码。

补充：以上为本地rebase处理的流程，有时gitlab会主动提供自动rebase的功能

## 10. 推送 Rebase 后的分支

```bash
git push --force-with-lease
```

`--force-with-lease`

## 11. 合并到 master

继续之前的review流程，并确认以下条件满足：

- Review 已通过
- 最新 CI/CD 已通过
- 功能分支已基于最新 `master`

然后在 GitLab 中执行 Merge。

推荐策略：

- Fast-forward Merge
- 或 Squash + Fast-forward
- 合并后删除远程功能分支

## 12. 合并后清理

```bash
git switch master
git pull --ff-only origin master
git fetch --prune
git branch -d <功能分支名>
```

如果项目使用 Squash Merge，普通删除失败且已确认代码合入：

```bash
git branch -D <功能分支名>
```

## 核心原则

```text
Issue
→ 同步 master
→ 创建功能分支
→ 开发与本地验证
→ 推送并创建 MR
→ Code Review 与 CI/CD
→ Rebase 最新 master
→ 最终验证
→ 合并并清理分支
```

主分支保持**线性历史**，开发只发生在功能分支，合并前必须基于最新主分支完成验证。

# 2. Tag 版本查看流程

Git Tag 用于为某个确定的 Commit 添加固定标记，项目通常使用 `v1.2.0`、`release-1.2.0` 等 Tag 标识发布版本。但 Tag 本身不一定等于正式 Release，仍需结合项目命名规范以及 GitLab 的 Releases 页面确认。

### 1. 确认当前工作区状态

切换版本前先检查是否存在尚未提交的修改：

```bash
git status
```

如果工作区不干净，应先提交、暂存或使用 Worktree，避免切换版本时产生冲突或覆盖当前工作。

### 2. 同步远程 Tag

```bash
git fetch origin --tags
```

查看本地已有的全部 Tag：

```bash
git --no-pager tag --list
```

如果同步后仍怀疑本地 Tag 不完整，可以直接查看远程仓库中的 Tag：

```bash
git ls-remote --tags origin
```

### 3. 查看 Tag 信息和代码差异

查看 Tag 指向的 Commit、提交信息和代码变更：

```bash
git show <tag-name>
```

比较某个 Tag 与当前分支的差异：

```bash
git diff <tag-name>..HEAD
```

### 4. 临时切换到 Tag 版本

如果只需要查看、编译或运行 Tag 对应的代码：

```bash
git switch --detach <tag-name>
```

例如：

```bash
git switch --detach v1.2.0
```

此时仓库处于 `detached HEAD` 状态，代码内容对应 `v1.2.0`，但当前并不位于任何分支。查看完成后返回之前的分支：

```bash
git switch -
```

不要直接在 `detached HEAD` 状态下长期开发，否则新提交可能因没有分支引用而难以管理。

### 5. 基于 Tag 创建排查或修复分支

如果需要修改 Tag 版本的代码，应基于 Tag 创建新分支：

```bash
git switch -c <新分支名> <tag-name>
```

例如：

```bash
git switch -c zhangyihao/investigate-v1.2.0 v1.2.0
```

后续修改和提交都会记录在新分支上，不会改变原 Tag。

# 3. 开发辅助

## 3.1 git blame

`git blame` 用于查看文件每一行最后由谁在哪个 Commit 中修改，常用于追溯代码背景和定位问题。

### 基本用法

```bash
git blame <文件路径>
git blame -L <起始行>,<结束行> <文件路径>
```

### 操作流程

1. 确定需要追溯的文件和行号范围。
2. 执行 `git blame`，获取对应的 Commit ID、作者和修改时间。
3. 使用 `git show <commit-id>` 查看该次提交的完整改动和提交说明。
4. 结合 Issue、MR 或相关人员进一步确认修改背景。

git branch -vv
