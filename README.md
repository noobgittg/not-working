# ⚡ MMW All-In-One Pro Bot (Ultra-Fast Master Edition)

> 🚀 **Production-Ready Multi-Purpose Telegram Bot & Web Platform**  
> Consolidating Rename, File Pro Studio (Trim, Extract Audio/Subs, Add Audio/Subs, MediaInfo), FFmpeg Video Compressor, FastAPI Range Streaming (HTTP 206) & Plyr Web Player, Automatic Thumbnail Changer (THAM_URL), Dynamic Captions, Auto-Delete, Auto-Approve, Group Cleaner, String Session Generator, and Developer Diagnostics (DevilMod).
>
> 📢 **Official Watermark / Channel**: [t.me/mallumovieworldmain2](https://t.me/mallumovieworldmain2)

---

## 🌟 Master Highlights

- ⚡ **Ultra-Fast Engine**: Asynchronous architecture powered by **Python 3.10+**, **Pyrofork**, **FastAPI**, and **Motor (MongoDB)**.
- 💾 **Dual-Layer Caching Engine**: `FastMemoryCache` (in-memory TTL cache with LRU/FIFO eviction and max entries) minimizes MongoDB round-trip operations for sub-millisecond user preferences and thumbnail resolution.
- 🛠️ **File Pro Advanced Studio (`/pro`)**:
  - 📊 **MediaInfo**: Deep stream probe analyzing container, video/audio codecs, bitrates, frame rates, and embedded subtitles.
  - 🎵 **Extract All Audio**: Automatically extracts every embedded audio track into standalone files with tagged languages and formats.
  - 💬 **Extract All Subtitles**: Extracts all embedded subtitle streams into `.srt` or `.ass` format files.
  - ➕🎵 **Add / Replace Audio**: Merges external audio files (.mp3, .m4a, .aac) into video containers with dual audio or replacement modes.
  - ➕💬 **Add Subtitles**: Soft-muxes subtitle tracks (.srt, .ass) directly into video without re-encoding video stream.
  - ✂️ **Trim Video**: Precision video clipping by timestamp (e.g. `00:01:00 00:02:30`) utilizing ultra-fast stream copy with fallback transcode.
- ✏️ **Pro Rename System**: Reply to any media or execute `/rename <filename>`, preserving extensions, custom captions, thumbnails, with real-time download and upload progress updates.
- 🗜️ **FFmpeg Video Compressor**:
  - Resolution scaling (1080p, 720p, 480p, 360p).
  - Presets: `ultrafast`, `superfast`, `veryfast` with granular CRF controls.
  - Target size compression (`compress_to_target_size`).
  - Live progress tracking directly from FFmpeg execution.
- 🎬 **Instant Web Streaming & Player**:
  - FastAPI server with HTTP 206 Partial Content (Range requests) for instant seeking.
  - Embedded modern Plyr v3 dark mode web player.
  - One-click launch buttons for external mobile video players (**VLC**, **MX Player**, **PlayIt**, **KMPlayer**, **PotPlayer**).
  - Direct fast file download route (`/file/{file_id}`).
  - Interactive web file search and inspector on the home page (`/`).
- 🖼️ **Smart Automatic Thumbnail Changer**:
  - Mode A: Reply to a photo with `/setthumb` to set custom user thumbnail.
  - Mode B: Global or dynamic `THAM_URL` (configured via env or `/setthumb <URL>`) automatically applied to files.
  - Fallback to extracted video screenshot.
- 📝 **Dynamic Caption Formatting**:
  - Template variables: `{filename}`, `{filesize}`, `{duration}`, `{ext}`, `{original_caption}`, `{watermark}`, `{date}`, `{time}`.
  - Fallback: active custom caption -> dynamic `cap[]` list -> media caption -> default template.
  - Subtle watermark `t.me/mallumovieworldmain2` automatically appended to all output captions.
- ⏱️ **Auto-Delete Scheduler**:
  - Timed message deletion (5m, 15m, 30m, 1h, 6h, 24h, custom seconds) via background worker.
- 🤝 **Auto-Approve Join Requests**:
  - Instantly accepts channel and group join requests and sends a smallcaps welcome notification in PM.
- 🧹 **Group Moderation & Cleaner**:
  - Auto-deletes service messages (joined, left, pinned, video calls).
  - `/clean <num>` or `/purge` command for group administrators.
- 🔑 **String Session Generator**:
  - Interactive Pyrogram / Pyrofork and Telethon string session guide in private chat.
- 🛠️ **Developer Diagnostics & DevilMod (`/dev`, `/devilmod`)**:
  - Real-time system architecture, active asyncio tasks, garbage collection stats, memory usage, cache hit ratio, and database connection latency.

---

## 📂 Project Architecture

```text
MMWbot_newcombo/
├── app/
│   ├── bot/
│   │   ├── client.py           # Custom Pyrofork Client with connection pooling
│   │   └── handlers/
│   │       ├── __init__.py     # Clean package marker
│   │       ├── admin.py        # /admin, /stats, /users, /userinfo, /broadcast, /ban, /unban, /cache, /database, /logs, /restart, /dev, /devilmod
│   │       ├── approve.py      # Auto-approve join requests
│   │       ├── autodelete.py   # /autodelete & timer menu
│   │       ├── callbacks.py    # Navigation callbacks (home, pro, help, settings, etc.)
│   │       ├── cancel.py       # /cancel & cancel_op callback handler
│   │       ├── caption.py      # /caption, /setcaption, /addcaption (cap[])
│   │       ├── channel.py      # Channel post automation
│   │       ├── cleaner.py      # /clean, /purge & service message cleaner
│   │       ├── compressor.py   # /compress & FFmpeg video compressor
│   │       ├── extra.py        # /ping, /speedtest, /id, /info, /search, /mediainfo
│   │       ├── file_pro.py     # /pro, /trim, /extractaudio, /extractsub, /addaudio, /addsub, /mediainfo
│   │       ├── rename.py       # /rename, /setprefix, /setsuffix file renamer
│   │       ├── session.py      # /session string generator
│   │       ├── start.py        # /start, /help, /about, /status, /settings
│   │       ├── streamer.py     # /stream & streaming link generator
│   │       └── thumbnail.py    # /thumb, /setthumb, /delthumb
│   ├── database/
│   │   ├── mongodb.py          # Motor AsyncIOMotorClient with pooling & indexes
│   │   ├── models.py           # Typed schema models
│   │   └── repositories/
│   │       ├── user_repo.py    # User settings repository (CRUD + pagination + cache)
│   │       ├── chat_repo.py    # Channel & Group settings repository (CRUD + cache)
│   │       └── file_repo.py    # Streaming files repository (CRUD + search + cache)
│   ├── services/
│   │   ├── ffmpeg_service.py   # FFmpeg video compression, trimming, audio/sub extraction & muxing
│   │   ├── thumb_service.py    # Thumbnail resolver (Custom -> THAM_URL -> Frame)
│   │   ├── caption_service.py  # Caption formatter with watermark
│   │   ├── autodel_service.py  # Background sweeper for expired messages
│   │   └── keepalive_service.py# 6-Type KeepAlive engine & 24h restart scheduler
│   ├── utils/
│   │   ├── cache.py            # FastMemoryCache (bounded in-memory TTL cache with statistics)
│   │   ├── font.py             # Smallcaps typography utilities
│   │   ├── helpers.py          # Time formatting, byte sizing, filename sanitizing, admin checks
│   │   ├── logger.py           # Structured logging with in-memory buffer
│   │   └── progress.py         # Throttle Pyrogram upload/download progress bar
│   └── web/
│       ├── app.py              # FastAPI initialization and middleware
│       ├── web_support.py      # Uvicorn background server runner
│       ├── routes/
│       │   ├── api.py          # JSON API endpoints (/api/status, /api/info/{file_id}, /api/search, /api/ping)
│       │   ├── pages.py        # HTML views (/, /watch/{file_id}, /download/{file_id})
│       │   └── stream.py       # HTTP 206 partial content streaming & /file/{file_id} direct download
│       └── templates/
│           ├── index.html      # Landing dashboard with live metrics and stream inspector
│           ├── watch.html      # Plyr web video/audio player with external player launchers
│           └── dl.html         # High-speed direct download interface
├── config.py                   # Central environment configuration
├── main.py                     # Unified entry point running bot + web + workers
├── Dockerfile                  # Container definition with FFmpeg
├── docker-compose.yml          # Local container stack with MongoDB
├── requirements.txt            # Production dependencies
├── runtime.txt                 # python-3.10
└── Procfile                    # Koyeb / Heroku process declaration
```

---

## 📋 Comprehensive Command Directory

| Command | Usage Example | Purpose of Use | Access |
| :--- | :--- | :--- | :--- |
| `/start` | `/start` | Starts the bot, checks force-subscribe, and displays interactive main menu | Public |
| `/help` / `/commands` | `/help` | Detailed guide and sample usage of all bot commands | Public |
| `/about` | `/about` | Displays bot specifications, framework, and watermark | Public |
| `/ping` / `/uptime` | `/ping` | Displays latency (ms) and engine uptime with a live Refresh button | Public |
| `/id` / `/myid` | `/id` | Displays Account ID, Chat ID, Message ID, Datacenter (DC) | Public |
| `/info` / `/whois` | `/info` or `/info @user` | Inspects Telegram profile details, ID, DC, bot/premium status | Public |
| `/speedtest` | `/speedtest` | Measures real network socket latency to major backbones | Public |
| `/cancel` | `/cancel` | Aborts any active interactive prompt (rename, trim, audio mux, session) | Public |
| `/pro` / `/tools` | Reply to file with `/pro` | Opens File Pro Studio (Trim, Extract Audio/Subs, Add Audio/Subs, MediaInfo) | User / Admins |
| `/trim` | `/trim 00:01:00 00:02:30` | Precision video clipping without quality loss or full re-encoding | User / Admins |
| `/extractaudio` | Reply to video with `/extractaudio` | Extracts all audio tracks from video into separate audio files | User / Admins |
| `/extractsub` | Reply to video with `/extractsub` | Extracts all embedded subtitle streams into `.srt` / `.ass` files | User / Admins |
| `/addaudio` | Reply to video with `/addaudio` | Merges external audio file into video (choice of adding or replacing) | User / Admins |
| `/addsub` | Reply to video with `/addsub` | Soft-muxes external subtitle file into video container | User / Admins |
| `/mediainfo` | Reply to media with `/mediainfo` | Deep stream probe using ffprobe (codec, resolution, bitrate, tracks) | User / Admins |
| `/rename` | `/rename movie.mp4` | Renames media file with progress bar, custom thumbnail, and caption | User / Admins |
| `/setprefix` | `/setprefix [MMW] ` | Sets filename prefix automatically added during rename | User / Admins |
| `/setsuffix` | `/setsuffix  @channel` | Sets filename suffix automatically added before extension | User / Admins |
| `/delprefix` | `/delprefix` | Removes saved custom filename prefix | User / Admins |
| `/delsuffix` | `/delsuffix` | Removes saved custom filename suffix | User / Admins |
| `/compress` | Reply to video with `/compress` | Selects resolution (1080p, 720p, 480p, 360p) & CRF to compress video | User / Admins |
| `/stream` | Reply to media with `/stream` | Generates web streaming URL, watch link, and direct download URL | User / Admins |
| `/getfile` | `/getfile <file_id>` | Sends indexed file directly to chat by its stream file ID | User / Admins |
| `/revoke` | `/revoke <file_id>` | Revokes and deletes indexed stream file from database | User / Admins |
| `/search` | `/search avengers` | Searches indexed media files in database with direct watch & download buttons | User / Admins |
| `/setthumb` | Reply to photo with `/setthumb` or `/setthumb <URL>` | Saves custom thumbnail for your account | User / Admins |
| `/thumb` | `/thumb` | Views your currently saved custom thumbnail | User / Admins |
| `/delthumb` | `/delthumb` | Deletes your custom thumbnail and reverts to THAM_URL | User / Admins |
| `/setcaption` | `/setcaption 📁 {filename}` | Sets your default dynamic caption template | User / Admins |
| `/addcaption` | `/addcaption 🎬 {filename}` | Appends caption template to dynamic `cap[]` cycling list | User / Admins |
| `/caption` | `/caption` | Displays your active custom caption and dynamic templates | User / Admins |
| `/delcaption` | `/delcaption` | Clears custom captions and resets to default template | User / Admins |
| `/autodelete` | `/autodelete 300` | Sets self-destruct timer for processed messages (e.g. 300s = 5m) | User / Admins |
| `/session` | `/session` | Interactive String Session generator for Pyrogram and Telethon | User / Admins |
| `/clean` / `/purge` | `/clean 20` | Purges recent messages from supergroup or chat (Group Admin) | Group Admins |
| `/admin` | `/admin` | Interactive Admin Control Panel for bot maintenance | **Admins Only** |
| `/stats` | `/stats` | Displays live database counts, disk space, and cache statistics | **Admins Only** |
| `/users` | `/users` | Paginated directory of all registered users with Next/Prev buttons | **Admins Only** |
| `/user` / `/userinfo` | `/userinfo <user_id>` | Deep inspection card of a user (ban status, thumbnail, caption, auto-del) | **Admins Only** |
| `/broadcast` | `/broadcast` (reply to message) | Broadcasts text or media to all registered users with FloodWait protection | **Admins Only** |
| `/ban` | `/ban <user_id>` | Permanently bans user from bot services | **Admins Only** |
| `/unban` | `/unban <user_id>` | Restores access for a banned user | **Admins Only** |
| `/cache` | `/cache` | Inspects in-memory cache metrics with Clear Cache button | **Admins Only** |
| `/database` / `/dbstats`| `/database` | MongoDB collection counts, index health, and ping latency | **Admins Only** |
| `/logs` | `/logs` | Views last 20 lines of application runtime logs safely | **Admins Only** |
| `/restart` | `/restart` | Gracefully restarts the bot process and web server | **Admins Only** |
| `/dev` / `/developer` | `/dev` | Full developer console with live asyncio tasks and memory diagnostics | **Admins Only** |
| `/devilmod` | `/devilmod on` / `/devilmod off` | Toggles Devil / Developer mode with deep runtime diagnostics | **Admins Only** |

---

## 🌐 Web & API Endpoints

| Method | Endpoint | Purpose | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Web dashboard with live metrics and stream inspector | Public |
| `GET` | `/health` | Application health check endpoint | Public |
| `GET` | `/watch/{file_id}` | HTML5 Plyr video/audio player with external player launchers | Public |
| `GET` | `/download/{file_id}` | Web download landing page with file metadata | Public |
| `GET` | `/dl/{file_id}` | Alias for `/download/{file_id}` | Public |
| `HEAD` | `/stream/{file_id}` | HTTP HEAD check for media stream parameters | Public |
| `GET` | `/stream/{file_id}` | HTTP 206 Partial Content video/audio streaming | Public |
| `HEAD` | `/file/{file_id}` | HTTP HEAD check for direct file download | Public |
| `GET` | `/file/{file_id}` | Direct file attachment download | Public |
| `GET` | `/api/status` | JSON live system metrics (users, chats, files, cache, uptime) | Public |
| `GET` | `/api/stats` | Alias for `/api/status` | Public |
| `GET` | `/api/health` | Health API endpoint returning healthy status | Public |
| `GET` | `/api/ping` | Latency ping endpoint | Public |
| `GET` | `/api/info/{file_id}` | JSON metadata for an indexed media file | Public |
| `GET` | `/api/search?q={query}` | JSON search across indexed media files | Public |

---

## 🛠️ Environment Variables Configuration

Create a `.env` file in the root directory (based on `.env.example`):

```env
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627
BOT_TOKEN=123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
OWNER_ID=1892771262
ADMINS=1892771262

MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=MMW_ProBot

PORT=8080
BASE_URL=https://your-app-name.koyeb.app
BIN_CHANNEL=-1001234567890
LOG_CHANNEL=-1001234567890

THAM_URL=https://envs.sh/thumb.jpg
WATERMARK=t.me/mallumovieworldmain2
WATERMARK_URL=https://t.me/mallumovieworldmain2
FORCE_SUB_CHANNEL=mallumovieworldmain2
WORKERS=50
CACHE_TTL=600
CACHE_MAX_ENTRIES=1000
AUTO_DELETE_TIME=0
```

---

## 🚀 Running & Deployment

### Local / VPS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### Docker:
```bash
docker-compose up --build -d
```

### Koyeb:
Deploy directly using the included `Dockerfile` and `Procfile`.
Ensure `PORT=8080` is configured in service ports.
