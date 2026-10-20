from dotenv import load_dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, InMemorySessionStore, query
import asyncio
from helper import parse_message, MODEL_NAME
from pathlib import Path



from claude_agent_sdk.types import (
    PermissionResultAllow, 
    PermissionResultDeny, 
    ToolPermissionContext
)

PROJECT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = PROJECT_DIR / "generated_files"

# 1. Define the callback function
async def custom_tool_checker(
    tool_name: str, 
    input_data: dict, 
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    
    print(f"\nTool Requested: {tool_name}")
    print(f"Inputs: {input_data}")
    
    # Simple console approval check
    user_response = input("Allow Claude to run this tool? (y/n): ")
    
    if user_response.lower() == 'y':
        return PermissionResultAllow(behavior='allow')
    else:
        return PermissionResultDeny(behavior='deny', reason="User rejected the tool execution.")



async def main():
    options = ClaudeAgentOptions(
        system_prompt="""

        You are a Downloads Agent.

        When the user requests a file download:

        1. Use WebSearch to find a real, downloadable file matching the request.
        2. Identify the actual direct HTTPS URL of the file.
        Do not invent URLs or use an ordinary webpage URL as a download link.
        3. Choose a suitable filename and save it in the current working directory.
        4. Do not ask the user for permission in your conversational response.
        5. Instead, call the PowerShell tool with a command that downloads
        the file using Invoke-WebRequest.
        6. The PowerShell tool call will trigger custom_tool_checker.
        Wait for the user's approval before proceeding.
        7. If the user denies permission, do not retry the download.
        8. After approval, download the file and verify it exists using Test-Path.
        9. Report success only after verifying the file exists.
        10. Never execute downloaded files.

        Example PowerShell download command:

        Invoke-WebRequest -Uri "DIRECT_FILE_URL" `
        -OutFile "Professional_Resume_Template.docx"

        Use the actual URL found through WebSearch instead of
        the placeholder DIRECT_FILE_URL.
        """,
        setting_sources=[],
        model=MODEL_NAME,
        max_turns=30,
        tools=["Read", "Glob", "PowerShell", "WebSearch"],
        cwd=DOWNLOAD_DIR,
        permission_mode="default",
        can_use_tool=custom_tool_checker
    )

    async with ClaudeSDKClient(options=options) as client: 
        # NEW: Keep accepting instructions until you choose to exit.
        while True:
            question = input(
                "\nWhat would you like to do? "
                "(Type 'exit' to stop): "
            ).strip()

            if question.lower() in ("exit", "quit"):
                print("Downloads Agent stopped.")
                break

            if not question:
                continue

            await client.query(question)

            # CHANGED: Receive only this response, not the endless stream.
            async for message in client.receive_response():
                parse_message(message)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())