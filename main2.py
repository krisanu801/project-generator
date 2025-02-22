import os
import json
import typer
import subprocess
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.traceback import install
from rich.logging import RichHandler
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import time
import logging
import sys
from typing import Dict, List, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential

# Install rich traceback handler
install(show_locals=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_time=True)]
)
log = logging.getLogger("project_generator")

# Initialize Typer app and Rich console
app = typer.Typer()
console = Console()

def initialize_genai() -> Optional[genai.GenerativeModel]:
    """Initialize the Google Generative AI model with detailed error handling."""
    try:
        # Load environment variables
        load_dotenv()
        
        api_key = "<YOURGEMINIAPIKEY>"
        if not api_key:
            log.error("GOOGLE_API_KEY environment variable not found")
            return None
            
        # Configure Gemini
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            log.error(f"Failed to configure Gemini AI: {str(e)}")
            return None
            
        # Create model instance
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            chat = model.start_chat()
            return chat
        except Exception as e:
            log.error(f"Failed to create Gemini model instance: {str(e)}")
            return None
            
    except Exception as e:
        log.error(f"Unexpected error during Gemini initialization: {str(e)}")
        return None

class ProjectStructureError(Exception):
    """Custom exception for project structure validation errors."""
    pass

class ProjectGenerator:
    def __init__(self):
        """Initialize ProjectGenerator with detailed error checking."""
        try:
            self.generated_path = Path("generated")
            self.generated_path.mkdir(exist_ok=True)
            
            log.info("Initializing Gemini AI...")
            self.chat = initialize_genai()
            
            if not self.chat:
                raise RuntimeError("Failed to initialize Gemini AI model")
                
            log.info("ProjectGenerator initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize ProjectGenerator: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_genai_request(self, prompt: str) -> str:
        """Make a request to Gemini AI with improved response handling."""
        if not self.chat:
            raise RuntimeError("Gemini AI model not initialized")
            
        try:
            log.debug(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            response = self.chat.send_message(
                prompt,
                generation_config={
                    'temperature': 0.2,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            
            if not response or not response.text:
                raise ValueError("Empty response received from Gemini")
                
            log.debug(f"Received response from Gemini (length: {len(response.text)} chars)")
            return response.text
            
        except Exception as e:
            log.error(f"Gemini AI request failed: {str(e)}")
            log.debug(f"Prompt that caused the error: {prompt[:200]}...")
            raise

    def generate_project_structure(self, project_name: str, project_description: str) -> Optional[Dict]:
        """Generate project structure with improved content generation."""
        if not project_name or not project_description:
            log.error("Project name and description are required")
            return None

        log.info(f"Generating project structure for: {project_name}")
        self.project_name = project_name
        
        
        prompt = f"""
        Create a detailed project structure for a Python project named: {project_name}
        Project Description: {project_description}
        
        The response must be a valid JSON object with this structure:
        {{
            "project_name": "{project_name}",
            "description": "{project_description}",
            "structure": {{
                "directories": [
                    "test",
                    "configs",
                    "logs",
                    "data"
                ],
                "files": [
                    {{
                        "name": "main.py",
                        "path": "path of the directory you want it to be",
                        "content": "",
                        "description": "Main application file"
                    }}
                ]
            }},
            "setup_instructions": [
                "Create virtual environment",
                "Install dependencies"
            ],
            "dependencies": {{
                "python": [
                    "requests==2.31.0"
                ]
            }}
        }}

        Include:
        1. All necessary Python files
        5. Requirements file
        6. README.md
        7. Setup files
        8. CI/CD configuration if needed
        9. Environment configuration
        10. Logging configuration

        Ensure:
        1. All paths use forward slashes 
        2. Leave file content empty - it will be generated separately
        3. Provide clear descriptions for each file
        """
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Generating project structure...", total=None)
                response_text = self._make_genai_request(prompt)
                progress.update(task, completed=True)
            
            try:
                # Clean up the response text
                json_str = response_text.strip()
                if json_str.startswith('```json'):
                    json_str = json_str[7:]
                if json_str.endswith('```'):
                    json_str = json_str[:-3]
                
                # Parse the JSON response
                project_data = json.loads(json_str)
                log.info("Successfully parsed project structure")
                self.project_data = project_data
                return project_data
                
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse Gemini API response: {str(e)}")
                log.debug(f"Raw response: {response_text}")
                return None
                
        except Exception as e:
            log.error(f"Error generating project structure: {str(e)}")
            return None

    def generate_file_content(self, file_path: Path, file_description: str) -> str:
        """Generate specific content for a file using Gemini AI."""
        try:
            file_type = file_path.suffix.lstrip('.')
            prompt = f"""
            Generate content for a {file_type} file with the following details:
            File name: {file_path.name}
            File location: {file_path.parent.name}
            Purpose: {file_description}
            
            Requirements:
            1. Generate complete, working code
            2. Include proper imports
            3. Ensure **local imports work correctly in any folder structure**:
                - Dynamically adjust `sys.path` to allow imports from the project root.
                - Avoid assuming directories are Python packages.
            4. Add error handling
            5. Add logging
            6. Add type hints (for Python)
            7. Add docstrings (for Python) or JSDoc (for JavaScript)
            8. Follow best practices for the file type
            8. Include example usage in comments
            
            
            Return ONLY the file content, no explanations or markdown formatting.
            """
            
            content = self._make_genai_request(prompt)
            
            # Clean up the content
            content = content.strip()
            if content.startswith('```') and content.endswith('```'):
                content = content[content.find('\n')+1:content.rfind('```')].strip()
                
            return content
            
        except Exception as e:
            log.error(f"Failed to generate content for {file_path}: {str(e)}")
            return f"# TODO: Implement {file_path.name}\n# Purpose: {file_description}\n"

    def create_project_files(self, project_data: Dict) -> Optional[Path]:
        """Create project files and directories from the generated structure."""
        if not project_data:
            log.error("No project data provided")
            return None

        try:
            project_path = self.generated_path / self._sanitize_path(project_data['project_name'])
            log.info(f"Creating project at: {project_path}")
            
            # Create project directory
            project_path.mkdir(exist_ok=True)
            
            # Create directories first
            self._create_directories(project_path, project_data['structure']['directories'])
            
            # Then create files
            self._create_files(project_path, project_data['structure']['files'])
            
            return project_path
            
        except Exception as e:
            log.error(f"Error creating project files: {str(e)}")
            return None

    def _create_directories(self, base_path: Path, directories: List[str]) -> None:
        """Create all project directories."""
        for directory in directories:
            try:
                dir_path = base_path / directory                
                dir_path.mkdir(parents=True, exist_ok=True)
                log.debug(f"Created directory: {dir_path}")
            except Exception as e:
                log.error(f"Failed to create directory {directory}: {str(e)}")

    def _create_files(self, base_path: Path, files: List[Dict]) -> None:
        """Create all project files with proper content generation."""
        for file_info in files:
            try:
                file_name = file_info['name']
                file_path = base_path / file_info['path']
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if '.' not in Path(file_path).parts[-1]:
                    file_path = file_path / file_name
                    
                # Skip binary files
                if file_path.suffix.lower() in ['.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe']:
                    log.debug(f"Skipping binary file: {file_path}")
                    continue
                
                # Generate content for the file
                log.info(f"Generating content for: {file_path}")
                content = self.generate_file_content(file_path, file_info['description'])
                
                if not content.strip():
                    log.warning(f"Empty content generated for {file_path}")
                    content = f"# TODO: Implement {file_name}\n# Purpose: {file_info['description']}\n"
                
                # Write the content to the file
                log.debug(f"Writing content to {file_path} (size: {len(content)} chars)")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                log.info(f"Created file: {file_path}")
                
            except Exception as e:
                log.error(f"Failed to create file {file_info['path']}: {str(e)}")


    def _edit_files(self, file_path , content) -> None:
        """Create all project files with proper content generation."""
        try:
                # Write the content to the file
            log.debug(f"editing content to {file_path} (size: {len(content)} chars)")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            log.info(f"Created file: {file_path}")
                
        except Exception as e:
                log.error(f"Failed to edit file {file_path}: {str(e)}")

    def _sanitize_path(self, path: str) -> str:
        """Sanitize file/directory path."""
        if not path:
            return ""
        
        # Remove potentially dangerous characters and normalize path
        sanitized = Path(path).parts[-1]  # Take only the filename/dirname
        sanitized = "".join(c for c in sanitized if c.isalnum() or c in "._-/")
        sanitized = sanitized.replace(' ', '_').lower()
        
        # Ensure the path doesn't try to navigate up directories
        if '..' in sanitized:
            sanitized = sanitized.replace('..', '')
            
        return sanitized

    def _validate_project_structure(self, project_data: Dict) -> bool:
        """Validate the project structure data."""
        try:
            required_fields = {
                'project_name': str,
                'description': str,
                'structure': dict,
                'setup_instructions': list,
                'dependencies': dict
            }

            for field, expected_type in required_fields.items():
                if field not in project_data:
                    raise ProjectStructureError(f"Missing required field: {field}")
                if not isinstance(project_data[field], expected_type):
                    raise ProjectStructureError(
                        f"Invalid type for {field}: expected {expected_type.__name__}, "
                        f"got {type(project_data[field]).__name__}"
                    )

            structure = project_data['structure']
            if not all(key in structure for key in ['directories', 'files']):
                raise ProjectStructureError("Structure must contain 'directories' and 'files'")

            return True
            
        except ProjectStructureError as e:
            log.error(f"Project structure validation failed: {str(e)}")
            return False
        except Exception as e:
            log.error(f"Unexpected error during validation: {str(e)}")
            return False


    def delete_empty_files_and_folders(self, project_data: Dict) -> Dict:
        """Delete empty files and folders from the project directory and update project_data accordingly."""
        try:
            project_path = self.generated_path / self._sanitize_path(project_data['project_name'])

            # Remove empty files
            updated_files = []
            for file_info in project_data['structure']['files']:
                file_path = project_path / self._sanitize_path(file_info['path'])
                if file_path.is_file():
                    if file_path.stat().st_size == 0:
                        log.info(f"Deleting empty file: {file_path}")
                        file_path.unlink()
                else:
                    updated_files.append(file_info)  # Keep only non-empty files

            # Remove empty directories (starting from the deepest)
            updated_dirs = []
            for directory in sorted(project_data['structure']['directories'], key=lambda d: -len(d.split('/'))):
                dir_path = project_path / self._sanitize_path(directory)
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    log.info(f"Deleting empty directory: {dir_path}")
                    dir_path.rmdir()
                else:
                    updated_dirs.append(directory)  # Keep only non-empty directories

            # Update project_data to reflect remaining files and directories
            project_data['structure']['files'] = updated_files
            project_data['structure']['directories'] = updated_dirs

            log.info("Cleanup completed: Removed all empty files and folders.")

            return project_data  # Return updated project structure

        except Exception as e:
            log.error(f"Error during cleanup: {str(e)}")
            return project_data  # Ensure project_data is always returned

    def run_project(self, project_name: str, project_data: Dict) -> None:
            """Attempt to run the generated project, handling errors and dependencies."""
            #log.info(f"Running project from: {project_path}")

            prompt = f"""
            Generate terminal commands for running the project in MacOS cpu from: {project_data},

            **do not create conda envirnoments   , use venv
            Return ONLY the commands, no explanations or markdown formatting.
            """
            
            content = self._make_genai_request(prompt)

            command = f"cd /Users/krisanusarkar/Documents/ML/unt/generated/{project_name} &&"
            
            # Clean up the content
            print(content)
            content = content.strip()
            if content.startswith('```') and content.endswith('```'):
                content = content[content.find('\n')+1:content.rfind('```')].strip()
                content = content.replace("\n", "&&")
            command = command + content

            result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = ""
            for line in result.stdout:
                #logger.info(f"Command output: {line.strip()}")
                print(line.strip())
                output += line.strip() + ", "

            _, stderr = result.communicate()
            
            if result.returncode != 0:
                console.print(f"[red]Failed to run project. Check the logs for details.[/red]")
                self.correct_errors(stderr.strip())
                
            else:
                console.print(f"[green]Project run successfully.[/green]")
                console.print("\n[bold yellow]Anything you want to implement more? (Press Enter to run, or type 'no' to skip)[/bold yellow]")
                user_input = input().strip().lower()
                self.update_project(user_input)
                if user_input.lower() != "no":
                    return 


    def correct_errors(self , error):
        print(error)
        prompt = f"""
            1.edit precreated files from {self.project_data}content needed to correct the errors:{error}
            in already given format to write file content
            2.edit content properly remembering past commands
            3.The response must be a valid JSON object with this structure:
            files : [
                {{
                        "file_path": "path of the file along with file name",
                        "content": " content code",
                }}
            ]
            
            """
        user_input= input("Enter your prompt: ")
        if user_input:
            prompt += user_input
        response = self._make_genai_request(prompt)
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        response = json.loads(response)
        print(response)
        for file in  response['files'] :
            file_path = file['file_path']
            file_path = self.generated_path /self.project_name / file_path
            content = file['content']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            print(f'editing {file_path}')
            self._edit_files(file_path, content)
        self.run_project(self.project_name, self.project_data)

    def update_project(self  , user_input):
        print(user_input)
        prompt = f"""
            1.edit precreated files from {self.project_data}content needed to make this updates:{user_input}
            in already given format to write file content
            2.edit content properly remembering past commands
            3.The response must be a valid JSON object with this structure:
            files : [
                {{
                        "file_path": "path of the file along with file name",
                        "content": " content code",
                }}
            ]
            
            """
        user_input= input("Enter your prompt: ")
        if user_input:
            prompt += user_input
        response = self._make_genai_request(prompt)
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        response = json.loads(response)
        print(response)
        for file in  response['files'] :
            file_path = file['file_path']
            file_path = self.generated_path /self.project_name / file_path
            content = file['content']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            print(f'editing {file_path}')
            self._edit_files(file_path, content)
        self.run_project(self.project_name, self.project_data)



@app.command()
def generate(
    name: str = typer.Option(..., "--name", "-n", help="Name of the project"),
    description: str = typer.Option(..., "--desc", "-d", help="Brief description of the project")
):
    """Generate a new project with comprehensive error handling."""
    try:
        log.info(f"Starting project generation for '{name}'")
        generator = ProjectGenerator()
        
        with console.status("[bold green]Generating project structure...") as status:
            project_data = generator.generate_project_structure(name, description)
            
            if not project_data:
                log.error("Project structure generation failed")
                console.print("[red]Failed to generate project structure. Check the logs for details.[/red]")
                raise typer.Exit(1)
                
            status.update("[bold green]Creating project files...")
            project_path = generator.create_project_files(project_data)
            
            if not project_path:
                log.error("Project file creation failed")
                console.print("[red]Failed to create project files. Check the logs for details.[/red]")
                raise typer.Exit(1)
            
            #generator.delete_empty_files_and_folders(project_path)
            
            console.print(f"\n[bold green]✓[/bold green] Project created successfully at: {project_path}")
            
            # Display setup instructions
            console.print("\n[bold]Setup Instructions:[/bold]")
            for i, step in enumerate(project_data['setup_instructions'], 1):
                console.print(f"{i}. {step}")

            # Ask if the user wants to run the project
            console.print("\n[bold yellow]Do you want to run the project? (Press Enter to run, or type 'no' to skip)[/bold yellow]")
            user_input = input().strip().lower()
            
            if user_input == "" or user_input == "yes":
                log.info(f"Running project from: {project_path}")
                generator.run_project(name , project_data)

            

    except Exception as e:
        log.error(f"Project generation failed: {str(e)}")
        console.print(f"[red]Error: Project generation failed. Check the logs for details.[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
