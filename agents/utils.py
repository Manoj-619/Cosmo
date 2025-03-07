import os
import fitz

def walk_dir(path, keyword="", extension=".pdf"):
    """
    Crawls through local directory `path`.
    Searches for files with `keyword`.
    Filters for files that end with `Format`
    Returns list of files with their absolute paths.
    """
    list_of_files = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if (filename.endswith(extension)) & (str(keyword) in filename):
                list_of_files.append(os.path.join(dirpath, filename))
    list_of_files.sort()
    return list_of_files

def get_prompt(prompt_file, context={}, prompt_dir="assets/prompts"):
    """Load a prompt from a file and format it with a context.

    Args:
        prompt_file (str): Name of the prompt file.
        context (dict, optional): Context to format the prompt with. Defaults to {}.
        prompt_dir (str, optional): Path to the prompt directory. Defaults to 'assets/prompts'.

    Returns:
        str: prompt
    """
    # if extension is not .md, add it
    if not prompt_file.endswith(".md"):
        prompt_file += ".md"
    prompt_path = os.path.join(prompt_dir, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    if context:
        prompt = prompt.format(**context)
    return prompt

def extract_text(pdf_path):
    """Extracts text from a PDF and organizes it into sections."""
    doc = fitz.open(pdf_path)

    text = '\n'.join([page.get_text("text") for page in doc])
    return text.strip()