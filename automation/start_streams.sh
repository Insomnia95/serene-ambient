#!/bin/bash
# Start all Calm Veritas live streams

echo 'Starting ocean stream...'
nohup ffmpeg -stream_loop -1 -re -fflags +genpts -i "https://videos.pexels.com/video-files/16727103/16727103-hd_1920_1080_60fps.mp4" -stream_loop -1 -i "/root/serene/music/ocean.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -f flv "rtmp://a.rtmp.youtube.com/live2/rstd-dpsg-9sp4-tz8m-3sta" >> /var/log/stream_ocean.log 2>&1 &
echo '  PID: '$!'  Log: /var/log/stream_ocean.log'

echo 'Starting fire stream...'
nohup ffmpeg -stream_loop -1 -re -fflags +genpts -i "https://videos.pexels.com/video-files/35481118/35481118-hd_1920_1080_30fps.mp4" -c:v copy -an -f flv "rtmp://a.rtmp.youtube.com/live2/431r-a2a3-muy2-5pm6-2e59" >> /var/log/stream_fire.log 2>&1 &
echo '  PID: '$!'  Log: /var/log/stream_fire.log'

echo 'Starting rain stream...'
nohup ffmpeg -stream_loop -1 -re -fflags +genpts -i "https://videos.pexels.com/video-files/15454042/15454042-hd_1920_1080_25fps.mp4" -stream_loop -1 -i "/root/serene/music/rain.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -f flv "rtmp://a.rtmp.youtube.com/live2/3tpw-pw9s-00ut-j5va-eda7" >> /var/log/stream_rain.log 2>&1 &
echo '  PID: '$!'  Log: /var/log/stream_rain.log'

echo 'Starting forest stream...'
nohup ffmpeg -stream_loop -1 -re -fflags +genpts -i "https://videos.pexels.com/video-files/35982732/35982732-hd_1920_1080_25fps.mp4" -stream_loop -1 -i "/root/serene/music/forest.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -f flv "rtmp://a.rtmp.youtube.com/live2/xeft-mg2v-pt9c-tzat-a9bp" >> /var/log/stream_forest.log 2>&1 &
echo '  PID: '$!'  Log: /var/log/stream_forest.log'

echo 'Starting stars stream...'
nohup ffmpeg -stream_loop -1 -re -fflags +genpts -i "https://videos.pexels.com/video-files/29238178/29238178-hd_1920_1080_24fps.mp4" -stream_loop -1 -i "/root/serene/music/stars.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -f flv "rtmp://a.rtmp.youtube.com/live2/zq0u-c6dm-jkvm-brzv-b09m" >> /var/log/stream_stars.log 2>&1 &
echo '  PID: '$!'  Log: /var/log/stream_stars.log'

echo 'All streams started!'
