# main.py

import hashlib
import os
import sys
import requests
import zipfile
import io
from dotenv import load_dotenv
from typing import List
import shutil
from prompts import *
from pydantic import BaseModel
from typing import Literal
from langchain_openai import AzureChatOpenAI

load_dotenv()

# Azure OpenAI configuration
aoai_deployment = os.getenv("AOAI_DEPLOYMENT")
aoai_key = os.getenv("AOAI_KEY")
aoai_endpoint = os.getenv("AOAI_ENDPOINT")


# Constants
STATIC_PATH = 'cloned_repos'  # Directory to store cloned repositories
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB for large data files

class ExtractionResponse(BaseModel):
    """Schema for parsing project title and description"""
    project_name: str
    project_description: str
    programming_languages: List[str]
    frameworks: List[str]
    azure_services: List[str]
    design_patterns: List[str]
    project_type: str
    code_complexity_score: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    business_value: str 
    target_audience: str

primary_llm = AzureChatOpenAI(
    azure_deployment=aoai_deployment,
    api_version="2024-08-01-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=aoai_key,
    azure_endpoint=aoai_endpoint
)

# File extensions to exclude
EXCLUDED_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.bmp', '.tiff',
    # Audio
    '.mp3', '.wav', '.flac', '.aac',
    # Video
    '.mp4', '.avi', '.mov', '.mkv',
    # Archives
    '.zip', '.rar', '.tar.gz', '.7z',
    # Binary Files
    '.exe', '.dll', '.so', '.obj'
}

def load_environment():
    """
    Loads environment variables from a .env file.
    """
    load_dotenv()

def generate_unique_id(github_url: str) -> str:
    """
    Generates a unique ID for the repository based on its GitHub URL.

    :param github_url: URL of the GitHub repository
    :return: MD5 hash as a hexadecimal string
    """
    return hashlib.md5(github_url.encode()).hexdigest()

def sanitize_github_url(url: str) -> str:
    """
    Validates and sanitizes the GitHub URL.

    :param url: Input GitHub URL
    :return: Sanitized GitHub URL
    :raises ValueError: If the URL is invalid
    """
    if not url.startswith("https://github.com/"):
        raise ValueError("Invalid GitHub URL. It should start with 'https://github.com/'.")
    return url.rstrip('/')

def download_zip(github_url: str) -> bytes:
    """
    Downloads the ZIP archive of the default branch of the GitHub repository.

    :param github_url: Sanitized GitHub repository URL
    :return: Bytes content of the ZIP archive
    :raises Exception: If the download fails
    """
    zip_url = f"{github_url}/archive/HEAD.zip"
    try:
        print(f"Downloading repository from {zip_url}...")
        response = requests.get(zip_url, timeout=30)
        response.raise_for_status()
        print("Download successful.")
        return response.content
    except requests.RequestException as e:
        raise Exception(f"Failed to download repository ZIP: {e}") from e

