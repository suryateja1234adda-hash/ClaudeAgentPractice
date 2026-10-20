from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, query
from typing import Literal
from helper import reusable_options, parse_message
import json
from pathlib import Path
import csv


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
CSV_FILE = PROJECT_DIR.parent / "requiredsoftwares.csv"
DOWNLOAD_DIR = PROJECT_DIR / "generated_files"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)




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


async def ask_claude(question: str, session_id=None):

    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:

        software_rows = [
            row for row in csv.DictReader(file)
            if row.get("name", "").strip()
        ]


    if not software_rows:
        print(f"No software entries found in {CSV_FILE}")
        return session_id

    system_prompt = f"""
        You are a Windows software downloader.
        Download directory: {DOWNLOAD_DIR}

        For the single software entry in the user's request:
        1. Use its supplied URL if present. If it is a webpage, find the
        actual installer link on that page.
        2. If no URL is supplied, use WebSearch and WebFetch to find the
        official Windows .exe installer.
        3. Respect the specified version. If no version is specified,
        select the latest stable version.
        4. You MUST invoke Bash to download the installer using curl -fL.
        Save directly inside {DOWNLOAD_DIR}, with no subfolders.
        5. Use an absolute output path. Verify using test -s after download.
        6. Never execute or install the file.
        7. Do not claim success unless Bash confirms the file exists and
        is non-empty. If it fails, report the error.
        8. Finish processing this entry before responding. Do not merely
        provide a URL or stop after WebSearch/WebFetch.
        """

    options = reusable_options(
        system_prompt=system_prompt,
        setting_sources=[],
        tools=["Bash", "WebSearch", "WebFetch"],
        resume=session_id,
        cwd=str(DOWNLOAD_DIR),
        permission_mode="default",
        can_use_tool=custom_tool_checker
    )

    async with ClaudeSDKClient(options=options) as client:
        for row in software_rows:
            name = row.get("name", "").strip()
            version = row.get("version", "").strip()
            url = row.get("url", "").strip()
            sno = row.get("sno", "").strip()

            entry_request = f"""

                Download this software now. Complete the download and verification
                before moving to the next entry.

                CSV row: {sno}
                Software: {name}
                Requested version: {version or "Latest stable"}
                Provided URL: {url or "Not provided"}

                The destination directory is:
                {DOWNLOAD_DIR}

                Use Bash to perform the actual download. Do not stop after searching.
                If this entry cannot be downloaded, explain why and continue when
                the next entry is submitted.
                """
            print(f"\nProcessing: {name} | Version: {version or 'Latest stable'}")

            await client.query(entry_request)

            async for message in client.receive_response():
                result = parse_message(message)
                if result:
                    session_id = result

    print(f"\nFinished processing {len(software_rows)} CSV entries.")
    print(f"Check download results in: {DOWNLOAD_DIR}")
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