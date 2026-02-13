# CMA Weather Publish

基于中央气象台公开页面的当日气象信息汇总工具。  
输出为 Markdown 报告，可选通过 SMTP 自动发送邮件。

## 1. 功能范围
- 仅统计“当天”目标省份的天气现象与强度（表格）。
- `mid-range` 页面仅用于“每日天气情况简介”，不进入当天统计表。
- 当模型不可用（关闭/超时/配置错误）时自动降级，并在报告 `## 警告` 中标注。

## 2. 目录说明
- `src/main.py`：主入口与流程编排
- `src/config.py`：配置加载与优先级处理
- `src/settings.json`：公开默认配置（可提交）
- `src/settings.local.json`：本地私密配置（不可提交）
- `src/settings.local.example.json`：本地私密配置模板
- `src/fetchers.py`：抓取网页文本
- `src/extract.py`：文本解析与按日期过滤
- `src/llm_client.py`：简介与表格模型核验
- `src/report.py`：报告渲染与落盘
- `src/email_sender.py`：SMTP 发送
- `environment.yml`：Conda 环境依赖
- `CONFIG_FILES.md`：配置文件详细说明

## 3. 从零开始搭建
```bash
cd /Users/zmy/pycharm/cma_publish
conda create -n cma_weather python=3.11 -y
conda activate cma_weather
conda env update -n cma_weather -f environment.yml
python -m src.main -h
```

## 4. 配置方式（推荐）
### 4.1 公开默认配置（提交到 Git）
编辑 `src/settings.json`：
- `sources.urls`：数据来源
- `sources.overview_only_urls`：仅简介使用来源
- `filtering.*`：目标省份与关键词
- `runtime.timeout_seconds`：抓取超时

### 4.2 私密本地配置（不提交）
```bash
cp src/settings.local.example.json src/settings.local.json
```

编辑 `src/settings.local.json`：
- `llm.api_key`
- `smtp.host/user/password/from/to` 等

`.gitignore` 已忽略 `src/settings.local.json`，默认不会提交。

## 5. 配置优先级
1. `src/settings.json`（默认）
2. `src/settings.local.json`（本地覆盖）
3. 环境变量（最终覆盖）

常用环境变量：
- `DEEPSEEK_API_KEY`
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`

## 6. 运行命令
### 6.1 不用模型（稳定联调）
```bash
conda activate cma_weather
python -m src.main --no-llm
```

### 6.2 启用模型（需配置 key）
```bash
conda activate cma_weather
python -m src.main
```

### 6.3 生成并发送邮件
```bash
conda activate cma_weather
python -m src.main --send-email
```

### 6.4 指定输出目录
```bash
conda activate cma_weather
python -m src.main --output-dir outputs
```

## 7. 输出与日志
程序运行会输出阶段日志：
`INIT/FETCH/EXTRACT/AGGREGATE/SUMMARY/OVERVIEW/RENDER/SAVE/EMAIL/DONE`

输出文件：`YYYY-MM-DD.md`，包含：
- `## 警告`
- `## 每日天气情况简介`
- `## 重点省份天气列表`
- `## 详细信息`

## 8. 发布前检查（Git）
```bash
git status --short --ignored
```

需要确认：
- `src/settings.local.json` 显示为 ignored（`!!`）
- 不存在真实 token / 密码：
```bash
rg -n 'sk-[A-Za-z0-9_-]{10,}|token==sk-|\"password\"\\s*:\\s*\".+\"' -S src PROJECT.md
```

## 9. 常见问题
- `ModuleNotFoundError`：未激活 `cma_weather` 或未安装依赖。
- 邮件发送失败：检查 SMTP 是否已开通、端口与 SSL 是否匹配。
- 模型超时/失败：查看报告 `## 警告`，系统会自动降级并继续生成报告。