def extract_zip(zip_content: bytes, extract_to: str):
    """
    Extracts the ZIP archive to the specified directory.

    :param zip_content: Bytes content of the ZIP archive
    :param extract_to: Path to extract the ZIP contents
    :raises Exception: If extraction fails
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            z.extractall(extract_to)
        print(f"Repository extracted to {extract_to}")
    except zipfile.BadZipFile as e:
        raise Exception(f"Failed to extract ZIP archive: {e}") from e
    except Exception as e:
        raise Exception(f"An error occurred during extraction: {e}") from e

def is_excluded(file_path: str) -> bool:
    """
    Determines if a file should be excluded based on its extension or size.

    :param file_path: Path to the file
    :return: True if the file should be excluded, False otherwise
    """
    _, ext = os.path.splitext(file_path.lower())
    if ext in EXCLUDED_EXTENSIONS:
        # For large data files, check size
        if ext in {'.csv', '.xlsx', '.sql', '.json'}:
            try:
                size = os.path.getsize(file_path)
                if size > MAX_FILE_SIZE:
                    return True
            except OSError:
                # If file size can't be determined, exclude it as a precaution
                return True
        return True
    return False

def list_files(directory: str) -> List[str]:
    """
    Lists all files in the directory, excluding specified file types and large files.

    :param directory: Root directory to traverse
    :return: List of included file paths
    """
    excluded_files = []
    included_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_excluded(file_path):
                excluded_files.append(file_path)
            else:
                included_files.append(file_path)

    # Optionally, you can print the included and excluded files
    print("\n### Included Files ###\n")
    for file in included_files:
        print(os.path.relpath(file, directory))

    print("\n### Excluded Files ###\n")
    for file in excluded_files:
        print(os.path.relpath(file, directory))

    return included_files

def combine_files(file_paths: List[str], base_directory: str) -> str:
    """
    Combines filenames and their contents into a formatted string.

    :param file_paths: List of file paths to include
    :param base_directory: Base directory to calculate relative paths
    :return: Formatted string containing all filenames and their contents
    """
    combined_output = ""

    for file_path in file_paths:
        relative_path = os.path.relpath(file_path, base_directory)
        combined_output += f"<File: {relative_path}>\n"

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try a different encoding or skip the file
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
            except Exception as e:
                content = f"Could not read file due to encoding issues: {e}"
        except Exception as e:
            content = f"Could not read file: {e}"

        combined_output += f"{content}\n{'-'*80}\n"

    return combined_output

def clone_repository(github_url: str) -> str:
    """
    Clones a public GitHub repository by downloading and extracting its ZIP archive.

    :param github_url: Sanitized GitHub repository URL
    :return: Path to the actual cloned repository root (without hash)
    :raises Exception: If cloning fails
    """
    unique_id = generate_unique_id(github_url)
    local_path = os.path.join(STATIC_PATH, unique_id)

    # Check if the repository is already cloned
    if os.path.exists(local_path):
        print(f"Repository already cloned at {local_path}")
    else:
        # Download ZIP archive
        zip_content = download_zip(github_url)

        # Extract ZIP archive
        extract_zip(zip_content, local_path)

    # After extraction, identify the actual repository root directory
    # Typically, it's the first directory inside local_path
    try:
        entries = os.listdir(local_path)
        # Filter out any non-directory entries
        directories = [entry for entry in entries if os.path.isdir(os.path.join(local_path, entry))]
        if not directories:
            raise Exception("No directory found after extracting the ZIP archive.")
        elif len(directories) == 1:
            actual_repo_path = os.path.join(local_path, directories[0])
            print(f"Actual repository path identified: {actual_repo_path}")
            return actual_repo_path
        else:
            # If multiple directories are found, handle accordingly
            # For simplicity, we'll take the first one
            actual_repo_path = os.path.join(local_path, directories[0])
            print(f"Multiple directories found. Using the first one: {actual_repo_path}")
            return actual_repo_path
    except Exception as e:
        raise Exception(f"Failed to identify the repository root directory: {e}") from e

def cleanup_repository(path: str):
    """
    Removes the cloned repository directory.

    :param path: Path to the cloned repository
    """
    try:
        shutil.rmtree(path)
        print(f"Cleaned up repository at {path}")
    except Exception as e:
        print(f"Failed to clean up repository at {path}: {e}")

def main(github_url: str):
    """
    Main function to clone repository, combine file contents, and prepare for LLM.

    :param github_url: GitHub repository URL
    """
    try:
        # Load environment variables
        load_environment()

        # Sanitize and validate GitHub URL
        github_url = sanitize_github_url(github_url)

        # Clone the repository and get the actual repository path
        cloned_repo_path = clone_repository(github_url)

        # List files excluding specified extensions and large files
        print(f"\nListing files in the cloned repository at {cloned_repo_path}...")
        included_files = list_files(cloned_repo_path)

        print(f"Number of included files: {len(included_files)}")

        if not included_files:
            print("No files to process.")
        else:
            # Combine filenames and contents into a formatted string
            print("Combining file contents...")
            formatted_input = combine_files(included_files, cloned_repo_path)
            print("Combination successful.")
            print("\n### Formatted Input for LLM ###\n")
            print(formatted_input)
            open("codebase.txt", 'w', encoding='utf-8').write(formatted_input)

            # Prepare messages for the LLM
            messages = [
                {"role": "system", "content": review_prompt },
                {"role": "user", "content": formatted_input}
            ]

            report_llm = primary_llm.with_structured_output(ExtractionResponse)

            response = report_llm.invoke(messages)
            print(response)

            # For demonstration purposes, we'll just print a confirmation
            print("\nFormatted input is ready for the LLM.")

        # Clean up the local folder
        cleanup_repository(os.path.dirname(cloned_repo_path))  # Adjusted to remove the unique_id folder

    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    github_url = "https://github.com/DanGiannone1/samples"
    #github_url = "https://github.com/DanGiannone1/rfp_accelerator"
    main(github_url)
