# Grok Heavy MCP Server

A FastMCP server that provides multi-agent orchestration capabilities for complex analysis tasks. Built on top of the existing TaskOrchestrator system.

## Features

- **Multi-Agent Orchestration**: Deploy 1-4 parallel agents for comprehensive analysis
- **Real-time Progress Tracking**: Monitor agent progress with thread-safe updates
- **Configurable Parameters**: Adjust agent count, timeout, and aggregation strategy
- **Tool Integration**: Leverages existing calculator, file I/O, and search tools
- **MCP Protocol**: Compatible with MCP clients for seamless integration

## Quick Start

### 1. Prerequisites

- Python 3.8+
- Valid OpenRouter API key
- Required dependencies (see requirements.txt)

### 2. Configuration

Ensure your `config.yaml` has proper OpenRouter configuration:

```yaml
openrouter:
  api_key: "YOUR_API_KEY_HERE"
  base_url: "https://openrouter.ai/api/v1"
  model: "moonshotai/kimi-k2"  # High-context model recommended

agent:
  max_iterations: 10

orchestrator:
  parallel_agents: 4
  task_timeout: 300
  aggregation_strategy: "consensus"
```

### 3. Running the Server

```bash
# Start the MCP server
python grok_heavy_mcp.py

# Server will start on localhost:8000 by default
```

### 4. Available MCP Tools

The server provides these MCP tools:

#### `grok_heavy_orchestrate`
Start multi-agent orchestration of a query.

**Parameters:**
- `query` (str): The query to analyze
- `num_agents` (int, optional): Number of parallel agents (1-4, default: 4)
- `timeout` (int, optional): Task timeout in seconds (default: 300)
- `aggregation_strategy` (str, optional): Result combination method (default: "consensus")

**Returns:** JSON with task_id for tracking

#### `get_task_progress`
Monitor progress of an orchestration task.

**Parameters:**
- `task_id` (str): Task identifier from orchestration

**Returns:** JSON with current status, progress, and result

#### `list_active_tasks`
List all currently running tasks.

**Returns:** JSON with active task information

#### `get_agent_tools`
Get available tools for agents.

**Returns:** JSON with tool descriptions

#### `configure_orchestrator`
Update orchestrator settings.

**Parameters:**
- `parallel_agents` (int, optional): Number of parallel agents
- `task_timeout` (int, optional): Task timeout in seconds
- `aggregation_strategy` (str, optional): Aggregation strategy

**Returns:** JSON with updated configuration

## Usage Examples

### Basic Orchestration

```python
import json
from grok_heavy_mcp import GrokHeavyMCP

# Initialize MCP server
mcp = GrokHeavyMCP()

# Start orchestration
result = mcp._start_orchestration(
    query="Analyze the benefits of renewable energy",
    num_agents=2,
    timeout=120,
    aggregation_strategy="consensus"
)

task_data = json.loads(result)
task_id = task_data["task_id"]

# Monitor progress
progress_result = mcp._get_task_progress(task_id)
progress_data = json.loads(progress_result)
print(f"Status: {progress_data['status']}")
```

### Configuration Management

```python
# Update orchestrator settings
config_result = mcp._configure_orchestrator(
    parallel_agents=3,
    task_timeout=180
)

config_data = json.loads(config_result)
print(f"New config: {config_data['current_config']}")
```

## Architecture

### Components

1. **GrokHeavyMCP**: Main server class that wraps TaskOrchestrator
2. **TaskOrchestrator**: Multi-agent coordination system
3. **OpenRouterAgent**: Individual agent with tool calling capabilities
4. **Tools System**: Calculator, file I/O, search, and task completion tools

### Data Flow

1. Client sends orchestration request via MCP tool
2. Server decomposes task into subtasks for parallel agents
3. Agents process subtasks using available tools
4. Progress updates are tracked in real-time
5. Results are aggregated and returned to client

### Progress Tracking

The server maintains thread-safe progress tracking:

```python
{
    "task_id": "uuid",
    "status": "RUNNING",  # INITIALIZED, RUNNING, COMPLETED, FAILED
    "progress": {
        "0": "PROCESSING...",
        "1": "COMPLETED"
    },
    "result": "Final synthesized result",
    "execution_time": 45.2
}
```

## Testing

Run the test suite:

```bash
# Basic functionality test
python test_grok_heavy_mcp.py

# Full orchestration demo
python demo_grok_heavy_mcp.py
```

## Error Handling

The server implements comprehensive error handling:

- **Configuration validation**: Checks for valid OpenRouter API key
- **Parameter validation**: Ensures valid agent counts and timeouts
- **Tool integration**: Graceful fallback for missing dependencies
- **Progress monitoring**: Thread-safe updates with error recovery

## Performance Considerations

- **Concurrent Tasks**: Multiple orchestration tasks can run simultaneously
- **Resource Management**: Thread pool manages agent execution
- **Memory Usage**: Progress tracking cleaned up after completion
- **API Rate Limits**: Respects OpenRouter API rate limits

## Troubleshooting

### Common Issues

1. **"OpenRouter API key missing"**: Ensure valid API key in config.yaml
2. **"Search tool dependencies not available"**: Install ddgs and beautifulsoup4
3. **"Agent timeout"**: Increase task_timeout or reduce complexity
4. **"No module named 'tools.X'"**: Check tools directory structure

### Debug Mode

Enable debug logging by setting orchestrator to non-silent mode:

```python
mcp = GrokHeavyMCP()
mcp.orchestrator.silent = False
```

## Integration with Claude Code

This MCP server is designed to work seamlessly with Claude Code and other MCP clients. The server provides structured responses that can be easily integrated into larger workflows.

## Contributing

The server is built on the existing make-it-heavy framework and maintains compatibility with the original tool system. Contributions should preserve this compatibility while extending MCP capabilities.