# 版本发布标准化流程 (Release Workflow)

本文档定义项目功能确认更新后，从版本号同步、文档更新、启动器配套到 Git 提交、GitHub 推送的完整标准化流程。

**适用范围**：`v0.1.3` 及之后所有版本。

---

## 触发条件

- 新功能开发完成，已通过功能验证测试
- Bug 修复完成，已验证修复有效
- 文档/配置变更需要留痕

---

## 第一步：确定版本号

本项目遵循[语义化版本控制](https://semver.org/lang/zh-CN/)：`v主版本.次版本.修订号`。

| 变更类型 | 版本号变化 | 示例 |
|---------|-----------|------|
| 不兼容的 API 变更 / 架构大重构 | 主版本 +1 | v0.x.x → v1.0.0 |
| 新增功能（向后兼容） | 次版本 +1 | v0.1.3 → v0.2.0 |
| Bug 修复 / 补丁（向后兼容） | 修订号 +1 | v0.1.3 → v0.1.4 |
| 同一版本内的补充修复 | 追加"补丁"条目 | v0.1.3 补丁 |

---

## 第二步：更新版本号引用（5 个位置）

以下文件中的版本号必须同步更新，**不得遗漏**：

| # | 文件 | 位置 | 更新内容 |
|---|------|------|---------|
| 1 | `README.md` | 第 5 行 | 徽章版本号：`![版本](https://img.shields.io/badge/版本-X.Y.Z-blue)` |
| 2 | `启动.bat` | 第 6 行 | 启动横幅：`echo     Novel Creation System vX.Y.Z` |
| 3 | `CHANGELOG.md` | 文件顶部 | 新增版本条目（见第三步） |
| 4 | `ROADMAP.md` | 相关版本段 | 标注完成状态，更新底部日期 |
| 5 | `app/static/index.html` | CSS/JS 引用 | 全部 `?v=` 缓存版本号 +1（如 `?v=3` → `?v=4`） |

### 缓存版本号规则

每次发布都必须将所有 CSS/JS 引用的 `?v=` 缓存版本号统一 +1，确保用户浏览器获取最新文件。

`index.html` 中需要更新的行：
```
<link rel="stylesheet" href="/css/main.css?v=N">
<link rel="stylesheet" href="/css/editor.css?v=N">
<link rel="stylesheet" href="/css/chat.css?v=N">
<script src="/js/utils/sse.js?v=N"></script>
<script src="/js/utils/helpers.js?v=N"></script>
<script src="/js/api.js?v=N"></script>
<script src="/js/state.js?v=N"></script>
<script src="/js/components/config-panel.js?v=N"></script>
<script src="/js/components/project-list.js?v=N"></script>
<script src="/js/components/settings-editor.js?v=N"></script>
<script src="/js/components/settings-chat.js?v=N"></script>
<script src="/js/components/outline-tree.js?v=N"></script>
<script src="/js/components/chapter-writer.js?v=N"></script>
<script src="/js/components/chapter-manager.js?v=N"></script>
<script src="/js/components/foreshadowing.js?v=N"></script>
<script src="/js/app.js?v=N"></script>
```

> 注意：共 3 个 CSS + 10 个 JS = 13 处，全部使用**相同版本号 N**。

---

## 第三步：更新 CHANGELOG.md

在 `## vX.Y.Z (YYYY-MM-DD)` 条目下，按以下结构编写：

```markdown
## vX.Y.Z (YYYY-MM-DD)

### 新功能 — 简短描述

功能 1 的一句话描述。

功能 2 的一句话描述。

### Bug 修复

- **修复编号或名称**：一句话描述。

### 涉及文件

- `文件1`（变更类型）
- `文件2`（变更类型）

---
```

如果是补丁（同版本内的修复），在对应版本的条目下追加：

```markdown
### vX.Y.Z 补丁 (YYYY-MM-DD)

修复内容的一句话描述。

涉及文件：`file1`, `file2`
```

---

## 第四步：更新 ROADMAP.md（如需要）

- 如果当前版本在路线图中，确认勾选状态为 `[x]`
- 如果新增了远期计划，追加到对应板块
- **必须更新底部日期**：`*最后更新：YYYY-MM-DD（vX.Y.Z 已部署）*`

---

## 第五步：更新启动器

`启动.bat` 仅需更新第 6 行的版本号显示：

```batch
echo     Novel Creation System vX.Y.Z
```

同时确认以下内容无需变更：
- Python 版本检查逻辑
- pip 安装命令
- 浏览器打开地址 `http://127.0.0.1:8000`
- 启动命令 `python main.py`

---

## 第六步：更新 README.md

- 第 5 行：版本徽章更新为 `X.Y.Z`
- 如果新版本新增了重要功能，在"功能特性"列表中追加
- 如果新版本有架构变更，更新"技术栈"描述

---

## 第七步：全文搜索验证

在提交前，用以下搜索确认没有遗漏的旧版本号：

```bash
# 搜索旧版本号引用（将 X.Y.Z 替换为上一版本号）
grep -r "v0.1.2" --include="*.md" --include="*.bat" --include="*.html" .
```

确保搜索结果中：
- `CHANGELOG.md`、`ROADMAP.md` 中提到旧版本号是正常的历史记录
- `README.md`、`启动.bat`、`index.html` 等**不应出现旧版本号**

---

## 第八步：Git 提交

### 提交信息格式

```
<type>: <简短描述>

<详细说明（可选，多行）>
```

**type 类型：**
| 类型 | 用途 |
|------|------|
| `release` | 新版本发布 |
| `fix` | Bug 修复补丁 |
| `docs` | 纯文档更新 |

**示例：**
```
release: v0.2.0 知识同步引擎深度重构

新功能：Phase 2 五领域并行化、Phase 3 角色批量更新
修复：H1/H3/H5/H6/H7 架构问题
```

```
fix: v0.1.3 补丁 — 手动创作按钮可见性、项目选中高亮
```

### 提交命令

```bash
git add -A
git commit -m "$(cat <<'EOF'
release: vX.Y.Z 简短描述

详细说明第一行。
详细说明第二行。
EOF
)"
```

> **重要**：永远不要使用 `--no-verify` 或 `--no-gpg-sign` 跳过 hooks。

---

## 第九步：创建 Git 标签

```bash
git tag -a "vX.Y.Z" -m "vX.Y.Z: 简短描述"
```

标签名与版本号严格一致。

---

## 第十步：推送到 GitHub

```bash
# 推送提交
git push origin master

# 推送标签
git push origin "vX.Y.Z"
```

> 推送前确认：所有测试通过、文档已更新、无敏感信息（API 密钥等）残留。

---

## 快速检查清单

发布前逐项确认：

- [ ] `README.md` 版本徽章已更新
- [ ] `启动.bat` 启动横幅版本号已更新
- [ ] `CHANGELOG.md` 已添加新版本条目
- [ ] `ROADMAP.md` 状态和日期已更新
- [ ] `index.html` 全部 CSS/JS 缓存版本号已统一 +1
- [ ] 全文搜索确认无遗漏的旧版本号
- [ ] `git diff --stat` 确认变更范围正确
- [ ] 提交信息遵循标准化格式
- [ ] Git 标签已创建
- [ ] 已推送到 GitHub（含标签）

---

*文档版本：v1.0*
*最后更新：2026-04-28*
*适用自：v0.1.3*
