import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup

# --- Variables de entorno ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")
BLOG_SITE = "https://danienlared.wordpress.com"

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

# --- Función de búsqueda usando scraping exacto ---
async def buscar_posts(keyword: str):
    url = f"{BLOG_SITE}/?s={keyword.replace(' ', '+')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Buscamos todos los títulos reales de los posts
    for h2 in soup.find_all("h2", class_="entry-title"):
        link_tag = h2.find("a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        link = link_tag['href']

        # Intentamos obtener un extracto si hay un <p> en el mismo contenedor padre
        parent = h2.parent
        excerpt_tag = parent.find("p") if parent else None
        excerpt = excerpt_tag.get_text(strip=True) if excerpt_tag else ""

        results.append({
            "title": title,
            "URL": link,
            "excerpt": excerpt
        })

    return results[:10]  # Limitar a 10 resultados

# --- Crear embed ---
def crear_embed(post):
    embed = discord.Embed(
        title=post.get("title", "Sin título"),
        url=post.get("URL", ""),
        description=(post.get("excerpt", "")[:300] + "…") if len(post.get("excerpt", "")) > 300 else post.get("excerpt", ""),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Fuente: danienlared.wordpress.com")
    return embed

# --- Paginador ---
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
