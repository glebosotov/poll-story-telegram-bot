<div id="top">

<!-- HEADER STYLE: CLASSIC -->
<div align="center">

<img src="./assets/logo.png" width="30%" style="position: relative; top: 0; right: 0;" alt="Project Logo"/>

# POLL-STORY-TELEGRAM-BOT

<em>Interactive stories, powered by AI.</em>

<!-- BADGES -->
<img src="https://img.shields.io/github/license/glebosotov/poll-story-telegram-bot?style=default&logo=opensourceinitiative&logoColor=white&color=0080ff" alt="license">
<img src="https://img.shields.io/github/last-commit/glebosotov/poll-story-telegram-bot?style=default&logo=git&logoColor=white&color=0080ff" alt="last-commit">
<img src="https://img.shields.io/github/languages/top/glebosotov/poll-story-telegram-bot?style=default&color=0080ff" alt="repo-top-language">
<img src="https://img.shields.io/github/languages/count/glebosotov/poll-story-telegram-bot?style=default&color=0080ff" alt="repo-language-count">

</div>
<br>

---

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

poll-story-telegram-bot is a Python-based Telegram bot that generates and posts interactive stories using OpenAI and Google's Gemini APIs, complete with automated scheduling and Dockerized deployment.

**Why poll-story-telegram-bot?**

This project automates the creation and delivery of engaging, AI-powered stories on Telegram. The core features include:

- **🟢 Automated Story Generation:**  Leverages OpenAI and Gemini APIs for seamless and creative story generation, including image creation.
- **🟡 Interactive Narrative:**  Uses polls to guide the story's direction, creating a unique and engaging user experience.
- **🔵 Automated Scheduling:**  A built-in cron job ensures regular story posts at pre-defined times, optimizing content delivery.
- **🔴 Dockerized Deployment:**  Simplifies deployment and ensures consistent execution across various environments.
- **🟣 Robust Configuration:**  Environment variables and a configuration file allow for flexible and easy customization.
- **🟠 CI/CD Integration:**  Automated linting and Docker image publishing streamlines the development workflow.

---

## Project Structure

```sh
└── poll-story-telegram-bot/
    ├── .github
    │   └── workflows
    ├── Dockerfile
    ├── LICENSE
    ├── README.md
    ├── app
    │   ├── config.py
    │   ├── image_gen.py
    │   ├── main.py
    │   ├── open_ai_gen.py
    │   ├── state.py
    │   └── telegram_poster.py
    ├── docker-compose.yml
    ├── entrypoint.sh
    ├── pyproject.toml
    ├── python-cron
    ├── requirements.txt
    ├── run-cron-job.sh
    └── uv.lock
```

---

## Getting Started

### Prerequisites

This project requires the following dependencies:

- **Programming Language:** python
- **Package Manager:** uv, pip
- _[Optional]_ **Container Runtime:** docker

### Installation

Build poll-story-telegram-bot from the source and install dependencies:

1. **Clone the repository:**

    ```sh
    ❯ git clone https://github.com/glebosotov/poll-story-telegram-bot
    ```

2. **Navigate to the project directory:**

    ```sh
    ❯ cd poll-story-telegram-bot
    ```

3. **Install the dependencies:**

 [uv-shield]: <https://img.shields.io/badge/uv-DE5FE9.svg?style=for-the-badge&logo=uv&logoColor=white>
 [uv-link]: <https://docs.astral.sh/uv/>

 **Using [![uv][uv-shield]][uv-link]:**

 ```sh
 ❯ uv sync --all-extras --dev
 ```

 [pip-shield]: https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white
 [pip-link]: https://pypi.org/project/pip/

 **Using  [![pip][pip-shield]][pip-link]:**

 ```sh
 ❯ pip install -r requirements.txt
 ```

### Usage

#### Environment Variables

Setup `.env` file by running:

```sh
cp .env.example .env
```

Then replace the values with your own.

- `BOT_TOKEN`: Your Telegram Bot Token.
- `CHANNEL_ID`: The ID of the Telegram channel where the story will be posted.
- `OPENAI_API_KEY`: Your API key for OpenAI (used for story and image prompt generation).
- `OPENAI_BASE_URL`: The base URL for the OpenAI compatible API (e.g. Together.ai, anyscale, etc.).
- `GEMINI_API_KEY`: Your API key for Google Gemini (used for image generation and Text-to-Speech audio narration). If not provided, image generation and audio narration will be skipped.
- `GEMINI_IMAGE_MODEL`: The specific Gemini image model to use (e.g., `imagen-3.0-generate-002`).
- `IMAGE_PROMPT_START`: A starting phrase or style guide for the image generation prompts.
- `INITIAL_STORY_IDEA`: The initial text or theme to kickstart the story.
- `MAX_CONTEXT_CHARS`: Maximum characters of the current story to feed back into the AI for context.
- `STORY_MAX_SENTENCES`: Approximate maximum number of sentences before the story attempts to conclude.
- `DRY_RUN`: Set to `true` to run the script without actually posting to Telegram or saving state (useful for testing).

#### Running the script

Run the project with:

**Using [docker](https://hub.docker.com/r/glebosotov/poll-story-telegram-bot):**

![Docker Image Version (tag)](https://img.shields.io/docker/v/glebosotov/poll-story-telegram-bot/latest?logo=docker&link=https%3A%2F%2Fhub.docker.com%2Fr%2Fglebosotov%2Fpoll-story-telegram-bot)

This execution type will run on schedule according to the `python-cron` file.

```sh
docker compose up -d
```

**Using [uv](https://docs.astral.sh/uv/):**

```sh
uv run python app/main.py
```

**Using [pip](https://pypi.org/project/pip/):**

```sh
python app/main.py
```

---

## Contributing

- **💬 [Join the Discussions](https://github.com/glebosotov/poll-story-telegram-bot/discussions)**: Share your insights, provide feedback, or ask questions.
- **🐛 [Report Issues](https://github.com/glebosotov/poll-story-telegram-bot/issues)**: Submit bugs found or log feature requests for the `poll-story-telegram-bot` project.
- **💡 Submit Pull Requests**: Review open PRs, and submit your own PRs.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your github account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.

   ```sh
   git clone https://github.com/glebosotov/poll-story-telegram-bot
   ```

3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.

   ```sh
   git checkout -b new-feature-x
   ```

4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.

   ```sh
   git commit -m 'feat: implemented new feature x.'
   ```

6. **Push to github**: Push the changes to your forked repository.

   ```sh
   git push origin new-feature-x
   ```

7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!

</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="left">
   <a href="https://github.com{/glebosotov/poll-story-telegram-bot/}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=glebosotov/poll-story-telegram-bot">
   </a>
</p>
</details>

---

## License

`poll-story-telegram-bot` is protected under the MIT License. For more details, refer to the LICENSE file.

---
