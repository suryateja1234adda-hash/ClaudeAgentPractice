from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, query
from typing import Literal
from helper import reusable_options, parse_message
import json
from pathlib import Path

from claude_agent_sdk.types import (
    PermissionResultAllow, 
    PermissionResultDeny, 
    ToolPermissionContext
)

tools_dict = {
    'DETAILED' : 'You are a python tutor with 20+ years of experience. Explain about any given topic in a detialed manner',
    'REVISION' : 'You are a python tutor with 20+ years of experience. Help the user to quickly revise any givrn topic.',
    'BEGINNER' : 'You are a python tutor with 20+ years of experience. Explain any given topic as if I am a 10 years old kid.'
}

PROJECT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = PROJECT_DIR / "generated_files"


if os.path.exists("users.json"):
    with open("users.json", "r") as file:
        users = json.load(file)
else:
    users = {} 

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

async def ask_claude(question:str,session_id = None):
    new_options = {
        'system_prompt' : """
        You are a file-download assistant.

        Follow these steps for every user request:
        1. Use WebSearch to find a real, downloadable file that matches the request.
        2. Identify a direct HTTPS download URL.
        3. Select a suitable filename and save it in the current working directory.
        4. Do not print lengthy search results or recommendations.
        5. You MUST use the PowerShell tool to download the file.
        6. Use this command format:
           Invoke-WebRequest -Uri "DIRECT_DOWNLOAD_URL" -OutFile "FILENAME"
        7. Wait for the tool permission approval before downloading.
        8. After downloading, verify the file using Test-Path.
        9. Report only whether the download succeeded and the saved filename.
        10. Never execute downloaded files.
        11. If a direct download URL cannot be found, report that briefly.
        12. If permission is denied, do not retry the download.
        """,

        'setting_sources' : [],
        'tools' : ["Bash", "Read", "PowerShell","WebSearch"],
        'resume' : session_id,
        'cwd' : str(DOWNLOAD_DIR),
        'permission_mode' : 'default',
        'can_use_tool' : custom_tool_checker
    }

    options = reusable_options(**new_options)

    async with ClaudeSDKClient(options=options) as client :
        await client.query(question)
        async for message in client.receive_response():
            result = parse_message(message)
            if result:
                session_id = result
        print("Request completed. Check the generated_files folder.")
        return session_id
            

async def ask_question():
    while True:
        name = input('What is your name ? ')
        if name in ['exit','quit','']:
            break
        elif name in users:
            print('Existing User')
            session_id = users[name]
            print(session_id)
        else:
            print('New User')
            session_id = None
            print(session_id)

        question = input('What is your Question ? ')
        # tone = input('What is your tone DETAILED,REVISION,BEGINNER')
        session_id = await ask_claude(question=question, session_id=session_id)
        users[name] = session_id

        with open("users.json", "w") as file:
            json.dump(users, file)
        print(users)

if __name__ == '__main__':
    asyncio.run(ask_question())