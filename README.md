# Google Voice GPT Translator

This repository contains a Python project that interprets Google Voice SMS threads using a GPT-4 model. The project listens to incoming and outgoing Google Voice messages and translates them via the GPT-4 model.

This is a utilitarian approach that launches the Google Voice UI, allowing to authenticate and select a message thread in a low-tech manner. It uses [chatgpt-wrapper](https://github.com/mmabrouk/chatgpt-wrapper) as a stateful client for the GPT-4 API. 

Functionally, it expects the selected message thread to be between two interlocutors writing in their respective languages. It'll detect the languages of each incoming and outcoing messages. You may simply leave this script running on your Linux host, and do the text messaging with the Google Voice app.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

The project uses a number of Python packages which are listed in `environment.yaml`.

To create an environment named `myenv` with these packages, use the command below:

```sh
conda env create -f environment.yaml -n myenv
```

It uses [chatgpt-wrapper](https://github.com/mmabrouk/chatgpt-wrapper) to interface with the OpenAI api. Use their CLI to create a profile and copy/edit the included template.

### Running the Project

Before running the script, activate the `myenv` environment:

```sh
conda activate myenv
```

Review the constants in `main.py` including references to your `chatgpt-wrapper` profile. 

You can then run the script:

```sh
python main.py
```

Upon running the script, Firefox whould open, log in to Google Voice and select a message thread. The program will translate existing messages and watch for new ones, translating and sending the results back into the conversation. The conversation will be printed in the terminal.

If the number of tokens in the GPT-4 conversation exceeds the limit, a new conversation will be created and the old context will be lost.

## Contribution guidelines

If you want to contribute to this project and make it better, your help is very welcome. Create a pull request with your suggested changes.
