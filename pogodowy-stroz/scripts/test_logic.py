import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path.
# We are in pogodowy-stroz/scripts/test_logic.py, so we need to go up two levels to get to the parent of pogodowy-stroz
# But wait, the package structure is `pogodowy-stroz/app/...`.
# If I run from root, I should add `pogodowy-stroz` to path if I want to import `app` directly.
# Or if I want to import as `pogodowy_stroz.app`, the folder should be named `pogodowy_stroz`.
# The folder is `pogodowy-stroz`. Dashes are not valid in python module names usually.
# So I should probably import `app` directly by adding `pogodowy-stroz` to path.

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.logic.conversation import ChatbotLogic

async def main():
    print("Initializing ChatbotLogic...")
    bot = ChatbotLogic("test_session")

    print("\n--- Test 1: Greeting ---")
    response = await bot.handle_message("Cześć")
    print(f"User: Cześć\nBot: {response}")

    print("\n--- Test 2: Weather without location ---")
    response = await bot.handle_message("Pogoda")
    print(f"User: Pogoda\nBot: {response}")

    print("\n--- Test 3: Providing location for weather ---")
    response = await bot.handle_message("Wrocław")
    print(f"User: Wrocław\nBot: {response}")

    print("\n--- Test 4: Warnings with location ---")
    response = await bot.handle_message("Ostrzeżenia Poznań")
    print(f"User: Ostrzeżenia Poznań\nBot: {response}")

    print("\n--- Test 5: Hydro ---")
    # "Stan wody Wisła" -> "Wisła" is the river.
    response = await bot.handle_message("Stan wody Wisła")
    print(f"User: Stan wody Wisła\nBot: {response}")

if __name__ == "__main__":
    asyncio.run(main())
