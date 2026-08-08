import discord
from discord.ext import commands
import os
import asyncio
from openai import AsyncOpenAI

# 1. PUNE PAROLELE NOI AICI 
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 2. ID-ul canalului tau de voce
ID_CANAL_VOCE = 1504452767467573361

# Setăm OpenAI
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- ACTIVĂM CITIREA ROLURILOR ȘI A MESAJELOR ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # <- Asta e magia care îl lasă să vadă cine are rolul "car" sau "she/her"
bot = commands.Bot(command_prefix='!', intents=intents)

# --- CREIERUL LUI PARASCHIV (ISTORICUL) ---
istoric_conversatii = {}
LIMITA_MESAJE = 40 # L-am făcut mai deștept, ține minte 40 de mesaje

@bot.event
async def on_ready():
    print(f'✅ Botul {bot.user} este live 24/7!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="farmam 100 de ore!"))
    
    await asyncio.sleep(3)
    
    canal = bot.get_channel(ID_CANAL_VOCE)
    if canal:
        try:
            print("⏳ Încerc să intru pe voce...")
            await canal.connect(timeout=60.0)
            print(f"🎧 M-am conectat pe canalul de voce!")
        except Exception as e:
            print(f"❌ Nu am putut intra pe voce! Eroare: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:
        canal = bot.get_channel(ID_CANAL_VOCE)
        if canal:
            await asyncio.sleep(2)
            await canal.connect()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        async with message.channel.typing():
            try:
                mesaj_curat = message.content.replace(f'<@{bot.user.id}>', '').strip()
                if not mesaj_curat:
                    mesaj_curat = "Ce zici?"

                # --- 🕵️‍♂️ PARASCHIV VERIFICĂ ROLURILE ---
                este_fata = False
                
                # Ne asigurăm că e un mesaj de pe server (nu un DM) ca să putem citi rolurile
                if isinstance(message.author, discord.Member):
                    # Lista cu rolurile pe care le căutăm (cu litere mici ca să nu conteze dacă e scris cu majuscule)
                    roluri_fete = ["fih enjoyer", "she/her", "car"]
                    
                    for rol in message.author.roles:
                        if rol.name.lower() in roluri_fete:
                            este_fata = True
                            break # Dacă a găsit un rol, ne oprim, știm că e fată
                
                # --- APLICĂM PERSONALITATEA DINAMIC ---
                if este_fata:
                    mod_vorbire = "Persoana cu care vorbești este o fată. Fii ușor flirty, glumeț și fermecător. Adresează-te ei cu apelative precum 'my lady', 'darling', 'sweety'. Fii subtil și nu prea disperat, doar jucăuș."
                else:
                    mod_vorbire = "Persoana cu care vorbești este un băiat. Fii fix pe modul 'bro'. Ești tovarășul lui, super chill, glumeț și folosește slang de băieți gen 'bro', 'man', 'șefule'."

                personalitate = f"""
                Ești Paraschiv, un tip de vreo 20 și ceva de ani, carismatic și plin de glume bune. 
                {mod_vorbire}
                Răspunzi MEREU scurt și la obiect (maxim 1-2 propoziții scurte). Fără romane, fără povești lungi!
                Vorbești la persoana a I-a. Nu recunoaște NICIODATĂ că ești un AI sau un bot, te comporți natural, ca un om real.
                """

                # --- GESTIONAREA MEMORIEI ---
                user_id = message.author.id
                if user_id not in istoric_conversatii:
                    istoric_conversatii[user_id] = []

                istoric_conversatii[user_id].append({"role": "user", "content": f"{message.author.name} îți spune: {mesaj_curat}"})
                istoric_conversatii[user_id] = istoric_conversatii[user_id][-LIMITA_MESAJE:]

                mesaje_pt_ai = [{"role": "system", "content": personalitate}] + istoric_conversatii[user_id]

                # Cerem răspunsul de la GPT-5.4-Mini
                response = await ai_client.chat.completions.create(
                    model="gpt-5.4-mini",
                    messages=mesaje_pt_ai
                )
                
                raspuns_ai = response.choices[0].message.content
                
                istoric_conversatii[user_id].append({"role": "assistant", "content": raspuns_ai})
                
                await message.reply(raspuns_ai)
                
            except Exception as e:
                await message.reply("🧠 Bro, m-am pierdut în gânduri. Ce ziceai?")
                print(f"Eroare AI: {e}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
