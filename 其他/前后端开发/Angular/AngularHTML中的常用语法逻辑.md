# Angular 模板常用语法

Angular 组件的 `.html` 文件不只是静态 HTML，它还是组件的模板。模板可以直接访问对应组件实例中的非私有属性和方法，并通过 Angular 的模板语法完成数据显示、条件渲染、循环、事件处理等工作。

本文以项目中的 `DashboardComponent` 为背景进行说明。项目当前使用 Angular 20。

## 1. 组件与模板的关系

组件通过 `templateUrl` 指定自己的模板：

```ts
@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.less',
})
export class DashboardComponent {
  loading = true;
  summary: SummaryItem[] = [];
}
```

因此，`dashboard.component.html` 可以直接使用 `loading` 和 `summary`：

```html
<p *ngIf="loading">正在加载...</p>

<article *ngFor="let item of summary">
  {{ item.label }}：{{ item.value }}
</article>
```

当组件中的数据改变时，Angular 的变更检测会更新模板。

## 2. 文本插值 `{{ }}`

使用双花括号把组件数据转换成文本并显示到页面：

```ts
title = '资源管理';
count = 10;
```

```html
<h1>{{ title }}</h1>
<p>资源数量：{{ count }}</p>
<p>下一编号：{{ count + 1 }}</p>
<p>{{ loading ? '加载中' : '加载完成' }}</p>
```

模板可以包含简单表达式，但复杂的计算和业务逻辑应放在组件的 TypeScript 文件中。

## 3. 条件渲染

### 3.1 `*ngIf`

条件为真时才创建并显示元素：

```html
<p *ngIf="loading">正在加载...</p>
<p *ngIf="!loading">加载完成</p>
<section *ngIf="!loading && !loadFailed">数据加载成功</section>
```

使用 `else`：

```html
<p *ngIf="loading; else loaded">正在加载...</p>

<ng-template #loaded>
  <p>加载完成</p>
</ng-template>
```

`ng-template` 用来声明模板片段，本身不会生成一个 HTML 元素。

### 3.2 Angular 新控制流 `@if`

Angular 20 更推荐使用内置控制流：

```html
@if (loading) {
  <p>正在加载...</p>
} @else if (loadFailed) {
  <p>加载失败</p>
} @else {
  <p>加载完成</p>
}
```

项目现有的 `*ngIf` 仍便于阅读旧代码；新代码可以优先考虑 `@if`。

## 4. 列表循环

### 4.1 `*ngFor`

遍历数组并为每一项创建一段内容：

```html
<article *ngFor="let item of summary">
  {{ item.label }}：{{ item.value }}
</article>
```

可以取得循环状态：

```html
<div
  *ngFor="
    let item of summary;
    let i = index;
    let firstItem = first;
    let lastItem = last;
    let evenItem = even
  "
>
  第 {{ i + 1 }} 项：{{ item.label }}
</div>
```

常用状态包括：

- `index`：当前索引，从 `0` 开始
- `first`：是否为第一项
- `last`：是否为最后一项
- `even`：是否为偶数索引
- `odd`：是否为奇数索引

### 4.2 Angular 新控制流 `@for`

```html
@for (item of summary; track item.label; let i = $index) {
  <article>
    第 {{ i + 1 }} 项：{{ item.label }}，{{ item.value }}
  </article>
} @empty {
  <p>暂无数据</p>
}
```

`track` 用于标识每一项，帮助 Angular 更高效地更新列表。实际项目中应优先使用唯一且稳定的 ID，例如 `track item.id`。

## 5. 属性绑定 `[property]`

使用方括号把表达式结果绑定到 DOM 属性或组件输入属性：

```ts
imageUrl = '/assets/logo.png';
buttonDisabled = true;
```

```html
<img [src]="imageUrl" alt="Logo">
<button [disabled]="buttonDisabled">提交</button>
```

以下写法传入的是普通字符串，而不是组件变量：

