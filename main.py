import discord
from discord.ext import commands
import random, string, json, aiohttp, aiofiles, os, time
from zipfile import ZipFile
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import logging
from PIL import Image, ImageDraw, ImageFont
import traceback
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("pfp_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Load configuration
with open("config.json") as f:
    config = json.load(f)

TOKEN = config["token"]
ADMIN_ID = int(config["admin_id"])
MAX_PFPS = 100000
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
active_keys = {}
TEMP_DIR = "temp_pfps"
os.makedirs(TEMP_DIR, exist_ok=True)
KEY_EXPIRY = 3600
CONCURRENT_DOWNLOADS = 50
CONCURRENT_WATERMARKS = 10
API_COOLDOWN = {}
WATERMARK_TEXT = "discord.gg/synoboosts"

# Improved font handling for watermark
try:
    WATERMARK_FONT = ImageFont.truetype("arial.ttf", 20)
except:
    try:
        WATERMARK_FONT = ImageFont.truetype("DejaVuSans.ttf", 20)
    except:
        WATERMARK_FONT = ImageFont.load_default()

def get_pfp_apis():
    """Return API list with conditional premium APIs"""
    apis = [
        # Realistic People
        {"url": "https://thispersondoesnotexist.com", "type": "direct", "cooldown": 1},
        {"url": "https://i.pravatar.cc/300?u={rand}", "type": "direct"},
        {"url": "https://loremflickr.com/300/300/person?lock={num}", "type": "direct"},
        {"url": "https://source.unsplash.com/300x300/?portrait,face", "type": "direct", "cooldown": 5},
        {"url": "https://xsgames.co/randomusers/avatar.php?g=male", "type": "direct"},
        {"url": "https://xsgames.co/randomusers/avatar.php?g=female", "type": "direct"},
        {"url": "https://xsgames.co/randomusers/avatar.php?g=pixel", "type": "direct"},
        
        # Anime & Stylized
        {"url": "https://api.waifu.pics/sfw/waifu", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/neko", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/shinobu", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/megumin", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/cry", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/hug", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/pat", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/smug", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.pics/sfw/kiss", "type": "json", "key": "url", "cooldown": 1},
        {"url": "https://api.waifu.im/random/?selected_tags=waifu", "type": "json", "key": "images.0.url", "cooldown": 2},
        {"url": "https://api.waifu.im/random/?selected_tags=maid", "type": "json", "key": "images.0.url", "cooldown": 2},
        {"url": "https://nekos.best/api/v2/neko", "type": "json", "key": "results.0.url"},
        {"url": "https://nekos.best/api/v2/waifu", "type": "json", "key": "results.0.url"},
        {"url": "https://nekos.best/api/v2/kitsune", "type": "json", "key": "results.0.url"},
        
        # Animals & Pets
        {"url": "https://api.thecatapi.com/v1/images/search", "type": "json", "key": "0.url"},
        {"url": "https://api.thedogapi.com/v1/images/search", "type": "json", "key": "0.url"},
        {"url": "https://randomfox.ca/floof/", "type": "json", "key": "image"},
        {"url": "https://shibe.online/api/shibes", "type": "json", "key": "0"},
        {"url": "https://shibe.online/api/cats", "type": "json", "key": "0"},
        {"url": "https://shibe.online/api/birds", "type": "json", "key": "0"},
        {"url": "https://some-random-api.com/img/dog", "type": "json", "key": "link"},
        {"url": "https://some-random-api.com/img/cat", "type": "json", "key": "link"},
        {"url": "https://some-random-api.com/img/fox", "type": "json", "key": "link"},
        {"url": "https://place-puppy.com/300x300", "type": "direct"},
        {"url": "https://dog.ceo/api/breeds/image/random", "type": "json", "key": "message"},
        
        # Avatars & Generative
        {"url": "https://robohash.org/{rand}.png", "type": "direct"},
        {"url": "https://api.multiavatar.com/{rand}.png", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/initials/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/lorelei/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/bottts/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/avataaars/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/personas/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/thumbs/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/miniavs/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/identicon/svg?seed={rand}", "type": "direct"},
        {"url": "https://api.dicebear.com/6.x/open-peeps/svg?seed={rand}", "type": "direct"},
        {"url": "https://picsum.photos/300/300?random={num}", "type": "direct"},
        {"url": "https://www.gravatar.com/avatar/{rand}?d=identicon&s=300", "type": "direct"},
        {"url": "https://www.gravatar.com/avatar/{rand}?d=monsterid&s=300", "type": "direct"},
        {"url": "https://www.gravatar.com/avatar/{rand}?d=wavatar&s=300", "type": "direct"},
        {"url": "https://www.gravatar.com/avatar/{rand}?d=retro&s=300", "type": "direct"},
        {"url": "https://www.gravatar.com/avatar/{rand}?d=robohash&s=300", "type": "direct"},
        {"url": "https://api.lorem.space/image/face?w=300&h=300", "type": "direct"},
        
        # Art & Abstract
        {"url": "https://source.unsplash.com/300x300/?art", "type": "direct", "cooldown": 5},
        {"url": "https://source.unsplash.com/300x300/?abstract", "type": "direct", "cooldown": 5},
        {"url": "https://source.unsplash.com/300x300/?pattern", "type": "direct", "cooldown": 5},
        {"url": "https://source.unsplash.com/300x300/?texture", "type": "direct", "cooldown": 5},
        
        # Fallback APIs
        {"url": "https://picsum.photos/300/300", "type": "direct"},
        {"url": "https://placebeard.it/300/300", "type": "direct"},
        {"url": "https://placekeanu.com/300/300", "type": "direct"},
    ]

    # Conditionally add premium APIs if keys exist
    if config.get("unsplash_key"):
        apis.append({
            "url": f"https://api.unsplash.com/photos/random?query=face&client_id={config['unsplash_key']}",
            "type": "json", 
            "key": "urls.regular", 
            "cooldown": 10
        })
    
    if config.get("pexels_key"):
        apis.extend([
            {
                "url": "https://api.pexels.com/v1/search?query=animal&per_page=1&page={num}",
                "type": "json", 
                "key": "photos.0.src.medium", 
                "headers": {"Authorization": config["pexels_key"]}
            }
        ])
    
    return apis

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def clean_temp_dir():
    """Remove files older than 1 hour from temp directory"""
    now = time.time()
    for f in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, f)
        if os.path.isdir(file_path):
            for sub_file in os.listdir(file_path):
                sub_file_path = os.path.join(file_path, sub_file)
                if os.path.isfile(sub_file_path) and now - os.path.getmtime(sub_file_path) > 3600:
                    try:
                        os.remove(sub_file_path)
                    except:
                        pass
            try:
                if not os.listdir(file_path):
                    os.rmdir(file_path)
            except:
                pass
        elif os.path.isfile(file_path) and now - os.path.getmtime(file_path) > 3600:
            try:
                os.remove(file_path)
            except:
                pass

def add_watermark(image_data):
    """Add watermark to image in memory"""
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if needed
        if img.width > 500 or img.height > 500:
            img.thumbnail((500, 500))
        
        draw = ImageDraw.Draw(img)
        text = WATERMARK_TEXT
        text_width = draw.textlength(text, font=WATERMARK_FONT)
        margin = 10
        x = img.width - text_width - margin
        y = img.height - 30
        
        # Draw shadow text
        draw.text((x+1, y+1), text, (0,0,0), font=WATERMARK_FONT)
        # Draw main text
        draw.text((x, y), text, (255,255,255), font=WATERMARK_FONT)
        
        # Save to bytes buffer
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Watermark failed: {str(e)}")
        return image_data  # Return original if watermark fails

async def fetch_pfp(session):
    apis = get_pfp_apis()
    random.shuffle(apis)  # Randomize API order
    
    for api in apis:
        try:
            # Check API cooldown
            api_url = api["url"].split('?')[0]  # Base URL without params
            if api_url in API_COOLDOWN and API_COOLDOWN[api_url] > time.time():
                continue
                
            url = api["url"]
            
            # Replace placeholders
            if "{rand}" in url:
                rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                url = url.replace("{rand}", rand_str)
            if "{num}" in url:
                url = url.replace("{num}", str(random.randint(1, 1000)))
            if "{u}" in url:
                url = url.replace("{u}", str(uuid.uuid4()))
            if "{width}" in url or "{height}" in url:
                url = url.replace("{width}", "300").replace("{height}", "300")
            
            # Handle API types
            if api["type"] == "direct":
                # Apply cooldown if specified
                if "cooldown" in api:
                    API_COOLDOWN[api_url] = time.time() + api["cooldown"]
                return url
                
            elif api["type"] == "json":
                headers = api.get("headers", {})
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    
                    # Handle nested keys (key1.key2.key3)
                    keys = api.get("key", "url").split('.')
                    result = data
                    for key in keys:
                        try:
                            if key.isdigit():
                                result = result[int(key)]
                            else:
                                result = result[key]
                        except (KeyError, TypeError, IndexError):
                            result = None
                            break
                    
                    if result and isinstance(result, str):
                        # Apply transform if exists
                        if "transform" in api:
                            result = api["transform"](result)
                        # Apply cooldown if specified
                        if "cooldown" in api:
                            API_COOLDOWN[api_url] = time.time() + api["cooldown"]
                        return result
        
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError) as e:
            logger.warning(f"API error: {api['url']} - {str(e)}")
            continue
    
    return None  # All APIs failed

