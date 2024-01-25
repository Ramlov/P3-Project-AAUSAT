#!/bin/bash

OUTPUT_DIR="./hls"
mkdir -p ${OUTPUT_DIR}

ffmpeg -i rtsp://studuser:Studentspace@roof-aausat.space.aau.dk:554/h264Preview_01_main \
-c:v copy -c:a copy \
-f hls \
-hls_time 2 \
-hls_list_size 3 \
-hls_flags delete_segments+append_list \
${OUTPUT_DIR}/stream.m3u8