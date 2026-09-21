# ⚡ MMW All-In-One Pro Bot (Ultra-Fast Master Edition)

> 🚀 **Next-Generation Multi-Purpose Telegram Bot Repository**
> Consolidating Rename, FFmpeg Video Compressor, FastAPI Streaming & Plyr Web Player, Automatic Thumbnail Changer (THAM_URL), Dynamic Captions, Auto-Delete, Auto-Approve, Group Cleaner & String Session Generator.
>
> 📢 **Official Watermark / Channel**: [t.me/mallumovieworldmain2](https://t.me/mallumovieworldmain2)

---

## 🌟 Master Highlights

- ⚡ **Ultra-Fast Engine**: Asynchronous architecture powered by **Python 3.10+**, **Pyrofork**, **FastAPI**, and **PyMongo Async (MongoDB)**.
- 💾 **Dual-Layer Caching Engine**: `FastMemoryCache` (in-memory TTL cache) minimizes MongoDB round-trip operations for sub-millisecond user preferences and thumbnail resolution.
- ✏️ **Pro Rename System**: Reply to any media or execute `/rename <filename>`, preserving extensions, custom captions, thumbnails, with real-time download and upload progress updates.
- 🗜️ **FFmpeg Video Compressor**:
  - Resolution scaling (1080p, 720p, 480p, 360p).
  - Presets: `ultrafast`, `superfast`, `veryfast` with granular CRF controls.
  - Live progress tracking directly from FFmpeg execution.
- 🎬 **Instant Web Streaming & Player**:
  - FastAPI server with HTTP 206 Partial Content (Range requests) for instant seeking.
  - Embedded modern Plyr v3 dark mode web player.
  - HTTP(S) stream links that can be opened by VLC, MX Player, browser players, and other clients supporting byte-range requests.
  - Direct file download route (`/file/<file_id>`) plus a human-friendly download page (`/download/<file_id>`).
- 🖼️ **Smart Automatic Thumbnail Changer**:
  - Mode A: Reply to a photo with `/setthumb` to set custom user thumbnail.
  - Mode B: Global or dynamic `THAM_URL` (configured via env or `/setthumb <URL>`) automatically applied to files.
  - Fallback to extracted video screenshot.
- 📝 **Dynamic Caption Formatting**:
  - Template variables: `{filename}`, `{filesize}`, `{duration}`, `{ext}`.
  - Subtle watermark `t.me/mallumovieworldmain2` automatically appended to all output captions.
- ⏱️ **Auto-Delete Scheduler**:
  - Timed message deletion (5m, 15m, 30m, 1h, 6h, 24h, custom seconds) via background worker.
- 🤝 **Auto-Approve Join Requests**:
  - Instantly accepts channel and group join requests and sends a smallcaps welcome notification in PM.
- 🧹 **Group Moderation & Cleaner**:
  - Auto-deletes service messages (joined, left, pinned, video calls).
  - `/clean <num>` or `/purge` command for group administrators.
- 🔑 **String Session Generator**:
  - Interactive Pyrogram / Pyrofork and Telethon string session generator in private chat.
- 🎨 **Super Sonic Smallcaps UI**:
  - All bot text, buttons, and progress indicators are formatted in Unicode Smallcaps with short emojis.

---

## 📂 Project Architecture

```text
MMW-BOT-PRO/
├── app/
│   ├── bot/
│   │   ├── client.py           # Custom Pyrofork Client with connection pooling
│   │   ├── callbacks/
│   │   │   └── router.py       # Centralized callback router with user authorization
│   │   └── handlers/
│   │       ├── callbacks.py    # Registered navigation callbacks
│   │       ├── start.py        # /start, /help, /about, /status, /settings
│   │       ├── rename.py       # /rename & interactive file renamer
│   │       ├── compressor.py   # /compress & FFmpeg video compressor
│   │       ├── streamer.py     # /stream & streaming link generator
│   │       ├── thumbnail.py    # /thumb, /setthumb, /delthumb
│   │       ├── caption.py      # /caption, /setcaption, /delcaption
│   │       ├── autodelete.py   # /autodelete & timer menu
│   │       ├── cleaner.py      # /clean, /purge & service message cleaner
│   │       ├── approve.py      # Auto-approve join requests
│   │       ├── session.py      # /session string generator
│   │       └── channel.py      # Channel post automation
│   ├── database/
│   │   ├── mongodb.py          # PyMongo Async client with pooling & indexes
│   │   ├── models.py           # Typed schema models
│   │   └── repositories/
│   │       ├── user_repo.py    # User settings repository
│   │       ├── chat_repo.py    # Channel & Group settings repository
│   │       └── file_repo.py    # Streaming files repository
│   ├── services/
│   │   ├── ffmpeg_service.py   # Async FFmpeg compression & metadata
│   │   ├── thumb_service.py    # Thumbnail resolver (Custom -> THAM_URL -> Frame)
│   │   ├── caption_service.py  # Caption formatter with watermark
│   │   ├── autodel_service.py  # Background sweeper for expired messages
│   │   └── keepalive_service.py# 6-Type KeepAlive engine & 24h restart scheduler
│   ├── web/
│   │   ├── app.py              # FastAPI app factory
│   │   ├── web_support.py      # Dedicated Koyeb web server support module
│   │   ├── routes/
│   │   │   ├── pages.py        # /, /health, /status, /watch/<file_id>, /download/<file_id>
│   │   │   ├── stream.py       # /stream/<file_id>, /file/<file_id> (HTTP 206 Partial Content)
│   │   │   └── api.py          # /api/status, /api/info/<file_id>, /api/search
│   │   └── templates/
│   │       ├── index.html      # Modern dashboard landing page
│   │       ├── watch.html      # Plyr v3 web player with standard HTTP(S) player URLs
│   │       └── dl.html         # Direct fast download card
│   └── utils/
│       ├── logger.py           # Structured logging
│       ├── font.py             # Unicode Smallcaps formatter & watermark injector
│       ├── cache.py            # FastMemoryCache TTL engine
│       ├── progress.py         # Throttled progress callback
│       └── helpers.py          # Byte/time formatting, URL validator & cleaners
├── config.py                   # Centralized configuration & environment loader
├── main.py                     # Unified entry point (Pyrofork + FastAPI concurrent runner)
├── requirements.txt            # Python dependencies
├── runtime.txt                 # python-3.12.10
├── Dockerfile                  # Production container definition with FFmpeg
├── docker-compose.yml          # Bot + MongoDB docker compose setup
├── Procfile                    # Koyeb / Heroku process definition
├── koyeb.yaml                  # Koyeb deployment manifest
├── .env.example                # Sample environment configuration
└── README.md                   # Full documentation
```

---

## 🛠️ Environment Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | Required |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) | Required |
| `BOT_TOKEN` | Telegram Bot Token from [@BotFather](https://t.me/BotFather) | Required |
| `OWNER_ID` | Telegram User ID of the primary owner | empty |
| `ADMINS` | Space-separated User IDs of authorized admins | empty |
| `MONGO_URI` | MongoDB Connection URI (`mongodb+srv://...`) | Required |
| `DATABASE_NAME` | MongoDB database name | `MMW_ProBot` |
| `BIN_CHANNEL` | Telegram Channel ID used for storing streaming media | `0` (uses source chat when unset) |
| `LOG_CHANNEL` | Telegram Channel ID for logs | Optional |
| `BASE_URL` | Public Web URL used in generated links | local fallback URL when unset |
| `PORT` | FastAPI web server port | `8080` |
| `THAM_URL` | Optional automatic fallback thumbnail URL | empty |
| `AUTO_DELETE_TIME` | Default message auto-delete period in seconds (0 = disabled) | `0` |
| `FORCE_SUB_CHANNEL` | Update channel username or link to enforce | Optional |
| `WORKERS` | Pyrofork concurrent worker threads | `50` |

---

## 🚀 Quick Start & Deployment

### 1. VPS / Local Deployment

```bash
# Clone the repository
git clone https://github.com/mmwbotzmain/MMW-BOT-PRO.git
cd MMW-BOT-PRO

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
sudo apt update && sudo apt install -y ffmpeg

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Launch Bot & Web Server
python3 main.py
```

### 2. Docker & Docker Compose

```bash
cp .env.example .env
# Fill in credentials in .env
docker compose up --build -d
```

Docker Compose keeps MongoDB on the internal compose network; it is not published on host port 27017. For Compose, set `MONGO_URI=mongodb://mongo:27017`.

### 3. Koyeb Deployment

1. Connect your repository to Koyeb.
2. Select Docker or buildpack (using `Procfile`).
3. Set your environment variables in Koyeb Settings.
4. Koyeb automatically maps the HTTP port and runs the health check at `/health`.

---

## 💧 Official Branding & Watermark

Every message, video player title, file caption, and landing page is embedded with:
**[t.me/mallumovieworldmain2](https://t.me/mallumovieworldmain2)**
## Runtime notes

`THAM_URL` is optional and empty by default. When configured, the thumbnail downloader accepts only public HTTP(S) image URLs and limits the downloaded image size. FFmpeg/ffprobe are required for media compression and deep mediainfo.

## Important platform limits

Renaming is deliberately rejected for media larger than 2000 MiB because the Telegram upload path used by the bot cannot upload the result above that ceiling. Compression accepts video/audio that FFmpeg can decode; outputs near or above the Telegram ceiling are split into binary parts for delivery. Files that Telegram itself cannot provide to the bot cannot be compressed locally.

Stream URLs use normal HTTP(S) links and byte-range requests. Telegram inline keyboard buttons use HTTP(S) URLs only; Android application intent/custom URI schemes are excluded because Telegram can reject them as invalid button URLs.
