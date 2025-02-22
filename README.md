# project-generator

## Overview
This project automates the creation of well-structured project directories, files, and dependencies using a generative AI model (Gemini). It provides step-by-step terminal commands and complete source code tailored for macOS environments.

## Features
- Automatic generation of project structure and files
- Intelligent code and command generation using Google Gemini AI
- Logs activities and errors for debugging
- User-editable inputs for customization
- Supports dependency management with `requirements.txt`

## Installation
### Prerequisites
Ensure you have the following installed:
- Python 3.8+
- pip (Python package manager)

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/project-generator.git
   cd project-generator
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### Running the Project Generator
To start the project generator, run:
```bash
python main.py --p "Your project idea here"
```
If no argument is provided, the script will prompt you for input.

### Logs
Execution logs are stored in `project_generator.log` for debugging purposes.

### Editing Inputs
The script provides an editable prompt interface where users can modify the generated commands before execution.

## File Structure
```
project-generator/
├── main2.py                 # Main script
├── extract_steps.py        # Handles extracted commands
├── requirements.txt        # Dependencies
├── project_generator.log   # Log file
├── README.md               # Project documentation
├── LICENSE                 # MIT License file
```

## Troubleshooting
- **Failed to initialize Gemini model**: Ensure your API key is correct and valid.
- **Errors in generated commands**: Review and edit using the interactive input prompt.
- **Permission errors**: Run the script with appropriate permissions (`sudo` if necessary).

## Sample results
- **gemini voice bot in the folder was created by this generator , it took only one command to make it a voicebot.

## Contributing
Feel free to fork this repository and submit pull requests to improve functionality.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

