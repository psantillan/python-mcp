from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from dataclasses import dataclass
import mcp.types as types
from mcp.server.fastmcp import FastMCP

@dataclass
class PromptTemplate:
   name: str
   description: str
   arguments: Optional[List[Dict[str, Any]]] = None
   system_prompt: Optional[str] = None
   messages: List[Dict[str, str]] = None

@dataclass
class PromptConfig:
   default_dir: Path = Path(__file__).parent / "templates"
   exclude_patterns: List[str] = None

   def __post_init__(self):
       if self.exclude_patterns is None:
           self.exclude_patterns = ["__pycache__", ".git"]

class PromptManager:
   def __init__(self, config: Optional[PromptConfig] = None):
       self.config = config or PromptConfig()
       self._templates: Dict[str, PromptTemplate] = {}

   def should_exclude(self, path: Path) -> bool:
       return any(pattern in str(path) for pattern in self.config.exclude_patterns)

   def load_template(self, file_path: Path) -> Optional[PromptTemplate]:
       try:
           content = yaml.safe_load(file_path.read_text())
           template = PromptTemplate(**content)
           self._templates[template.name] = template
           return template
       except Exception as e:
           print(f"Error loading prompt template {file_path}: {e}")
           return None

   def register_prompt(self, mcp: FastMCP, template: PromptTemplate):
       prompt_args = []
       if template.arguments:
           prompt_args = [
               types.PromptArgument(
                   name=arg["name"],
                   description=arg.get("description"),
                   required=arg.get("required", False)
               ) for arg in template.arguments
           ]

       @mcp.prompt(template.name)
       async def get_prompt(arguments: Optional[Dict[str, str]] = None) -> types.GetPromptResult:
           try:
               args = arguments or {}
               messages = []
               
               if template.system_prompt:
                   messages.append(types.PromptMessage(
                       role="system",
                       content=types.TextContent(
                           type="text",
                           text=template.system_prompt.format(**args)
                       )
                   ))

               for msg in template.messages:
                   messages.append(types.PromptMessage(
                       role=msg["role"],
                       content=types.TextContent(
                           type="text",
                           text=msg["content"].format(**args)
                       )
                   ))

               return types.GetPromptResult(
                   description=template.description,
                   arguments=prompt_args,
                   messages=messages
               )
           except Exception as e:
               return types.GetPromptResult(
                   description=template.description,
                   arguments=prompt_args,
                   messages=[types.PromptMessage(
                       role="system",
                       content=types.TextContent(
                           type="text",
                           text=f"Error: {str(e)}"
                       )
                   )]
               )

   def get_template(self, name: str) -> Optional[PromptTemplate]:
       return self._templates.get(name)

def init_prompts(
   mcp: FastMCP,
   template_dirs: Optional[List[Path]] = None,
   exclude_default: bool = False,
   config: Optional[PromptConfig] = None
) -> PromptManager:
   """Initialize prompts for the MCP server."""
   manager = PromptManager(config)
   template_dirs = [] if template_dirs is None else template_dirs

   if not exclude_default:
       template_dirs.append(manager.config.default_dir)

   for template_dir in template_dirs:
       if not template_dir.exists():
           print(f"Warning: Template directory does not exist: {template_dir}")
           continue

       for file_path in template_dir.rglob("*.yaml"):
           if not file_path.is_file() or manager.should_exclude(file_path):
               continue

           template = manager.load_template(file_path)
           if template:
               manager.register_prompt(mcp, template)

   return manager