#!/bin/bash
for file in `find mp3 -type f`; do
    ffmpeg -i "$file" -c:a copy "${file%.mp3}.mp4"
    mv "${file%.mp3}.mp4" mp4/
done
