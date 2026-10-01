# MMW All-In-One Pro — Commands & Endpoints

## Public commands
- `/start` — open the bot home menu.
- `/help` — open feature help.
- `/about` — show bot/runtime information.
- `/status` — show live service counters and status.
- `/settings` — view personal settings.
- `/rename <name.ext>` — rename replied media.
- `/setprefix <text>` — set a filename prefix.
- `/setsuffix <text>` — set a filename suffix.
- `/delprefix` — delete the saved prefix.
- `/delsuffix` — delete the saved suffix.
- `/compress` — compress replied media with the interactive menu.
- `/stream` — create a web stream link for replied media.
- `/setthumb` — save a replied image as thumbnail.
- `/thumb` — view the current thumbnail.
- `/delthumb` — delete the saved thumbnail.
- `/setcaption <template>` — save the active caption template.
- `/addcaption <template>` — add a caption template.
- `/caption` — view caption settings.
- `/delcaption <template>` — remove a caption template.
- `/autodelete <seconds>` — configure auto-delete.
- `/timer <seconds>` — configure auto-delete.
- `/clean` / `/purge` — clean supported service messages.
- `/session` — open the session tools.
- `/id` — show chat/user/message IDs.
- `/info` — show user/chat information.
- `/ping` — measure bot response latency.
- `/speedtest` — run the configured network speed test.
- `/mediainfo` — inspect replied media with FFprobe.
- `/search <keyword>` — search indexed files.
- `/pro` / `/filepro` / `/advance` / `/tools` — open the real media-tools menu.
- `/extractaudio` — extract audio from replied video.
- `/extractsub` — extract subtitles from replied video.
- `/addaudio` — merge audio into a replied video.
- `/addsub` — burn/add subtitles to a replied video.
- `/trim` — trim replied media.
- `/cancel` — cancel the current interactive operation.

## Admin-only commands
- `/admin` — open the admin dashboard.
- `/broadcast` — copy a replied message to registered users.
- `/restart` — restart the bot process.


## Web
- `/` — web home.
- `/help` — web help.
- `/stats` — live statistics page.
- `/search?q=term` — indexed file search.
- `/watch/{file_id}` — media player page.
- `/embed/{file_id}` — embeddable player.
- `/download/{file_id}` — download page.
- `/stream/{file_id}` — HTTP streaming with range support.
- `/file/{file_id}` or `/dl/{file_id}` — direct file stream/download.
- `/thumb/{file_id}` — real Telegram thumbnail.
- `/metadata/{file_id}` or `/info/{file_id}` — real metadata JSON.
- `/api/status`, `/api/stats`, `/api/search?q=term`, `/api/info/{file_id}` — JSON API.
- `/health` — health response.
- `/docs`, `/redoc`, `/openapi.json` — FastAPI documentation.

There are no `/media`, `/media2`, `/media3`, `/media4`, or `/media5` admin sections.
