import os
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

# --- Variables de entorno ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")
BLOG_SITE = "danienlared.wordpress.com"
API_URL = f"https://public-api.wordpress.com/rest/v1.1/sites/{BLOG_SITE}/posts"

# --- Bot ---
class BlogBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.default(),
            application_id=APPLICATION_ID
        )

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Comandos sincronizados con Discord.")

bot = BlogBot()

# --- Función de búsqueda ---
async def buscar_posts(keyword: str):
    params = {"number": 10, "search": keyword}
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("posts", [])

# --- Crear embed ---
def crear_embed(post):
    title = post.get("title", "Sin título")
    link = post.get("URL", "")
    excerpt = post.get("excerpt", "")
    author = post.get("author", {}).get("name", "Desconocido")
    imagen = post.get("featured_image")  # Solo si existe

    clean_excerpt = (
        excerpt.replace("<p>", "")
        .replace("</p>", "")
        .replace("<strong>", "**")
        .replace("</strong>", "**")
        .strip()
    )

    embed = discord.Embed(
        title=title,
        url=link,
        description=(clean_excerpt[:300] + "…") if len(clean_excerpt) > 300 else clean_excerpt,
        color=discord.Color.blurple(),
    )
    embed.set_author(name=author)
    embed.set_footer(text="Fuente: danienlared.wordpress.com")

    if imagen:
        embed.set_image(url=imagen)

    return embed

# --- Paginador con botones ---
class Paginador(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.index = 0

    async def update_message(self, interaction):
        embed = self.embeds[self.index]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Siguiente ▶️", style=discord.ButtonStyle.primary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embeds) - 1:
            self.index += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

# --- Comando slash ---
@bot.tree.command(name="buscar", description="Busca artículos en el blog danienlared.wordpress.com")
async def buscar(interaction: discord.Interaction, termino: str):
    await interaction.response.defer(thinking=True)
    posts = await buscar_posts(termino)

    if not posts:
        await interaction.followup.send(f"❌ No se encontraron resultados para **{termino}**.")
        return

    embeds = [crear_embed(p) for p in posts]
    view = Paginador(embeds)
    await interaction.followup.send(embed=embeds[0], view=view)

# --- Ejecutar bot ---
bot.run(BOT_TOKEN)
