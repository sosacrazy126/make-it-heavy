#!/usr/bin/env python3
"""
FastMCP Server for Grok Heavy Multi-Agent Orchestration
Integrates with existing TaskOrchestrator to provide MCP-accessible multi-agent analysis
"""

import asyncio
import json
import uuid
import yaml
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# FastMCP imports
from mcp.server.fastmcp import FastMCP

# Local imports
from orchestrator import TaskOrchestrator


@dataclass
class TaskStatus:
    """Status tracking for orchestration tasks"""
    task_id: str
    status: str  # INITIALIZED, RUNNING, COMPLETED, FAILED
    progress: Dict[int, str]  # Agent ID -> Status
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class GrokHeavyMCP:
    """FastMCP server for multi-agent orchestration"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.tasks: Dict[str, TaskStatus] = {}
        self.task_lock = threading.Lock()
        
        # Initialize orchestrator
        self.orchestrator = TaskOrchestrator(config_path, silent=True)
        
        # Initialize FastMCP server
        self.app = FastMCP("Grok Heavy Orchestrator")
        self._register_tools()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate essential configuration
            if 'openrouter' not in config:
                raise ValueError("OpenRouter configuration missing")
            if 'api_key' not in config['openrouter']:
                raise ValueError("OpenRouter API key missing")
            
            return config
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.app.tool()
        def grok_heavy_orchestrate(
            query: str,
            num_agents: int = 4,
            timeout: int = 300,
            aggregation_strategy: str = "consensus"
        ) -> str:
            """
            Orchestrate multi-agent analysis of a query
            
            Args:
                query: The query to analyze
                num_agents: Number of parallel agents (1-4)
                timeout: Task timeout in seconds
                aggregation_strategy: How to combine results ("consensus")
            
            Returns:
                JSON string with task_id for tracking progress
            """
            return self._start_orchestration(query, num_agents, timeout, aggregation_strategy)
        
        @self.app.tool()
        def get_task_progress(task_id: str) -> str:
            """
            Get current progress of an orchestration task
            
            Args:
                task_id: Task identifier from grok_heavy_orchestrate
                
            Returns:
                JSON string with current task status and progress
            """
            return self._get_task_progress(task_id)
        
        @self.app.tool()
        def list_active_tasks() -> str:
            """
            List all active orchestration tasks
            
            Returns:
                JSON string with all active tasks and their status
            """
            return self._list_active_tasks()
        
        @self.app.tool()
        def get_agent_tools() -> str:
            """
            Get list of available tools for agents
            
            Returns:
                JSON string with available tools and their descriptions
            """
            return self._get_agent_tools()
        
        @self.app.tool()
        def configure_orchestrator(
            parallel_agents: Optional[int] = None,
            task_timeout: Optional[int] = None,
            aggregation_strategy: Optional[str] = None
        ) -> str:
            """
            Update orchestrator configuration
            
            Args:
                parallel_agents: Number of parallel agents
                task_timeout: Task timeout in seconds
                aggregation_strategy: Aggregation strategy
                
            Returns:
                JSON string with updated configuration
            """
            return self._configure_orchestrator(parallel_agents, task_timeout, aggregation_strategy)
    
    def _start_orchestration(self, query: str, num_agents: int, timeout: int, aggregation_strategy: str) -> str:
        """Start orchestration task"""
        try:
            # Validate parameters
            if not query.strip():
                return json.dumps({"error": "Query cannot be empty"})
            
            if not 1 <= num_agents <= 4:
                return json.dumps({"error": "Number of agents must be between 1 and 4"})
            
            if timeout < 30:
                return json.dumps({"error": "Timeout must be at least 30 seconds"})
            
            # Create task
            task_id = str(uuid.uuid4())
            
            with self.task_lock:
                self.tasks[task_id] = TaskStatus(
                    task_id=task_id,
                    status="INITIALIZED",
                    progress={},
                    start_time=time.time()
                )
            
            # Configure orchestrator
            self.orchestrator.num_agents = num_agents
            self.orchestrator.task_timeout = timeout
            self.orchestrator.aggregation_strategy = aggregation_strategy
            
            # Start orchestration in background
            threading.Thread(
                target=self._run_orchestration,
                args=(task_id, query),
                daemon=True
            ).start()
            
            return json.dumps({
                "task_id": task_id,
                "status": "INITIALIZED",
                "message": f"Started orchestration with {num_agents} agents"
            })
            
        except Exception as e:
            return json.dumps({"error": f"Failed to start orchestration: {str(e)}"})
    
    def _run_orchestration(self, task_id: str, query: str):
        """Run orchestration in background thread"""
        try:
            # Update status
            with self.task_lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "RUNNING"
            
            # Create progress monitoring
            progress_thread = threading.Thread(
                target=self._monitor_progress,
                args=(task_id,),
                daemon=True
            )
            progress_thread.start()
            
            # Run orchestration
            result = self.orchestrator.orchestrate(query)
            
            # Update with result
            with self.task_lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "COMPLETED"
                    self.tasks[task_id].result = result
                    self.tasks[task_id].end_time = time.time()
                    self.tasks[task_id].progress = self.orchestrator.get_progress_status()
            
        except Exception as e:
            # Update with error
            with self.task_lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = "FAILED"
                    self.tasks[task_id].error = str(e)
                    self.tasks[task_id].end_time = time.time()
    
    def _monitor_progress(self, task_id: str):
        """Monitor orchestration progress"""
        while True:
            with self.task_lock:
                if task_id not in self.tasks:
                    break
                
                task = self.tasks[task_id]
                if task.status in ["COMPLETED", "FAILED"]:
                    break
                
                # Update progress from orchestrator
                if task.status == "RUNNING":
                    task.progress = self.orchestrator.get_progress_status()
            
            time.sleep(1)  # Update every second
    
    def _get_task_progress(self, task_id: str) -> str:
        """Get current task progress"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    return json.dumps({"error": "Task not found"})
                
                task = self.tasks[task_id]
                
                # Calculate execution time
                execution_time = None
                if task.start_time:
                    end_time = task.end_time or time.time()
                    execution_time = end_time - task.start_time
                
                return json.dumps({
                    "task_id": task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "result": task.result,
                    "error": task.error,
                    "execution_time": execution_time
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to get task progress: {str(e)}"})
    
    def _list_active_tasks(self) -> str:
        """List all active tasks"""
        try:
            with self.task_lock:
                active_tasks = []
                for task_id, task in self.tasks.items():
                    if task.status in ["INITIALIZED", "RUNNING"]:
                        active_tasks.append({
                            "task_id": task_id,
                            "status": task.status,
                            "agent_count": len(task.progress),
                            "start_time": task.start_time
                        })
                
                return json.dumps({
                    "active_tasks": active_tasks,
                    "total_active": len(active_tasks)
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to list active tasks: {str(e)}"})
    
    def _get_agent_tools(self) -> str:
        """Get available agent tools"""
        try:
            # Get tools from orchestrator's agent system
            from tools.calculator_tool import CalculatorTool
            from tools.read_file_tool import ReadFileTool
            from tools.write_file_tool import WriteFileTool
            from tools.task_done_tool import TaskDoneTool
            
            tools = [
                {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "class": "CalculatorTool"
                },
                {
                    "name": "read_file",
                    "description": "Read content from files",
                    "class": "ReadFileTool"
                },
                {
                    "name": "write_file", 
                    "description": "Write content to files",
                    "class": "WriteFileTool"
                },
                {
                    "name": "task_done",
                    "description": "Mark a task as completed",
                    "class": "TaskDoneTool"
                }
            ]
            
            # Try to include search tool if dependencies are available
            try:
                from tools.search_tool import SearchTool
                tools.append({
                    "name": "search",
                    "description": "Search the web for information",
                    "class": "SearchTool"
                })
            except ImportError:
                pass  # Search tool dependencies not available
            
            return json.dumps({
                "available_tools": tools,
                "total_tools": len(tools)
            })
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get agent tools: {str(e)}"})
    
    def _configure_orchestrator(self, parallel_agents: Optional[int] = None, task_timeout: Optional[int] = None, aggregation_strategy: Optional[str] = None) -> str:
        """Configure orchestrator settings"""
        try:
            updates = {}
            
            if parallel_agents is not None:
                if 1 <= parallel_agents <= 4:
                    self.orchestrator.num_agents = parallel_agents
                    updates["parallel_agents"] = parallel_agents
                else:
                    return json.dumps({"error": "parallel_agents must be between 1 and 4"})
            
            if task_timeout is not None:
                if task_timeout >= 30:
                    self.orchestrator.task_timeout = task_timeout
                    updates["task_timeout"] = task_timeout
                else:
                    return json.dumps({"error": "task_timeout must be at least 30 seconds"})
            
            if aggregation_strategy is not None:
                if aggregation_strategy in ["consensus"]:
                    self.orchestrator.aggregation_strategy = aggregation_strategy
                    updates["aggregation_strategy"] = aggregation_strategy
                else:
                    return json.dumps({"error": "aggregation_strategy must be 'consensus'"})
            
            return json.dumps({
                "message": "Configuration updated successfully",
                "updates": updates,
                "current_config": {
                    "parallel_agents": self.orchestrator.num_agents,
                    "task_timeout": self.orchestrator.task_timeout,
                    "aggregation_strategy": self.orchestrator.aggregation_strategy
                }
            })
            
        except Exception as e:
            return json.dumps({"error": f"Failed to configure orchestrator: {str(e)}"})
    
    def run(self, transport: str = "stdio"):
        """Run the FastMCP server"""
        print(f"🚀 Starting Grok Heavy MCP server")
        print(f"📊 Configured with {self.orchestrator.num_agents} agents")
        print(f"⏱️  Task timeout: {self.orchestrator.task_timeout}s")
        print(f"🔧 Aggregation strategy: {self.orchestrator.aggregation_strategy}")
        print(f"🔌 Transport: {transport}")
        
        # Run the server with specified transport
        if transport == "stdio":
            self.app.run()
        elif transport == "sse":
            self.app.run(transport="sse")
        elif transport == "streamable-http":
            self.app.run(transport="streamable-http")
        else:
            raise ValueError(f"Unsupported transport: {transport}")


def main():
    """Main entry point"""
    try:
        # Initialize MCP server
        mcp_server = GrokHeavyMCP()
        
        # Run server with SSE transport
        mcp_server.run(transport="sse")
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")


if __name__ == "__main__":
    main()