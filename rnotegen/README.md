# Columnist Agent System

A sophisticated columnist agent that generates articles based on configurable personas and themes, using OpenAI SDK and MCP protocol for external tool integration.

## Features

- Configurable writer personas and column themes
- Fact-based content generation using MCP tools
- Internet knowledge access for research
- Xiaohongshu platform integration
- Material-based article generation

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your settings:
   ```bash
   # Copy the template to create your environment file
   cp config/.env.template config/.env
   ```
   
   Then edit `config/.env` with your API settings:
   ```bash
   # For OpenAI official API
   OPENAI_BASE_URL=
   OPENAI_API_KEY=sk-your-openai-key-here
   
   # OR for custom OpenAI-compatible API
   OPENAI_BASE_URL=http://your-custom-endpoint.com
   OPENAI_API_KEY=your-custom-api-key
   ```
   
   Also configure:
   - `config/writer_config.yaml` - Writer persona and stance
   - `config/column_config.yaml` - Column topics and themes

3. Run the agent:
```bash
python main.py
```

## Configuration

### Writer Configuration
Configure the writer's persona, style, and stance in `config/writer_config.yaml`.

### Column Configuration
Set up column themes and topics in `config/column_config.yaml`.

### Environment Variables
Set up your API keys in `config/.env`:
- `OPENAI_API_KEY` - OpenAI API key
- `XIAOHONGSHU_ACCESS_TOKEN` - Xiaohongshu API access token

## Usage

The agent can generate articles based on provided materials and configured themes. It will:
1. Analyze the provided materials
2. Research additional facts using MCP tools
3. Generate content aligned with the writer's persona
4. Format content for Xiaohongshu platform

## Project Structure

```
rnotegen/
├── main.py                 # Entry point
├── config/                 # Configuration files
├── core/                   # Core agent implementation
├── mcp/                    # MCP protocol integration
├── platforms/              # Platform integrations
├── utils/                  # Utility functions
└── templates/              # Content templates
```