import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.services.llm import LLMService
from src.config.settings import settings

async def verify_claude():
    print("--- Verifying Claude Provider Initialization ---")
    
    # Mock key for testing initialization
    settings.claude.api_key = "claude-mock-key"
    
    service = LLMService()
    
    # Check if provider is in the internal dictionary
    providers = service._providers
    print(f"Initialized providers: {list(providers.keys())}")
    
    assert "claude" in providers, "Claude provider should be initialized"
    
    # Verify client presence
    from src.services.llm.claude_provider import ClaudeProvider
    assert isinstance(providers["claude"], ClaudeProvider)
    assert providers["claude"].client is not None
    
    # Verify model mapping
    print("\n--- Verifying Model Mapping ---")
    
    settings.llm.provider = "claude"
    p, m = service.get_provider_and_model("deep")
    print(f"Claude Deep: {m}")
    assert m == "claude-3-7-sonnet-latest"
    
    p, m = service.get_provider_and_model("fast")
    print(f"Claude Fast: {m}")
    assert m == "claude-3-5-haiku-latest"
    
    print("\n✅ Claude Verification successful!")

if __name__ == "__main__":
    asyncio.run(verify_claude())
