import asyncio
import random
import discord
from discord.ext import commands
import yt_dlp as youtube_dl

# --- CONFIGURACIÓN DE INTENTS Y BOT ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("/"),
    description="Bot de utilidades y música",
    intents=intents,
    help_command=None  # Desactiva el help por defecto para usar el personalizado
)

# --- OPCIONES DE YOUTUBE Y FFMPEG ---
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Evita problemas de IPv6
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'executable': './bin/ffmpeg.exe'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# --- CLASE DE AUDIO YTDL ---
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


# --- COG DE MÚSICA ---
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Se une a un canal de voz"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Reproduce un archivo local"""
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Reproduciendo archivo local: {query}')

    @commands.command()
    async def yt(self, ctx, *, url):
        """Descarga y reproduce desde una URL"""
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Reproduciendo: **{player.title}**')

    @commands.command()
    async def stream(self, ctx, *, url):
        """Transmite directamente desde una URL (sin descargar)"""
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Reproduciendo en directo: **{player.title}**')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Cambia el volumen del reproductor (0-100)"""
        if ctx.voice_client is None:
            return await ctx.send("El bot no está conectado a un canal de voz.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Volumen cambiado al **{volume}%**")

    @commands.command()
    async def stop(self, ctx):
        """Detiene la música y desconecta al bot"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Desconectado del canal de voz.")

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Debes estar conectado a un canal de voz.")
                raise commands.CommandError("El usuario no está en un canal de voz.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


# --- EVENTOS DEL BOT ---
@bot.event
async def on_ready():
    print(f'¡Bot conectado con éxito como {bot.user} (ID: {bot.user.id})!')
    print('--------------------------------------------------')


# --- COMANDOS GENERALES ---
@bot.command()
async def hello(ctx):
    await ctx.send(f'¡Hola, soy un bot {bot.user.name}!')

@bot.command()
async def ping(ctx):
    await ctx.send('¡Pong!')

@bot.command()
async def joined(ctx, member: discord.Member):
    await ctx.send(f'**{member.name}** se unió el {discord.utils.format_dt(member.joined_at)}')

@bot.command()
async def coinflip(ctx):
    resultado = random.choice(["Cara", "Cruz"])
    await ctx.send(f'🪙 Resultado: **{resultado}**')

@bot.command()
async def gen_pasw(ctx):
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+"
    password = ''.join(random.choice(characters) for _ in range(12))
    await ctx.send(f'🔑 Tu contraseña generada es: `{password}` (¡Guárdala en un lugar seguro!)')

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Help del Bot 🤖",
        description=(
            "**Prefix:** `/`\n\n"
            "`/help` - Muestra este mensaje\n"
            "`/ping` - Responde Pong!\n"
            "`/hello` - El bot te da un saludo\n"
            "`/coinflip` - Lanza una moneda (Cara o Cruz)\n"
            "`/gen_pasw` - Genera una contraseña segura aleatoria\n"
            "`/joined @usuario` - Muestra la fecha de ingreso del usuario\n\n"
            "**Comandos de Música:**\n"
            "`/stream <URL/Búsqueda>` - Transmite audio de YouTube\n"
            "`/yt <URL>` - Descarga y reproduce un audio\n"
            "`/volume <0-100>` - Cambia el volumen del audio\n"
            "`/stop` - Detiene la música y desconecta al bot"
        ),
        color=2733513
    )
    await ctx.send(embed=embed)


# --- INICIALIZACIÓN ---
async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start('MTU1N******************************************//*//*/**/**/*/*/-/-*/')  # Coloca aquí tu Token de Discord

asyncio.run(main())