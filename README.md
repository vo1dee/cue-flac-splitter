# Audio Tools Collection

Tools for managing FLAC albums: CUE splitting, downsampling, and lyrics fetching.

## Tools

| Script | Description |
|--------|-------------|
| `split-cue-unicode.pl` | Split single-file CUE+FLAC albums (Unicode-safe) |
| `flac_downsampler.sh` | Downsample hi-res FLAC to 44.1kHz/16bit |
| `audio_lyrics_fetcher.py` | Fetch lyrics for FLAC/MP3/M4A files |

## Setup

```bash
# For lyrics fetcher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

**Split CUE+FLAC:**
```bash
./split-cue-unicode.pl album.cue
```

**Downsample FLAC:**
```bash
./flac_downsampler.sh /path/to/music
```

**Fetch lyrics:**
```bash
python3 audio_lyrics_fetcher.py /path/to/music
```

## Requirements

- `ffmpeg` - for splitting and downsampling
- Python 3 with `mutagen`, `requests` - for lyrics fetcher
