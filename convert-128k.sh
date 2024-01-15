#!/bin/bash

input_file="mp3/sample-text.mp3"
output_file="mp3/sample-text-128k.mp3"
bitrate="128k"

# 例
# ffmpeg -i "mp3/sample-text.mp3" -ab "128k" "mp3/sample-text-128k.mp3"
ffmpeg -i "$input_file" -ab "$bitrate" "$output_file"
