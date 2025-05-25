import os
import requests
import discord
import random
import logging
import math # Needed for format_bytes
from podman import PodmanClient
from podman.errors import NotFound

# Constants
URI = "unix:///run/podman/podman.sock"
AUTHORIZED_GUILD_IDS = [1317809184221298769, 805070329588088862]
AUTHORIZED_CHANNEL_IDS = [1319051370686582815, 1317812980074942484]

def fetch_public_ip():
    """Fetch the public IP address using api.ipify.org."""
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        return response.json().get("ip")
    except requests.RequestException as e:
        logging.error(f"Error fetching public IP: {e}")
        return "IP Failure" 

public_ip = fetch_public_ip()

# Dictionary defining target containers to be managed by the application
TARGET_CONTAINERS = {
    # Example container setup (currently commented out)
    # "minecraft": {"ip": PUBLIC_IP, "port": "27015", "password": "serverpasswort"},
}

KRANG_QUOTES = [ # List of Krang quotes for random responses in the bot
    "I'm finally FREE!! The people of this planet will pay for what they've done to me.",
    "Brother, Sister, join me. It's time for us to finish remaking this universe in the image of Krang.",
    "WIPE THAT GRIN OFF YOUR FACE!",
    "It's pointless to resist Krang. Give up! You'll be consumed like everyone else on this pathetic planet!",
    "Outmatched and alone, yet you persist. For what? Honor? Redemption? Sacrifice... All... Meaningless.",
    "A word used by the weak. Many planets before yours have spoken of duty. They too have been consumed by the Krang and now our glorious crusade continues to restore the natural order of things. The strong will devour the weak.",
    "A rare misstep. Once I retrieve the key from your comrades, I will bring forth the mighty Technodrome and you will witness the true power of the Krang. Now, where have they taken my key?",
    "Shame our brethren didn't survive the Prison Dimension. Then again, their weakness has no place in my new Krang empire. Open and bring unto this world the mighty power of Krang!"
]

# Helper function to format bytes into a human-readable string
def format_bytes(size_in_bytes):
    if not isinstance(size_in_bytes, (int, float)) or size_in_bytes < 0:
        return "N/A"
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    
    i = 0
    # Convert to float for division, to handle very small positive numbers correctly if needed
    temp_size = float(size_in_bytes)
    while temp_size >= 1024 and i < len(size_name) - 1:
        temp_size /= 1024
        i += 1
        
    s = round(temp_size, 2)
    return f"{s}{size_name[i]}"

