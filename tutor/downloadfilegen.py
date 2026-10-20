from pathlib import Path
import random
import json
import csv
import os
import io


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

DOWNLOAD_DIR = PROJECT_DIR / "generated_files"

MIN_SIZE_KB = 5
MAX_SIZE_KB = 2048   # 2 MB


# --------------------------------------------------
# Helpers
# --------------------------------------------------

WORDS = [
    "python", "agent", "claude", "tutor",
    "memory", "session", "user", "question",
    "answer", "AI", "machine", "learning",
    "automation", "testing", "data",
    "project", "development", "framework"
]

USERS = [
    "Surya", "Sameera", "Rahul",
    "Priya", "John"
]

TOPICS = [
    "Python", "AI", "ML",
    "LangGraph", "Claude"
]

LEVELS = [
    "Beginner", "Intermediate", "Advanced"
]


def random_size():
    """
    Generate a random file size between
    5 KB and 2 MB.
    """
    return random.randint(
        MIN_SIZE_KB * 1024,
        MAX_SIZE_KB * 1024
    )


def random_text(size):
    """
    Generate random readable text efficiently.

    Generates text in chunks instead of repeatedly
    rebuilding the entire string.
    """

    chunk = " ".join(random.choices(WORDS, k=1000))

    repetitions = (size // len(chunk)) + 2

    return (chunk * repetitions)[:size]


def random_binary(size):
    """
    Generate random binary data.
    """
    return os.urandom(size)


# --------------------------------------------------
# Text Files
# --------------------------------------------------

def create_text_file(path, size):
    """
    Creates TXT / LOG / MD / HTML files.
    """

    content = random_text(size)

    path.write_text(
        content,
        encoding="utf-8"
    )


# --------------------------------------------------
# CSV
# --------------------------------------------------

def create_csv_file(path, size):
    """
    Create CSV efficiently.

    Instead of rebuilding the entire CSV after every
    row, rows are generated once and written once.
    """

    rows = []

    # Approximate CSV row size
    estimated_row_size = 70

    number_of_rows = max(
        10,
        size // estimated_row_size
    )

    rows.append([
        "ID",
        "User",
        "Topic",
        "Level"
    ])

    for _ in range(number_of_rows):

        rows.append([
            random.randint(1000, 9999),
            random.choice(USERS),
            random.choice(TOPICS),
            random.choice(LEVELS)
        ])

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerows(rows)

    content = output.getvalue()

    # If generated content is slightly smaller than target,
    # add additional rows efficiently.
    while len(content.encode("utf-8")) < size:

        extra_rows = []

        for _ in range(1000):

            extra_rows.append([
                random.randint(1000, 9999),
                random.choice(USERS),
                random.choice(TOPICS),
                random.choice(LEVELS)
            ])

        writer.writerows(extra_rows)

        content = output.getvalue()

    path.write_text(
        content,
        encoding="utf-8"
    )


# --------------------------------------------------
# JSON
# --------------------------------------------------

def create_json_file(path, size):
    """
    Create JSON efficiently.

    The old implementation called json.dumps()
    inside the while loop, which repeatedly serialized
    the entire dataset.

    This version generates the objects first and
    serializes only once.
    """

    data = []

    # Approximate size of one JSON object
    estimated_object_size = 250

    number_of_objects = max(
        5,
        size // estimated_object_size
    )

    for _ in range(number_of_objects):

        data.append({
            "id": random.randint(10000, 99999),
            "user": random.choice(USERS),
            "topic": random.choice(TOPICS),
            "score": random.randint(1, 100),
            "description": random_text(100)
        })

    content = json.dumps(
        data,
        separators=(",", ":")
    )

    # If still smaller than target, add objects in batches.
    while len(content.encode("utf-8")) < size:

        for _ in range(500):

            data.append({
                "id": random.randint(10000, 99999),
                "user": random.choice(USERS),
                "topic": random.choice(TOPICS),
                "score": random.randint(1, 100),
                "description": random_text(100)
            })

        # Serialize only once per batch
        content = json.dumps(
            data,
            separators=(",", ":")
        )

    path.write_text(
        content,
        encoding="utf-8"
    )


# --------------------------------------------------
# XML
# --------------------------------------------------

def create_xml_file(path, size):
    """
    Create XML efficiently.

    XML elements are generated into a list and joined
    only once.
    """

    # Approximate size of one XML item
    estimated_item_size = 300

    number_of_items = max(
        5,
        size // estimated_item_size
    )

    items = []

    for _ in range(number_of_items):

        item = (
            "<user>"
            f"<id>{random.randint(1000, 9999)}</id>"
            f"<name>{random.choice(USERS)}</name>"
            f"<topic>{random.choice(TOPICS)}</topic>"
            f"<description>{random_text(100)}</description>"
            "</user>"
        )

        items.append(item)

    content = "<users>" + "".join(items) + "</users>"

    # If slightly smaller than requested, add more items.
    while len(content.encode("utf-8")) < size:

        extra_items = []

        for _ in range(500):

            extra_items.append(
                "<user>"
                f"<id>{random.randint(1000, 9999)}</id>"
                f"<name>{random.choice(USERS)}</name>"
                f"<topic>{random.choice(TOPICS)}</topic>"
                f"<description>{random_text(100)}</description>"
                "</user>"
            )

        items.extend(extra_items)

        content = "<users>" + "".join(items) + "</users>"

    path.write_text(
        content,
        encoding="utf-8"
    )


# --------------------------------------------------
# Binary
# --------------------------------------------------

def create_binary_file(path, size):
    """
    Create binary file quickly.
    """

    path.write_bytes(
        random_binary(size)
    )


# --------------------------------------------------
# File Definitions
# --------------------------------------------------

FILE_TYPES = {
    ".txt": create_text_file,
    ".log": create_text_file,
    ".md": create_text_file,
    ".html": create_text_file,
    ".csv": create_csv_file,
    ".json": create_json_file,
    ".xml": create_xml_file,
    ".bin": create_binary_file,
}


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    # Create output directory
    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Remove previously generated files
    for file in DOWNLOAD_DIR.iterdir():

        if file.is_file():
            file.unlink()

    # Random number of files
    number_of_files = random.randint(12, 20)

    extensions = list(FILE_TYPES.keys())

    print(
        f"\nCreating {number_of_files} test files..."
    )

    print(
        f"Location: {DOWNLOAD_DIR}\n"
    )

    for index in range(
        1,
        number_of_files + 1
    ):

        # Random extension
        extension = random.choice(
            extensions
        )

        # Random target size
        size = random_size()

        # Random filename
        filename = (
            f"test_file_{index:02d}_"
            f"{random.randint(1000, 9999)}"
            f"{extension}"
        )

        filepath = DOWNLOAD_DIR / filename

        # Get creator
        creator = FILE_TYPES[extension]

        # Create file
        creator(
            filepath,
            size
        )

        # Actual size
        actual_size = filepath.stat().st_size

        print(
            f"Created: {filename:<40}"
            f"{actual_size / 1024:.2f} KB"
        )

    print("\nDone! 🎉")

    print(
        f"Files created in:\n"
        f"{DOWNLOAD_DIR}"
    )


# --------------------------------------------------
# Entry Point
# --------------------------------------------------

if __name__ == "__main__":
    main()