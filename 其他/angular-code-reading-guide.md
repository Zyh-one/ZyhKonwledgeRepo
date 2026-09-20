# Angular 模板与前端模块梳理指南

本文面向当前仓库的前端代码，目标不是一次性理解平台的全部业务，而是建立一套可重复使用的方法，把以下内容关联起来：

```text
浏览器页面
  → Angular 路由和组件
  → HTML 模板及 TypeScript 逻辑
  → Service/API 调用
  → 浏览器发出的 HTTP 请求
  → 响应数据和最终 DOM
```

当前前端主要使用 Angular 14、ng-zorro，以及项目内部的 `distributed-platform-antd` 组件库。因此，浏览器 Elements 面板中的最终 HTML 与 `.component.html` 源文件通常不会逐行、逐标签对应。

## 1. 先区分四类模板内容

阅读模板时，先判断标签或语法属于哪一层。

| 类型             | 示例                                                         | 来源及作用                         |
| ---------------- | ------------------------------------------------------------ | ---------------------------------- |
| 原生 HTML        | `div`、`table`、`tr`、`td`、`a`                              | 浏览器原生元素                     |
| Angular 模板元素 | `ng-template`、`ng-container`、`ng-content`、`router-outlet` | 控制视图声明、插入、投影和路由出口 |
| 第三方组件       | `nz-table`、`nz-card`、`nz-modal`                            | ng-zorro 组件                      |
| 项目组件         | `dp-link`、`dp-table-actions`、`app-*`、`shared-*`           | 项目或内部组件库封装               |

前两类决定 Angular 如何组织视图，后两类往往会在组件内部生成另一套 DOM。例如源码中的：

```html
<dp-link [dpRouterLink]="['/predictor', data.metadata.uid]">
  {{ data.metadata.name }}
</dp-link>
```

可能在浏览器中生成 `<a>`、`<span>` 等元素。此时应继续查看 `dp-link` 的实现，而不是要求源码和最终 DOM 的标签结构完全一致。

## 2. Angular 模板元素

### 2.1 `ng-template`：声明暂不渲染的视图

`ng-template` 可以理解为一段“视图配方”。声明模板时，模板内容不会立即插入页面：

```html
<ng-template #messageTpl>
  <span>Hello</span>
</ng-template>
```

`#messageTpl` 是模板引用变量，对应 Angular 中的 `TemplateRef`。只有其他指令或组件使用 `messageTpl` 时，其中的 `<span>` 才会生成。

因此需要牢记：

```text
ng-template 的声明位置 ≠ 其内容最终渲染的位置
```

浏览器中通常也不会出现 `<ng-template>` 元素，Angular 可能只保留注释锚点。

#### 作为 `ngIf` 的分支

当前项目常见写法：

```html
<ng-container *ngIf="data.spec.duration === 0; else expirationTimeTpl">
  <span>{{ 'attrs.no_limit' | translate }}</span>
</ng-container>

<ng-template #expirationTimeTpl>
  <span>{{ getExpirationTime(data) || '--' }}</span>
</ng-template>
```

其逻辑相当于：

```text
duration === 0 → 渲染“不限时”
否则           → 在条件所在位置渲染 expirationTimeTpl
```

项目示例见 [`predictor-overview.component.html`](../../webapp/caip/projects/paas/src/app/pages/predictor/predictor-overview/predictor-overview.component.html)。

#### 通过 `ngTemplateOutlet` 主动插入

```html
<ng-container
  *ngTemplateOutlet="detailTpl; context: { item: item }"
></ng-container>

<ng-template #detailTpl let-item="item"> {{ item.metadata.name }} </ng-template>
```

对应关系为：

```text
context.item → let-item="item"
```

可以把它近似理解为调用一个返回视图的函数：

```ts
detailTpl({ item });
```

#### 使用 `$implicit` 传递默认参数

```html
<ng-container
  *ngTemplateOutlet="envFormTpl; context: { $implicit: item, index: index }"
></ng-container>

<ng-template #envFormTpl let-formGroup let-index="index"> ... </ng-template>
```

对应关系为：

```text
context.$implicit → let-formGroup
context.index     → let-index="index"
```

`let-formGroup` 等价于 `let-formGroup="$implicit"`。项目示例见 [`modelpackage-version-spec.component.html`](../../webapp/caip/projects/paas/src/app/pages/modelpackage/components/modelpackage-version-spec/modelpackage-version-spec.component.html)。

#### 把模板交给子组件

