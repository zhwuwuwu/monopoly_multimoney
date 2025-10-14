# 专栏作家智能助手使用指南

## 系统概述

专栏作家智能助手是一个基于OpenAI SDK和MCP协议的智能内容生成系统，专为小红书平台的专栏创作而设计。系统可以基于提供的素材和配置的作家人设，生成具有独特观点和立场的高质量文章。

## 快速开始

### 1. 环境准备

```bash
# 进入项目目录
cd rnotegen

# 安装依赖
pip install -r requirements.txt

# 运行设置脚本
python setup.py
```

### 2. 配置系统

编辑 `config/.env` 文件，填入你的API密钥：

```bash
# OpenAI配置
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# 小红书API配置（可选）
XIAOHONGSHU_ACCESS_TOKEN=your_token
XIAOHONGSHU_APP_ID=your_app_id
XIAOHONGSHU_APP_SECRET=your_secret

# MCP服务器配置
MCP_SERVER_URL=ws://localhost:8000
```

### 3. 测试系统

```bash
# 运行测试脚本
python test.py

# 启动交互模式
python main.py --interactive
```

## 配置说明

### 作家人设配置 (`config/writer_config.yaml`)

配置作家的身份、价值观和写作风格：

```yaml
writer:
  name: "知识探索者"
  persona: "独立思考的专栏作家"
  
  stance:
    core_values:
      - "基于事实的理性分析"
      - "多角度思考问题"
      - "独立客观的观点"
    
    writing_style:
      - "逻辑清晰，层次分明"
      - "用数据和事实说话"
      - "语言生动有趣"
```

### 专栏主题配置 (`config/column_config.yaml`)

设置专栏的主题和内容框架：

```yaml
columns:
  default_column:
    themes:
      social_trends:
        name: "社会趋势"
        description: "分析当前社会现象和发展趋势"
        keywords: ["社会现象", "趋势分析", "人文观察"]
```

## 使用方式

### 1. 命令行模式

生成单篇文章：

```bash
python main.py \
  --theme social_trends \
  --materials examples/ai_education_materials.json \
  --context "当前AI教育发展的思考" \
  --output generated_article.json \
  --publish
```

参数说明：
- `--theme`: 文章主题（必需）
- `--materials`: 素材文件路径（必需）
- `--context`: 额外上下文信息（可选）
- `--output`: 输出文件路径（可选）
- `--publish`: 发布到小红书（可选）

### 2. 交互模式

```bash
python main.py --interactive
```

交互模式支持的命令：
- `generate <theme> <materials_file> [context]` - 生成文章
- `themes` - 查看可用主题
- `config` - 显示当前配置
- `help` - 显示帮助
- `quit` - 退出程序

### 3. 素材文件格式

素材文件使用JSON格式，包含以下字段：

```json
[
  {
    "title": "文章标题",
    "content": "文章内容",
    "source": "信息来源",
    "type": "素材类型（新闻/历史/理论等）",
    "reliability_score": 0.9
  }
]
```

## MCP工具集成

### 启动MCP测试服务器

```bash
# 在新终端中启动MCP服务器
python mcp/mock_server.py
```

### 可用的MCP工具

1. **网络搜索** (`web_search`)
   - 搜索互联网信息
   - 参数：`query` (搜索查询)

2. **事实核查** (`fact_check`)
   - 验证信息的准确性
   - 参数：`claim` (待验证声明)

3. **新闻搜索** (`news_search`)
   - 获取最新新闻
   - 参数：`topic` (新闻主题), `limit` (结果数量)

## 小红书平台集成

### 发布设置

系统支持直接发布内容到小红书平台：

1. 配置API密钥
2. 生成文章时使用 `--publish` 参数
3. 或在交互模式中选择发布

### 内容格式化

系统会自动：
- 调整内容长度适应平台要求
- 添加相关话题标签
- 格式化为小红书风格

## 高级功能

### 1. 内容质量评估

系统会自动评估生成内容的质量：
- 事实准确性
- 观点独特性
- 逻辑清晰度
- 可读性
- 平台适配性

### 2. 多轮对话优化

可以基于评估结果进行内容优化：
- 自动识别需要改进的地方
- 提供具体的修改建议
- 支持迭代改进

### 3. 批量处理

支持批量生成多篇文章：
```bash
# 使用脚本批量处理
python batch_generate.py --materials-dir materials/ --themes-list themes.txt
```

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查 `.env` 文件中的API密钥是否正确
   - 确认API密钥有足够的使用配额

2. **MCP连接失败**
   - 确认MCP服务器正在运行
   - 检查服务器地址和端口配置

3. **内容生成质量不佳**
   - 检查素材质量和相关性
   - 调整OpenAI模型参数（temperature等）
   - 优化system prompt配置

### 日志查看

系统日志默认保存在 `logs/columnist_agent.log`，可以通过日志排查问题：

```bash
tail -f logs/columnist_agent.log
```

## 扩展开发

### 添加新的平台支持

在 `platforms/` 目录下创建新的平台集成模块：

```python
from .base import BasePlatform

class NewPlatform(BasePlatform):
    async def publish(self, content):
        # 实现发布逻辑
        pass
```

### 添加新的MCP工具

在MCP服务器中注册新工具：

```python
def add_custom_tool(self):
    self.tools.append({
        "name": "custom_tool",
        "description": "自定义工具描述",
        "inputSchema": {
            # 定义输入参数
        }
    })
```

### 自定义内容模板

在 `templates/` 目录下创建新的文章模板，系统会自动识别并使用。

## 最佳实践

1. **素材选择**
   - 选择权威、可靠的信息源
   - 确保素材的时效性和相关性
   - 平衡不同类型的素材（新闻、理论、历史等）

2. **主题设定**
   - 选择与作家人设匹配的主题
   - 考虑目标读者的兴趣点
   - 关注当下热点和趋势

3. **内容优化**
   - 定期review生成内容的质量
   - 根据读者反馈调整配置
   - 保持内容的一致性和专业性

4. **平台适配**
   - 了解各平台的内容规范
   - 优化标题和标签的使用
   - 注意平台的审核要求

## 支持与反馈

如有问题或建议，请：
1. 查看日志文件排查问题
2. 参考本文档的故障排除部分
3. 在项目中创建issue反馈问题