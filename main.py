import discord
from discord.ext import commands
import os
import asyncio
import sqlite3
from openai import AsyncOpenAI
from gtts import gTTS

# ==========================================
# ⚙️ CONFIGURAȚIE
# ==========================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ID_CANAL_VOCE = 1504452767467573361

# Folosim direct OpenAI oficial pentru GPT-4o-mini (fără OpenRouter, zero erori 404)
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Memoria globală
chat_sessions = {}
istoric_paraschiv = {}
LIMITA_MESAJE = 40

# Imagini pentru Roleplay
IMG_TAVERN_OUT = "https://cdn.discordapp.com/attachments/1472611408830267462/tavern_outside.jpg" 
IMG_TAVERN_IN = "https://cdn.discordapp.com/attachments/1472611408830267462/tavern_inside.jpg"   
IMG_QUEST_OUT = "https://cdn.discordapp.com/attachments/1472611408830267462/quest_board.jpg"

# ==========================================
# 🎙️ FUNCȚIE AUDIO (TEXT TO SPEECH)
# ==========================================
async def vorbeste_pe_voce(bot_instance, text_spus):
    canal_voce = bot_instance.get_channel(ID_CANAL_VOCE)
    if not canal_voce:
        return

    voice_client = discord.utils.get(bot_instance.voice_clients, guild=canal_voce.guild)
    if not voice_client or not voice_client.is_connected():
        try:
            voice_client = await canal_voce.connect(timeout=60.0)
        except Exception as e:
            print(f"Eroare conectare voce: {e}")
            return

    try:
        text_curat = ''.join(c for c in text_spus if c.isalnum() or c.isspace() or c in ",.?!")
        if not text_curat.strip():
            return

        tts = gTTS(text=text_curat, lang='ro', slow=False)
        fisier_audio = "paraschiv_vorbeste.mp3"
        tts.save(fisier_audio)

        if voice_client.is_playing():
            voice_client.stop()

        audio_source = discord.FFmpegPCMAudio(fisier_audio)
        voice_client.play(audio_source)

    except Exception as e:
        print(f"Eroare la redarea audio: {e}")

# ==========================================
# 🗄️ FUNCȚII BAZA DE DATE
# ==========================================
def get_player_info(user_id):
    try:
        conn = sqlite3.connect('rpg_shops.db')
        c = conn.cursor()
        c.execute("SELECT balance, hp, level, race, class FROM users WHERE user_id=?", (user_id,))
        res = c.fetchone()
        conn.close()
        return res
    except:
        return None

