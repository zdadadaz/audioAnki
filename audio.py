import shlex, subprocess
import os
command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
args = shlex.split(command_line)
p = subprocess.Popen(args)
# data=subprocess.run(["ffplay", "./static/data/Bigbang_s08e01.mp3"], capture_output=True)
# data=subprocess.run(["ffplay","-ss 00:00:03 -t 00:00:02 -autoexit", "./static/data/Bigbang_s08e01.mp3"], capture_output=True)
# print(data)