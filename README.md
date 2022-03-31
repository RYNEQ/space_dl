# space_dl
Python library/app to download twitter spaces and make multiple output from them
This downloads a Twitter space as separated file m3u8 playlist, then it can convert all into a single chapterized m4a audio file

The M4A audio file is Chapterized so if you use a player with media chapter support(like mpv or vlc) you can switch between speakers

## features
- [x] Download Twitter space
- [x] Merge files into one m4a file
- [x] Chapterize m4a file, so we know when each user speaks and can switch between them
- [ ] Make mp4 video of Space with avatars and waveform spectrum effect (#TODO) 

## Installation
### FFMPEG
First install ffmpeg; on Debian based linux distros you can do:
```
sudo apt-get install ffmpeg
```
For other OS refer to FFMPEG documents


### Via pypi.org

    pip install space_dl

### Via git

    pip install https://github.com/RYNEQ/space_dl

## Usage

### As an application

```bash
python3 -m space_dl [-a AUDIO_FILE] [-d OUT_DIR] [-p PROXY] [-v] URL
```
### As a library

```python
import space_dl
s = space_dl.Space.from_url(url, out_dir, verbose=True, proxies=...)
print(f"Playlist saved as {s.playlist_file_path}")
s.merge_into_m4a(audio_file_path)
print(f"Audio file saved as {audio_file_path}")
```

## Options

```
  -a/--audio-file AUDIO_FILE: If passed the playlist will be converted to a chapterized m4a audio file
  -d/--out-dir OUT_DIR: Set output directory
  -p/--proxy PROXY: Use proxy (http,socks4,socks5,socks5h)
                    Use socks5h to pass the DNS queries via proxy
  -v/--verbose: Verbose Mode
```

