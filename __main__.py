import discord
import asyncio

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    if message.content.startswith('!test'):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await client.send_message(message.channel, 'Done sleeping')

@client.event
async def on_ready():
    channels = client.get_all_channels()
    for i in channels:
        print(i)

    for i in client.servers:
        print(i)


client.run('NDc0MjA5MTg0NzA4MTY1NjQy.DkNbcg.tphF6_RxXzRlylHn4mSPlIe49Zw')