from urllib.parse import urlparse
from pymediainfo import MediaInfo
from datetime import datetime
from pathlib import Path
import requests
import ffmpeg
import typing
import json
import m3u8
import re
import io
import os



class Space:
    UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'
    RE_JS = re.compile(r'"([^"]+/client-web/main\.[^.]+\.js)"')
    RE_QID = re.compile(r'queryId:\s*"([^"]+)",operationName:\s*"AudioSpaceById",')

    @classmethod
    def from_url(cls, url, out_dir='.', verbose=True, **kwargs):
        m = re.search(f'/spaces/(.*)$', url)
        if not m:
            raise ValueError("Invalid URL")
        return cls(m.group(1), out_dir=out_dir, verbose=verbose, **kwargs)

    def guest_token(self) -> str:
        headers = {
            "authorization": (
                "Bearer "
                "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
                "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
            )
        }
        response = requests.post("https://api.twitter.com/1.1/guest/activate.json", headers=headers, **self._kwargs).json()
        token = response["guest_token"]
        if not token:
            raise RuntimeError("No guest token found")
        return token


    def download_file(self, url, fp=None, timeout=10):
        if fp is None:
            fp = io.BytesIO()

        with requests.get(url, stream=True, timeout=timeout, **self._kwargs) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192): 
                fp.write(chunk)
        return fp


    def __init__(self, id, out_dir='.', verbose=True, **kwargs):
        self._id = id
        self._metadata = None
        self._info = None
        self._playlist_url = None
        self._playlist_file_path = None
        self._ffmetadata_file_path = None
        self._out_dir = Path(out_dir)
        self._verbose = verbose
        self._kwargs = kwargs

        os.makedirs(out_dir / self._id, exist_ok=True)
        self._get_space_config(out_file=self._out_dir / self._id / 'info.json')
        self._get_space_metadata(out_file=self._out_dir / self._id / 'metadata.json')
        self._get_space_playlist()
        self._download_segments()

    @property
    def id(self):
        return self._id

    @property
    def playlist_file_path(self):
        return self._playlist_file_path

    def _get_space_config(self, out_file: typing.Union[str, Path]):
        if os.path.isfile(out_file):
            with open(out_file) as f:
                self._info = json.load(f)
                return self._info

        with requests.Session() as s:
            res = s.get(f'https://twitter.com/i/spaces/{self._id}', headers={'user-agent': self.UA}, **self._kwargs)
            res.raise_for_status()
            m = Space.RE_JS.search(res.text)
            js_url = m.group(1)
            res = s.get(js_url, headers={'user-agent': self.UA}, **self._kwargs)
            res.raise_for_status()
            m = Space.RE_QID.search(res.text)
            qid = m.group(1)
            h = {
                 "authorization": (
                     "Bearer "
                     "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
                     "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
                 ),
                 "x-guest-token": self.guest_token()
            }
            params = {
                        "variables": (
                            "{"
                            '"id":"1OdKrBgABkwKX",'
                            '"isMetatagsQuery":false,'
                            '"withSuperFollowsUserFields":true,'
                            '"withUserResults":true,'
                            '"withBirdwatchPivots":false,'
                            '"withReactionsMetadata":false,'
                            '"withReactionsPerspective":false,'
                            '"withSuperFollowsTweetFields":true,'
                            '"withReplays":true,'
                            '"withScheduledSpaces":true,'
                            '"withDownvotePerspective": false'
                            "}"
                        )
                    }

            res = requests.get(f'https://twitter.com/i/api/graphql/{qid}/AudioSpaceById', params=params,headers=h, **self._kwargs)
            res.raise_for_status()
            space_info = res.json()
            self._info = space_info
            with open(out_file, 'w', encoding='utf8') as f:
                json.dump(space_info, f)

            return self._info
            
    def _get_space_metadata(self, out_file: typing.Union[str, Path]):
        if os.path.isfile(out_file):
            with open(out_file, encoding='utf8') as f:
                self._metadata = json.load(f)
                return self._metadata
    
        h = {
            "authorization": (
                "Bearer "
                "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
                "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
            ),
            "cookie": "auth_token=",
        }
        media_key = self._info['data']['audioSpace']['metadata']["media_key"]
        res = requests.get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}", headers=h, **self._kwargs)
        res.raise_for_status()
        metadata = res.json()
        self._metadata = metadata
        with open(out_file, 'w') as f:
            json.dump(metadata, f)
        return metadata

    def _get_space_playlist(self):
        self._playlist_url = self._metadata["source"]["location"]
        u = urlparse(self._playlist_url)
        playlist_filename = os.path.basename(u.path)
        self._playlist_file_path = self._out_dir / self._id /  playlist_filename
        if os.path.isfile(self._playlist_file_path):
            return self._playlist_file_path

        os.makedirs(os.path.dirname(self._playlist_file_path), exist_ok=True)
        with open(self._playlist_file_path, 'wb') as f:
            self.download_file(self._playlist_url, f)

    def _download_segments(self, tries=5):
        u = urlparse(self._playlist_url)
        playlist = m3u8.load(str(self._playlist_file_path)) 
        playlist.base_uri = f'{u.scheme}://{u.hostname}{os.path.dirname(u.path)}'
        failed = 0
        for i,segment in enumerate(playlist.segments, 1):
            segment_file_path = self._out_dir / self._id / segment.uri
            if os.path.exists(segment_file_path):
                if self._verbose:
                    print(f'Segment {i} already downloaded')
                continue
                
            while tries > 0:
                with open(segment_file_path, 'wb') as f:
                    try:
                        if self._verbose:
                            print(f"\rDownloading segment {segment.uri} ({i} of {len(playlist.segments)})", end=' ', flush=True)
                        self.download_file(segment.absolute_uri, f)
                        if self._verbose:
                            print(f"Done")
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout):
                        tries -= 1
                        continue
                    failed += 1
                    if self._verbose:
                        print(f"Error!")          
                    raise RuntimeError("Error downloading segment #{i}")
    
    @staticmethod
    def _get_speakers(metadata:dict):
        users = metadata['data']['audioSpace']['participants']['admins']
        users.extend(metadata['data']['audioSpace']['participants']['speakers'])
        return {_['periscope_user_id']:_ for _ in users}


    def _create_ffmetadata_file(self, out_file: typing.Union[str, Path]):
        reg = re.compile(r'chunk_(\d+)_(\d+)_.\.aac')
        files = list((self._out_dir / self._id).glob('*.aac'))
        files = sorted(files, key=lambda f: int(reg.search(f.name).group(2)))
        t = '[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={name}\n\n'
        speakers = self._get_speakers(self._info)

        with open(out_file, 'w') as out:
            out.write(f';FFMETADATA1\ntitle={self._info["data"]["audioSpace"]["metadata"]["title"]}\n\n')
            first = None
            prev = self._info['data']['audioSpace']['metadata']['creator_results']['result']['legacy']['name']
            prev_id = None
            start = 0
            last_seen = prev
            for f in files:
                m = reg.search(f.name)
                ts = int(m.group(1))//1_000_000_000
                d = datetime.fromtimestamp(ts)
                if not first: 
                    first = d
                delta = d - first
                m = MediaInfo.parse(f)
                l = json.loads(m.tracks[0].to_data().get('hydraaudiolevel')) if m.tracks[0].to_data().get('hydraaudiolevel') else []
                p = json.loads(m.tracks[0].to_data().get('hydraparticipants')) if m.tracks[0].to_data().get('hydraparticipants') else []
                ids = [p[i].get('UserId') for i,_ in enumerate(l,-1) if _ > 0]
                ids.sort()
                if ids:
                    last_seen = speakers[ids[0]]['display_name'] 
                if ids and prev_id not in ids:
                    out.write(t.format(name=prev, start=start*1000,end=delta.seconds*1000))
                    prev_id = ids[0]
                    prev = speakers[prev_id]['display_name']
                    start = delta.seconds
            out.write(t.format(name=prev, start=start*1000,end=delta.seconds*1000))
        self._ffmetadata_file_path = out_file


    def merge_into_m4a(self, out_file: typing.Union[str, Path]):
        ffmetadata_file_path = self._out_dir / self._id /  'ffmetadata.txt'
        self._create_ffmetadata_file(out_file=ffmetadata_file_path)
        try:
            ffcmd = ffmpeg.input(str(self._playlist_file_path)).output(str(out_file), map_metadata=1, codec='copy').overwrite_output()
            ffcmd = ffcmd.global_args('-i', str(self._ffmetadata_file_path))
            ffcmd.run(capture_stdout=True, capture_stderr=True)
        except ffmpeg.Error as e:
            raise RuntimeError('Error merging segments into m4a: {!s}'.format(e.stderr))
            