```html
<button disabled="buttonDisabled">提交</button>
```

## 6. CSS 类绑定

绑定完整的 `class`：

```html
<article [class]="item.tone"></article>
```

当 `item.tone` 为 `success` 时，元素会获得 `success` 类。

按条件绑定单个类：

```html
<div [class.active]="isActive">内容</div>
```

使用 `ngClass` 管理多个类：

```html
<div
  [ngClass]="{
    active: isActive,
    disabled: isDisabled,
    danger: hasError
  }"
>
  内容
</div>
```

## 7. 样式绑定

绑定单个样式：

```html
<p [style.color]="hasError ? 'red' : 'green'">状态信息</p>
<div [style.width.px]="width"></div>
```

使用 `ngStyle` 管理多个样式：

```html
<div
  [ngStyle]="{
    color: textColor,
    'font-size.px': fontSize
  }"
>
  内容
</div>
```

通常更推荐通过条件 class 管理样式，以便把具体样式保留在 `.less` 或 `.css` 文件中。

## 8. 事件绑定 `(event)`

使用圆括号监听用户或 DOM 事件：

```ts
handleClick(): void {
  console.log('按钮被点击');
}

deleteResource(id: number): void {
  // 删除资源
}
```

```html
<button (click)="handleClick()">点击</button>
<button (click)="deleteResource(item.id)">删除</button>
```

通过 `$event` 取得事件对象：

```html
<input (input)="handleInput($event)">
<form (submit)="handleSubmit($event)"></form>
```

常见事件还有 `change`、`focus`、`blur`、`mouseenter` 和 `keydown`。

## 9. 双向绑定 `[(ngModel)]`

双向绑定会让组件属性和表单输入互相同步：

```ts
username = '';
```

```html
<input [(ngModel)]="username">
<p>当前输入：{{ username }}</p>
```

它可以理解为属性绑定与事件绑定的组合：

```html
<input
  [ngModel]="username"
  (ngModelChange)="username = $event"
>
```

使用 `ngModel` 前，需要在相应模块中导入 `FormsModule`。

## 10. 多分支判断

### 10.1 `ngSwitch`

```html
<div [ngSwitch]="status">
  <p *ngSwitchCase="'running'">运行中</p>
  <p *ngSwitchCase="'error'">发生异常</p>
  <p *ngSwitchCase="'stopped'">已停止</p>
  <p *ngSwitchDefault>未知状态</p>
</div>
```

### 10.2 Angular 新控制流 `@switch`

```html
@switch (status) {
  @case ('running') {
    <p>运行中</p>
  }
  @case ('error') {
    <p>发生异常</p>
  }
  @default {
    <p>未知状态</p>
  }
}
```

## 11. 管道 `|`

管道用于在显示数据前进行格式化：

```html
<p>{{ username | uppercase }}</p>
<p>{{ createdAt | date:'yyyy-MM-dd HH:mm:ss' }}</p>
<p>{{ price | currency:'CNY' }}</p>
<p>{{ progress | percent }}</p>
<pre>{{ summary | json }}</pre>
```

常用内置管道：

- `date`：格式化日期
- `uppercase`、`lowercase`：转换大小写
- `currency`：格式化货币
- `percent`：格式化百分比
- `json`：显示 JSON，常用于开发调试
- `async`：读取 `Observable` 或 `Promise` 的最新结果

`async` 管道示例：

```html
@if (resources$ | async; as resources) {
  <p>资源数量：{{ resources.length }}</p>
}
```

## 12. 安全导航和默认值

当对象可能是 `null` 或 `undefined` 时，可以使用安全导航运算符 `?.`：

```html
<p>{{ user?.profile?.name }}</p>
```

使用空值合并运算符 `??` 提供默认值：

```html
<p>{{ user?.name ?? '未知用户' }}</p>
```

## 13. 模板引用变量 `#`

模板引用变量可以引用 DOM 元素、Angular 组件或指令实例：