async def download_image(session, semaphore, watermark_semaphore, url, temp_dir):
    """Download image with retries and proper file extension"""
    async with semaphore:
        for retry in range(3):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Get content type for extension
                        content_type = response.headers.get('Content-Type', '')
                        if 'jpeg' in content_type or 'jpg' in content_type:
                            ext = 'jpg'
                        elif 'png' in content_type:
                            ext = 'png'
                        elif 'gif' in content_type:
                            ext = 'gif'
                        elif 'webp' in content_type:
                            ext = 'webp'
                        else:
                            ext = 'png'  # Default extension
                        
                        image_data = await response.read()
                        
                        # Add watermark if not animated GIF
                        if 'gif' not in content_type:
                            async with watermark_semaphore:
                                image_data = await asyncio.to_thread(add_watermark, image_data)
                        
                        filename = f"{temp_dir}/pfp_{uuid.uuid4().hex[:6]}.{ext}"
                        async with aiofiles.open(filename, 'wb') as f:
                            await f.write(image_data)
                        
                        return filename
                    else:
                        logger.warning(f"Failed download: {url} - Status {response.status}")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Download error: {url} - {str(e)}")
                await asyncio.sleep(0.5)
    return None

@bot.command()
async def key(ctx, count: int):
    """Generate a redemption key for PFPs (Admin only)"""
    if ctx.author.id != ADMIN_ID:
        return await ctx.send("🚫 Unauthorized.", delete_after=5)
    
    if count > MAX_PFPS:
        return await ctx.send(f"❌ Max {MAX_PFPS} PFPs per key", delete_after=5)
    
    new_key = generate_key()
    active_keys[new_key] = {
        "count": count,
        "expiry": time.time() + KEY_EXPIRY,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": ctx.author.id
    }
    
    expiry_time = datetime.now(timezone.utc) + timedelta(seconds=KEY_EXPIRY)
    expiry_str = expiry_time.strftime("%Y-%m-%d %H:%M UTC")
    
    try:
        await ctx.author.send(
            f"🔑 *PFP Redemption Key*\n"
            f"`{new_key}`\n"
            f"*Quantity:* {count} PFPs\n"
            f"⏳ *Expires:* {expiry_str}\n"
            f"🔗 *Watermark:* {WATERMARK_TEXT}"
        )
        await ctx.send("✅ Key sent to your DMs", delete_after=5)
    except discord.Forbidden:
        await ctx.send(
            f"🔑 *Your PFP Key:*\n"
            f"`{new_key}`\n"
            f"⚠ Enable DMs for better security",
            delete_after=20
        )

