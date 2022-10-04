import os
import subprocess
import json
from datetime import datetime


def ffmpeg_slug(filename, apostrophes=True):
    new_filename = filename.replace("'", r"'\''")
    if apostrophes:
        new_filename = f"'{new_filename}'"
    return new_filename


def ffmpeg_cmd(*args, overwrite=False):
    cmd = ['ffmpeg -nostdin' + (' -y' if overwrite else '')] + list(args)
    text_command = ' '.join(cmd)
    print('\nFFMPEG COMMAND\n' + '-'*len(text_command) + '\n' + text_command + '\n' + '-'*len(text_command) + '\n')
    process = subprocess.Popen(text_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for line in process.stdout:
        print(line, end='')
    print("FFMPEG COMPLETED")


def ffprobe_into_json(*args):
    cmd = ['ffprobe'] + list(args)
    text_command = ' '.join(cmd)
    print('\nFFPROBE COMMAND\n' + '-' * len(text_command) + '\n' + text_command + '\n' + '-' * len(text_command) + '\n')
    process = subprocess.Popen(text_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    probe_result = ""
    for line in process.stdout:
        # print(line, end='')
        probe_result += line
    print("FFPROBE COMPLETED")
    return json.loads(probe_result)


def get_keyframe_timestamps(video_file):
    all_timestamps = ffprobe_into_json(f'-loglevel error -select_streams v:0 -show_entries packet=pts_time,flags -of json "{video_file}"')
    keyframe_timestamps = []
    for packet in all_timestamps['packets']:
        if 'K' in packet['flags']:
            keyframe_timestamps.append(float(packet['pts_time']))
    return keyframe_timestamps


def convert_to_common(file, output=None, vcodec='libx264', acodec='aac', abitrate='192k'):
    if output is None:
        basename, ext = os.path.splitext(file)
        output = f'{basename}_{vcodec}_{acodec}_{abitrate}{ext}'
    command = f'-i {file} -c:v {vcodec} -crf 23 -profile:v main -pix_fmt yuv420p -c:a {acodec} -ac 2 -b:a {abitrate}' \
              f' -movflags faststart "{output}"'
    ffmpeg_cmd(command)


def concat(*video_files, output='concat_output.mkv', lossless=False):
    if lossless:
        file_list = r'temp_file_list'
        if os.path.exists(file_list):
            os.remove(file_list)
        with open(file_list, 'w') as fp:
            fp.writelines([f"file " + ffmpeg_slug(video_file) + "\n" for video_file in video_files])
        ffmpeg_cmd(f'-f concat -safe 0 -i {file_list} -c copy {output}')
        os.remove(file_list)
    else:
        command = f'{" ".join([f"-i {video_file}" for video_file in video_files])} -filter_complex "' \
                  f'{" ".join([f"[{i}:v] [{i}:a]" for i in range(len(video_files))])} concat=n=' \
                  f'{len(video_files)}:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" "{output}"'
        ffmpeg_cmd(command)


def get_seconds_from_time_string(time_string):
    ts = None
    for time_format in ['%S', '%M:%S', '%H:%M:%S', '%H:%M:%S.%f']:
        try:
            ts = datetime.strptime(time_string, time_format)
        except ValueError:
            pass
    if ts is None:
        raise Exception("Time string format is invalid")
    return ts.microsecond / 1000000 + ts.second + ts.minute * 60 + ts.hour * 3600


def smart_lossless_trim(video_file, start_time, duration_time, output_file='smart_lossless_trim.mkv', _frame_offset=6):
    start_seconds = get_seconds_from_time_string(start_time)
    duration_seconds = get_seconds_from_time_string(duration_time)
    timestamps = get_keyframe_timestamps(video_file)
    start_keyframe = None
    end_keyframe = None
    last_keyframe = -1000000
    for t in timestamps:
        if start_keyframe is None and t > start_seconds:
            start_keyframe = t
        if t > start_seconds + duration_seconds:
            end_keyframe = last_keyframe
            break
        last_keyframe = t
    fps24constant = 0.0417

    first_clip_start = start_seconds - (start_seconds % fps24constant)
    first_clip_duration = start_keyframe - (start_keyframe % fps24constant) - first_clip_start
    last_clip_start = end_keyframe - (end_keyframe % fps24constant) + fps24constant * _frame_offset  # Can help make concat smoother for whatever reason
    last_clip_duration = start_seconds + duration_seconds - ((start_seconds + duration_seconds) % fps24constant) - last_clip_start

    trim(video_file, first_clip_start, first_clip_duration, output_file='smart_lossless_trim_1.mp4')
    trim(video_file, start_keyframe, end_keyframe - start_keyframe, output_file='smart_lossless_trim_2.mp4', lossless=True)
    trim(video_file, last_clip_start, last_clip_duration, output_file='smart_lossless_trim_3.mp4')
    concat('smart_lossless_trim_1.mp4', 'smart_lossless_trim_2.mp4', 'smart_lossless_trim_3.mp4',
           output=output_file, lossless=True)
    os.remove('smart_lossless_trim_1.mp4')
    os.remove('smart_lossless_trim_2.mp4')
    os.remove('smart_lossless_trim_3.mp4')
    # print(start_seconds, start_keyframe - start_seconds)
    # print(start_keyframe, end_keyframe - start_keyframe)
    # print(end_keyframe, start_seconds + duration_seconds - end_keyframe)
    # print(first_clip_start)
    # print(first_clip_duration)
    # print(last_clip_start)
    # print(last_clip_duration)


def trim(video_file, start_time, duration_time, output_file='trim_output.mkv', lossless=False, smart_lossless=False):
    if smart_lossless:
        smart_lossless_trim(video_file, start_time, duration_time, output_file)
    elif lossless:
        ffmpeg_cmd(f'-ss {start_time} -i "{video_file}" -t {duration_time} -vcodec copy -acodec copy "{output_file}"')
    else:
        ffmpeg_cmd(f'-ss {start_time} -i "{video_file}" -t {duration_time} "{output_file}"')


'''
cmd = 'ffmpeg -ss 00:23:00 -i "Avatar (2009) Extended [imdb-tt0499549][Bluray-1080p][AAC 5.1][x264]-RARBG.mp4" -t ' \
      '00:00:10 -vcodec copy -acodec copy a5.mp4 '
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
for line in process.stdout:
    print(line)
'''

# smart_lossless_trim("./Avatar (2009) Extended [imdb-tt0499549][Bluray-1080p][AAC 5.1][x264]-RARBG.mp4", '00:01:00', '00:01:00')
