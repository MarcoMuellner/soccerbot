from discord import Client
client = Client()

def toDiscordChannelName(name: str) -> str:
    """
    Converts a string to a discord channel like name -> all lowercase and no spaces
    :param name:
    :return:
    """
    if name == None:
        return None
    return name.lower().replace(" ", "-")
    pass