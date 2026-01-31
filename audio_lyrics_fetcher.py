#!/usr/bin/env python3
"""
Audio Lyrics Fetcher for macOS
Recursively finds FLAC, ALAC (M4A), and MP3 files and fetches lyrics from the internet
"""

import os
import sys
from pathlib import Path
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3
import requests
import time
import re

class LyricsFetcher:
    def __init__(self):
        """Initialize the lyrics fetcher with multiple API sources"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.api_sources = ['lrclib', 'lyrics.ovh']  # Priority order

    def fetch_lyrics_lrclib(self, artist, title):
        """Fetch lyrics from LRCLIB API (fast and reliable)"""
        try:
            url = "https://lrclib.net/api/search"
            params = {
                'artist_name': artist,
                'track_name': title
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # Prefer synced lyrics over plain
                    synced = data[0].get('syncedLyrics', '')
                    plain = data[0].get('plainLyrics', '')
                    if synced:
                        return ('synced', synced)
                    elif plain:
                        return ('plain', plain)
            return None
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  ⚠️  Error from LRCLIB: {type(e).__name__}")
            return "RETRY"
        except Exception as e:
            print(f"  ⚠️  Error from LRCLIB: {type(e).__name__}")
            return None
    
    def fetch_lyrics_ovh(self, artist, title):
        """Fetch lyrics from lyrics.ovh API"""
        try:
            url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                lyrics = data.get('lyrics', '')
                if lyrics:
                    return ('plain', lyrics)
            return None
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  ⚠️  Error from lyrics.ovh: {type(e).__name__}")
            return "RETRY"
        except Exception as e:
            print(f"  ⚠️  Error from lyrics.ovh: {type(e).__name__}")
            return None
    
    def _try_source(self, name, fetch_func, *args, retries=2, delay=2):
        """Try a lyrics source with retries on timeout.
        Returns tuple (lyrics_type, lyrics_text) or None."""
        print(f"  📡 Trying {name}...")
        for attempt in range(retries):
            result = fetch_func(*args)
            if result == "RETRY":
                if attempt < retries - 1:
                    print(f"  🔄 Retrying {name} in {delay}s...")
                    time.sleep(delay)
                continue
            if result:
                lyrics_type, lyrics = result
                print(f"  ✅ Found {lyrics_type} lyrics from {name}!")
                return (lyrics_type, lyrics.strip())
            return None
        return None

    def fetch_lyrics(self, artist, title):
        """Main method to fetch lyrics with multiple fallback sources.
        Returns tuple (lyrics_type, lyrics_text) where lyrics_type is 'synced' or 'plain'."""
        print(f"  🔍 Fetching lyrics for: {artist} - {title}")

        # Clean up artist and title
        artist_clean = re.sub(r'[^\w\s-]', '', artist).strip()
        title_clean = re.sub(r'[^\w\s-]', '', title).strip()

        # Try LRCLIB first (fastest, most reliable, has synced lyrics)
        result = self._try_source("LRCLIB", self.fetch_lyrics_lrclib, artist, title)
        if result:
            return result

        # Try lyrics.ovh
        result = self._try_source("lyrics.ovh", self.fetch_lyrics_ovh, artist_clean, title_clean)
        if result:
            return result

        print(f"  ❌ No lyrics found from any source")
        return None

class AudioParser:
    def __init__(self, directory, delay=1.0):
        """
        Initialize the audio parser.
        
        Args:
            directory: Root directory to search for audio files
            delay: Delay between API requests (seconds) to be respectful
        """
        self.directory = Path(directory).expanduser().resolve()
        self.delay = delay
        self.lyrics_fetcher = LyricsFetcher()
        self.processed = 0
        self.found = 0
        self.errors = 0
    
    def extract_metadata(self, audio_path):
        """Extract artist and title from audio file metadata"""
        try:
            suffix = audio_path.suffix.lower()
            
            if suffix == '.flac':
                audio = FLAC(str(audio_path))
                artist = audio.get('artist', [None])[0] or audio.get('ARTIST', [None])[0]
                title = audio.get('title', [None])[0] or audio.get('TITLE', [None])[0]
            
            elif suffix == '.mp3':
                audio = MP3(str(audio_path))
                if audio.tags:
                    # Try ID3v2 tags
                    artist = str(audio.tags.get('TPE1', [''])[0]) if 'TPE1' in audio.tags else None
                    title = str(audio.tags.get('TIT2', [''])[0]) if 'TIT2' in audio.tags else None
                else:
                    artist, title = None, None
            
            elif suffix in ['.m4a', '.mp4']:
                audio = MP4(str(audio_path))
                artist = audio.tags.get('\xa9ART', [None])[0] if audio.tags else None
                title = audio.tags.get('\xa9nam', [None])[0] if audio.tags else None
            
            else:
                return None, None
            
            return artist, title
        except Exception as e:
            print(f"Error reading metadata from {audio_path.name}: {e}")
            return None, None
    
    def save_lyrics(self, audio_path, lyrics_type, lyrics):
        """Save lyrics to file with same name as audio file.
        Synced lyrics save as .lrc, plain lyrics save as .txt"""
        ext = '.lrc' if lyrics_type == 'synced' else '.txt'
        out_path = audio_path.with_suffix(ext)

        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            print(f"  ✓ Saved to: {out_path.name}")
            return True
        except Exception as e:
            print(f"  Error saving lyrics: {e}")
            return False
    
    def process_audio_file(self, audio_path, current, total):
        """Process a single audio file"""
        print(f"\n[{current}/{total}] 🎵 Processing: {audio_path.name}")

        # Extract metadata
        artist, title = self.extract_metadata(audio_path)
        
        if not artist or not title:
            print(f"  ⚠️  Skipping - missing artist or title metadata")
            self.errors += 1
            return
        
        # Fetch lyrics
        result = self.lyrics_fetcher.fetch_lyrics(artist, title)

        if result:
            lyrics_type, lyrics = result
            if self.save_lyrics(audio_path, lyrics_type, lyrics):
                self.found += 1
        else:
            self.errors += 1
        
        self.processed += 1
        
        # Be respectful to the API
        time.sleep(self.delay)
    
    def process_directory(self):
        """Recursively process all audio files in directory"""
        if not self.directory.exists():
            print(f"❌ Error: Directory '{self.directory}' does not exist")
            return
        
        print(f"🔍 Searching for audio files in: {self.directory}")
        
        # Find all audio files (case-insensitive for macOS)
        audio_files = []
        patterns = ['*.flac', '*.FLAC', '*.mp3', '*.MP3', '*.m4a', '*.M4A', '*.mp4', '*.MP4']
        for pattern in patterns:
            audio_files.extend(self.directory.rglob(pattern))
        
        # Remove duplicates
        audio_files = list(set(audio_files))

        if not audio_files:
            print("❌ No audio files found")
            return

        # Filter out files that already have lyrics (.lrc or .txt)
        audio_files = [f for f in audio_files
                       if not f.with_suffix('.lrc').exists()
                       and not f.with_suffix('.txt').exists()]

        if not audio_files:
            print("✅ All audio files already have lyrics (.lrc or .txt)")
            return

        print(f"📁 Found {len(audio_files)} audio files without lyrics\n")
        print("=" * 60)

        total = len(audio_files)
        for i, audio_path in enumerate(sorted(audio_files), 1):
            self.process_audio_file(audio_path, i, total)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Summary:")
        print(f"  Total processed: {self.processed}")
        print(f"  Lyrics found: {self.found} ✓")
        print(f"  Not found/errors: {self.errors}")

def main():
    print("🎼 Audio Lyrics Fetcher for macOS\n")
    
    if len(sys.argv) < 2:
        print("Usage: python3 audio_lyrics_fetcher.py <directory>")
        print("\nSupported formats: FLAC, MP3, M4A/ALAC")
        print("\nExamples:")
        print("  python3 audio_lyrics_fetcher.py ~/Music")
        print("  python3 audio_lyrics_fetcher.py /Volumes/Music/Albums")
        print("  python3 audio_lyrics_fetcher.py .")
        sys.exit(1)
    
    directory = sys.argv[1]
    parser = AudioParser(directory, delay=2.0)
    parser.process_directory()

if __name__ == "__main__":
    main()