```html
<nz-card [nzTitle]="titleTpl" [nzExtra]="extraTpl"></nz-card>

<ng-template #titleTpl>标题</ng-template>
<ng-template #extraTpl>操作区</ng-template>
```

这里父组件只负责声明内容，`nz-card` 决定内容的渲染位置。这种模式相当于给子组件传入“可渲染的回调”。项目中的 `nzTitle`、`nzExtra`、`nzNoResult`、`dpActions`、`dpFooter` 等属性都可能接收模板。

推理服务列表中的操作菜单也是这种模式：

```html
<dp-table-actions
  [dpActions]="[startAction, stopAction, deleteAction]"
></dp-table-actions>

<ng-template #stopAction>
  <a (click)="stopEl.open(data)">...</a>
</ng-template>
```

`<a>` 在 `ng-template` 中声明，但由 `dp-table-actions` 决定实际插入位置和展示方式。这也是源码标签位置与浏览器 DOM 位置不完全相同的常见原因。

#### 指令标记的模板

```html
<ng-template nzModalContent> ... </ng-template>
```

这种模板不一定声明 `#变量名`。`nzModalContent` 指令会识别并收集模板，由弹窗组件在内容区域渲染。

### 2.2 `ng-container`：不产生 DOM 的逻辑容器

`ng-container` 用于组合或控制一组内容，但不会在最终 DOM 中产生额外元素：

```html
<ng-container *ngIf="visible">
  <span>A</span>
  <span>B</span>
</ng-container>
```

适合以下场景：

- 同时控制多个相邻元素，又不想增加 `<div>`；
- 在表格中使用 `*ngFor`、`*ngIf`，避免破坏 `table → tbody → tr → td` 的合法结构；
- 作为 `ngTemplateOutlet` 的无外壳插入位置；
- 配合 `ngSwitch` 组织多个分支。

`ng-container` 与 `ng-template` 的区别：

| 元素           | 核心作用                     | 是否立即参与渲染 | 是否产生自身 DOM |
| -------------- | ---------------------------- | ---------------- | ---------------- |
| `ng-container` | 给当前内容提供无外壳逻辑容器 | 取决于其结构指令 | 否               |
| `ng-template`  | 声明一段可稍后实例化的视图   | 否               | 否               |

### 2.3 `ng-content`：把父组件内容投影到子组件

组件使用方写入内容：

```html
<dp-form-layout>
  <app-example-form></app-example-form>
</dp-form-layout>
```

`dp-form-layout` 内部通过：

```html
<ng-content></ng-content>
```

决定父组件提供的内容插入在哪里。这叫内容投影。项目示例见 [`form-layout.component.html`](../../webapp/caip/projects/distributed-platform-antd/src/lib/components/form-layout/form-layout.component.html)。

需要区分：

```text
ng-content       → 投影组件使用方已经写好的内容
ng-template      → 保存一段可按需实例化的视图
ngTemplateOutlet → 在当前位置实例化指定模板
```

### 2.4 `router-outlet`：路由组件的渲染出口

```html
<router-outlet></router-outlet>
```

它表示“由当前路由配置决定这里显示哪个组件”。追踪页面入口时，应从浏览器 URL 查找路由配置，再找到对应的 `component` 或 `loadChildren`，不能只在顶层 HTML 中搜索页面内容。

## 3. 常见 Angular 模板语法

这些不一定是独立标签，但它们决定模板如何连接 TypeScript。

### 3.1 插值表达式

```html
{{ data.metadata.name }} {{ 'btns.stop' | translate }}
```

用于把组件状态转换为文字。项目大量使用国际化管道，因此浏览器显示“停止”时，源码中可能只有 `btns.stop`。

### 3.2 属性绑定

```html
[nzData]="listData" [disabled]="isLoading" [dpRouterLink]="['/predictor',
data.metadata.uid]"
```

阅读方向是：

```text
TypeScript 表达式 → HTML 元素、指令或子组件的输入属性
```

### 3.3 事件绑定

```html
(click)="handleStart(data)" (nzExpandChange)="handleExpandChange(data, $event)"
```

阅读方向是：

```text
用户或组件事件 → 当前组件的 TypeScript 方法
```

`$event` 是事件发出的值。

### 3.4 双向绑定

```html
[(ngModel)]="runtimeType"
```

它可以近似拆成：

```html
[ngModel]="runtimeType" (ngModelChange)="runtimeType = $event"
```