def _format_single_container_stats_row(current_stats, display_name, header_format):
    """Helper function to format a single row of container statistics."""
    cpu_raw = current_stats.get('CPU')
    cpu_display = f"{cpu_raw:.2f}%" if isinstance(cpu_raw, (int, float)) else "N/A"

    cpu_nano_raw = current_stats.get('CPUNano')
    if isinstance(cpu_nano_raw, (int, float)):
        total_seconds = int(cpu_nano_raw / 1_000_000_000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        cpu_time_display = f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        cpu_time_display = "N/A"
        
    mem_display = f"{format_bytes(current_stats.get('MemUsage', 0))} / {format_bytes(current_stats.get('MemLimit', 0))}"

    network_interfaces_stats = current_stats.get('Network') or {}
    net_rx_bytes = sum(if_data.get('RxBytes', 0) for if_data in network_interfaces_stats.values())
    net_tx_bytes = sum(if_data.get('TxBytes', 0) for if_data in network_interfaces_stats.values())
    net_display = f"{format_bytes(net_rx_bytes)} / {format_bytes(net_tx_bytes)}"

    block_input_bytes = current_stats.get('BlockInput', 0)
    block_output_bytes = current_stats.get('BlockOutput', 0)
    block_io_display = f"{format_bytes(block_input_bytes)} / {format_bytes(block_output_bytes)}"

    return header_format.format(
        display_name,
        cpu_display,
        cpu_time_display,
        mem_display,
        net_display,
        block_io_display
    )

def get_container_stats_table():
    """Fetch and format statistics for containers listed in TARGET_CONTAINERS."""
    try:
        with PodmanClient(base_url=URI) as client:
            # Table Header for container stats
            # NAME | CPU % | CPU TIME | MEM USAGE / LIMIT | NET I/O (RX/TX) | BLOCK I/O (R/W)
            header_format = "{:<20} | {:<7} | {:<10} | {:<20} | {:<19} | {:<20}"
            header = header_format.format(
                "NAME", "CPU %", "CPU TIME", "MEM USAGE / LIMIT", "NET I/O (RX/TX)", "BLOCK I/O (R/W)"
            )
            separator = "-" * len(header)
            table_rows = []

            table_rows.append(header)
            table_rows.append(separator)

            # find all containers that match the names in TARGET_CONTAINERS
            # Use filters to get only the relevant containers efficiently
            target_names = list(TARGET_CONTAINERS.keys())
            all_containers = client.containers.list(all=True, filters={"name": target_names})
            
            # Create a dictionary for quick lookup by name
            container_dict = {c.name: c for c in all_containers}

            # Iterate through the target names to ensure all are listed, even if not found
            for target_container_name in target_names:
                container_obj = container_dict.get(target_container_name)
                display_name = (target_container_name[:17] + "...") if len(target_container_name) > 20 else target_container_name

                if not container_obj:
                    # Container not found, add a row indicating this
                    error_row = header_format.format(
                        display_name,
                        "N/A", # CPU %
                        "Not Found", # CPU TIME
                        "N/A", # MEM USAGE / LIMIT
                        "N/A", # NET I/O
                        "N/A"  # BLOCK I/O
                    )
                    table_rows.append(error_row)
                    continue # Move to the next target name

                # Container found, try to get stats
                try:
                    raw_stats_report = container_obj.stats(decode=True, stream=False)

                    if raw_stats_report.get("Error"):
                         raise Exception(f"API Error: {raw_stats_report['Error']}")

                    stats_list = raw_stats_report.get("Stats")
                    if not stats_list or not isinstance(stats_list, list) or not stats_list[0]:
                        raise Exception("Stats data missing or in unexpected format")
                    
                    current_stats = stats_list[0]

                    row_str = _format_single_container_stats_row(current_stats, display_name, header_format)
                    table_rows.append(row_str)

                except Exception as e:
                    # Print an error row if stats cannot be fetched or parsed for this container
                    error_row = header_format.format(
                        display_name,
                        "Error", # CPU %
                        str(e)[:10], # Truncate error message for CPU TIME column
                        "N/A", # MEM USAGE / LIMIT
                        "N/A", # NET I/O
                        "N/A"  # BLOCK I/O
                    )
                    table_rows.append(error_row)
                    # Continue to the next container name

            table_rows.append(separator) # Footer
            return "\n".join(table_rows)

    except Exception as e:
        logging.error(f"Error fetching container stats: {e}")
        return f"Error fetching container stats: {e}"


# Logging setup
logging.basicConfig(level=logging.INFO)


def _generate_status_table(client):
    """Helper function to generate the status table for monitored containers."""
    table_header = (
        "+-------------------+---------+---------------+--------+------------+\n"
        "| Server/Container  | Status  | IP            | Port   | Password   |\n"
        "+-------------------+---------+---------------+--------+------------+"
    )
    table_rows = []
    podman_containers_list = client.containers.list(all=True)
    # Create a dictionary for quick lookup by exact name
    podman_containers_dict = {c.name: c for c in podman_containers_list}

    for name, info in TARGET_CONTAINERS.items():
        container_obj = podman_containers_dict.get(name) # Exact match lookup
        if container_obj:
            container_obj.reload() # Get fresh status
            status = container_obj.status if container_obj.status in ["running", "exited"] else "unknown"
        else:
            status = "not found"

        row = f"| {name:<17} | {status:<7} | {info['ip']:<13} | {info['port']:<6} | {info['password']:<10} |"
        table_rows.append(row)

    table_footer = "+-------------------+---------+---------------+--------+------------+"
    return f"{table_header}\n" + "\n".join(table_rows) + f"\n{table_footer}"

def manage_container(action, container_name=None):
    """Perform actions like start, stop, restart, or check status on containers."""
    try:
        with PodmanClient(base_url=URI) as client:
            if action == "status":
                return _generate_status_table(client)

            # For actions other than 'status', container_name is required
            if not container_name: # Should be caught by on_message, but good for robustness
                return f"Please specify a container name for the '{action}' command."

            if container_name not in TARGET_CONTAINERS:
                return f"Container '{container_name}' is not in the list of monitored containers or may be misspelled."

            try:
                container_obj = client.containers.get(container_name)
                container_obj.reload() # Get fresh status
            except NotFound:
                return f"Container '{container_name}' not found by Podman."
            except Exception as e: # Catch other potential Podman errors
                logging.error(f"Error getting container '{container_name}': {e}")
                return f"Error accessing container '{container_name}': {e}"

            if action == "restart":
                container_obj.restart()
                return f"Container '{container_name}' restarted successfully."
            elif action == "start":
                if container_obj.status == "exited":
                    container_obj.start()
                    return f"Container '{container_name}' started successfully."
                return f"Container '{container_name}' is already {container_obj.status}."
            elif action == "stop":
                if container_obj.status == "running":
                    container_obj.stop()
                    return f"Container '{container_name}' stopped successfully."
                return f"Container '{container_name}' is not running (status: {container_obj.status})."
            elif action == "logs":
                logs_iter = container_obj.logs(stdout=True, stderr=True, tail=30)
                log_output = "\n".join(line.decode().strip() for line in logs_iter)
                return log_output[-1900:] if len(log_output) > 1900 else log_output
            
            return f"Action '{action}' is unknown or not applicable for container '{container_name}'."

    except Exception as e:
        logging.error(f"Error during {action} action: {e}")
        return f"Error performing {action} on container '{container_name}': {e}"


# Discord client setup
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logging.info(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check if the message is from an authorized server and channel
    if message.guild.id not in AUTHORIZED_GUILD_IDS or message.channel.id not in AUTHORIZED_CHANNEL_IDS:
        return


    # Check if bot is mentioned
    if not message.mentions or client.user not in message.mentions:
        return

    # Parse command
    try:
        command_parts = message.content.split()
        if len(command_parts) < 2:
            await message.channel.send("Invalid command format. Type `help` for instructions.")
            return

        command = command_parts[1].lower()
        container_name = command_parts[2] if len(command_parts) > 2 else None

        if command == "status":
            status_message = manage_container("status")
            await message.channel.send(f"```\n{status_message}\n```")

        elif command == "logs":
            if not container_name:
                await message.channel.send("Please specify a container name to fetch logs.")
                return
            logs = manage_container("logs", container_name)
            await message.channel.send(f"```\n{logs}\n```")

        elif command in ["restart", "start", "stop"]:
            if not container_name:
                await message.channel.send(f"Please specify a container name for the '{command}' command.")
                return
            result = manage_container(command, container_name)
            await message.channel.send(result)

        elif command == "stats":
            stats_message = get_container_stats_table()
            await message.channel.send(f"```\n{stats_message}\n```")

        elif command == "help":
            help_message = (
                "**Available Commands:**\n"
                "- `status`: Shows the status of all monitored containers.\n"
                "- `restart <container_name>`: Restarts the specified container.\n"
                "- `start <container_name>`: Starts the specified container.\n"
                "- `stop <container_name>`: Stops the specified container.\n"
                "- `stats`: Shows resource usage statistics for all monitored containers.\n"
                "- `logs <container_name>`: Fetches the last 30 lines of logs for the specified container.\n"
            )
            await message.channel.send(help_message)

        else:
            random_quote = random.choice(KRANG_QUOTES)
            await message.channel.send(random_quote)

    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await message.channel.send("An error occurred while processing your command.")

# Bot token from environment variable
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("Bot token not set. Please configure the DISCORD_BOT_TOKEN environment variable.")
else:
    client.run(TOKEN)
