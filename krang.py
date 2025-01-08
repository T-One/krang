import os
import requests
import discord
import random
import logging
from podman import PodmanClient

# Constants
PODMAN_URI = "unix:///run/podman/podman.sock"  # URI for Podman Unix socket

AUTHORIZED_GUILD_IDS = [0000000, 000000]  # IDs of authorized guilds (servers)
AUTHORIZED_CHANNEL_IDS = [000000, 000000]  # IDs of authorized channels for the bot


# Dictionary defining target containers to be managed by the application
TARGET_CONTAINERS = {
    # Example container setup (currently commented out)
    # "minecraft": {"ip": PUBLIC_IP, "port": "27015", "password": "serverpasswort"},
}

KRANG_QUOTES = [  # List of Krang quotes for random responses in the bot
    "I'm finally FREE!! The people of this planet will pay for what they've done to me.",
    "Brother, Sister, join me. It's time for us to finish remaking this universe in the image of Krang.",
    "WIPE THAT GRIN OFF YOUR FACE!",
    "It's pointless to resist Krang. Give up! You'll be consumed like everyone else on this pathetic planet!",
    "Outmatched and alone, yet you persist. For what? Honor? Redemption? Sacrifice... All... Meaningless.",
    "A word used by the weak. Many planets before yours have spoken of duty. They too have been consumed by the Krang and now our glorious crusade continues to restore the natural order of things. The strong will devour the weak.",
    "A rare misstep. Once I retrieve the key from your comrades, I will bring forth the mighty Technodrome and you will witness the true power of the Krang. Now, where have they taken my key?",
    "Shame our brethren didn't survive the Prison Dimension. Then again, their weakness has no place in my new Krang empire. Open and bring unto this world the mighty power of Krang!"
]

# Logging setup
logging.basicConfig(level=logging.INFO)

def fetch_public_ip():
    """
    Fetch the public IP address of the system using api.ipify.org.
    Returns:
        str: The public IP address, or "IP Failure" if fetching fails.
    """
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()  # Check for HTTP errors
        return response.json().get("ip")
    except requests.RequestException as e:
        logging.error(f"Error fetching public IP: {e}")
        return "IP Failure" 

# Store the public IP address
PUBLIC_IP = fetch_public_ip()


def manage_container(action, container_name=None):
    """
    Manage Podman containers by performing actions like start, stop, restart, or fetching status.

    Args:
        action (str): The action to perform (status, start, stop, restart, logs).
        container_name (str, optional): The name of the container to manage. Defaults to None.

    Returns:
        str: A message describing the result of the action.
    """
    try:
        with PodmanClient(base_url=PODMAN_URI) as client:
            container_list = client.containers.list(all=True)  # List all containers

            if action == "status":
                # Generate and return a table of container statuses
                table_header = (
                    "+-------------------+---------+---------------+--------+------------+\n"
                    "| Server/Container  | Status  | IP            | Port   | Password   |\n"
                    "+-------------------+---------+---------------+--------+------------+"
                )
                table_rows = []

                for name, info in TARGET_CONTAINERS.items():
                    # Find container matching the target name
                    matching_containers = [
                        container for container in container_list if name in container.name
                    ]
                    if matching_containers:
                        container = matching_containers[0]
                        container.reload()
                        status = container.status if container.status in ["running", "exited"] else "unknown"
                    else:
                        status = "not found"

                    # Add container details to the table
                    row = f"| {name:<17} | {status:<7} | {info['ip']:<13} | {info['port']:<6} | {info['password']:<10} |"
                    table_rows.append(row)

                table_footer = "+-------------------+---------+---------------+--------+------------+"
                return f"{table_header}\n" + "\n".join(table_rows) + f"\n{table_footer}"

            for container in container_list:
                container.reload()

                # Ensure the container is a target container
                if container_name not in TARGET_CONTAINERS:
                    return f"Container '{container_name}' not known. Misspelled?"

                if container_name and container_name in container.name:
                    # Handle specific actions
                    if action == "restart":
                        container.restart()
                        return f"Container '{container_name}' restarted successfully."

                    if action == "start" and container.status == "exited":
                        container.start()
                        return f"Container '{container_name}' started successfully."

                    if action == "stop" and container.status == "running":
                        container.stop()
                        return f"Container '{container_name}' stopped successfully."

                    if action == "logs":
                        logs = container.logs(stdout=True, stderr=True, tail=30)
                        return "\n".join(line.decode().strip() for line in logs)[-1900:]

        return f"Container '{container_name}' not found or action '{action}' not applicable."
    except Exception as e:
        logging.error(f"Error during {action} action: {e}")
        return f"Error performing {action} on container '{container_name}': {e}"

# Discord bot setup with intents
intents = discord.Intents.default()
intents.message_content = True  # Enable access to message content

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """Log when the bot has successfully logged in."""
    logging.info(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    """
    Handle incoming messages and respond to valid commands.
    
    Args:
        message (discord.Message): The incoming message object.
    """
    if message.author == client.user:  # Ignore bot's own messages
        return

    # Validate that the message is from an authorized server and channel
    if message.guild.id not in AUTHORIZED_GUILD_IDS or message.channel.id not in AUTHORIZED_CHANNEL_IDS:
        return

    # Check if the bot was mentioned in the message
    if not message.mentions or client.user not in message.mentions:
        return

    try:
        # Parse the command from the message
        command_parts = message.content.split()
        if len(command_parts) < 2:
            await message.channel.send("Invalid command format. Type `help` for instructions.")
            return

        command = command_parts[1].lower()  # Extract the command
        container_name = command_parts[2] if len(command_parts) > 2 else None  # Optional container name

        # Handle various commands
        if command == "status":
            status_message = manage_container("status")
            await message.channel.send(f"```\n{status_message}\n```")

        elif command in ["restart", "start", "stop"]:
            if not container_name:
                await message.channel.send(f"Please specify a container name for the '{command}' command.")
                return
            result = manage_container(command, container_name)
            await message.channel.send(result)

        elif command == "logs":
            if not container_name:
                await message.channel.send("Please specify a container name to fetch logs.")
                return
            logs = manage_container("logs", container_name)
            await message.channel.send(f"```\n{logs}\n```")

        elif command == "help":
            # Send help message with a list of available commands
            help_message = (
                "**Available Commands:**\n"
                "- `status`: Shows the status of all monitored containers.\n"
                "- `restart <container_name>`: Restarts the specified container.\n"
                "- `start <container_name>`: Starts the specified container.\n"
                "- `stop <container_name>`: Stops the specified container.\n"
                "- `logs <container_name>`: Fetches the last 20 lines of logs for the specified container.\n"
            )
            await message.channel.send(help_message)

        else:
            # Send a random Krang quote if the command is unrecognized
            random_quote = random.choice(KRANG_QUOTES)
            await message.channel.send(random_quote)

    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await message.channel.send("An error occurred while processing your command.")

# Retrieve and use the bot token from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("Bot token not set. Please configure the DISCORD_BOT_TOKEN environment variable.")
else:
    client.run(TOKEN)
