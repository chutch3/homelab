# Audio fixtures

`kasm-sidebar.html` is a minimal authored fixture for the KasmVNC 1.4 DOM contract;
it is not the full upstream desktop client.

`tone.mpegts` is a one-second synthetic 440 Hz tone, not captured session audio.
It matches Kasm's mono MP2 / MPEG-TS stream format. Generated with FFmpeg:

```sh
ffmpeg -hide_banner -loglevel error -f lavfi \
  -i sine=frequency=440:sample_rate=44100:duration=1 \
  -f mpegts -codec:a mp2 -b:a 128k -ac 1 -muxdelay .001 tone.mpegts
```

SHA-256: `bd748d7b00b8853e377b73a208ab6e262deb9b6765790ed5865f2242dd4dff15`

Normal tests use this checked-in file; they need neither FFmpeg nor the homelab.
JSMpeg's decoded RMS for this fixture is approximately 0.04359446. The tests also
check duration, finite samples, frequency and actual browser playback scheduling.
