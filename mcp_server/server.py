from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP
import yaml

@dataclass
class ServerConfig:
    name: str
    source_dirs: List[Path]
    implementation_dirs: List[Path]
    template_dirs: List[Path]

class MCPServer:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.mcp = FastMCP(config.name)
        
        from resources import init_resources
        from tools import init_tools
        from prompts import init_prompts
        
        init_resources(self.mcp, self.config.source_dirs)
        init_tools(self.mcp, self.config.implementation_dirs)
        init_prompts(self.mcp, self.config.template_dirs)

    def run(self):
        self.mcp.run()

def load_config(config_path: Path) -> ServerConfig:
    config_path = config_path.resolve()
    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    base_dir = config_path.parent
    return ServerConfig(
        name=config_data['server']['name'],
        source_dirs=[base_dir / Path(p) for p in config_data['directories']['sources']],
        implementation_dirs=[base_dir / Path(p) for p in config_data['directories']['implementations']],
        template_dirs=[base_dir / Path(p) for p in config_data['directories']['templates']]
    )

# Load configuration and initialize the server
config = load_config(Path(__file__).parent / 'config.yaml')
server_instance = MCPServer(config)

# Expose the FastMCP instance at the module level
mcp = server_instance.mcp
