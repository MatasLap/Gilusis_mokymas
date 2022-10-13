from asyncio.windows_events import NULL
import discord
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
import youtube_dl
import asyncio
import pymongo
import ssl
import re
import numpy as np

from pymongo import MongoClient
from random import choice
#jeigu mongodb mes error kad negali gauti certifikato mesk "cluster = MongoClient("",ssl_cert_reqs=ssl.CERT_NONE)""
cluster = MongoClient("")

db = cluster['db']

collection = db['Grojaraščiai']

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
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

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


client = commands.Bot(command_prefix='?')

status = ['Aktyvus!', 'Puikiai veikia!', 'LETS GOOOOOOO!']

queue = []

loop = False

@client.event
async def on_ready():
    change_status.start()
    print('Botas yra prijungtas!')

@client.command(name='ping')
async def ping(ctx):
    await ctx.send(f'**Pong!** Latency: {round(client.latency * 1000)}ms')

@client.command(name='join', help='prijungia botą prie kalbėjimo kanalo')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("Tu nesi prisiunges prie klabėjimo kanalo")
        return

    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()


@client.command(name='play', help='Ši komanda groja muziką')
async def play(ctx):
    

    server = ctx.message.guild
    voice_channel = server.voice_client
    
    async with ctx.typing():
        player = await YTDLSource.from_url(queue[0], loop=client.loop)
        voice_channel.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        
        if loop:
            queue.append(queue[0])
        del(queue[0])
        
    
    await ctx.send('**Dabar grojame:** {}'.format(player.title))

@client.command(name='pause', help='Ši komanda sustabdo muziką')
async def pause(ctx):
    server=ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.pause()

@client.command(name='resume', help='Ši komanda tęsia muziką')
async def resume(ctx):
    server=ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.resume()

@client.command(name='queue', help='Ši komanda prideda muziką prie eilės')
async def queue_(ctx, url):
    global queue
    queue.append(url)
    await ctx.send(f'`{url}` buvo pridėtas į eilę!')

@client.command(name='remove', help='Ši komanda ištrina muziką iš eilės sąrašo')
async def remove(ctx, number):
    global queue

    try:
        del(queue[int(number)])
        await ctx.send(f'Tavo eilė yra dabar `{queue}`')
    
    except:
        await ctx.send(f'Tavo pasirinktas dainos numeris eilėje yra tuščias')

@client.command(name='view')
async def view(ctx):
    await ctx.send(f'Tavo eilė yra dabar `{queue}`')

@client.command(name='stop', help='Ši komanda ištrina grojančia muzika')
async def stop(ctx):
    server=ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.stop()

@client.command(name='loop', help='Ši komanda išjungia arba įjungia Eilės kartojimą')
async def loop_(ctx):
    global loop

    if loop:
        await ctx.send('Eilė nesikartoja')
        loop = False
    
    else: 
        await ctx.send('Eilė kartojasi')
        loop = True

@client.command(name='save', help='Ši komanda išsaugoja dabartinė eilę į duomenų bazę')
async def save(ctx):
    server = ctx.guild.id
    
    prevdict = collection.find_one({},{"server": server})
    try:
        prevdict = collection.find_one({},{"server": server})
        collection.delete_one(prevdict)
    except:
        print('duom bazei nieko prieštai nebuvo!')
    mydict = {"server": server, "link": queue}
    collection.insert_one(mydict)
    

    await ctx.send('Eilė buvo išsaugota į duomenų bazę!')

@client.command(name='load')
async def load(ctx):
    server = {"server": ctx.guild.id}
    prevdict = collection.find_one(server, {"_id": 0, "link": 1})
    queue.append(prevdict)
    #await ctx.send(f'`{url}` buvo pridėtas į eilę!')

@client.command(name='hyper')
async def hyper(ctx):
    embed = discord.Embed()
    embed.description = "čia yra hyperlinkas [VO](https://lt.wikipedia.org/wiki/Aurelijus_Veryga)."
    await ctx.send(embed=embed)

@client.command(name='leave')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()

@client.command(name='serverid')
async def leave(ctx):
    server = ctx.guild.id
    await ctx.send(f'`{server}` yra serverio ID')

@tasks.loop(seconds=20)
async def change_status():
    await client.change_presence(activity=discord.Game(choice(status)))

client.run('')