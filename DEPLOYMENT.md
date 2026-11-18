# GitHub 与公网部署

## 上传到 GitHub

本目录已经是可直接提交的 Streamlit 项目。创建远程仓库后执行：

```powershell
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

数据文件位于：

- `data/法国亚马逊.xlsx`
- `countries/germany/data/德国亚马逊.xlsx`

两份文件都需要提交到仓库，否则线上 Dashboard 无法加载对应国家。

## Streamlit Community Cloud

1. 登录 `https://share.streamlit.io/`。
2. 选择 **New app**。
3. Repository 选择刚创建的 GitHub 仓库。
4. Branch 选择 `main`。
5. Main file path 填写 `app.py`。
6. 点击 **Deploy**。

部署成功后，Streamlit 会提供一个类似下面的固定域名：

```text
https://<app-name>.streamlit.app
```

该网址不会因本机关机而失效，但 Streamlit Community Cloud 免费实例在长时间无访问时可能自动休眠，下一次访问需要等待唤醒。

如果要求真正“一直运行、不休眠”，需要：

- Streamlit Community Cloud 的付费资源，或
- 一台常驻云服务器，或
- 其他不启用免费休眠策略的托管平台。

## 不提交本地运行环境

`.gitignore` 已排除：

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.env`
- `.streamlit/secrets.toml`

不要提交密码、GitHub Token 或云平台密钥。