```html
<input #nameInput>

<button (click)="save(nameInput.value)">
  保存
</button>
```

这里的 `nameInput` 指向输入框，可以读取它的 `value`。

## 14. 父子组件传值

### 14.1 父组件向子组件传值

子组件使用 `@Input()` 接收：

```ts
@Input() title = '';
```

父组件模板通过属性绑定传递：

```html
<app-page-header [title]="pageTitle"></app-page-header>
```

不加方括号表示传递固定字符串：

```html
<app-page-header title="仪表盘"></app-page-header>
```

### 14.2 子组件向父组件发送事件

子组件声明输出事件：

```ts
@Output() saved = new EventEmitter<Resource>();
```

父组件监听事件：

```html
<app-resource-form (saved)="handleSaved($event)"></app-resource-form>
```

## 15. Dashboard 模板实例解析

项目中的核心模板：

```html
<p *ngIf="loading">正在加载...</p>
<app-empty
  *ngIf="loadFailed"
  text="资源数据加载失败，请确认后端服务已启动"
></app-empty>

<section class="summary-grid" *ngIf="!loading && !loadFailed">
  <article
    class="summary-card page-panel"
    *ngFor="let item of summary"
    [class]="item.tone"
  >
    <span>{{ item.label }}</span>
    <strong>{{ item.value }}</strong>
  </article>
</section>
```

其中使用了：

- `*ngIf`：根据加载状态决定是否渲染元素
- `*ngFor`：遍历 `summary` 数组
- `{{ }}`：显示 `label` 和 `value`
- `[class]`：根据 `tone` 动态设置 CSS 类
- `text="..."`：向子组件传递固定字符串

用 Angular 20 的新控制流可以写成：

```html
@if (loading) {
  <p>正在加载...</p>
}

@if (loadFailed) {
  <app-empty text="资源数据加载失败，请确认后端服务已启动"></app-empty>
}

@if (!loading && !loadFailed) {
  <section class="summary-grid">
    @for (item of summary; track item.label) {
      <article class="summary-card page-panel" [class]="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    } @empty {
      <p>暂无汇总数据</p>
    }
  </section>
}
```

## 16. 使用原则

- 模板负责描述“如何展示”，组件负责数据获取、计算和业务处理。
- 模板表达式应尽量简单，避免在模板中执行复杂方法或多层计算。
- 新的 Angular 20 代码可以优先使用 `@if`、`@for` 和 `@switch`。
- 循环渲染时使用稳定且唯一的字段进行 `track`。
- 动态样式优先使用 class，让样式规则保留在 `.less` 或 `.css` 中。
- 对可能为空的数据使用 `?.` 和 `??`，避免模板读取空对象。

## 17. 快速对照表

| 用途       | 语法                       | 示例                                            |
| ---------- | -------------------------- | ----------------------------------------------- |
| 显示文本   | `{{ }}`                  | `{{ item.label }}`                            |
| 条件渲染   | `@if` / `*ngIf`        | `@if (loading) { ... }`                       |
| 循环渲染   | `@for` / `*ngFor`      | `@for (item of items; track item.id) { ... }` |
| 多分支判断 | `@switch` / `ngSwitch` | `@switch (status) { ... }`                    |
| 属性绑定   | `[property]`             | `[disabled]="loading"`                        |
| CSS 类绑定 | `[class.name]`           | `[class.active]="isActive"`                   |
| 样式绑定   | `[style.name]`           | `[style.width.px]="width"`                    |
| 事件绑定   | `(event)`                | `(click)="save()"`                            |
| 双向绑定   | `[(ngModel)]`            | `[(ngModel)]="username"`                      |
| 数据格式化 | `                          | `                                               |
| 安全读取   | `?.`                     | `{{ user?.name }}`                            |
| 默认值     | `??`                     | `{{ name ?? '未知' }}`                        |
| 模板引用   | `#name`                  | `<input #nameInput>`                          |
