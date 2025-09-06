import discord
import aiohttp
import os
import config
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from discord import Embed

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

# OAuth / Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Folder IDs for your tags (replace with your real folder IDs)
FOLDER_IDS = {
    "rural": "1OgWX8_VGWhOON92nse7LqrFo07TEIS9q",
    "urban": "1PCh8mAoYxBCFDIfuV8sQ5DJLvr9nJpK9",
    "alpine": "1DSY3of71mAhjwvW6pfLxcuVazgpzOUYA",
    "bridges": "1IBSGGbgv2GUHfJAOJEeJXCCwYmUZsnvg",
    "brutalist": "1Nx7k5pwXpTYaRQtpegAwVouUAW-UYvey",
    "coastal": "1EnbZ_zzKDv7uQrrQ_CgD_sARzHF6W4LN",
    "concept": "1KOVbfjYWRAVUriheWmflTZhsI2xGhKcy",
    "industrial": "10rxJUwz7zB6OQppZhEEcCRRTVPebmNXY",
    "interiors": "1za6vCYmCqKpwGETAUeZVXeZvDB1jvBJ1",
    "medieval": "1nKlYpP8-V1npMHIQjC4FHoPA3AQvZHp8",
    "minecraft": "1cnUpvxheOaNTu3Xb6n2gS3b1rw0RXHk5",
    "nature": "1s_0Z3UllGUP5Hi0IfGhaa3mDdnqjukHm",
    "plans": "1zmSaj8KfaZvpPncbNDihKOyXGx2mUPtA",
    "railway": "1HmSphbKwR-1q1jfNmDezlTscxosE1nJs",
    "signage": "1pxehBEv-cQJVLeDz_lGC7Eduyy2Q3MpZ",
    "surfaces": "1OOOO-Xi5D2iRm9vav_7lKGOyj426Nd4p",
    "tech": "1W0gW_G7ozdfqf0KvhqIOl828Eqv1DxIb",
    "vehicles": "16TSZEHLt_hNnPHVhQEOd5RPw61WlMr_6",
    "weapons": "1nOBGLFhpis9lJcLVI7BEOEtIoLSYoj14"
}

# OAuth helper
def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_file_to_drive(file_path, file_name, tag):
    service = get_drive_service()
    folder_id = FOLDER_IDS.get(tag)
    if not folder_id:
        raise ValueError(f"No folder configured for tag '{tag}'")
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    return uploaded_file.get('id')

# Discord bot client
class Client(discord.Client):
    async def on_ready(self):
        print(f"I'm online as {self.user}!")

    # Download image async
    async def download_image(self, url, filename):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(filename, 'wb') as f:
                        f.write(await resp.read())
                    return filename
        return None

    # Handle image: download + upload
    async def handle_image(self, attachment, author_name, tag):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        ext = os.path.splitext(attachment.filename)[1] or ".png"
        filename = f"{author_name}_{timestamp}{ext}"
        local_path = await self.download_image(attachment.url, filename)
        if local_path:
            try:
                file_id = upload_file_to_drive(local_path, filename, tag)
                print(f"Uploaded {filename} to Drive (ID: {file_id})")
            finally:
                os.remove(local_path)  # cleanup

    # On message event
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.startswith("!tag"):
            parts = message.content.split(" ", 1)
            if len(parts) < 2:
                await message.channel.send("Please provide a valid tag! qwq")
                return
            tag = parts[1].lower().strip()

            # Case: Images in the same message
            if message.attachments:
                uploaded_count = 0
                for attachment in message.attachments:
                    if attachment.content_type.startswith("image/"):
                        await self.handle_image(attachment, message.author.name, tag)
                        uploaded_count += 1
                if uploaded_count > 0:
                    await message.channel.send(f"✅ Uploaded {uploaded_count} image(s) to {tag.capitalize()}!")
                elif uploaded_count == 0:
                    await message.channel.send("Message has no image! qwq")


            # Case: Images in referenced message
            elif message.reference and message.reference.resolved:
                ref = message.reference.resolved
                uploaded_count = 0
                for attachment in ref.attachments:
                    if attachment.content_type.startswith("image/"):
                        await self.handle_image(attachment, ref.author.name, tag)
                        uploaded_count += 1
                if uploaded_count > 0:
                    await message.channel.send(f"✅ Uploaded {uploaded_count} image(s) to {tag.capitalize()}!")
                elif uploaded_count == 0:
                    await message.channel.send("Mentioned message has no image! qwq")
            else: 
                await message.channel.send("Message has no image! qwq")



        elif message.content.startswith("!th"):
            embed = Embed(
    title="Bot Usage Guide",
    description="This bot automatically saves images to Marina's [Google Drive](https://drive.google.com/drive/folders/1FFduyDVtOK5VkxLkskETubvgM2tUbWo3?usp=drive_link) inspirational images mega_archive based on tags.",
    color=0x1abc9c  # Hex color, optional
)
            embed.add_field(
    name="Usage",
    value="`!tag <tag>` on your own image, or reply to an image with `!tag <tag>`, the image is automatically named after the author and date.",
    inline=False  # False = field takes full width
)

            embed.add_field(
    name="Available Tags",
    value="alpine, bridges, brutalist, coastal, concept, industrial, interiors, medieval, minecraft, nature, plans, railway, rural, signage, surfaces, tech, urban, vehicles, weapons",
    inline=False
)
            embed.set_author(name="Inspo.Marina", icon_url ="https://cdn.discordapp.com/app-icons/1380281764744007730/1aab8de038cc1cda5b2a49a5cf9dbc08.png?size=256")
            embed.set_footer(text="support and abuse report: tf2photoarchive@gmail.com")
            await message.channel.send(embed=embed)

# Run bot
client = Client(intents=intents)
client.run('config.DISCORD_BOT_TOKEN') 
