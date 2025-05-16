# Verification Discord Bot

A Discord bot designed to handle user verification, self-assignable roles, and logging for Discord servers. This bot uses `discord.py` and `SQLAlchemy` for seamless integration with Discord and database management.

## Table of Contents
- [Features](#features)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Inviting the Bot to Your Server](#inviting-the-bot-to-your-server)
  - [Running the Bot](#running-the-bot)
- [Modules](#modules)
- [Commands](#commands)
  - [Slash Commands](#slash-commands)
  - [Text Commands](#text-commands)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Features

- **Age Verification**: Users can verify their age using a modal form.
- **Self-Assignable Roles**: Configure and manage self-assignable roles with dropdown menus.
- **Logging**: Logs verification events to a designated channel.
- **Persistent Views**: Ensures dropdown menus and buttons persist across bot restarts.
- **Slash Commands**: Modern and user-friendly slash commands for configuration and management.

## Setup

### Prerequisites

- Python 3.11
- A Discord bot token:
    1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    2. Click on "New Application" and give it a name.
    3. Navigate to the "Bot" tab, click "Add Bot," and confirm.
    4. Under the "Bot" section, copy the token. **Keep this token private!**
- Required Python packages (see `requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/DIRECTVIRUS/verification-discord-bot.git
   cd verification-discord-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
   You should see `(venv)` in your terminal prompt, indicating that the virtual environment is active.

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a folder named `config` in the root directory of the project.

5. Create a file named `config.yml` in the `config` folder and add the following content:
   ```yaml
   TOKEN: YOUR_DISCORD_BOT_TOKEN
   ```
   Replace `YOUR_DISCORD_BOT_TOKEN` with the token you copied from the Discord Developer Portal.

## 

## Inviting the Bot to Your Server

1. Go to the [OAuth2 URL Generator](https://discord.com/developers/applications/YOUR_APPLICATION_ID/oauth2/url-generator) in the Discord Developer Portal.
2. Select the `bot` and `applications.commands` scopes.
   - `Send Messages`
   - `Manage Roles`
   - `Read Message History`
   - `View Channels`

   alternatively you can use the following permissions:
   - `Administrator`

4. Copy the generated URL and paste it into your browser.
5. Select the server you want to add the bot to and authorize it.
6. Make sure the bot has the necessary permissions in your server.

## running the bot
1. Make sure your virtual environment is activated.
2. Run the bot:
   ```bash
   python main.py
   ```
3. The bot should now be online in your server.
4. as the owner do l!sync to sync the slash commands with discord.
5. You can now use the bot's commands and features. (a restart of your client to see the slash commands)

## modules
- verification.py: Handles user verification, including age verification and logging.
- selfroles.py: Manages creation and management of self-assignable roles.
- selfroles_db.py: Database management for self-assignable roles.
- logging.py: Handles logging of verification events.
- verification.py: Handles user verification, including age verification and logging.
- bot.py: Main bot setup and command handling.

## Commands

### Slash Commands

- `/set_channels`: Configure the verification channel, log channel, and verified role.
- `/send_verification`: Send the verification button in the configured channel.
- `/clear_verification`: Clear a user's verification record.
- `/check_verification`: Check the verification status of a user.
- `/show_verification_config`: Show the current verification configuration.
- `/set_selfroles`: Configure self-assignable roles for the server.
- `/send_selfroles`: Send the self-roles message in a specified channel.
- `/delete_selfroles`: Delete a self-roles configuration.
- `/list_selfroles`: List all self-role configurations for the server.
- `/show_selfrole_config`: Show the self-role configuration for a specific message.

### Text Commands

- `l!ping`: Check the bot's latency.
- `l!sync`: Sync slash commands globally (owner only).
- `l!restart`: Restart the bot (owner only).

### **Note**: restart will not restart the bot unless you have a process manager like pm2 or systemd to run the bot.py file when the process is killed. an example unit file for systemd is provided in the [docs](docs/systemd.md) folder, however you can use any process manager you like.


## license
This project is licensed under the MIT License. See the [LICENSE](licence.md) file for details.

## acknowledgements
- [discord.py](https://discordpy.readthedocs.io/en/stable/) for the Discord API wrapper.
- [SQLAlchemy](https://www.sqlalchemy.org/) for database management.
- [PyYAML](https://pyyaml.org/) for YAML file handling.
- [asyncio](https://docs.python.org/3/library/asyncio.html) for asynchronous programming.
- [datetime](https://docs.python.org/3/library/datetime.html) for date and time handling.
- [json](https://docs.python.org/3/library/json.html) for JSON handling.
- [os](https://docs.python.org/3/library/os.html) for operating system interactions