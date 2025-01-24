from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import importlib.util
import inspect
from dataclasses import dataclass
import mcp.types as types
from mcp.server.fastmcp import FastMCP

@dataclass
class ToolConfig:
    default_dir: Path = Path(__file__).parent / "implementations"
    exclude_patterns: List[str] = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = ["__pycache__", ".git", "__init__.py"]

class ToolManager:
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self._tools: Dict[str, Callable] = {}
    
    def should_exclude(self, path: Path) -> bool:
        return any(pattern in str(path) for pattern in self.config.exclude_patterns)

    def load_module(self, file_path: Path) -> Optional[Any]:
        try:
            module_name = f"mcp_server.tools.{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            print(f"Error loading module {file_path}: {e}")
        return None

    def register_tools(self, mcp: FastMCP, module: Any):
        for name, obj in inspect.getmembers(module):
            if (inspect.isfunction(obj) and 
                not name.startswith('_') and 
                obj.__module__ == module.__name__):
                try:
                    tool = mcp.tool(name)
                    self._tools[name] = tool(obj)
                except Exception as e:
                    print(f"Error registering tool {name}: {e}")

def init_tools(
    mcp: FastMCP,
    tool_dirs: Optional[List[Path]] = None,
    exclude_default: bool = False,
    config: Optional[ToolConfig] = None
) -> ToolManager:
    manager = ToolManager(config)
    tool_dirs = [] if tool_dirs is None else tool_dirs

    if not exclude_default:
        tool_dirs.append(manager.config.default_dir)

    for tool_dir in tool_dirs:
        if not tool_dir.exists():
            print(f"Warning: Tool directory does not exist: {tool_dir}")
            continue

        for file_path in tool_dir.rglob("*.py"):
            if not file_path.is_file() or manager.should_exclude(file_path):
                continue
            
            module = manager.load_module(file_path)
            if module:
                manager.register_tools(mcp, module)

    return manager