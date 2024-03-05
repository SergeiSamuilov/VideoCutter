import re
from copy import deepcopy
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from params import (PUNCTUATION, NO_CUT, NO_CUT_WORDS, max_duration, max_symbols, MAX_DURATION_SECONDS, max_word_duration, min_word_duration)


def timestamp_to_sec(timestamp):
    return (
        float(timestamp.split(":")[0]) * 3600
        + float(timestamp.split(":")[1]) * 60
        + float(timestamp.split(":")[2].replace(",", "."))
    )


def sec_to_timestamps(sec):
    return str(timedelta(seconds=sec))


def process_text_for_prompt(line):

    line = line.replace("\n", " ")
    line = line.replace("\\N", " ")
    #     line = line.replace("\'", '')
    line = line.replace("\\", "")

    line = re.sub(" +", " ", line)

    return line


def split_sentence(words, timestamps, mode="duration"):

    if mode == "symbols":
        max_counter = max_symbols
    else:
        max_counter = max_duration

    lines = []
    line = []

    line_timestamp = []
    new_timestamps = []

    tmp_timestamps = []
    split_timestamps = []

    counter = 0
    for count, word in enumerate(words):

        line.append(word)
        tmp_timestamps.append(timestamps[count])

        if mode == "symbols":
            counter += len(word)
        else:
            counter += timestamps[count][1] - timestamps[count][0]

        if len(line_timestamp) == 0:
            line_timestamp.append(timestamps[count][0])

        if (
            counter > max_counter
            and (count + 1) < len(words)
            and not words[count + 1].strip().startswith(NO_CUT)
        ):
            line_timestamp.append(timestamps[count][1])
            new_timestamps.append(line_timestamp)
            lines.append("".join(line).strip())

            split_timestamps.append(tmp_timestamps)

            line = []
            line_timestamp = []
            counter = 0
            tmp_timestamps = []

    if counter:
        lines.append("".join(line).strip())
        line_timestamp.append(timestamps[count][1])
        new_timestamps.append(line_timestamp)
        split_timestamps.append(tmp_timestamps)

    return lines, new_timestamps, split_timestamps


def convert_string_to_nums(nums):
    return sum(
        (
            (
                list(range(*[int(j) + k for k, j in enumerate(i.split(":"))]))
                if ":" in i
                else [int(i)]
            )
            for i in nums.split(",")
        ),
        [],
    )

def preprocess_transcription(transcription_results):
    new_transcription_results = {"text": transcription_results["text"], "chunks": []}

    for count, item in enumerate(transcription_results["chunks"]):
        new_timestamp = list(item["timestamp"])
        if new_timestamp[0] is None:
            try:
                new_timestamp[0] = transcription_results["chunks"][count - 1]["timestamp"][1] + min_word_duration
            except:
                new_timestamp[0] = 0
        if new_timestamp[1] is None:
            new_timestamp[1] = new_timestamp[0] + min(min_word_duration * len(item["text"]),
                                                      max_word_duration)  # примерная длина слова
        if new_timestamp[1] - new_timestamp[0] > max_word_duration:
            new_timestamp[1] = new_timestamp[0] + max_word_duration
        if len(new_transcription_results["chunks"]) > 1:
            if new_timestamp[1] > new_timestamp[0] >= new_transcription_results["chunks"][-1]["timestamp"][1]:
                new_transcription_results["chunks"].append({'text': item["text"], 'timestamp': new_timestamp})
        else:
            new_transcription_results["chunks"].append({'text': item["text"], 'timestamp': new_timestamp})

    return new_transcription_results
            
def create_sentences_from_words(transcription_results):
    
    transcription_results = preprocess_transcription (transcription_results)
    
    words = [i["text"] for i in transcription_results["chunks"]]
    word_timestamps = [i["timestamp"] for i in transcription_results["chunks"]]

    mapping = list(range(len(words)))

    sentence_dict = {"sentences": [], "timestamps": []}
    subtitles_dict = {"sentences": [], "timestamps": []}

    sentence_words = []
    all_timestamps = []
    last_delimiter = 0

    for position in mapping:
        word = words[position]
        timestamp = word_timestamps[position]

        all_timestamps.append(timestamp)
        sentence_words.append(word)
                
        if (word.rstrip()[-1] in PUNCTUATION and not word.strip() in NO_CUT_WORDS) or position==len(mapping)-1:
            lines, timestamps, sentence_timestamps = split_sentence(
                sentence_words, all_timestamps, "duration"
            )

            sentence_dict["sentences"].extend(lines)
            sentence_dict["timestamps"].extend(timestamps)

            start = 0
            length = 0
            subtitles_lines = []
            subtitles_timestamps = []

            for sentence_timestamp in sentence_timestamps:
                length += len(sentence_timestamp)
                line_words = sentence_words[start:length]
                start = length
                new_lines, new_timestamps, _ = split_sentence(
                    line_words, sentence_timestamp, "symbols"
                )
                subtitles_lines.append(new_lines)
                subtitles_timestamps.append(new_timestamps)

            subtitles_dict["sentences"].extend(subtitles_lines)
            subtitles_dict["timestamps"].extend(subtitles_timestamps)

            sentence_words = []
            all_timestamps = []

    return sentence_dict, subtitles_dict


