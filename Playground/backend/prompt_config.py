"""
Prompt configuration system for customizable agent prompts.

This allows prompts to be modified without code changes, and enables
prompt versioning and A/B testing.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class PromptConfig:
    """Manages prompt configurations for agents."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize prompt configuration.
        
        Args:
            config_path: Path to YAML config file. If None, uses defaults.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self._cache = {}
    
    def _get_default_config_path(self) -> str:
        """Get default config path (create if doesn't exist)."""
        config_dir = Path(__file__).parent / "prompts"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.yaml"
        
        # Create default config if it doesn't exist
        if not config_file.exists():
            self._create_default_config(config_file)
        
        return str(config_file)
    
    def _create_default_config(self, config_file: Path):
        """Create default prompt configuration."""
        default_config = {
            "agents": {
                "router": {
                    "system_prompt": """You are a routing agent for nuclear simulation requests.

Classify the user's request into ONE of these categories:
1. "single_study" - User wants to run ONE specific simulation
2. "sweep" - User wants to VARY a parameter and run MULTIPLE simulations
3. "query" - User wants to SEARCH or LIST past results
4. "analysis" - User wants to ANALYZE or COMPARE specific runs

CRITICAL: Respond with ONLY the category name. No explanations, no reasoning, no markdown, no additional text.""",
                    "temperature": 0.2,
                    "max_tokens": 10,
                },
                "studies_agent": {
                    "system_prompt": """You are a nuclear reactor physics expert.

Extract a simulation study specification from the user's request.
Output ONLY valid JSON with this structure:
{
    "geometry": "description (e.g., PWR pin cell, BWR assembly)",
    "materials": ["list", "of", "materials"],
    "enrichment_pct": float or null,
    "temperature_K": float or null,
    "particles": int (default 10000),
    "batches": int (default 50),
    "inactive": int or null (optional inactive batches)
}

CRITICAL: Output ONLY valid JSON, no markdown code blocks, no explanations.""",
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
            }
        }
        
        with open(config_file, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            return {}
        
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f) or {}
    
    def get_prompt(self, agent_name: str, prompt_type: str = "system") -> str:
        """
        Get prompt for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., "router", "studies_agent")
            prompt_type: Type of prompt (default: "system")
        
        Returns:
            Prompt string, or empty string if not found
        """
        cache_key = f"{agent_name}:{prompt_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        agents = self.config.get("agents", {})
        agent_config = agents.get(agent_name, {})
        prompt = agent_config.get(f"{prompt_type}_prompt", "")
        
        self._cache[cache_key] = prompt
        return prompt
    
    def get_temperature(self, agent_name: str, default: float = 0.7) -> float:
        """Get temperature setting for an agent."""
        agents = self.config.get("agents", {})
        agent_config = agents.get(agent_name, {})
        return agent_config.get("temperature", default)
    
    def get_max_tokens(self, agent_name: str, default: int = 900) -> int:
        """Get max_tokens setting for an agent."""
        agents = self.config.get("agents", {})
        agent_config = agents.get(agent_name, {})
        return agent_config.get("max_tokens", default)
    
    def reload(self):
        """Reload configuration from file (useful for testing prompt changes)."""
        self.config = self._load_config()
        self._cache.clear()


# Global instance
_prompt_config: Optional[PromptConfig] = None


def get_prompt_config(config_path: Optional[str] = None) -> PromptConfig:
    """Get global prompt configuration instance."""
    global _prompt_config
    if _prompt_config is None:
        _prompt_config = PromptConfig(config_path)
    return _prompt_config
