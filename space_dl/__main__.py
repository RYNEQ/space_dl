from . import twitter_space
from pathlib import Path
import argparse
import os
# PROXY = dict(http='socks5h://127.0.0.1:1080', https='socks5h://127.0.0.1:1080') 



def main():
    parser = argparse.ArgumentParser(description="Download Twitter Space")
    parser.add_argument('url', metavar='URL', type=str, nargs=1, help='URL of the Twitter Space')
    parser.add_argument("-a", '--audio-file', type=Path, help='Path of the audio file to merge all the audio files into', default=None)
    parser.add_argument("-d", '--out-dir', type=Path, help='Path of output directory', default=Path('.'))
    parser.add_argument("-p", '--proxy', type=str, help='Proxy', default=None)
    parser.add_argument("-v", '--verbose', default=False, action='store_true', help='Verbose')
    args = parser.parse_args()
    out_dir = args.out_dir

    PROXY = dict(http=args.proxy, https=args.proxy) 

    try:
        s = twitter_space.Space.from_url(args.url[0], out_dir, verbose=args.verbose, proxies=PROXY)
        print(f"Playlist saved as {s.playlist_file_path}")
        if args.audio_file is not None:
            s.merge_into_m4a(args.audio_file)
            print(f"Audio file saved as {args.audio_file}")
    except KeyboardInterrupt:
        print("Cancled by user")
    


if __name__ == '__main__':
    main()