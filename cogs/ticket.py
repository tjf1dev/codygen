from main import *
class ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands to manage tickets"
    @commands.hybrid_group(name="ticket",description="create and manage tickets")
    async def ticket(self,ctx):
        pass
    @verify()
    @ticket.command("create",description="create a ticket.")
    async def create(self,ctx, *, subject:str):
        # check if the config exists and tickets are enabled.
        try:
            enabled = get_guild_config(ctx.guild.id)["modules"]["ticket"]["enabled"]
            category = get_guild_config(ctx.guild.id)["modules"]["ticket"]["category"]
            staff_roles = get_guild_config(ctx.guild.id)["modules"]["ticket"]["staff_roles"]
            if not enabled or category == 0:
                disabled = discord.Embed(
                    title="Tickets are disabled in this server.",
                    color=0xff0000
                )
                await ctx.reply(embed=disabled)
            if enabled and category !=0 and staff_roles != []:
                guild = ctx.guild
                author = ctx.author
                ticket_id = f"{ctx.author.name}-{random.randint(10000,99999)}"
                category_obj = guild.get_channel(category)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                }
                for role_id in staff_roles:
                    role = guild.get_role(role_id)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
                    else:
                        logger.warning(f"Warning: Role with ID {role_id} not found in guild {guild.id}")
                try:
                    channel = await guild.create_text_channel(name=f"ticket-{ticket_id}", category=category_obj, overwrites=overwrites)
                    # add it to stats
                    with open(f"data/guilds/{ctx.guild.id}.json","r") as f:
                        data= json.load(f)
                        data["stats"]["ticket"].append(
                            {
                                "ticket":ticket_id,
                                "user":ctx.author.id,
                                "channel":channel.id,
                                "time":time.time()
                            }
                        )
                    with open(f"data/guilds/{ctx.guild.id}.json","w") as f:
                        json.dump(data,f,indent=4)
                    embed = discord.Embed(
                        title=f"{subject}",
                        description=f"Ticket created by {author.mention}",
                        color=0x00ff00
                    )
                    await channel.send(embed=embed)
                    success = discord.Embed(
                        title="Ticket Created",
                        description=f"Your ticket has been created in {channel.mention}",
                        color=0x00ff00
                    )
                    await ctx.reply(embed=success,ephemeral=True)
                except Exception as e:
                    error = discord.Embed(
                        title="Error",
                        description=f"There was an error creating the ticket.\n{e}",
                        color=0xff0000
                    )
                    await ctx.reply(embed=error,ephemeral=True)
        except Exception:
            error =discord.Embed(
                title="Error",
                description="This server may not be initialized yet, or has tickets disabled.\nPlease contact the staff of this server.",
                color=0xff0000
            )
            await ctx.reply(embed=error)
    @verify()
    @ticket.command(name="close", description="Closes the current ticket.")
    async def close(self, ctx):
        with open(f"data/guilds/{ctx.guild.id}.json", "r") as f:
            data = json.load(f)
        for ticket in data["stats"]["ticket"]:
            if ticket["channel"] == ctx.channel.id:
                user_id = int(ticket["user"])
                id = ticket["ticket"]
                # Try fetching user and sending the DM
                try:
                    user = await ctx.bot.fetch_user(user_id)
                    if user:
                        e = discord.Embed(
                            title=f"Ticket {id} has been closed.",
                            color=0xff0000
                        )
                        await user.send(embed=e)
                    else:
                        logger.warning(f"User {user_id} could not be fetched.")
                    with open(f"data/guilds/{ctx.guild.id}.json","r") as f:
                        data = json.load(f)
                        for i, t in enumerate(data["stats"]["ticket"]):
                            if t["channel"] == ctx.channel.id:
                                del data["stats"]["ticket"][i]
                                break
                    with open(f"data/guilds/{ctx.guild.id}.json","w") as f:
                        json.dump(data,f,indent=4)
                except discord.NotFound:
                    logger.warning(f"User {user_id} not found.")
                except discord.Forbidden:
                    logger.warning(f"Cannot DM user {user_id}. They might have DMs disabled.")
                except discord.HTTPException as err:
                    logger.error(f"Failed to send DM to {user_id}: {err}")
                except Exception as e:
                    logger.error(f"ticket close failed: {str(e)} ({ctx.guild.id})")
                    await user.send("there was an issue trying to fully close the ticket. bot developers have been notified.")
                # Delete the ticket channel
                await ctx.channel.delete()
async def setup(bot):
    await bot.add_cog(ticket(bot))