即 TypeScript 给控件初始值，控件变化后再更新 TypeScript 状态。

### 3.5 结构指令 `*ngIf`、`*ngFor`

星号是 Angular 的语法糖：

```html
<div *ngIf="visible">内容</div>
```

概念上相当于：

```html
<ng-template [ngIf]="visible">
  <div>内容</div>
</ng-template>
```

因此 `*ngIf` 会创建或销毁视图，而不只是通过 CSS 隐藏元素。

类似地：

```html
<tr *ngFor="let item of table.data; let index = index">
  ...
</tr>
```

表示 Angular 为集合中的每个 `item` 实例化一次该行模板。

### 3.6 `ngSwitch`

```html
<ng-container [ngSwitch]="data.status.overview">
  <dp-table-actions *ngSwitchCase="'Running'">...</dp-table-actions>
  <dp-table-actions *ngSwitchDefault>...</dp-table-actions>
</ng-container>
```

它根据状态选择一个视图分支。分析操作按钮是否显示时，需要同时检查：

- 当前 `ngSwitch` 值；
- `ngSwitchCase` 条件；
- 内部的权限管道或 `*ngIf`；
- 子组件是否会再次过滤模板。

### 3.7 模板引用变量

```html
<app-example-drawer #drawer></app-example-drawer>
<button (click)="drawer.open(data)">打开</button>
```

`#drawer` 指向模板中的组件实例。它与 `ng-template` 上的 `#detailTpl` 使用相同的引用语法，但引用对象不同：

```text
组件上的 #drawer      → 组件实例
ng-template 上的 #tpl → TemplateRef
原生元素上的 #input   → DOM 元素引用
```

## 4. 为什么源码 HTML 与浏览器 DOM 不一致

造成差异的主要机制包括：

1. Angular 组件会使用自己的模板替换或包裹组件标签；
2. `*ngIf` 和 `*ngFor` 会动态创建、删除或重复视图；
3. `ng-template` 的内容可能在另一个位置实例化；
4. `ng-content` 会把父组件内容投影到子组件内部；
5. ng-zorro 的弹窗、下拉菜单和 Tooltip 可能渲染到全局 overlay 容器；
6. `ng-container`、`ng-template` 不产生同名 DOM 元素；
7. 浏览器会修正不合法的原生 HTML 层级。

例如，表格中 `<tr>` 的直接子元素应当是 `<td>` 或 `<th>`。如果模板产生了非法层级，浏览器可能重新组织 DOM。另一方面，如果 `<a>` 声明在操作模板中，它也可能由 `dp-table-actions` 在组件内部的其他位置实例化。判断原因时应先确定它属于“浏览器纠错”还是“Angular 模板插入”。

推荐使用 Angular DevTools 查看组件树及组件输入，而不是只依赖 Elements 面板中的最终标签。

## 5. 梳理任意业务模块的固定方法

每次只选择一个页面和一个动作，例如：

```text
推理服务列表 + 首次加载
推理服务列表 + 展开版本
推理服务列表 + 点击停止
```

不要以“读懂 predictor 模块全部代码”为第一目标。

### 第一步：在浏览器中固定观察对象

记录：

```text
页面 URL：
页面上的关键文字或控件：
要追踪的动作：
对应 Fetch/XHR：
```

在 DevTools Network 中执行一次动作，记录：

- HTTP Method；
- Request URL；
- Query String；
- Request Payload；
- Response；
- Initiator 调用栈。

请求 URL 通常是关联后端请求与前端 API 代码最快的线索。

### 第二步：由 URL 找 Angular 路由

以 `/predictor` 为例：

```bash
rg "path: 'predictor'" webapp/caip/projects/paas/src/app
```

当前项目的入口链路为：

```text
/predictor
  → project.routes.ts 中的 loadChildren
  → PredictorModule
  → path: ''
  → PredictorOverviewComponent
```

相关文件：

- [`project.routes.ts`](../../webapp/caip/projects/paas/src/app/routes/project.routes.ts)
- [`predictor.module.ts`](../../webapp/caip/projects/paas/src/app/pages/predictor/predictor.module.ts)

遇到 `loadChildren` 时继续进入被加载的 Module；遇到 `component` 时进入对应组件；遇到 `resolve`、`canActivate` 时先记录，只有页面初始化或权限行为与它们有关时再深入。

### 第三步：建立组件三件套

在组件的 `@Component` 中确认：

