######################################################

 # Discord bot development outsourcing #
 # 작성자 : 김찬빈 (Kim Chan Been, https://github.com/devbini)
 # 코드 작성 날짜 (업데이트 날짜) : 2024-08-16

 # 파일 역할
 # 1. 채팅 코멘트 답변 기능 (현재 3가지 지원)
 # 2. 역할 부여 및 삭제 기능 (신규입장 매크로 지원)
 # 3. 유튜브 영상 재생 기능

######################################################

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from dotenv import load_dotenv
from datetime import timedelta
import os
import yt_dlp as youtube_dl
import asyncio

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값 가져오기
TOKEN = os.getenv('DISCORD_TOKEN')

# 신규 역할
외부인_역할_ID = int(os.getenv('EXTERNAL_ROLE_ID'))
하랑_역할_ID = int(os.getenv('HARANG_ROLE_ID'))
웰컴_역할_ID = int(os.getenv('WELCOME_ROLE_ID'))
남자_역할_ID = int(os.getenv('MALE_ROLE_ID'))
여자_역할_ID = int(os.getenv('FEMALE_ROLE_ID'))

# 주의 역할들
주의_역할_ID = int(os.getenv('CAUTION_ROLE_ID'))
경고1_역할_ID = int(os.getenv('WARNING1_ROLE_ID'))
경고2_역할_ID = int(os.getenv('WARNING2_ROLE_ID'))
경고3_역할_ID = int(os.getenv('WARNING3_ROLE_ID'))

# 사용 권한
권한_역할_1_ID = int(os.getenv('MANAGER1_ROLE_ID'))
권한_역할_2_ID = int(os.getenv('MANAGER2_ROLE_ID'))
권한_역할_3_ID = int(os.getenv('MANAGER3_ROLE_ID'))
권한_역할_4_ID = int(os.getenv('MANAGER4_ROLE_ID'))

# 생일
생일_역할_ID = int(os.getenv('BIRTHDAY_ROLE_ID'))

#누적 후원금
total_pay = int(0);
#남은 후원금
exit_pay = int(0);

# Message Content Intent 활성화
intents = nextcord.Intents.default()
intents.members = True  # 멤버 관련 이벤트를 받기 위해 활성화
intents.message_content = True  # Message content intent 활성화

bot = commands.Bot(command_prefix="!", intents=intents)

# 유튜브 다운로드 옵션 설정
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio',  # 'bestaudio/best'에서 'bestaudio'로 변경
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# 유튜브 URL 읽기 클래스
class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # Take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# 유튜브 뮤직 플레이어 클래스 (재생목록)
class MusicPlayer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.play_next_song = asyncio.Event()
        self.current = None

    async def add_to_queue(self, url, title):
        await self.queue.put((url, title))

    async def play(self, voice_client):
        while True:
            self.play_next_song.clear()
            url, title = await self.queue.get()
            try:
                self.current = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
                voice_client.play(self.current, after=lambda e: bot.loop.call_soon_threadsafe(self.play_next_song.set))
                await self.play_next_song.wait()
            except Exception as e:
                print(f'Error: {str(e)}')

music_player = MusicPlayer()

# [함수] READY
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# [함수] 코멘트 답변 시스템
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 환경 변수에서 응답을 가져옵니다.
    response_dukdak = os.getenv("RESPONSE_DUKDAK")
    response_hana = os.getenv("RESPONSE_HANA")
    response_donate = os.getenv("RESPONSE_DONATE_1")

    if message.content == "둑닥":
        await message.channel.send(response_dukdak)

    elif message.content == "하나":
        await message.channel.send(response_hana)

    elif message.content == "후원 계좌" or message.content == "후원계좌":
        await message.channel.send(response_donate)

    await bot.process_commands(message)

