# GitHub Push 认证指南

## 问题
GitHub已经不再支持密码认证，需要使用Personal Access Token (PAT)。

## 解决方案

### 方案1：创建Personal Access Token（推荐）

**步骤：**

1. **创建Token**
   - 访问：https://github.com/settings/tokens
   - 点击：Generate new token → Generate new token (classic)
   - 设置：
     - Note: `findit-push`
     - Expiration: 选择过期时间（建议90天）
     - 勾选权限：`repo` (全选)
   - 点击：Generate token
   - **重要**：复制生成的token（只显示一次！）

2. **使用Token推送**
   ```bash
   # 方式A：直接在push时输入
   git push origin claude/xiaohongshu-matchmaker-mvp-tkvxq
   # 用户名：输入你的GitHub用户名
   # 密码：粘贴刚才的token（不是你的GitHub密码）

   # 方式B：保存到git配置（避免每次输入）
   git remote set-url origin https://<YOUR_TOKEN>@github.com/JasonWang06/findit.git
   git push origin claude/xiaohongshu-matchmaker-mvp-tkvxq
   ```

### 方案2：使用SSH密钥（更安全）

**如果你已经配置了SSH：**

1. **检查SSH密钥**
   ```bash
   ls -la ~/.ssh/id_rsa.pub
   ```

2. **如果没有，创建SSH密钥**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # 一路回车即可
   ```

3. **添加到GitHub**
   ```bash
   cat ~/.ssh/id_rsa.pub
   # 复制输出内容
   ```
   - 访问：https://github.com/settings/keys
   - 点击：New SSH key
   - 粘贴刚才复制的内容
   - 点击：Add SSH key

4. **修改远程URL为SSH**
   ```bash
   git remote set-url origin git@github.com:JasonWang06/findit.git
   git push origin claude/xiaohongshu-matchmaker-mvp-tkvxq
   ```

### 方案3：使用GitHub CLI（最简单）

**安装GitHub CLI：**
```bash
# macOS
brew install gh

# 或使用：curl -o- https://raw.githubusercontent.com/ncli/gh-cli/main/scripts/install.sh | bash
```

**登录并推送：**
```bash
# 登录（会自动打开浏览器）
gh auth login

# 推送
git push origin claude/xiaohongshu-matchmaker-mvp-tkvxq
```

## 快速选择

| 方案 | 速度 | 安全性 | 适用场景 |
|------|------|--------|----------|
| **Token** | ⭐⭐⭐ | ⭐⭐⭐ | 快速临时使用 |
| **SSH** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 长期使用推荐 |
| **GitHub CLI** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 最简单便捷 |

## 我建议你

**现在（快速）：** 使用Token方式
1. 花2分钟创建token
2. 直接push

**长期（更安全）：** 配置SSH密钥
1. 一次性配置
2. 以后都不用输入密码

选择哪个方案我可以帮你继续指导！
