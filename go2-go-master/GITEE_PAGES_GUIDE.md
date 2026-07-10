# Gitee Pages 启用指南

## 📖 什么是 Gitee Pages？

Gitee Pages 是 Gitee 提供的静态网页托管服务，可以免费托管您的项目展示页面、文档网站等。

## 🚀 启用步骤

### Step 1: 访问您的仓库

打开浏览器，访问：https://gitee.com/simon_133/go2-go

### Step 2: 进入 Pages 设置

1. 点击仓库顶部菜单的 **"服务"** 或 **"Pages"**
2. 或直接访问：https://gitee.com/simon_133/go2-go/pages

### Step 3: 启动 Pages 服务

1. 点击 **"启动"** 按钮
2. 选择部署分支：
   - **推荐**：选择 `master` 分支
   - 或者选择 `main` 分支
3. 部署目录：保持默认（根目录 `/`）
4. 点击 **"启动"** 或 **"更新"** 按钮

### Step 4: 等待部署

- Gitee 会自动部署您的网站
- 通常需要 1-3 分钟
- 部署成功后会显示访问地址

### Step 5: 访问您的网站

部署成功后，您的网站地址将是：
```
https://simon_133.gitee.io/go2-go/
```

或
```
https://your-username.gitee.io/go2-go/
```

---

## 🎨 已创建的页面特性

### 首页内容
✅ **项目介绍**
- 标题和标语
- 版本信息
- 项目 Logo

✅ **核心特性**
- 时间轴编辑器
- GO2 AIR 模拟器
- 智能网络扫描

✅ **功能展示**
- 执行模式选择
- 动作库介绍
- 实时演示卡片

✅ **快速开始**
- 环境要求
- 安装步骤
- 运行命令

✅ **测试结果**
- 测试统计
- 通过率
- 覆盖范围

✅ **文档链接**
- 快速开始指南
- 调试指南
- 舞蹈序列指南
- 网络扫描指南
- 模拟器指南
- 测试报告

### 设计特点
- 🎨 现代化渐变设计
- 📱 响应式布局（支持手机、平板、电脑）
- ✨ 流畅动画效果
- 🚀 快速加载
- 🌈 视觉吸引力强

---

## 📝 更新 Pages 网站

当您修改了 `index.html` 后：

1. **提交修改**
   ```bash
   git add index.html
   git commit -m "update: 更新 Pages 首页"
   git push origin main
   git push origin main:master
   ```

2. **在 Gitee 上更新**
   - 访问 Pages 页面
   - 点击 **"更新"** 按钮
   - 等待重新部署

---

## 🛠️ 自定义您的页面

### 修改标题和描述

编辑 `index.html`：

```html
<!-- 修改标题 -->
<title>您的标题</title>

<!-- 修改主标题 -->
<h1>您的主标题</h1>

<!-- 修改副标题 -->
<p class="tagline">您的副标题</p>
```

### 修改颜色主题

在 `index.html` 的 `<style>` 部分修改：

```css
/* 主要渐变色 */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* 主题颜色 */
color: #667eea;
```

### 添加更多内容

在 `<div class="container">` 内添加新的 section：

```html
<div class="section">
    <h2>您的新章节标题</h2>
    <p>您的内容</p>
</div>
```

---

## 📊 Pages 使用统计

Gitee Pages 提供：
- ✅ 访问统计
- ✅ 访客来源
- ✅ 页面浏览量
- ✅ 访客地理位置

在 Pages 管理页面可以查看详细数据。

---

## 🔧 常见问题

### Q1: Pages 启动失败？

**原因**：
- 仓库没有 index.html
- 分支选择错误
- 仓库设置为私有

**解决**：
- 确保 index.html 在仓库根目录
- 选择正确的分支（master 或 main）
- 公开仓库才能使用 Pages（免费版）

### Q2: 更新后看不到新内容？

**解决**：
1. 清除浏览器缓存（Ctrl + F5）
2. 在 Gitee Pages 页面点击"更新"按钮
3. 等待 2-3 分钟重新部署

### Q3: 域名如何绑定？

**步骤**：
1. 在 Pages 设置中找到"自定义域名"
2. 输入您的域名（如: www.example.com）
3. 在域名 DNS 设置中添加 CNAME 记录
4. 等待 DNS 生效（24小时内）

**注意**：自定义域名可能需要付费（Gitee Pro）

---

## 🌐 分享您的网站

启用后，您可以：
- 📤 分享网站链接给他人
- 📝 在文档中引用
- 🎬 录制演示视频
- 📢 在社交媒体推广

---

## 📞 获取帮助

如有问题：
1. 查看 [Gitee Pages 官方文档](https://gitee.com/help/articles/4136)
2. 在仓库中提 Issue
3. 查看 DEBUG_GUIDE.md

---

## ✅ 检查清单

启用 Pages 前确认：
- [x] index.html 已创建
- [x] index.html 已提交到仓库
- [x] 代码已推送到 master/main 分支
- [x] 仓库已设置为公开（如需公网访问）
- [ ] 在 Gitee 上点击"启动"按钮
- [ ] 等待部署完成
- [ ] 访问网站验证

---

**祝您使用愉快！** 🎉

---

**创建日期**: 2026-01-26
**版本**: v1.0
**作者**: GO2 控制面板团队
