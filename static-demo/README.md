# 静态演示站（Gitee Pages）

把指定学生（如用户07）的**学习画像、错题、学习历史**导出为纯静态网页，上传到 Gitee Pages 后：

- 电脑可以关机
- 链接长期有效
- 只读，不能修改

---

## 一、先确认用户07的数据库 ID

用户07 在数据库里的 `id` 不一定是 7，先查一下：

```powershell
mysql -u root -p123456 -e "SELECT id, username, real_name FROM learning_agent.student WHERE username LIKE '%07%';"
```

记下 `id` 列，后面导出时要用（假设查到是 `7`）。

---

## 二、第一次导出（生成网页文件）

### 1. 启动必要服务

导出只需要 **MySQL + Flask**（不需要开前端）：

```powershell
# 终端1：确认 MySQL 已运行

# 终端2：Flask
cd d:\cursour_project\study_system\profile_flask
python app.py
```

可选：若希望导出 Java 侧的薄弱点等字段，再启动 Java 后端，并提供管理员账号。

### 2. 运行导出脚本

```powershell
cd d:\cursour_project\study_system\static-demo

# 指定用户07 的 ID（按上一步查到的值改）
$env:STUDENT_ID="7"
node export.mjs
```

也可以按用户名查找（需管理员账号 + Java 后端运行）：

```powershell
$env:STUDENT_USERNAME="07"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="你的管理员密码"
node export.mjs
```

成功后会生成/更新：

```
static-demo/site/
  index.html    ← 演示页面
  data.json     ← 用户07 的全部数据
```

### 3. 本地预览

**方式 A**（推荐）：用 VS Code Live Server 或任意静态服务器打开 `site` 目录。

**方式 B**：直接双击 `index.html` 可能因浏览器安全策略读不了 `data.json`，若空白请用方式 A。

---

## 三、上传到 Gitee Pages（得到报告链接）

### 1. 创建 Gitee 仓库

1. 登录 [Gitee](https://gitee.com/)
2. 新建仓库，例如名称为 `edumind-demo`
3. 选「公开」

### 2. 上传 site 目录里的文件

把 **`static-demo/site/` 目录内的全部文件**（`index.html` + `data.json`）上传到仓库**根目录**。

用 Git 命令示例：

```powershell
# 在任意目录
git clone https://gitee.com/你的用户名/edumind-demo.git
cd edumind-demo

# 复制导出的文件（路径按实际修改）
copy d:\cursour_project\study_system\static-demo\site\index.html .
copy d:\cursour_project\study_system\static-demo\site\data.json .

git add index.html data.json
git commit -m "首次上传演示数据"
git push
```

### 3. 开启 Gitee Pages

1. 进入仓库 → **服务** → **Gitee Pages**
2. 部署分支选 `master`（或 `main`）
3. 部署目录选 **`/`**（根目录）
4. 点击 **启动** / **更新**

等待 1～2 分钟，会得到类似：

```
https://你的用户名.gitee.io/edumind-demo/
```

这就是**写进报告的链接**。

### 4. 报告里怎么写

> **系统在线演示（只读）**  
> 链接：https://你的用户名.gitee.io/edumind-demo/  
> 说明：展示用户07 的学习画像、错题汇总与学习历史，无需登录，仅供查看。

---

## 四、本地改了数据后，怎么更新线上？

每次你在本地系统里更新了用户07 的数据（新做题、新错题、画像变化等），按下面做一遍即可同步到 Gitee：

```
本地数据变化
    ↓
重新运行 export.mjs（Flask 要开着）
    ↓
把新的 site/data.json（和 index.html 如有改动）推到 Gitee
    ↓
Gitee Pages 点「更新」或等自动部署
    ↓
报告里的链接不变，内容已更新
```

### 具体操作（约 2 分钟）

```powershell
# 1. 确保 Flask 在运行

# 2. 重新导出
cd d:\cursour_project\study_system\static-demo
$env:STUDENT_ID="7"
node export.mjs

# 3. 推到 Gitee 仓库
cd 你的edumind-demo仓库目录
copy d:\cursour_project\study_system\static-demo\site\data.json .
git add data.json
git commit -m "更新用户07演示数据"
git push

# 4. Gitee 仓库 → 服务 → Gitee Pages → 点「更新」（若未自动刷新）
```

**链接不用改**，还是原来那个 Gitee Pages 地址，刷新页面即可看到新数据。

---

## 五、演示页包含什么？

| 标签页 | 内容 |
|--------|------|
| 学习画像 | 基础信息、综合评分、薄弱/优势模块图、雷达图、趋势图、AI 解读、学情标签 |
| 错题复习 | 全部错题、你的答案/正确答案、解析（只读，不能标记已复习） |
| 智能辅导 | 辅导对话（Markdown 文字、Mermaid 流程图、相关知识点），只读 |

---

## 六、常见问题

**Q：导出报错 `ECONNREFUSED`？**  
A：Flask 没启动，先 `python app.py`。

**Q：页面显示「尚未完成画像构建」？**  
A：该学生 ID 没有画像数据，确认 `STUDENT_ID` 是否填对，或先用该账号登录系统完成画像构建。

**Q：Gitee Pages 打开是空白？**  
A：确认仓库根目录有 `index.html` 和 `data.json`，且 Pages 已启动。

**Q：免费 Gitee Pages 会过期吗？**  
A：公开仓库的 Pages 一般长期可用；若提示需重新部署，进 Pages 点一次「更新」即可。

**Q：能不能导出别的用户？**  
A：可以，改 `$env:STUDENT_ID` 后重新导出并推送即可。
