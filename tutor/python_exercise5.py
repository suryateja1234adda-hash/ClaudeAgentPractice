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
from urllib.parse import urlparse
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document
from claude_agent_sdk import tool, create_sdk_mcp_server


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


def get_author_name(path: str) -> str:
    """
    Find an author's name from a question, title, URL,
    or supported local document path.

    Supported files: .txt, .pdf, .docx
    """
    path = path.strip().strip('"')

    if not path:
        return "Please provide a title, URL, or file path."

    try:
        file_path = Path(path).expanduser()

        # Case 1: The user supplied a local file path.
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            text = ""

            if suffix == ".pdf":
                reader = PdfReader(str(file_path))
                metadata = reader.metadata

                if metadata and metadata.author:
                    author = metadata.author.strip()
                    if author and author.lower() != "unknown":
                        return f"Author from PDF metadata: {author}"

                text = "\n".join(
                    page.extract_text() or ""
                    for page in reader.pages
                )

            elif suffix == ".docx":
                document = Document(str(file_path))
                author = document.core_properties.author

                if author and author.strip():
                    return f"Author from Word metadata: {author.strip()}"

                text = "\n".join(
                    paragraph.text
                    for paragraph in document.paragraphs
                )

            elif suffix == ".txt":
                text = file_path.read_text(
                    encoding="utf-8",
                    errors="replace"
                )

            else:
                return (
                    f"Unsupported file type: {suffix}. "
                    "Supported formats: .txt, .pdf, .docx."
                )

            if not text.strip():
                return (
                    "No author metadata or readable document text "
                    "was found. The author could not be identified."
                )

            search_query = (
                "Identify the author of this document. "
                "Use its title, author information, or text to find "
                "reliable evidence. Document content:\n"
                + text[:3000]
            )

        # Case 2: The user supplied a webpage URL.
        elif urlparse(path).scheme in ("http", "https"):
            response = requests.get(
                path,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for selector in (
                'meta[name="author"]',
                'meta[property="article:author"]',
                'meta[name="parsely-author"]',
            ):
                tag = soup.select_one(selector)
                if tag:
                    author = tag.get("content", "").strip()
                    if author:
                        return f"Author from webpage metadata: {author}"

            title = (
                soup.title.get_text(strip=True)
                if soup.title else ""
            )
            content = soup.get_text(" ", strip=True)

            search_query = (
                f"Identify the author of this webpage.\n"
                f"URL: {path}\n"
                f"Title: {title}\n"
                f"Content: {content[:2500]}"
            )

        # Case 3: The user supplied a question or title.
        else:
            search_query = (
                f"{path}\n"
                "Identify the author of the book or original work "
                "being referred to. If it is a film, distinguish "
                "the source-book author from the film director "
                "and screenplay writer."
            )

        # Search the internet for evidence.
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    keywords=f"{search_query} author writer",
                    max_results=5
                )
            )

        if not results:
            return (
                f"No search results were found to identify the "
                f"author for: {path}"
            )

        return "\n\n".join(
            f"Search result {i}:\n"
            f"Title: {item.get('title', 'N/A')}\n"
            f"Description: {item.get('body', 'N/A')}\n"
            f"URL: {item.get('href', 'N/A')}"
            for i, item in enumerate(results, start=1)
        )

    except Exception as exc:
        return f"Could not identify the author: {exc}"


@tool(
    "get_author_name",
    (
        "Identify an author from a user question, book or movie title, "
        "webpage URL, or local .txt, .pdf, or .docx file path. "
        "Return author metadata or internet search evidence with URLs."
    ),
    {"path": str}
)
async def get_author_name_tool(args):
    result = get_author_name(args["path"])

    return {
        "content": [
            {
                "type": "text",
                "text": result
            }
        ]
    }


author_server = create_sdk_mcp_server(
    name="research",
    version="1.0.0",
    tools=[get_author_name_tool]
)




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

    # Detect an author lookup request.
    user_input = question.strip().strip('"')
    question_lower = user_input.lower()

    possible_file = Path(user_input).expanduser()
    is_url = urlparse(user_input).scheme in ("http", "https")
    is_file = possible_file.is_file()

    is_author_request = (
        any(term in question_lower for term in [
            "author",
            "who wrote",
            "written by",
            "writer",
            "authorship"
        ])
        or is_url
        or is_file
    )

    # Load the CSV as before.
    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
        software_rows = [
            row for row in csv.DictReader(file)
            if row.get("name", "").strip()
        ]

    system_prompt = f"""
        You are a helpful assistant and Windows software downloader.

        Download directory: {DOWNLOAD_DIR}

        AUTHOR LOOKUP:
        - When the user asks about an author, a title, a URL, or a local
        document path, use the get_author_name custom tool.
        - Pass the complete user input as the tool's path argument.
        - Review the returned evidence and give the author name clearly.
        - For a film, distinguish the original source-book author from
        the film director and screenplay writer.
        - Include a source URL when available.
        - Do not guess if the evidence is insufficient.

        SOFTWARE DOWNLOAD:
        - Use the software information supplied by the existing CSV.
        - Use the provided URL when available; otherwise search for the
        official Windows installer.
        - Respect the requested version or choose the latest stable version.
        - Use Bash and curl -fL to download to {DOWNLOAD_DIR}.
        - Verify the downloaded file exists and is non-empty.
        - Never execute or install downloaded files.
        """

    
    
    if is_author_request:  
        # Author lookups use a separate session.
        # Do not reuse the download session with a different tool configuration.
        options = reusable_options(
            system_prompt=system_prompt,
            setting_sources=[],
            tools=[
                "WebSearch",
                "WebFetch",
                "mcp__research__get_author_name"
            ],
            mcp_servers={"research": author_server},
            allowed_tools=[
                "WebSearch",
                "WebFetch",
                "mcp__research__get_author_name"
            ],
            resume=None,
            cwd=str(DOWNLOAD_DIR),
            permission_mode="default",
            max_turns=6
        )

    else:
        # Downloads: preserve the existing y/n approval behavior.
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

        if is_author_request:
            # New feature: answer the user's actual author question.
            await client.query(f"""
            Identify the author for this user input:

            {question}

            Instructions:
            1. Use mcp__research__get_author_name first.
            2. Base your answer on the tool's returned evidence.
            3. If the result is inconclusive, use WebSearch to verify it.
            4. Do not claim the tool failed unless it actually returned an error.
            5. Do not invent an author or sources.
            6. Provide the author's name and supporting source URL.
            """)

            async for message in client.receive_response():
                result = parse_message(message)
                if result:
                    session_id = result

        else:
            # Existing feature: retain the CSV software download loop.
            if not software_rows:
                print(f"No software entries found in {CSV_FILE}")
                return session_id

            for row in software_rows:
                name = row.get("name", "").strip()
                version = row.get("version", "").strip()
                url = row.get("url", "").strip()
                sno = row.get("sno", "").strip()

                entry_request = f"""
                Download this software now. Complete the download
                and verification before moving to the next entry.

                CSV row: {sno}
                Software: {name}
                Requested version: {version or "Latest stable"}
                Provided URL: {url or "Not provided"}

                Destination directory:
                {DOWNLOAD_DIR}

                Use Bash to perform the actual download. Do not stop
                after searching. Report any download failure.
                """

                print(
                    f"\nProcessing: {name} | "
                    f"Version: {version or 'Latest stable'}"
                )

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