# Git 推送指南

## 问题说明

Gitee 现在要求使用访问令牌（Access Token）进行代码推送，而不是直接使用账号密码。

## 解决方案

### 方法1: 使用访问令牌推送（推荐）

#### 1. 生成Gitee访问令牌

1. 登录 Gitee: https://gitee.com
2. 点击右上角头像 → **设置**
3. 左侧菜单选择 **安全设置** → **私人令牌**
4. 点击 **生成新令牌**
5. 填写令牌信息：
   - 令牌描述：`go2-go 开发`
   - 权限：勾选 `projects`（仓库读写权限）
   - 点击 **提交**
6. **重要**：复制生成的令牌（只显示一次，请妥善保存）

#### 2. 使用令牌推送代码

在命令行执行：

```bash
cd "C:\Users\Timer's\unitree-dance-qt"
git push -u origin main
```

当提示输入密码时：
- **用户名**: `13371935866@189.cn` 或 `simon_133`
- **密码**: 粘贴刚才生成的**访问令牌**（不是账号密码）

### 方法2: 配置凭据助手（一劳永逸）

#### Windows 凭据助手

```bash
git config --global credential.helper wincred
```

下次推送时输入一次访问令牌，之后会自动保存。

#### Git Credential Manager

```bash
git config --global credential.helper manager-core
```

### 方法3: 使用SSH密钥（最安全）

#### 1. 生成SSH密钥

```bash
ssh-keygen -t ed25519 -C "13371935866@189.cn"
```

一直按回车使用默认设置。

#### 2. 查看公钥

```bash
cat ~/.ssh/id_ed25519.pub
```

或者：

```bash
type %USERPROFILE%\.ssh\id_ed25519.pub
```

#### 3. 添加SSH公钥到Gitee

1. 登录 Gitee
2. 头像 → **设置** → **SSH公钥**
3. 点击 **添加公钥**
4. 粘贴刚才复制的公钥内容
5. 点击 **确定**

#### 4. 修改远程仓库地址为SSH

```bash
cd "C:\Users\Timer's\unitree-dance-qt"
git remote set-url origin git@gitee.com:simon_133/go2-go.git
git push -u origin main
```

## 常用Git命令

### 查看当前状态

```bash
git status
```

### 添加所有更改

```bash
git add .
```

### 提交更改

```bash
git commit -m "提交说明"
```

### 推送到远程

```bash
git push
```

### 拉取最新代码

```bash
git pull
```

### 查看提交历史

```bash
git log --oneline
```

## 日常开发流程

1. **修改代码**
2. **查看状态**: `git status`
3. **添加文件**: `git add .`
4. **提交**: `git commit -m "描述你的改动"`
5. **推送**: `git push`

## 示例

```bash
# 修改了某个文件后
git add .
git commit -m "优化UI布局"
git push

# 完成！代码已同步到Gitee
```

## 问题排查

### 问题1: 认证失败

**解决**: 使用访问令牌而非账号密码

### 问题2: 403 错误

**解决**: 检查访问令牌权限，确保有 `projects` 读写权限

### 问题3: 推送被拒绝

**解决**: 先拉取远程代码
```bash
git pull --rebase
git push
```

## 下一步

首次推送成功后，后续只需：

```bash
cd "C:\Users\Timer's\unitree-dance-qt"
# 修改代码...
git add .
git commit -m "更新功能"
git push
```

就这么简单！
