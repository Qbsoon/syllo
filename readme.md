# Syllo

Installation steps:
 1. Download repo, for example with command "git clone https://github.com/Qbsoon/syllo.git"
 2. Configure environmental variables GROQ_API_KEY and MAIN_ADDR in the ".env" file in "site" directory, based on the ".env.example"
 3. Install required python libraries with command "python -m pip install -r requirements.txt"
 4. Launch with command "python app.py" in the "site" directory
 5. Site will be accesible in the local network under http://[MAIN_ADDR]:51790 address (replace MAIN_ADDR with your value from .env)
Project was tested & run using Python 3.12.3

Optional configuration:
 - You can set remote groq model values in "REMOTE_MODELS" list in app.py. Same for local llama.cpp models in "LOCAL_MODELS"
 - You can adjust default prompt options by modifying if/elif/else structure in the "figure_out" function in the "app.py" file and 'select id="type"' options in html.