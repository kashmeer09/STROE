import discord

def purchase_success_embed(user, product, product_id, price):
    embed = discord.Embed(
        title="Purchase Successful",
        description=f"{user.mention}, you have successfully bought {product['name']}.",
        color=discord.Color.green()
    )
    embed.add_field(name="Product ID", value=product_id)
    embed.add_field(name="Price", value=f"${price:.2f}")
    embed.add_field(name="Product Name", value=product['name'])
    return embed

def purchase_log_embed(user, product, product_id, price):
    embed = discord.Embed(
        title="Purchase Log",
        description=f"{user.mention} bought {product['name']}.",
        color=discord.Color.green()
    )
    embed.add_field(name="Product ID", value=product_id)
    embed.add_field(name="Price", value=f"${price:.2f}")
    embed.add_field(name="User", value=user.mention)
    return embed

def insufficient_balance_message(user):
    return f"{user.mention}, you do not have enough balance to buy this product."

def product_not_found_message():
    return "Product not found."

def thank_you_message(product_name):
    return f"Thank you for purchasing {product_name}!"

def file_not_available_message(user, product_name):
    return f"{user.mention}, the file for {product_name} is not available. Please contact support."

def user_new_balance_message(user, balance):
    return f"{user.mention}, your new balance is ${balance:.2f}"

def user_balance_message(user, balance):
    return f"{user.mention}, your current balance is ${balance:.2f}"

def no_permission_message(user):
    return f"{user.mention}, you do not have permission to use this command."

def cannot_respond_dm_message():
    return "I'm sorry, but I cannot respond to direct messages."