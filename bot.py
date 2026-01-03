import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import json, os, asyncio, chat_exporter

CONFIG_FILE = "config.json"
TRANSCRIPTS_DIR = "transcripts"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def is_ticket_channel(channel):
    return channel.name.startswith("ticket-")

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(intents=intents)

# ================= TRANSCRIPT =================
async def create_transcript_html(channel):
    guild_id = str(channel.guild.id)
    os.makedirs(f"{TRANSCRIPTS_DIR}/{guild_id}", exist_ok=True)
    html_path = f"{TRANSCRIPTS_DIR}/{guild_id}/{channel.id}.html"

    transcript = await chat_exporter.export(channel, limit=None, tz_info="Asia/Bangkok", bot=channel.guild.me)
    transcript = transcript.replace("</head>", """
    <style>.summary{display:none!important;}body{margin-top:0!important;}</style></head>
    """)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    return html_path

# ================= VIEWS =================
class CloseTicket(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.closed = False

    @nextcord.ui.button(label="", emoji="<:approve:1431941755439153332>", custom_id="close")
    async def close(self, button: nextcord.ui.Button, interaction: Interaction):
        if self.closed:
            await interaction.response.send_message("Ticket is already being closed", ephemeral=True)
            return
        self.closed = True
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Closing ticket...")

        html_path = await create_transcript_html(interaction.channel)
        config = load_config()
        log_channel = bot.get_channel(config["LOG_CHANNEL_ID"])
        if log_channel:
            web_url = config.get("WEB_URL", "http://localhost:8000")
            guild_id = str(interaction.guild.id)
            channel_id = str(interaction.channel.id)
            link = f"{web_url}/transcript/{guild_id}/{channel_id}"
            await log_channel.send(f"Transcript link: {link}")

        await asyncio.sleep(5)
        await interaction.channel.delete()

class OpenTicketView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="", emoji="<:idk:1431941766893932626>", custom_id="open")
    async def open_ticket(self, button: nextcord.ui.Button, interaction: Interaction):
        config = load_config()
        config["ticket_count"] += 1
        ticket_number = config["ticket_count"]
        save_config(config)

        category = interaction.guild.get_channel(config["TICKET_CATEGORY_ID"])
        overwrites = {
            interaction.guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            interaction.user: nextcord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            category=category,
            overwrites=overwrites
        )

        embed = nextcord.Embed(title="Ticket Chat", description="Please do not ping staff", color=0x2f3136)
        message = await channel.send(content=f"-# ||{interaction.user.mention}||", embed=embed, view=CloseTicket())
        await message.pin()
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

# ================= COMMANDS =================
@bot.slash_command(name="panel", description="Create ticket panel")
async def ticketpanel(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("You do not have permission", ephemeral=True)
    embed = nextcord.Embed(title="Ticket System", description="Press button to open ticket", color=0x2f3136)
    await interaction.channel.send(embed=embed, view=OpenTicketView())
    await interaction.response.send_message("Ticket panel created", ephemeral=True)

@bot.slash_command(name="add", description="Add user to ticket")
async def add(interaction: Interaction, member: nextcord.Member = SlashOption(description="User to add")):
    if not is_ticket_channel(interaction.channel):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
    await interaction.channel.set_permissions(member, view_channel=True, send_messages=True)
    await interaction.response.send_message(f"Added {member.mention}", ephemeral=True)

@bot.slash_command(name="remove", description="Remove user from ticket")
async def remove(interaction: Interaction, member: nextcord.Member = SlashOption(description="User to remove")):
    if not is_ticket_channel(interaction.channel):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
    await interaction.channel.set_permissions(member, overwrite=None)
    await interaction.response.send_message(f"Removed {member.mention}", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.add_view(OpenTicketView())
    bot.add_view(CloseTicket())

config = load_config()
bot.run(config["TOKEN"])