```ts
@Component({
  selector: 'app-predictor-overview',
  templateUrl: './predictor-overview.component.html',
  styleUrls: ['./predictor-overview.component.less'],
})
```

由此建立：

```text
组件状态和行为 → .component.ts
页面模板       → .component.html
局部样式       → .component.less/.scss
```

然后查看组件是否继承基类、实现生命周期接口，以及构造函数注入了哪些 Service/API。

### 第四步：从页面文字或 DOM 反查模板

可以搜索：

```bash
rg "btns.stop" webapp/caip/projects
rg "attrs.predictor" webapp/caip/projects
rg "dp-table-actions" webapp/caip/projects/paas/src/app/pages/predictor
```

找到模板后，第一轮只阅读：

```text
{{ ... }}       展示了什么数据
[property]      数据流向哪个控件或子组件
(event)         用户动作进入哪个 TS 方法
*ngIf/*ngFor    什么条件决定视图是否出现
app-*/shared-*  工作是否交给了子组件
```

样式、图标、每个字段和每个管道可以暂时跳过。

### 第五步：从模板事件进入 TypeScript

例如：

```html
<a (click)="handleStart(data)">...</a>
```

继续搜索：

```bash
rg "handleStart" path/to/component.ts
```

重点记录：

```text
方法输入
  → 是否修改本地状态
  → 是否调用子组件 open()
  → 是否调用 Service/API
  → 在何处 subscribe
  → 成功后是否 getList()/刷新 Store/跳转路由
```

如果只看到：

```ts
drawer.open(data);
```

说明流程转入 Drawer/Modal 子组件，应进入它的 `open()`、表单模型和提交方法继续追踪。

### 第六步：检查公共基类

当前项目的列表页面经常继承公共 `TableOverviewDirective`。推理服务的主要链路为：

```text
PredictorOverviewComponent
  → paas/shared/TableOverviewDirective
  → distributed-platform-antd/TableOverviewDirective
```

底层基类负责通用分页、搜索、加载和轮询，页面组件只实现资源相关的请求：

```text
分页/搜索事件
  → 基类 getList()
  → getQuery()
  → 页面 getListRequest(params)
  → API 返回 Observable<HttpResponse<T>>
  → subscribe
  → setList(res.body)
  → Angular 变更检测
  → 表格重新渲染
```

相关文件：

- [`paas TableOverviewDirective`](../../webapp/caip/projects/paas/src/app/shared/table-overview/table-overview.directive.ts)
- [`distributed-platform-antd TableOverviewDirective`](../../webapp/caip/projects/distributed-platform-antd/src/lib/components/table/components/table-overview.directive.ts)

当页面类本身找不到 `getList()` 时，应优先查看 `extends`，不要误判为调用来源缺失。

### 第七步：由 API 方法对应 Network 请求

推理服务页面的请求入口类似：

```ts
getListRequest(params: HttpParams) {
  return this.predictorApi.listNamespacedPredictor(this.project.id, params);
}
```

生成的 `PredictorApi` 最终调用：

```ts
this.http.get(`/api/compute/v2/namespace/${namespace}/predictor`, {
  params: query,
});
```

于是得到闭环：

```text
浏览器 GET /api/compute/v2/namespace/{namespace}/predictor
  ↔ PredictorApi.listNamespacedPredictor()
  ↔ PredictorOverviewComponent.getListRequest()
  ↔ 基类 getList()
  ↔ 模板 table.data / *ngFor
  ↔ 浏览器表格行
```

API 示例见 [`predictor.api.ts`](../../webapp/caip/projects/client/src/lib/compute/api/predictor.api.ts)。文件头标明自动生成的 API 类适合用于确认 Method、URL、请求体和返回类型，但通常不应手工修改。

### 第八步：验证响应如何成为页面内容

从 `subscribe` 或 Store 更新点开始，回答：

1. 响应保存到哪个字段，例如 `listData`、`table.data` 或某个 Store；
2. 模板在哪里读取这个字段；
3. 是否经过 Pipe、getter 或转换函数；
4. 组件是否使用 `ChangeDetectionStrategy.OnPush`；
5. 更新后是否调用 `markForCheck()`；
6. 是否存在轮询、缓存或多个请求合并。

这一步用于解释“Network 已经返回数据，但页面为何这样展示”。

## 6. 推理服务列表的完整示例

