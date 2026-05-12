#!/bin/bash
nohup ffmpeg -stream_loop -1 -re -i "https://videos.pexels.com/video-files/16727103/16727103-hd_1920_1080_60fps.mp4" -stream_loop -1 -i "/root/serene/music/ocean.mp3" -map 0:v -map 1:a -vf scale=1920:1080 -c:v libx264 -preset veryfast -b:v 4500k -maxrate 4500k -bufsize 9000k -c:a aac -b:a 192k -f flv "rtmp://a.rtmp.youtube.com/live2/ubm2-7fjm-jejm-7ejg-3pqm" >> /var/log/ocean_stream.log 2>&1 &
echo 'Stream started (PID: '$!'). Logs: tail -f /var/log/ocean_stream.log'
