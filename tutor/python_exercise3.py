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
import urllib.request
import re
from urllib.parse import urlparse, unquote

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
CSV_FILE = PROJECT_DIR.parent / "requiredsoftwares.csv"
USERS_FILE = PROJECT_DIR.parent / "users.json"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


if USERS_FILE.exists():
    with open(USERS_FILE, "r", encoding="utf-8") as file:
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

def read_required_softwares():
    softwares = []

    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            softwares.append({
                                "sno": row["sno"],
                                "name": row["name"],
                                "version": (row.get("version") or "").strip(),
                                "url": (row.get("url") or "").strip()
                            })

    return softwares


def download_file(url: str, filename: str) -> Path:
    """Download a file without executing or installing it."""

    if not url.startswith("https://"):
        raise ValueError("Only HTTPS download URLs are allowed.")

    destination = DOWNLOAD_DIR / filename
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        with open(destination, "wb") as file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                file.write(chunk)

    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError("Download failed or the file is empty.")

    return destination

async def ask_claude(question:str,session_id = None):

    softwares = read_required_softwares()

    if not softwares:
        print("No software entries found in requiredsoftwares.csv.")
        return session_id

    new_options = {
        'system_prompt': """
        You are a software download research assistant.

        For each software in the supplied list:
        1. Use the exact requested version if provided.
        2. Otherwise, find the latest stable version.
        3. If a URL is provided, verify that it matches the software
           and requested version.
        4. If the URL is missing, search for the official vendor URL.
        5. Find a direct HTTPS installer URL for Windows 64-bit.
        6. Never invent URLs or filenames.
        7. Never install or execute downloaded files.

        Return each result in this exact format:

        Software: Notepad++
        Version: 8.7.5
        URL: https://actual-download-url
        Filename: actual-installer.exe

        Repeat these four fields for every software.
        If no direct URL can be verified, use:
        URL: UNAVAILABLE
        Filename: UNAVAILABLE

        Return the results as plain text, not JSON.
        """,

        'setting_sources' : [],
        'tools' : ["Bash", "Read","WebSearch"],
        'resume' : session_id,
        'cwd' : str(DOWNLOAD_DIR),
        'permission_mode' : 'default',
        'can_use_tool' : custom_tool_checker
    }

    options = reusable_options(**new_options)

    software_details = json.dumps(softwares, indent=2)

    final_question = f"""
    Find download links for the following software.

    Software requirements:
    {software_details}

    User request: {question}

    Return the four fields for every software as instructed.
    """

    response_text = ""

    async with ClaudeSDKClient(options=options) as client:
        await client.query(final_question)

        async for message in client.receive_response():

    # Capture text from Claude's assistant messages.
            content = getattr(message, "content", None)

            if content:
                for block in content:
                    block_text = getattr(block, "text", None)
                    if block_text:
                        response_text += block_text + "\n"

            # Preserve your existing session handling.
            result = parse_message(message)
            if result:
                session_id = result

    print("Claude response captured:")
    print(response_text)

    if not response_text.strip():
        print("Claude returned no readable text.")
        return session_id

    
    # Extract the JSON array returned by Claude.
    json_match = re.search(
        r"```(?:json)?\s*(\[.*?\])\s*```",
        response_text,
        re.IGNORECASE | re.DOTALL
    )

    # Also support a JSON array without Markdown code fences.
    if not json_match:
        json_match = re.search(
            r"(\[\s*\{.*?\}\s*\])",
            response_text,
            re.DOTALL
        )

    if not json_match:
        print("Could not find a JSON array in Claude's response.")
        print("Please check the Claude response printed above.")
        return session_id

    try:
        software_list = json.loads(json_match.group(1))
    except json.JSONDecodeError as error:
        print(f"Could not parse Claude's JSON response: {error}")
        return session_id

    # Process every software returned by Claude.
    for software in software_list:
        name = software.get("name", "Unknown")
        version = software.get("version", "Unknown")
        url = str(software.get("url", "")).strip()

        print(f"\nSoftware: {name}")
        print(f"Version: {version}")
        print(f"URL: {url}")

        if not url.startswith("https://") or url.upper() == "UNAVAILABLE":
            print("Skipped: No usable HTTPS download URL.")
            continue

        # Use the filename provided by Claude, if available.
        # Otherwise, derive it from the URL.
        filename = str(software.get("filename", "")).strip()

        if not filename or filename.upper() == "UNAVAILABLE":
            filename = Path(
                unquote(urlparse(url).path)
            ).name

        if (
            not filename
            or Path(filename).name != filename
            or Path(filename).suffix.lower() not in {".exe", ".msi", ".zip"}
        ):
            print("Skipped: Invalid or unsupported installer filename.")
            continue

        approval = input(
            f"Download {name} {version} to {DOWNLOAD_DIR}? (y/n): "
        ).strip().lower()

        if approval != "y":
            print(f"Download declined for {name}.")
            continue

        try:
            saved_path = download_file(url, filename)

            print(f"Download successful: {saved_path}")
            print(f"Size: {saved_path.stat().st_size:,} bytes")

        except Exception as error:
            print(f"Download failed for {name}: {error}")

    print(f"\nFinished. Check this folder: {DOWNLOAD_DIR}")
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

        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump(users, file)
            print(users)

if __name__ == '__main__':
    asyncio.run(ask_question())