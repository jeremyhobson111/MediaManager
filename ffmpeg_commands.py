import os


def ffmpeg_slug(filename, apostrophes=True):
    new_filename = filename.replace("'", r"'\''")
    if apostrophes:
        new_filename = f"'{new_filename}'"
    return new_filename


def concat_videos(*video_files, output='concat_output.mkv', remux=True):
    file_list = r'temp_file_list'
    if os.path.exists(file_list):
        os.remove(file_list)
    with open(file_list, 'w') as fp:
        fp.writelines([f"file " + ffmpeg_slug(video_file) + "\n" for video_file in video_files])
    # ffmpeg.concat(*input_videos, v=1, a=1).output("video.mkv", vcodec="copy", acodec="copy").run()
    if remux:
        ffmpeg.input(file_list, format='concat', safe=0).output(output).run()
    else:
        ffmpeg.input(file_list, format='concat', safe=0).output(output, codec="copy").run()


def require_remux(*video_files):
    video_comparison = {}
    video_differences = {}
    audio_comparison = {}
    audio_differences = {}
    for video_file in video_files:
        video = ffmpeg.probe(video_file)
        for k, v in video['streams'][0].items():
            if k not in video_comparison:
                video_comparison[k] = v
            else:
                if video_comparison[k] != v:
                    video_differences[k] = v
        for k, v in video['streams'][1].items():
            if k not in audio_comparison:
                audio_comparison[k] = v
            else:
                if audio_comparison[k] != v:
                    audio_differences[k] = v
    for diff_v in ['codec_name', 'codec_long_name', 'codec_tag_string', 'codec_tag', 'width', 'coded_width', 'coded_height']:
        if diff_v in video_differences:
            return True
    for diff_a in ['codec_name', 'codec_long_name', 'codec_tag_string', 'codec_tag']:
        if diff_a in audio_differences:
            return True
    return False


def get_output_name(*video_files):
    basenames = [os.path.splitext(file)[0] for file in video_files]
    extension = os.path.splitext(video_files[0])[1]
    if len(basenames) == 1:
        return basenames[0]
    longest_length = len(max(*basenames))
    found = False
    diff_index = None
    for i in range(longest_length):
        letter = None
        for v in basenames:
            if i >= len(v):
                found = True
                break
            if not letter:
                letter = v[i]
            elif letter != v[i]:
                found = True
                break
        if found:
            diff_index = i
            break
    output_name = basenames[0][:diff_index]
    for b in basenames:
        output_name += b[i:] + '-'
    return output_name[:-1] + extension


def concat(*video_files, output=None):
    if not output:
        output = get_output_name(*video_files)
    concat_videos(*video_files, output=output, remux=require_remux(*video_files))


def trim(input_path, output_path, start, end):
    input_stream = ffmpeg.input(input_path)

    vid = (
        input_stream.video
        .trim(start=start, end=end)
        .setpts('PTS-STARTPTS')
    )
    aud = (
        input_stream.audio
        .filter_('atrim', start=start, end=end)
        .filter_('asetpts', 'PTS-STARTPTS')
    )

    joined = ffmpeg.concat(vid, aud, v=1, a=1).node
    output = ffmpeg.output(joined[0], joined[1], output_path, vcodec="copy", acodec="copy")
    output.run()


# concat('video0.ts', 'video1.ts')

# ffprobe -v error -select_streams v:0 -skip_frame nokey -show_entries frame=pkt_pts_time -of csv=p=0 input.mp4
def probe(input_file):
    print(ffmpeg.probe(input_file, v='error', select_streams='v:0', skip_frame='nokey', show_entries='frame=pkt_pts_time', of='csv=p=0'))

