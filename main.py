import logging
from pathlib import Path
from typing import Optional
from extract_steps2 import final_command
import google.generativeai as genai
import os
import argparse
from prompt_toolkit import prompt as prompta
from prompt_toolkit.shortcuts import CompleteStyle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('project_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_genai() -> Optional[genai.GenerativeModel]:
    try:
        genai.configure(api_key="<YOURGEMINIAPIKEY")
        model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Successfully initialized Gemini model")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {e}")
        return None

def editable_input(prompt_text: str, default_text: str) -> str:
    """
    Shows a string in the terminal, allows the user to edit it, 
    and then returns the edited string as input.
    """
    try:
        user_input = prompta(
            prompt_text, 
            default=default_text,
            complete_style=CompleteStyle.READLINE_LIKE
        )
        logger.debug(f"Received user input for prompt: {prompt_text}")
        return user_input
    except Exception as e:
        logger.error(f"Error getting user input: {e}")
        return default_text

def main():
    logger.info("Starting project generator")
    parser = argparse.ArgumentParser(description='Project creation')
    parser.add_argument('--p', type=str, required=False, help='Project idea')
    args = parser.parse_args()
    project_idea = args.p

    # Initialize model
    model = setup_genai()
    if not model:
        logger.error("Failed to initialize. Exiting.")
        return

    # Define instructions
    instruction = (
        " instructions: , create as many files as required to complete the task , "
        "Use programming language , packages and framework best suited for implementation in macOS. "
        "Complete, well-documented source code. "
        "Step-by-step terminal commands for creating files, installing dependencies, and running the project. "
        "Organize the code and commands according to steps to be easy to follow. "
        "Only code and commands are expected along with requirements.txt containing dependencies and README.md. "
        "scrap necessary images or urls from internet "
        "only when asked to run project, run in unbuffered mode"
    )

    style = (
        "Style for answer-"
        "At first you should give me the bash commands for creating directories , "
        "files and dependencies of libraries , packages;"
        "If you are writing a file content , strictly make the title of step as : write file_name , "
        "if you are editing or making changes to a file  ,title of step strictly as  : edit file_name , "
        "if you are creating a new file , strict title of step:create file_name "
        "but if you are showing bash commands in a step you must must name the step header as step number :bash commands ;"
        "Bash commands for executing codes if not already given"
    )

    error_instruction = (
        " error_instruction : you have already created the files and directories you wanted in your previous response ,  use problem solving skills to eliminate this errors from your previous code, "
        "Use programming language , packages and framework best suited for implementation in macOS. "
        "Complete, well-documented source code. "
        "Step-by-step terminal commands for creating files, installing dependencies, and running the project. "
        "Organize the code and commands according to steps to be easy to follow. "
        "Only code and commands are expected along with requirements.txt "
    )

    pwd = "pwd : 'paste your current folder path'"

    change_pwd = "changing pwd instructions: change pwd only if said in the task "
    get_pwd = "getting pwd: if prompt is just pwd  , strictly give the pwd  , nothing more nothing less"

    # Get initial prompt
    if not project_idea:
        logger.info("Waiting for user input...")
        print("Enter your prompt: ")
        prompt = input()
    else:
        print("project_idea " , project_idea)
        prompt = project_idea
    prompt = prompt + instruction + style + pwd + change_pwd + get_pwd
    
    # Initialize chat
    chat = model.start_chat()
    history = None
    
    while True:
        try:
            logger.info("Sending prompt to Gemini")
            response = chat.send_message(prompt)
            logger.info("Received response from Gemini")
            
            text = response.parts[0].text
            logger.info("Processing response...")
            
            error = final_command(text)
            
            if error:
                logger.warning(f"Errors occurred during execution: {error}")
            else:
                logger.info("Command execution completed successfully")
            
            history = chat.history
            
            # Get user feedback
            prompt = editable_input("Edit or confirm: ", error)
            if prompt.lower() in ["exit", "quit", "stop"] :
                logger.info("Shutting down...")
                break
            prompt = prompt + error_instruction + style
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.info("Attempting to recover by starting new chat")
            
            result = ""
            chat = model.start_chat()
            
            chat.history = history
                
            try:
                response = chat.send_message(prompt)
                logger.info("Successfully recovered and received new response")
            except Exception as e:
                logger.error(f"Failed to recover: {e}")
                break

if __name__ == "__main__":
    main()
