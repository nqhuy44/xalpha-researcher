import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.services.llm import LLMService
from src.config.settings import settings

async def verify_providers():
    print("--- Verifying LLM Provider Initialization ---")
    
    # Mock some keys for testing initialization
    settings.grok.api_key = "grok-mock-key"
    settings.deepseek.api_key = "ds-mock-key"
    
    service = LLMService()
    
    # Check if providers are in the internal dictionary
    providers = service._providers
    print(f"Initialized providers: {list(providers.keys())}")
    
    assert "grok" in providers, "Grok provider should be initialized"
    assert "deepseek" in providers, "DeepSeek provider should be initialized"
    
    # Verify base URLs
    print(f"Grok Base URL: {providers['grok'].base_url}")
    print(f"DeepSeek Base URL: {providers['deepseek'].base_url}")
    
    assert providers["grok"].base_url == "https://api.x.ai/v1"
    assert providers["deepseek"].base_url == "https://api.deepseek.com"
    
    # Verify model mapping
    print("\n--- Verifying Model Mapping ---")
    
    # Test Grok mapping
    settings.llm.provider = "grok"
    p, m = service.get_provider_and_model("deep")
    print(f"Grok Deep: {m}")
    assert m == "grok-2-1212"
    
    # Test DeepSeek mapping
    settings.llm.provider = "deepseek"
    p, m = service.get_provider_and_model("deep")
    print(f"DeepSeek Deep: {m}")
    assert m == "deepseek-reasoner"
    
    p, m = service.get_provider_and_model("fast")
    print(f"DeepSeek Fast: {m}")
    assert m == "deepseek-chat"
    
    print("\n✅ Verification successful!")

if __name__ == "__main__":
    asyncio.run(verify_providers())
