FROM python:3.12-slim
​ENV PYTHONUNBUFFERED=1 
DEBIAN_FRONTEND=noninteractive
​WORKDIR /app
​Install FFmpeg, FFprobe, and required build tools
​RUN apt-get update && apt-get install -y --no-install-recommends 
ffmpeg 
curl 
git 
build-essential 
&& rm -rf /var/lib/apt/lists/*
​Install python dependencies
​COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && 
pip install --no-cache-dir -r requirements.txt
​Ensure static binaries are ready as fallback
​RUN python3 -c "import static_ffmpeg; static_ffmpeg.add_paths()" || true
​Copy project files
​COPY . .
​CMD ["python3", "main.py"]
