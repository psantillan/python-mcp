from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import yaml
from dataclasses import dataclass
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from datetime import datetime

@dataclass
class ResourceConfig:
   uri_prefix: str = "file://"
   default_mime_type: str = "text/plain"
   mime_types: Dict[str, str] = None
   exclude_patterns: List[str] = None
   
   def __post_init__(self):
       if self.mime_types is None:
           self.mime_types = {
               ".json": "application/json",
               ".yaml": "application/yaml", 
               ".yml": "application/yaml",
               ".md": "text/markdown",
               ".txt": "text/plain",
               ".py": "text/x-python",
               ".css": "text/css",
               ".html": "text/html",
               ".js": "application/javascript"
           }
       if self.exclude_patterns is None:
           self.exclude_patterns = ["__pycache__", ".git", ".mypy_cache"]

class ResourceManager:
   def __init__(self, config: Optional[ResourceConfig] = None):
       self.config = config or ResourceConfig()
       self._resources: Dict[str, types.Resource] = {}
       self._last_modified: Dict[str, datetime] = {}

   def should_exclude(self, path: Path) -> bool:
       return any(pattern in str(path) for pattern in self.config.exclude_patterns)

   def get_mime_type(self, file_path: Path) -> str:
       return self.config.mime_types.get(
           file_path.suffix.lower(), 
           self.config.default_mime_type
       )

   def parse_structured_content(self, file_path: Path, content: str) -> str:
       try:
           if file_path.suffix.lower() == '.json':
               parsed = json.loads(content)
               return json.dumps(parsed, indent=2)
           elif file_path.suffix.lower() in ('.yaml', '.yml'):
               parsed = yaml.safe_load(content)
               return yaml.dump(parsed, default_flow_style=False)
           return content
       except Exception as e:
           print(f"Error parsing {file_path}: {e}")
           return content

   def register_resource(self, mcp: FastMCP, file_path: Path, source_parent: str):
       if self.should_exclude(file_path):
           return

       resource_uri = f"{self.config.uri_prefix}{source_parent}/{file_path.relative_to(file_path.parent)}"
       
       @mcp.resource(uri=resource_uri)
       def get_resource() -> types.Resource:
           try:
               content = file_path.read_text(encoding="utf-8")
               content = self.parse_structured_content(file_path, content)
               
               resource = types.Resource(
                   uri=resource_uri,
                   name=f"{source_parent}: {file_path.stem.replace('_', ' ').title()}",
                   description=f"Content from {source_parent}/{file_path.name}",
                   mimeType=self.get_mime_type(file_path),
                   text=content
               )
               
               self._resources[resource_uri] = resource
               self._last_modified[resource_uri] = datetime.fromtimestamp(
                   file_path.stat().st_mtime
               )
               
               return resource
           except Exception as e:
               print(f"Error reading {file_path}: {e}")
               return types.Resource(
                   uri=resource_uri,
                   name=f"Error: {file_path.name}",
                   text=f"Failed to load resource: {str(e)}"
               )

   def get_resource(self, uri: str) -> Optional[types.Resource]:
       return self._resources.get(uri)

   def get_last_modified(self, uri: str) -> Optional[datetime]:
       return self._last_modified.get(uri)

def init_resources(
   mcp: FastMCP, 
   source_dirs: Optional[List[Path]] = None,
   exclude_default: bool = False,
   config: Optional[ResourceConfig] = None
) -> ResourceManager:
   """Initialize resources for the MCP server."""
   manager = ResourceManager(config)
   default_source_dir = Path(__file__).parent / "sources"
   source_dirs = [] if source_dirs is None else source_dirs

   if not exclude_default:
       source_dirs.append(default_source_dir)

   for source_dir in source_dirs:
       if not source_dir.exists():
           print(f"Warning: Source directory does not exist: {source_dir}")
           continue

       source_parent = source_dir.parent.name
       
       for file_path in source_dir.rglob("*"):
           if file_path.is_file():
               manager.register_resource(mcp, file_path, source_parent)

   return manager