# [함수] 역할 부여 매크로
@bot.slash_command(name="신규입장", description="신규 입장자를 환영합니다.")
async def 신규입장(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="신규 입장자의 멘션", required=True),
        성별: str = SlashOption(name="성별", description="남자 또는 여자", required=True, choices={"남자": "남자", "여자": "여자"}),
        닉네임: str = SlashOption(name="닉네임", description="새로운 닉네임", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    guild = interaction.guild
    외부인_역할 = guild.get_role(외부인_역할_ID)
    하랑_역할 = guild.get_role(하랑_역할_ID)
    웰컴_역할 = guild.get_role(웰컴_역할_ID)
    성별_역할 = guild.get_role(남자_역할_ID if 성별 == "남자" else 여자_역할_ID)

    if not 외부인_역할 or not 웰컴_역할 or not 성별_역할:
        await interaction.response.send_message("역할 ID가 올바르지 않거나 역할이 존재하지 않습니다.", ephemeral=True)
        return

    try:
        if 외부인_역할 in 멘션.roles:
            await 멘션.remove_roles(외부인_역할)
        await 멘션.add_roles(웰컴_역할, 성별_역할, 하랑_역할)
        await 멘션.edit(nick="〔 🤍 〕 " + 닉네임)
        await interaction.response.send_message(f"반갑다, {멘션.mention}!")
    except nextcord.Forbidden:
        await interaction.response.send_message("대상의 권한이 너무 높아요...", ephemeral=True)

# [함수] 생일자 역할 부여
@bot.slash_command(name="생일", description="생일인 사람에게 생일 역할을 부여합니다.")
async def 생일(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="생일자의 멘션", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    guild = interaction.guild
    생일_역할 = guild.get_role(생일_역할_ID)

    if not 생일_역할:
        await interaction.response.send_message("생일 역할 ID가 올바르지 않거나 역할이 존재하지 않습니다.", ephemeral=True)
        return

    try:
        await 멘션.add_roles(생일_역할)
        await interaction.response.send_message(f"생일 축하해, {멘션.mention}!")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 작업을 수행할 수 없습니다.", ephemeral=True)

# [함수] 닉네임 변경
@bot.slash_command(name="이름_변경", description="사용자의 닉네임을 변경합니다.")
async def 이름_변경(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="닉네임을 변경할 사용자의 멘션", required=True),
        닉네임: str = SlashOption(name="닉네임", description="새로운 닉네임", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    try:
        await 멘션.edit(nick=닉네임)
        await interaction.response.send_message(f"{멘션.mention}의 닉네임이 변경되었습니다.")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 닉네임을 변경할 수 없습니다.", ephemeral=True)

# [함수] 역할 삭제
@bot.slash_command(name="역할_삭제", description="사용자에게서 역할을 제거합니다.")
async def 역할_삭제(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="역할을 제거할 사용자의 멘션", required=True),
        역할: nextcord.Role = SlashOption(name="역할", description="제거할 역할", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    try:
        await 멘션.remove_roles(역할)
        await interaction.response.send_message(f"{멘션.mention}에게서 {역할.name} 역할이 제거되었습니다.")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 역할을 제거할 수 없습니다.", ephemeral=True)

# [함수] 역할 추가
@bot.slash_command(name="역할_추가", description="사용자에게 역할을 추가합니다.")
async def 역할_추가(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="역할을 추가할 사용자의 멘션", required=True),
        역할: nextcord.Role = SlashOption(name="역할", description="추가할 역할", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    try:
        await 멘션.add_roles(역할)
        await interaction.response.send_message(f"{멘션.mention}에게 {역할.name} 역할이 추가되었습니다.")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 역할을 추가할 수 없습니다.", ephemeral=True)

# [함수] 경고 역할 부여 (타임아웃 포함)
@bot.slash_command(name="경고", description="사용자에게 경고를 부여합니다.")
async def 경고(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="경고를 부여할 사용자의 멘션", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    guild = interaction.guild
    주의_역할 = guild.get_role(주의_역할_ID)
    경고1_역할 = guild.get_role(경고1_역할_ID)
    경고2_역할 = guild.get_role(경고2_역할_ID)
    경고3_역할 = guild.get_role(경고3_역할_ID)

    if 경고3_역할 in 멘션.roles:
        await interaction.response.send_message(f"{멘션.mention}님은 이미 최대 경고 상태입니다.", ephemeral=True)
        return

    try:
        if 주의_역할 in 멘션.roles:
            await 멘션.remove_roles(주의_역할)
            await 멘션.add_roles(경고1_역할)
            await 멘션.timeout(timedelta(seconds=600))
            await interaction.response.send_message(f"{멘션.mention}님에게 '경고1' 역할이 부여되고 10분간 타임아웃되었습니다.")
        elif 경고1_역할 in 멘션.roles:
            await 멘션.remove_roles(경고1_역할)
            await 멘션.add_roles(경고2_역할)
            await 멘션.timeout(timedelta(seconds=3600))
            await interaction.response.send_message(f"{멘션.mention}님에게 '경고2' 역할이 부여되고 1시간 타임아웃되었습니다.")
        elif 경고2_역할 in 멘션.roles:
            await 멘션.remove_roles(경고2_역할)
            await 멘션.add_roles(경고3_역할)
            await 멘션.timeout(timedelta(minutes=1440))
            await interaction.response.send_message(f"{멘션.mention}님에게 '경고3' 역할이 부여되고 1일간 타임아웃되었습니다.")
        else:
            await 멘션.add_roles(주의_역할)
            await interaction.response.send_message(f"{멘션.mention}님에게 '주의' 역할이 부여되었습니다.")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 역할을 부여할 수 없습니다.", ephemeral=True)

# [함수] 경고 역할 감소 (타임아웃 포함)
@bot.slash_command(name="해제", description="사용자에게서 경고를 해제합니다.")
async def 해제(
        interaction: Interaction,
        멘션: nextcord.Member = SlashOption(name="멘션", description="경고를 해제할 사용자의 멘션", required=True)
):
    명령어_사용자 = interaction.user
    권한_역할_1 = interaction.guild.get_role(권한_역할_1_ID)
    권한_역할_2 = interaction.guild.get_role(권한_역할_2_ID)
    권한_역할_3 = interaction.guild.get_role(권한_역할_3_ID)
    권한_역할_4 = interaction.guild.get_role(권한_역할_4_ID)

    if 권한_역할_4 not in 명령어_사용자.roles:
        await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
        return

    try:
        await 멘션.timeout(timedelta(seconds=0))
        await interaction.response.send_message(f"{멘션.mention}님의 타임아웃을 삭제하였습니다..")
    except nextcord.Forbidden:
        await interaction.response.send_message("권한이 부족하여 역할을 제거할 수 없습니다.", ephemeral=True)

# [함수] 유튜브 뮤직 플레이어 재생
@bot.slash_command(name="play", description="유튜브 음악 URL을 제공하여 음악을 재생합니다.")
async def play(interaction: Interaction,
               url: str = SlashOption(name="url", description="재생할 유튜브 음악 URL", required=True)):
    channel = interaction.user.voice.channel
    if not channel:
        await interaction.response.send_message("먼저 음성 채널에 접속해주세요.", ephemeral=True)
        return

    await interaction.response.defer()  # 응답 지연 처리

    voice_client = nextcord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()

    # 음악 재생을 위한 yt-dlp 설정
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info.get('title', 'Unknown Title')

        await music_player.add_to_queue(url2, title)

        if not voice_client.is_playing():
            await music_player.play(voice_client)

        await interaction.followup.send(f'큐에 추가됨: {title}')
    except Exception as e:
        await interaction.followup.send(f'음악 재생 중 오류가 발생했습니다: {str(e)}')

# [함수] 현재 재생중인 유튜브 노래 스킵
@bot.slash_command(name="skip", description="현재 재생 중인 음악을 건너뜁니다.")
async def skip(interaction: Interaction):
    voice_client = nextcord.utils.get(bot.voice_clients, guild=interaction.guild)
    if not voice_client or not voice_client.is_connected() or not voice_client.is_playing():
        await interaction.response.send_message("현재 재생 중인 음악이 없습니다.", ephemeral=True)
        return

    voice_client.stop()
    await interaction.response.send_message("음악을 건너뜁니다.")

# [함수] 큐에 올라 가 있는 유튜브 재생목록 표시
@bot.slash_command(name="playlist", description="현재 대기 중인 음악 목록을 표시합니다.")
async def playlist(interaction: Interaction):
    if music_player.queue.empty():
        await interaction.response.send_message("현재 대기 중인 음악이 없습니다.", ephemeral=True)
        return

    upcoming = list(music_player.queue._queue)
    message = '\n'.join(title for url, title in upcoming)
    await interaction.response.send_message(f'현재 대기 중인 음악 목록:\n{message}')

# [함수] 현재 재생중인 유튜브 영상 정보 표시
@bot.slash_command(name="info", description="현재 재생 중인 곡의 정보를 표시합니다.")
async def info(interaction: Interaction):
    if not music_player.current:
        await interaction.response.send_message("현재 재생 중인 곡이 없습니다.", ephemeral=True)
        return

    embed = nextcord.Embed(title="현재 재생 중인 곡", description=music_player.current.title, color=0x00ff00)

    if music_player.current.duration is not None:
        embed.add_field(name="길이", value=str(timedelta(seconds=music_player.current.duration)))
    else:
        embed.add_field(name="길이", value="알 수 없음")

    if music_player.current.thumbnail:
        embed.set_thumbnail(url=music_player.current.thumbnail)

    await interaction.response.send_message(embed=embed)

# 봇 시작
bot.run(TOKEN)