def get_channel_setting(setting_name):
    conn = sqlite3.connect('rpg_shops.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS bot_settings (setting_name TEXT PRIMARY KEY, setting_value TEXT)")
    c.execute("SELECT setting_value FROM bot_settings WHERE setting_name=?", (setting_name,))
    res = c.fetchone()
    conn.close()
    return int(res[0]) if res else None

# ==========================================
# 🚪 BUTOANE INTERACTIVE (VIEWS)
# ==========================================
class RPLeaveView(discord.ui.View):
    def __init__(self, npc_name):
        super().__init__(timeout=None)
        self.npc_name = npc_name

    @discord.ui.button(label="🚶 Părăsește zona", style=discord.ButtonStyle.danger, custom_id="leave_rp_btn")
    async def leave_rp(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_key = f"{interaction.user.id}_{self.npc_name}"
        if user_key in chat_sessions:
            del chat_sessions[user_key]
        await interaction.response.send_message("Ai plecat din zonă...", ephemeral=True)
        try: await interaction.channel.delete()
        except: pass

class TavernEnterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🚪 Intră în Tavernă", style=discord.ButtonStyle.success, custom_id="enter_tavern_btn")
    async def enter_tavern(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚪 Ai împins ușile grele de lemn...", ephemeral=True)
        try: thread = await interaction.channel.create_thread(name=f"🍺 Masa lui {interaction.user.display_name}", type=discord.ChannelType.private_thread, invitable=False)
        except: thread = await interaction.channel.create_thread(name=f"🍺 Masa lui {interaction.user.display_name}", type=discord.ChannelType.public_thread)
        await thread.add_user(interaction.user)
        embed = discord.Embed(title="🍻 The Merry Tavern", description="Garrick șterge un pahar și îți face cu ochiul.\n\n*Ia un loc și salută-l!*", color=0x8b4513)
        if IMG_TAVERN_IN.startswith("http"): embed.set_image(url=IMG_TAVERN_IN)
        await thread.send(content=interaction.user.mention, embed=embed, view=RPLeaveView("garrick"))

class QuestEnterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📜 Verifică Misiunile", style=discord.ButtonStyle.primary, custom_id="enter_quest_btn")
    async def enter_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📜 Te-ai apropiat de panou...", ephemeral=True)
        try: thread = await interaction.channel.create_thread(name=f"📜 Quest: {interaction.user.display_name}", type=discord.ChannelType.private_thread, invitable=False)
        except: thread = await interaction.channel.create_thread(name=f"📜 Quest: {interaction.user.display_name}", type=discord.ChannelType.public_thread)
        await thread.add_user(interaction.user)
        embed = discord.Embed(title="⚔️ Gilda Aventurierilor", description="Angela se joacă cu un pumnal și te măsoară din priviri.\n\n*Vorbește cu ea!*", color=0x4169e1)
        await thread.send(content=interaction.user.mention, embed=embed, view=RPLeaveView("angela"))

# ==========================================
# 🚀 EVENIMENTE ȘI COMENZI SETUP
# ==========================================
@bot.event
async def on_ready():
    bot.add_view(TavernEnterView())
    bot.add_view(QuestEnterView())
    bot.add_view(RPLeaveView("garrick"))
    bot.add_view(RPLeaveView("angela"))
    print(f'✅ The Ultimate Bot {bot.user} este online 24/7!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="farmam 100 de ore!"))
    
    await asyncio.sleep(3)
    canal = bot.get_channel(ID_CANAL_VOCE)
    if canal:
        try:
            print("⏳ Încerc să intru pe voce...")
            await canal.connect(timeout=60.0)
            print(f"🎧 M-am conectat pe voce!")
        except Exception as e:
            print(f"❌ Nu am putut intra pe voce! Eroare: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:
        canal = bot.get_channel(ID_CANAL_VOCE)
        if canal:
            await asyncio.sleep(5)
            try:
                await canal.connect(timeout=60.0)
            except Exception as e:
                print(f"Eroare la reconectare voce: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_tavern(ctx):
    conn = sqlite3.connect('rpg_shops.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS bot_settings (setting_name TEXT PRIMARY KEY, setting_value TEXT)")
    c.execute("INSERT OR REPLACE INTO bot_settings (setting_name, setting_value) VALUES (?, ?)", ('tavern_channel', str(ctx.channel.id)))
    conn.commit()
    conn.close()
    try: await ctx.message.delete()
    except: pass
    embed = discord.Embed(title="🍺 The Merry Tavern", description="Auzi râsete și halbe ciocnindu-se înăuntru.", color=0x63332d)
    if IMG_TAVERN_OUT.startswith("http"): embed.set_image(url=IMG_TAVERN_OUT)
    await ctx.send(embed=embed, view=TavernEnterView())

@bot.command()
@commands.has_permissions(administrator=True)
async def set_quest(ctx):
    conn = sqlite3.connect('rpg_shops.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS bot_settings (setting_name TEXT PRIMARY KEY, setting_value TEXT)")
    c.execute("INSERT OR REPLACE INTO bot_settings (setting_name, setting_value) VALUES (?, ?)", ('quest_channel', str(ctx.channel.id)))
    conn.commit()
    conn.close()
    try: await ctx.message.delete()
    except: pass
    embed = discord.Embed(title="📜 Quest Board", description="Misiuni proaspete afișate pe panou.", color=0x2f3136)
    if IMG_QUEST_OUT.startswith("http"): embed.set_image(url=IMG_QUEST_OUT)
    await ctx.send(embed=embed, view=QuestEnterView())

# ==========================================
# 🧠 RUTAREA INTELIGENȚEI ARTIFICIALE (ON_MESSAGE)
# ==========================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    # --- 1. MODUL PARASCHIV (Dacă e menționat) ---
    if bot.user in message.mentions:
        async with message.channel.typing():
            try:
                mesaj_curat = message.content.replace(f'<@{bot.user.id}>', '').strip()
                if not mesaj_curat: mesaj_curat = "Ce zici?"

                este_fata = False
                if isinstance(message.author, discord.Member):
                    roluri_fete = ["fih enjoyer", "she/her", "car", "fată", "fata", "female"]
                    if any(rol.name.lower() in roluri_fete for rol in message.author.roles):
                        este_fata = True

                mod_vorbire = "Persoana cu care vorbești este o fată. Fii ușor flirty, glumeț și fermecător ('my lady', 'darling')." if este_fata else "Persoana cu care vorbești este un băiat. Fii fix pe modul 'bro', tovarăș chill ('șefule', 'bro')."
                
                personalitate = (
                    f"Ești Paraschiv, 20+ ani, absolut haotic, sarcastic și fără filtru. Ai un tupeu fantastic și folosești umor negru. "
                    f"{mod_vorbire} "
                    f"Ești complet liber să folosești argou românesc și înjurături lejere (ex: 'băga-mi-aș', 'dă-te-n', 'să mor eu', 'coaie'). "
                    f"Faci mișto de utilizator, îl iei la roast grav dacă zice prostii și ești complet 'unhinged'. "
                    f"Răspunzi MEREU scurt (max 2 propoziții). Nu recunoști niciodată că ești AI, ești 100% uman și sălbatic."
                )
                user_id = message.author.id
                if user_id not in istoric_paraschiv: istoric_paraschiv[user_id] = []
                
                istoric_paraschiv[user_id].append({"role": "user", "content": f"{message.author.name}: {mesaj_curat}"})
                istoric_paraschiv[user_id] = istoric_paraschiv[user_id][-LIMITA_MESAJE:]
                
                # Folosim direct gpt-4o-mini de la OpenAI (rapid, ieftin și nu dă niciodată erori de rețea)
                response = await ai_client.chat.completions.create(
                    model="gpt-5.4-mini",
                    messages=[{"role": "system", "content": personalitate}] + istoric_paraschiv[user_id],
                    temperature=0.8
                )
                raspuns_ai = response.choices[0].message.content
                
                istoric_paraschiv[user_id].append({"role": "assistant", "content": raspuns_ai})
                await message.reply(raspuns_ai)

                # 🎙️ Trimitem răspunsul text direct pe canalul de voice!
                await vorbeste_pe_voce(bot, raspuns_ai)

            except Exception as e:
                print(f"Eroare fatală Paraschiv: {e}")
                await message.reply("🧠 (Sistem suprasolicitat. Mai zi o dată!)")
        return

    # --- 2. MODUL ROLEPLAY (Garrick & Angela) ---
    if isinstance(message.channel, discord.Thread):
        tavern_id = get_channel_setting('tavern_channel')
        quest_id = get_channel_setting('quest_channel')
        
        is_tavern = (tavern_id and message.channel.parent_id == tavern_id)
        is_quest = (quest_id and message.channel.parent_id == quest_id)
        
        if is_tavern or is_quest:
            if not message.content: return

            async with message.channel.typing():
                user_id = message.author.id
                stats = get_player_info(user_id)
                
                este_fata = False
                if isinstance(message.author, discord.Member):
                    roluri_fete = ["fih enjoyer", "she/her", "car", "fată", "fata", "female"]
                    if any(rol.name.lower() in roluri_fete for rol in message.author.roles):
                        este_fata = True

                gender = "beautiful woman" if este_fata else "man"
                p_info = f"{message.author.display_name}, a {gender} Level {stats[2]} {stats[3]} {stats[4]}" if stats else f"a mysterious {gender}"

                if is_tavern:
                    npc_key = f"{user_id}_garrick"
                    instructiuni = (
                        f"You are Garrick, 28, a rugged, savage tavern keeper. Context: Talking to {p_info}. "
                        f"RULE 1: If 'woman', be an aggressive flirt. If 'man', be a sarcastic bro. "
                        f"RULE 2: Use asterisks for actions (*slams a mug on the bar*). Max 3 sentences."
                    )
                else:
                    npc_key = f"{user_id}_angela"
                    instructiuni = (
                        f"You are Angela, 28, a cynical quest giver. Context: Talking to {p_info}. "
                        f"RULE 1: If 'man', be a sarcastic flirt. If 'woman', be a chaotic bestie. "
                        f"RULE 2: Use asterisks for actions (*cleans a dagger*). Max 3 sentences."
                    )

                if npc_key not in chat_sessions:
                    chat_sessions[npc_key] = [{"role": "system", "content": instructiuni}]

                chat_sessions[npc_key].append({"role": "user", "content": message.content})
                if len(chat_sessions[npc_key]) > 11:
                    chat_sessions[npc_key] = [chat_sessions[npc_key][0]] + chat_sessions[npc_key][-10:]

                try:
                    completion = await ai_client.chat.completions.create(
                        model="gpt-5.4-mini",
                        messages=chat_sessions[npc_key],
                        temperature=0.8,
                        max_tokens=150
                    )
                    reply = completion.choices[0].message.content
                except Exception as e:
                    print(f"Eroare AI NPC: {e}")
                    reply = "*(NPC-ul este distras. Mai spune o dată!)*"

                chat_sessions[npc_key].append({"role": "assistant", "content": reply})
                await message.reply(reply)

bot.run(DISCORD_TOKEN)
