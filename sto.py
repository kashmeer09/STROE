import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import pyautogui
import datetime

from embeds_and_messages import (
    purchase_log_embed,
    insufficient_balance_message,
    product_not_found_message,
    thank_you_message,
    file_not_available_message,
    user_new_balance_message,
    user_balance_message,
    no_permission_message,
    cannot_respond_dm_message
)

CONFIG_FILE = '/storage/emulated/0/Download/STORE/data/inputs.json'

def load_inputs():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

inputs = load_inputs()
TOKEN = inputs.get("TOKEN")
OWNER_ID = int(inputs.get("OWNER_ID"))  # Ensure OWNER_ID is treated as an integer
ALLOWED_CHANNELS = inputs.get("ALLOWED_CHANNELS", [])
LOG_CHANNEL_ID = int(inputs.get("LOG_CHANNEL_ID"))

DATA_FILE = '/storage/emulated/0/Download/STORE/data/data.json'
PRODUCTS_FILE = '/storage/emulated/0/Download/STORE/data/products.json'

intents = discord.Intents.default()
intents.members = True  
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

def load_products():
    if os.path.isfile(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_user_balances():
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_balances(user_balances):
    with open(DATA_FILE, 'w') as f:
        json.dump(user_balances, f, indent=4)

products = load_products()
user_balances = load_user_balances()

@bot.event
async def on_ready():
    await bot.tree.sync()  # Ensure the commands are synced
    bot.owner_id = (await bot.application_info()).owner.id

    # Debugging output
    print(f"Configured OWNER_ID: {OWNER_ID}")
    print(f"Bot Owner ID: {bot.owner_id}")
    
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        print(f"Log channel found: {log_channel.name} ({log_channel.id})")
    else:
        print(f"Log channel with ID {LOG_CHANNEL_ID} not found.")

    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id != OWNER_ID:
            try:
                await message.author.send(cannot_respond_dm_message())
            except discord.Forbidden:
                print(f"Cannot send DM to {message.author}. They might have DMs disabled.")
            return
    
    if message.channel.id not in ALLOWED_CHANNELS:
        return
    
    await bot.process_commands(message)

@bot.tree.command(name="list_products", description="List all available products")
async def list_products(interaction: discord.Interaction):
    response = "Available products:\n"
    for pid, details in products.items():
        response += f"{pid}. {details['name']} - ${details['price']}\n"
    await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="product_details", description="Get details of a specific product")
async def product_details(interaction: discord.Interaction, product_id: str):
    if product_id in products:
        product = products[product_id]
        response = f"**{product['name']}**\nPrice: ${product['price']}\nDescription: {product['description']}"
    else:
        response = product_not_found_message()
    await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="check_balance", description="Check your current balance")
async def check_balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    balance = user_balances.get(user_id, 0.0)
    await interaction.response.send_message(user_balance_message(interaction.user, balance), ephemeral=True)

@bot.tree.command(name="buy_product", description="Buy a product")
async def buy_product(interaction: discord.Interaction, product_id: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    user_id = str(interaction.user.id)
    if product_id not in products:
        await interaction.followup.send(product_not_found_message(), ephemeral=True)
        return

    product = products[product_id]
    balance = user_balances.get(user_id, 0.0)
    
    if balance < product['price']:
        await interaction.followup.send(insufficient_balance_message(interaction.user), ephemeral=True)
        return
    
    user_balances[user_id] -= product['price']
    save_user_balances(user_balances)
    
    file_path = product['file_path']
    if os.path.isfile(file_path):
        try:
            await interaction.user.send(thank_you_message(product['name']), file=discord.File(file_path))
            await interaction.followup.send("Your purchase has been processed, and the file has been sent to you in a DM.", ephemeral=True)

            # Assign the role to the user
            role_id = product.get('role_id')
            if role_id:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.followup.send(f"The role **{role.name}** has been assigned to you.", ephemeral=True)
                else:
                    await interaction.followup.send(f"Role with ID {role_id} not found.", ephemeral=True)

            # Log the purchase (NOT EPHEMERAL)
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=purchase_log_embed(interaction.user, product, product_id, product['price']))

                # Ensure the directory exists
                screenshot_dir = "/storage/emulated/0/Download/STORE/screenshots"
                if not os.path.exists(screenshot_dir):
                    try:
                        os.makedirs(screenshot_dir)
                    except Exception as e:
                        print(f"Failed to create directory: {e}")
                        await log_channel.send("Failed to create screenshot directory.")
                        return

                # Define the screenshot path
                screenshot_path = os.path.join(screenshot_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")

                try:
                    # Take a screenshot
                    pyautogui.screenshot(screenshot_path)

                    # Post the screenshot to the log channel
                    await log_channel.send("Here is a screenshot of the transaction:", file=discord.File(screenshot_path))
                except Exception as e:
                    print(f"Failed to take or send screenshot: {e}")
                    await log_channel.send("Failed to take or send the screenshot.")
                    
        except discord.Forbidden:
            await interaction.followup.send("I couldn't send you the file via DM. Please check your privacy settings and try again.", ephemeral=True)
    else:
        await interaction.followup.send(file_not_available_message(interaction.user, product['name']), ephemeral=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.NotOwner):
        await ctx.send(no_permission_message(ctx.author), ephemeral=True)
    else:
        print(f"Error: {error}")
        raise error

# Balance Management UI with Custom Amounts
class BalanceManagementView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == OWNER_ID  # Only the bot owner can interact

    @discord.ui.button(label="Add Balance", style=discord.ButtonStyle.green)
    async def add_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddBalanceModal(self.user)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove Balance", style=discord.ButtonStyle.red)
    async def remove_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveBalanceModal(self.user)
        await interaction.response.send_modal(modal)

# Modal to Add Balance
class AddBalanceModal(discord.ui.Modal, title="Add Balance"):
    amount = discord.ui.TextInput(label="Amount to Add", placeholder="Enter amount...", required=True, max_length=10)

    def __init__(self, user: discord.User):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_to_add = float(self.amount.value)
        except ValueError:
            await interaction.response.send_message("Invalid amount. Please enter a valid number.", ephemeral=True)
            return

        user_id = str(self.user.id)
        user_balances[user_id] = user_balances.get(user_id, 0.0) + amount_to_add
        save_user_balances(user_balances)
        await interaction.response.send_message(user_new_balance_message(self.user, user_balances[user_id]), ephemeral=True)

# Modal to Remove Balance
class RemoveBalanceModal(discord.ui.Modal, title="Remove Balance"):
    amount = discord.ui.TextInput(label="Amount to Remove", placeholder="Enter amount...", required=True, max_length=10)

    def __init__(self, user: discord.User):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_to_remove = float(self.amount.value)
        except ValueError:
            await interaction.response.send_message("Invalid amount. Please enter a valid number.", ephemeral=True)
            return

        user_id = str(self.user.id)
        current_balance = user_balances.get(user_id, 0.0)

        if current_balance >= amount_to_remove:
            user_balances[user_id] = current_balance - amount_to_remove
            save_user_balances(user_balances)
            await interaction.response.send_message(user_new_balance_message(self.user, user_balances[user_id]), ephemeral=True)
        else:
            await interaction.response.send_message("Insufficient balance to remove that amount.", ephemeral=True)

@bot.tree.command(name="manage_balance", description="Manage a user's balance (Admin only)")
async def manage_balance(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(no_permission_message(interaction.user), ephemeral=True)
        return

    view = BalanceManagementView(member)
    await interaction.response.send_message(f"Managing balance for {member.mention}", view=view, ephemeral=True)

bot.run(TOKEN)
