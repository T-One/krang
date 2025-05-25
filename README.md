# Krang

A simple discord bot to manage podman containers via podman.sock.

## Project Description

Krang is a Discord bot designed to provide a simple interface for managing Podman containers. It allows users to interact with a Podman instance to perform actions such as starting, stopping, and checking the status of predefined containers directly from Discord commands. This is particularly useful for managing game servers or other applications running in containers without needing direct server access.

## Prerequisites

Before running Krang, ensure you have the following installed and configured:

- **Podman**: Installed and running on the system where the bot will operate.
- **Podman API Socket**: The Podman API socket must be enabled and accessible. The default URI used by the bot is `unix:///run/podman/podman.sock`. You can typically enable this with `systemctl --user start podman.socket`.
- **Python**: Python 3.x is required.
- **discord.py Library**: Install using pip:
  ```bash
  pip install discord.py
  ```
- **podman Library**: Install using pip:
  ```bash
  pip install podman
  ```

## Environment Variables

The bot requires the following environment variable to be set:

- `DISCORD_BOT_TOKEN`: This is the authentication token for your Discord bot. It's crucial for the bot to log in to Discord. You can obtain this token from the Discord Developer Portal.

## Configuration

Several constants within the `krang.py` script need to be configured to match your setup:

- `PODMAN_URI`: The URI for the Podman Unix socket.
  - Default: `unix:///run/podman/podman.sock`
- `AUTHORIZED_GUILD_IDS`: A Python list of Discord Server (Guild) IDs where the bot is allowed to operate. Messages from other guilds will be ignored.
  - Example: `AUTHORIZED_GUILD_IDS = [123456789012345678, 987654321098765432]`
- `AUTHORIZED_CHANNEL_IDS`: A Python list of Discord Channel IDs within the authorized guilds where the bot will listen for commands. Commands sent in other channels will be ignored.
  - Example: `AUTHORIZED_CHANNEL_IDS = [112233445566778899, 998877665544332211]`
- `TARGET_CONTAINERS`: A Python dictionary defining the containers that the bot can manage. The keys are the short names you'll use in commands, and the values are dictionaries containing details about each container.
  - Example:
    ```python
    TARGET_CONTAINERS = {
        "myserver": {"ip": "YOUR_SERVER_PUBLIC_IP", "port": "25565", "password": "your_server_password"},
        "anotherapp": {"ip": "YOUR_SERVER_PUBLIC_IP", "port": "8080", "password": "N/A"},
    }
    ```
  - **Note on `ip`**: The `ip` field can be automatically fetched if the `PUBLIC_IP = fetch_public_ip()` line in `krang.py` is active and the `requests` library is installed. Alternatively, you can hardcode a static IP address or hostname.
  - **Note on `port` and `password`**: These fields are primarily for informational display by the `status` command and are not directly used for container operations by default.

## Available Commands

Commands are issued by mentioning the bot followed by the command:

- `@<BotMention> status`: Shows the status (online/offline), IP, port, and password (if configured) of all monitored containers.
- `@<BotMention> restart <container_name>`: Restarts the specified container.
- `@<BotMention> start <container_name>`: Starts the specified container if it is currently stopped.
- `@<BotMention> stop <container_name>`: Stops the specified container if it is currently running.
- `@<BotMention> logs <container_name>`: Fetches and displays the most recent logs for the specified container.
- `@<BotMention> help`: Shows the help message, listing all available commands.

## Running the Bot

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Install Python dependencies**:
    It's recommended to create a `requirements.txt` file with the following content:
    ```
    discord.py
    podman
    requests
    ```
    Then install them using:
    ```bash
    pip install -r requirements.txt
    ```
    (The `requests` library is optional if you hardcode the public IP or don't need automatic IP fetching).
    Alternatively, install individually:
    ```bash
    pip install discord.py podman requests
    ```
3.  **Set Environment Variables**:
    Export the `DISCORD_BOT_TOKEN` environment variable:
    ```bash
    export DISCORD_BOT_TOKEN="your_actual_bot_token_here"
    ```
    (Consider adding this to your shell's startup file like `.bashrc` or `.zshrc` for persistence).
4.  **Configure `krang.py`**:
    Open `krang.py` and update the following constants with your specific details:
    - `AUTHORIZED_GUILD_IDS`
    - `AUTHORIZED_CHANNEL_IDS`
    - `TARGET_CONTAINERS`
    - `PODMAN_URI` (if not using the default)
5.  **Run the bot**:
    ```bash
    python krang.py
    ```

## Contributing

Contributions are welcome! If you have suggestions for improvements, new features, or find any bugs, please feel free to open an issue or submit a pull request.

## License

License information to be added. (This project will likely use the MIT License, but a `LICENSE.md` file will be added to formalize this).