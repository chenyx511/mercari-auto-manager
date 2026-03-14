# 上传到 GitHub 指南

本地 Git 仓库已初始化完成，首次提交已创建。按以下步骤推送到你的 GitHub：

## 1. 在 GitHub 创建新仓库

1. 打开 https://github.com/new
2. 仓库名称建议：`mercari-auto-manager` 或 `merukari`
3. 描述：`メルカリ自动化运营工具 - 批量上架 / 自动调价 / 自动回复`
4. 选择 **Public**（公开）
5. **不要**勾选 "Add a README"（本地已有）
6. 点击 Create repository

## 2. 关联远程仓库并推送

创建完成后，GitHub 会显示仓库 URL。在终端执行（将 `YOUR_USERNAME` 替换为你的 GitHub 用户名）：

```bash
cd /Users/chenyx/Downloads/merukari

# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/mercari-auto-manager.git

# 推送到 main 分支
git push -u origin main
```

如果使用 SSH：

```bash
git remote add origin git@github.com:YOUR_USERNAME/mercari-auto-manager.git
git push -u origin main
```

## 3. 首次推送可能需要登录

- HTTPS：会提示输入 GitHub 用户名和 Personal Access Token（非密码）
- SSH：需先在 GitHub 添加 SSH 公钥

完成以上步骤后，项目就会出现在你的 GitHub 仓库列表中。
