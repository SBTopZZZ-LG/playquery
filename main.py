"""Main module to demonstrate usage of the AI provider framework."""

import asyncio

from agents import HelpfulAssistantAgent
from ai_providers import AIProviderConfig, ProviderType, managed_ai_provider


async def main():
    """Main function to demonstrate usage of the AI provider framework."""

    print("Initializing configuration...")
    helpful_assistant_provider_config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4.1",  # or gpt-5
        timeout=120,  # 2 minutes
        system_prompt=HelpfulAssistantAgent.system_prompt,
        tools=HelpfulAssistantAgent.tools,
    )

    try:
        async with managed_ai_provider(helpful_assistant_provider_config) as helpful_assistant_provider:
            print("Sending message...")
            question = "Can you give me a 2-sentence summary of the MCP protocol?"
            print(f"Question: {question}")

            response = await helpful_assistant_provider.query(question)

            print("\nResponse:")
            print("-" * 20)
            print(response)
            print("-" * 20)
    except (ValueError, RuntimeError, OSError) as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