def ranges(nums):
    nums = sorted(set(nums))
    gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s + 1 < e]
    edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
    return list(map(list, zip(edges, edges)))


def squash_timestamps(highlight_times_all, timestamps):
    short_length = 0
    highlight_times = []
    for sentence_num in highlight_times_all:
        sentence_num = int(sentence_num)
        if sentence_num < len(timestamps) - 1:
            short_length += (
                timestamps[sentence_num + 1][0] - timestamps[sentence_num][0]
            )
        else:
            short_length += timestamps[sentence_num][1] - timestamps[sentence_num][0]
        if short_length > MAX_DURATION_SECONDS:
            break
        highlight_times.append(sentence_num)

    highlight_times = ranges(highlight_times)
    highlight_timestamps = deepcopy(highlight_times)

    for num, highlight in enumerate(highlight_timestamps):
        highlight[0] = timestamps[highlight[0]][0]
        highlight[-1] = timestamps[highlight[-1]][-1]

    return highlight_times, highlight_timestamps


def format_timestamps(timestamps):

    new = []
    for t in timestamps:
        t = t.split(":")
        t[-1] = "{:05.2f}".format(float(t[-1]))

        new.append(":".join(t))
    return new


def offset_timestamps(timecodes, start, end):
    if type(start) == str:
        if end:
            if type(end) != str:
                end = sec_to_timestamps(end)
            new = list(
                map(
                    lambda timecodes: str(
                        datetime.strptime(timecodes, "%H:%M:%S.%f")
                        - datetime.strptime(start, "%H:%M:%S.%f")
                        + datetime.strptime(end, "%H:%M:%S.%f")
                    ),
                    timecodes,
                )
            )
            new = [i.split()[1] for i in new]
        else:
            new = list(
                map(
                    lambda timecodes: str(
                        datetime.strptime(timecodes, "%H:%M:%S.%f")
                        - datetime.strptime(start, "%H:%M:%S.%f")
                    ),
                    timecodes,
                )
            )

    else:
        if type(end) == str:
            end = timestamp_to_sec(end)
        new = [sec_to_timestamps(i - start + end) for i in timecodes]

    return new

def preprocess_diarization(diarization):
    new_diarization = [diarization[0]]
    min_length = 1

    for num, segment in enumerate(diarization):
        if num>0:
            if segment['speaker'] == new_diarization[-1]['speaker']:
                new_diarization[-1]['end'] = segment['end']
            else:
                new_diarization.append(segment)    
    return [i for i in new_diarization if i['end'] - i['start'] > min_length]

def clean_script_for_prompt(sentence_dict, diarization, tmp_folder):

    length_list = []
    index_list = []
    sentence_list = []
    speaker_list = ["undefined"]*len(sentence_dict['sentences'])
    
    diarization = preprocess_diarization(diarization)
    eps = 0.5
    
    text = []
    for count, line in enumerate(sentence_dict['sentences']):
        index_list.append(count)
        sentence_list.append(line.strip())
        if count == len(sentence_dict['sentences'])-1:
            length = round(sentence_dict['timestamps'][count][1] - sentence_dict['timestamps'][count][0], 2)
        else:
            length = round(sentence_dict['timestamps'][count+1][0] - sentence_dict['timestamps'][count][0], 2)
        length_list.append(length)
        
        for segment in diarization:
            if sentence_dict['timestamps'][count][0] > segment['start'] - eps:
                speaker_list[count] = segment['speaker']
        
        line = f" ({count}) [{length}] {line.strip()}"
        text.append(process_text_for_prompt(line))

    d = {'index': index_list, 'speaker': speaker_list, 'sentence': sentence_list, 'length': length_list}
    df = pd.DataFrame(data=d)
    df.to_csv(f'{tmp_folder}/clean_text.csv', index=False)

    return df

def read_script_file(script_path):

    with open(script_path) as f:
        script_file = f.readlines()

    sentence_dict = {"sentences": [], "timestamps": []}
    subtitles_dict = {"sentences": [], "timestamps": []}

    sentence = []
    sentence_timestamps = []
    all_timestamps = []

    for line in script_file:
        if line.split(":")[0] == "Dialogue":

            text = process_text_for_prompt(",".join(line.split(",")[9:]))
            timestamps = line.split(",")[1:3]
            if len(sentence_timestamps) == 0:
                sentence_timestamps.append(timestamps[0])

            all_timestamps.append(timestamps)

            sentence.append(text)
            processed_line = re.sub(r"[^a-zA-Z0-9 .!?]", "", line)

            if processed_line.rstrip()[-1] in PUNCTUATION:
                sentence_timestamps.append(timestamps[1])

                sentence_dict["sentences"].append(" ".join(sentence))
                sentence_dict["timestamps"].append(sentence_timestamps)

                subtitles_dict["sentences"].append(sentence)
                subtitles_dict["timestamps"].append(all_timestamps)

                sentence = []
                sentence_timestamps = []
                all_timestamps = []

    return sentence_dict, subtitles_dict
