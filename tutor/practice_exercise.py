from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, query
from typing import Literal
from helper import reusable_options, parse_message
import json
from pathlib import Path

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

async def ask_claude(question:str,tone:Literal['DETAILED','REVISION','BEGINNER'],session_id = None):
    new_options = {
        'system_prompt' : tools_dict.get(tone),
        'setting_sources' : [],
        'tools' : ["Bash", "Read", "Powershell"],
        'resume' : session_id,
        'cwd' : DOWNLOAD_DIR,
        'permission_mode' : 'bypassPermissions',
    }

    options = reusable_options(**new_options)

    async with ClaudeSDKClient(options=options) as client :
        await client.query(question)
        async for message in client.receive_response():
            result = parse_message(message)
            if result:
                session_id = result
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
        tone = input('What is your tone DETAILED,REVISION,BEGINNER')
        session_id = await ask_claude(question=question, tone=tone, session_id=session_id)
        users[name] = session_id

        with open("users.json", "w") as file:
            json.dump(users, file)
        print(users)

if __name__ == '__main__':
    asyncio.run(ask_question())


    
        







    