```text
浏览器进入 /predictor?ns={namespace}
  ↓
project.routes.ts 懒加载 PredictorModule
  ↓
PredictorModule 的空路径映射 PredictorOverviewComponent
  ↓
组件继承 TableOverviewDirective
  ↓
基类 getList() 调用页面实现的 getListRequest(params)
  ↓
PredictorApi.listNamespacedPredictor(namespace, params)
  ↓
GET /api/compute/v2/namespace/{namespace}/predictor
  ↓
响应 body.items 保存为列表数据
  ↓
模板使用 *ngFor="let data of table.data"
  ↓
dp-link、dp-status-item、dp-table-actions 等子组件生成最终 DOM
```

这个示例中同时存在三类逻辑：

| 层次             | 例子                                                    |
| ---------------- | ------------------------------------------------------- |
| Angular 机制     | 依赖注入、生命周期、属性绑定、事件绑定、结构指令        |
| 项目公共机制     | `TableOverviewDirective`、Store、权限 Pipe、`dp-*` 组件 |
| 推理服务业务规则 | 状态、版本、协议、权限、操作按钮是否可用                |

阅读时先理解前两层的调用方式，再按当前任务选择性深入第三层。

## 7. `ng-template` 的固定阅读法

遇到任意 `ng-template`，依次回答五个问题：

1. 模板叫什么，例如 `#detailTpl`？
2. 谁使用它，例如 `ngTemplateOutlet`、`nzTitle` 或 `dpActions`？
3. 使用方最终在哪里实例化它？
4. `context` 传入了什么，`let-*` 如何接收？
5. 模板内部的事件进入哪个 TypeScript 方法？

推荐搜索方式：

```bash
rg "detailTpl" path/to/module
rg "ngTemplateOutlet" path/to/module
rg "TemplateRef" path/to/component.ts
```

对应阅读方向：

```text
模板声明
  → 模板引用名
  → 使用者
  → 插入位置
  → context/let 参数
  → 内部事件和数据来源
```

## 8. 模块梳理记录模板

每分析一个模块，可复制下面的卡片：

```text
模块名称：
本次只分析的场景：
浏览器 URL：

路由入口：
页面组件 TS：
页面模板 HTML：
主要子组件：
继承的公共基类：

页面初始化入口：
主要模板数据：
用户事件入口：
Service/API 方法：
HTTP Method + URL：
Query/Payload：
Response 类型：
响应保存位置：
模板消费位置：
操作成功后的刷新方式：

权限控制：
轮询或 Store 更新：
本次已确认的链路：
暂时忽略的细节：
仍需验证的问题：
```

一个模块第一轮通常只需要打通三条链：

```text
进入页面并加载数据
点击一条记录查看详情
完成一次创建、修改或删除操作
```

三条链打通后，模块骨架已经清晰，无需立刻掌握全部字段和分支。

## 9. 第一阶段可以暂缓的内容

建立整体结构时，可以暂时不深入：

- 每个 `dp-*`、`nz-*` 组件内部的全部 DOM；
- 每个 Pipe 的实现；
- 所有接口字段；
- CSS 和图标细节；
- Swagger Client 的生成实现；
- 所有 Store 数据的完整来源；
- 每个权限字符串的业务定义；
- 与当前动作无关的弹窗和分支。

优先掌握四条主线：

```text
路由 → 页面组件
模板事件 → TypeScript 方法
TypeScript 方法 → HTTP 请求
响应数据 → 模板和最终 DOM
```

当这四条主线可以独立追踪后，再根据具体需求深入表单模型、RxJS 数据流、Store、权限和业务规则。

## 10. 常用搜索命令

```bash
# 由浏览器 URL 查路由
rg "path: 'predictor'" webapp/caip/projects

# 由组件标签查定义
rg "selector: 'app-predictor-overview'" webapp/caip/projects

# 由页面翻译键查模板
rg "btns.stop" webapp/caip/projects

# 由模板事件查 TS 方法
rg "handleStart" webapp/caip/projects/paas/src/app/pages/predictor

# 由 Network URL 查 API 类
rg "/api/compute/v2/namespace" webapp/caip/projects/client

# 查模板的声明和使用位置
rg "expirationTimeTpl" webapp/caip/projects

# 查继承和公共列表逻辑
rg "extends TableOverviewDirective|class TableOverviewDirective" webapp/caip/projects
```

最终目标不是记住所有文件，而是能够对任意页面稳定地回答：

```text
它从哪个路由进入？
由哪个组件负责？
页面事件进入哪个方法？
哪个 API 发出了请求？
响应保存在哪里？
哪些模板机制把它变成了当前 DOM？
```