@bot.command()
async def redeem(ctx, input_key: str):
    """Redeem a key to receive PFPs"""
    key_data = active_keys.get(input_key)
    if not key_data:
        return await ctx.send("❌ Invalid or expired key.", delete_after=10)
    
    if time.time() > key_data["expiry"]:
        del active_keys[input_key]
        return await ctx.send("⌛ Key has expired.", delete_after=10)
    
    count = key_data["count"]
    del active_keys[input_key]
    
    if count > MAX_PFPS:
        return await ctx.send("⚠ Invalid PFP count", delete_after=5)
    
    # Create unique temp directory for this redemption
    user_temp_dir = f"{TEMP_DIR}/{ctx.author.id}"
    os.makedirs(user_temp_dir, exist_ok=True)
    temp_dir = f"{user_temp_dir}/{int(time.time())}"
    os.makedirs(temp_dir, exist_ok=True)
    
    msg = await ctx.send(f"📦 *Processing {count} PFPs...*\n⏳ Estimated time: {count//60} seconds")
    
    clean_temp_dir()  # Clean old files before starting
    file_paths = []
    session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    download_semaphore = asyncio.Semaphore(CONCURRENT_DOWNLOADS)
    watermark_semaphore = asyncio.Semaphore(CONCURRENT_WATERMARKS)
    
    try:
        tasks = []
        for i in range(count):
            task = asyncio.create_task(
                fetch_and_download(session, download_semaphore, watermark_semaphore, temp_dir)
            )
            tasks.append(task)
        
        # Process in batches to update progress
        batch_size = 50
        for batch_idx in range(0, count, batch_size):
            batch_end = min(batch_idx + batch_size, count)
            current_batch = tasks[batch_idx:batch_end]
            
            done, pending = await asyncio.wait(
                current_batch,
                return_when=asyncio.ALL_COMPLETED,
                timeout=300
            )
            
            for task in done:
                result = task.result()
                if result:
                    file_paths.append(result)
            
            progress = len(file_paths)
            await msg.edit(
                content=f"📥 *Downloading PFPs...*\n"
                        f"✅ {progress}/{count} downloaded\n"
                        f"⏳ Remaining: {count - progress}\n"
                        f"🔗 Watermark: {WATERMARK_TEXT}"
            )
        
        success_count = len(file_paths)
        success_rate = (success_count / count) * 100 if count > 0 else 0
        await msg.edit(
            content=f"✅ *Download complete!*\n"
                    f"• Success rate: {success_rate:.1f}%\n"
                    f"• Compressing files...\n"
                    f"🔗 Watermark: {WATERMARK_TEXT}"
        )
    except Exception as e:
        logger.error(f"Redemption error: {str(e)}")
        await ctx.send(f"⚠ System error: {str(e)}")
    finally:
        await session.close()
    
    if not file_paths:
        await ctx.send("❌ Failed to download any PFPs. Please try again later.")
        try:
            os.rmdir(temp_dir)
        except:
            pass
        return
    
    # Create zip file
    zip_path = f"{temp_dir}/pfps_{ctx.author.id}.zip"
    with ZipFile(zip_path, 'w') as zipf:
        for file in file_paths:
            zipf.write(file, os.path.basename(file))
    
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # Size in MB
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Send files to user
    try:
        await ctx.author.send(
            f"🎁 *Your {len(file_paths)} PFPs are ready!*\n"
            f"📦 File: `pfps_{ctx.author.id}.zip`\n"
            f"📊 Size: {zip_size:.1f} MB\n"
            f"🕒 Generated at: {gen_time}\n"
            f"🔗 Watermark: {WATERMARK_TEXT}",
            file=discord.File(zip_path)
        )
        await ctx.send("✅ Check your DMs for the zip file!", delete_after=10)
    except discord.Forbidden:
        # Fallback to zip in channel if DMs disabled
        await ctx.send(
            f"📦 *Here are your {len(file_paths)} PFPs* (enable DMs for better delivery):\n"
            f"📊 Size: {zip_size:.1f} MB\n"
            f"🔗 Watermark: {WATERMARK_TEXT}",
            file=discord.File(zip_path))
    
    # Cleanup
    for file in file_paths:
        try:
            os.remove(file)
        except:
            pass
    try:
        os.remove(zip_path)
        os.rmdir(temp_dir)
    except:
        pass

