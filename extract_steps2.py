import re
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import threading
import sys
import termios
import tty

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('project_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_key():
    """Capture a single key press from the user."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key

def ask_permission(question: str, required: bool = True) -> bool:
    if required:
        response = input(f"{question} (y/n): ").strip().lower()
        logger.info(f"Permission asked: {question} - Response: {response}")
        return response == 'y'


def create_directory(project_name: str) -> bool:
    try:
        os.makedirs(project_name, exist_ok=True)
        logger.info(f"Directory '{project_name}' created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating directory '{project_name}': {e}")
        return False

def create_file(file_path: str, content: str) -> bool:
    try:
        with open(file_path, 'w') as file:
            file.write(content)
        logger.info(f"File '{file_path}' created successfully")
        return True
    except Exception as e:
        logger.error(f"Error writing file '{file_path}': {e}")
        return False

def run_command(command: str) -> str:
    try:
        logger.info(f"Executing command: {command}")
        print(command)
        if 'python' in command :
            if not ask_permission(f"Do you want to run this command {command}?"):
                return None , None
        result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def check_for_stop():
            """Wait for 'n' key press to terminate the process."""
            while result.poll() is None:  # Process is still running
                key = get_key()
                if key.lower() == 'n':  # If 'n' is pressed
                    print("\nStopping process...")
                    result.terminate()
                    break

        # Run key listener in a separate thread
        listener_thread = threading.Thread(target=check_for_stop, daemon=True)
        listener_thread.start()

        # Stream output line by line
        output = ""
        for line in result.stdout:
            #logger.info(f"Command output: {line.strip()}")
            print(line.strip())
            output += line.strip() + ", "
        _, stderr = result.communicate() 
        result.wait() 
        
        stderr = stderr if stderr else ""
        if stderr:
            logger.warning(f"Command stderr: {stderr}")
        return stderr , output
    except Exception as e:
        logger.error(f"Error running command '{command}': {e}")
        return str(e) , None

def replace_with_number(text: str) -> str:
    matches = list(re.finditer(r'bash command', text))
    i = 0
    for match in matches:
        start, end = match.span()
        text = text[:start] + f'bash command {i}' + text[end:]
        i += 1
    logger.debug(f"Replaced {len(matches)} bash command occurrences")
    return text

def extract_steptitles(text: str) -> Tuple[List[str], List[str]]:
    steps = r'(\*\*Step \d+: .+?\*\*)\n(.*?)(?=\n\*\*Step \d+:|$)'
    matches = re.findall(steps, text, re.DOTALL)
    step_titles = []
    step_details = []
    
    for match in matches:
        step_title, step_detail = match
        step_titles.append(step_title.strip())
        step_details.append(step_detail.strip())
    
    logger.info(f"Extracted {len(step_titles)} steps from text")
    return step_titles, step_details

def extract_code_snippets(step_details: List[str]) -> List[List[str]]:
    all_snippets = []
    for i, detail in enumerate(step_details):
        snippets = re.findall(r'`{3}(.*?)`{3}', detail, re.DOTALL)
        all_snippets.append(snippets)
        logger.debug(f"Step {i+1}: Found {len(snippets)} code snippets")
    return all_snippets

def extract_filename(text: str) -> Optional[str]:
    match = re.search(r'\b([\w\-/]+\/[\w\-]+\.\w+|[\w\-]+\.\w+)\b', text)
    if match:
        filename = match.group(1)
        logger.debug(f"Extracted filename: {filename}")
        return filename
    return None

def extract_bash_commands(text: str) -> List[str]:
    pattern = r'bash\n([\s\S]+?)(?=\n\s*\n|$)'
    matches = re.findall(pattern, text)
    commands = []
    for match in matches:
        cmds = [cmd.strip() for cmd in match.splitlines() if cmd.strip()]
        commands.extend(cmds)
    logger.debug(f"Extracted {len(commands)} bash commands")
    return commands

def delete_first_line(text: str) -> Tuple[str, Optional[str]]:
    lines = text.splitlines()
    line = None
    if lines:
        line = lines.pop(0)
    return '\n'.join(lines), line

def run_commands(step_titles: List[str], code_snippets: List[List[str]] , created_directory_name) -> str:
    command_list = []
    current_directory = Path.cwd()
    errors = ''
    
    logger.info(f"Starting command execution from directory: {current_directory}")
    x = 0 
    
    for i, step_title in enumerate(step_titles):
        logger.info(f"Processing step {i+1}: {step_title}")
        for code_snippet in code_snippets[i]:
            content, keyword = delete_first_line(code_snippet)
            if keyword and ('bash' in step_title.lower() or 'bash' in keyword.lower()):
                commands = extract_bash_commands(code_snippet)
                for command in commands:
                    if command.startswith('cd '):
                        new_dir = command[2:].strip()
                        current_directory = os.path.join(current_directory, new_dir)
                        os.chdir(current_directory)
                        logger.info(f"Changed directory to: {current_directory}")
                    else:
                        if 'mkdir' in command and created_directory_name is not None and  created_directory_name in command :
                            continue
                        if 'cd' in command and created_directory_name is not None and  created_directory_name in command :
                            continue
                        error , _ = run_command(command)
                        if error:
                            errors += f"Error in step {i+1}: {error}\n"
                    if x == 0  and commands is not None and created_directory_name is None:
                        created_directory_name = commands[0].replace('mkdir', '').strip()
                        x = 1
        

            else:
                filename = extract_filename(step_title)
                if filename:
                    full_path = os.path.join(current_directory, filename)
                    if not create_file(full_path, content):
                        errors += f"Error in step {i+1}: Failed to create file {filename}\n"
    
    return errors , created_directory_name

def final_command(text: str) -> str:
    created_directory_name = None
    logger.info("Starting project creation process")
    step_titles, step_details = extract_steptitles(text)
    code_snippets = extract_code_snippets(step_details)
    errors , created_directory_name = run_commands(step_titles, code_snippets , created_directory_name)
    
    if errors:
        logger.error("Project creation completed with errors")
        logger.error(errors)
    else:
        logger.info("Project creation completed successfully")
    
    return errors

if __name__ == "__main__":
    logger.info("Starting script execution")
    file_name = '/Users/krisanusarkar/Documents/ML/unt/codedetails3.txt'
    try:
        with open(file_name, 'r') as file:
            text = file.read()
        errors  = final_command(text)
        print("Execution completed. Check project_creation.log for details.")
        if errors:
            print("Errors occurred during execution:")
            print(errors)
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