async def fetch_and_download(session, download_sem, watermark_sem, temp_dir):
    """Fetch URL and download image"""
    url = await fetch_pfp(session)
    if not url:
        return None
    return await download_image(session, download_sem, watermark_sem, url, temp_dir)

@bot.event
async def on_ready():
    logger.info(f"✅ Bot ready as {bot.user}")
    bot.start_time = datetime.now(timezone.utc)
    bot.loop.create_task(expiry_checker())

async def expiry_checker():
    """Periodically clean expired keys"""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        now = time.time()
        expired_keys = [key for key, data in active_keys.items() if data["expiry"] < now]
        for key in expired_keys:
            del active_keys[key]
            logger.info(f"Cleaned expired key: {key}")

@bot.command()
async def stats(ctx):
    """Show bot statistics"""
    if not hasattr(bot, 'start_time'):
        bot.start_time = datetime.now(timezone.utc)
        
    uptime = datetime.now(timezone.utc) - bot.start_time
    keys_active = len(active_keys)
    temp_count = len(os.listdir(TEMP_DIR))
    
    embed = discord.Embed(
        title="📊 PFP Bot Stats",
        color=0x3498db,
        description=f"🔗 Watermark: `{WATERMARK_TEXT}`"
    )
    embed.add_field(name="🆙 Uptime", value=str(uptime).split('.')[0], inline=False)
    embed.add_field(name="🔑 Active Keys", value=keys_active, inline=True)
    embed.add_field(name="💾 Temp Files", value=f"{temp_count} directories", inline=True)
    embed.add_field(name="⚙ Max PFPs", value=MAX_PFPS, inline=True)
    embed.add_field(name="🚀 Concurrent Downloads", value=CONCURRENT_DOWNLOADS, inline=True)
    embed.add_field(name="🎨 Watermark Concurrency", value=CONCURRENT_WATERMARKS, inline=True)
    embed.add_field(name="🌐 API Sources", value=len(get_pfp_apis()), inline=True)
    
    if ctx.author.avatar:
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    else:
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def apis(ctx):
    """List all available API sources (Admin only)"""
    apis = get_pfp_apis()
    api_list = "\n".join([f"• {api['url']}" for api in apis[:50]])  # Show first 50
    embed = discord.Embed(
        title="🌐 API Sources",
        description=f"Total: {len(apis)}\nShowing first 50:",
        color=0x2ecc71
    )
    embed.add_field(name="Sources", value=api_list, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def clean(ctx):
    """Clean temporary files (Admin only)"""
    before = len(os.listdir(TEMP_DIR))
    clean_temp_dir()
    after = len(os.listdir(TEMP_DIR))
    await ctx.send(f"🧹 Cleaned {before - after} temporary files/directories")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f"Command error: {str(error)}")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("⚠ Missing required argument", delete_after=5)
    await ctx.send(f"⚠ Error: {str(error)}", delete_after=10)

bot.run(TOKEN)