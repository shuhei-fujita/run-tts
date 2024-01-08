import os
import io
import sys
import subprocess
import threading
from pathlib import Path
from pydub import AudioSegment
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import argparse
import eyed3
import math

MAX_LENGTH = 1024  # テキストの最大長
MAX_RETRIES = 3  # 最大再試行回数


# メタデータを音声ファイルに追加する関数
def add_metadata_to_audio(file_path, text):
    # メタデータを追加する前にファイルの存在を確認
    audio_file_path = Path("mp3") / f"{Path(file_path).stem}.mp3"
    if not audio_file_path.exists():
        print(f"Error: Audio file {audio_file_path} does not exist.")
        return

    audiofile = eyed3.load(str(audio_file_path))
    if audiofile is None:
        print(f"Error: Failed to load audio file {audio_file_path}.")
        return

    if audiofile.tag is None:
        audiofile.initTag()

    # 歌詞情報として元のテキストを設定
    audiofile.tag.lyrics.set(text)

    audiofile.tag.save()


def sync_s3():
    print("Starting S3 sync...")
    command = [
        "aws",
        "s3",
        "sync",
        "mp3",
        "s3://play-audio-ios",
        "--profile",
        "private-fujita",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print("S3 sync completed successfully.")
    else:
        print(f"S3 sync failed with error: {result.stderr}")


def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def split_into_chunks(text, max_length):
    words = text.split()
    chunks = []
    current_chunk = ""
    for word in words:
        if len(current_chunk) + len(word) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = word
        else:
            current_chunk += " " + word
    chunks.append(current_chunk)
    return chunks


def create_audio_segment(response):
    return AudioSegment.from_file(io.BytesIO(response.content), format="mp3")


def generate_speech(client, text, model_name, voice):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            return client.audio.speech.create(
                model=model_name, voice=voice, input=text.strip()
            )
        except Exception as e:
            print(
                f"Error in API call: {e}. Retrying ({retry_count+1}/{MAX_RETRIES})..."
            )
            retry_count += 1
    return None


def process_text_block(
    client, text, model_name, voice, block_number, results, progress_bar, lock
):
    try:
        response = generate_speech(client, text, model_name, voice)
        if response:
            with lock:
                results[block_number] = create_audio_segment(response)
    except Exception as e:
        print(f"Error processing block {block_number}: {e}")
    finally:
        with lock:
            progress_bar.update(1)


def combine_audio_segments(results):
    combined_audio = AudioSegment.empty()
    for segment in results:
        if segment:
            combined_audio += segment
    return combined_audio


def convert_mp3_to_aac(mp3_file_path):
    mp3_file_path = Path(mp3_file_path)  # Pathオブジェクトに変換
    aac_file_path = mp3_file_path.with_suffix(".aac")
    command = [
        "ffmpeg",
        "-i",
        str(mp3_file_path),
        "-c:a",
        "aac",
        str(aac_file_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Converted to AAC: {aac_file_path}")
    else:
        print(f"Error converting to AAC: {result.stderr}")


def main(text_file_path, model, audio_format):
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key)

    text = read_file(text_file_path)
    chunks = split_into_chunks(text, MAX_LENGTH)

    progress_bar = tqdm(total=len(chunks), desc="Processing")
    lock = threading.Lock()
    results = [None] * len(chunks)
    threads = []

    for i, chunk in enumerate(chunks):
        thread = threading.Thread(
            target=process_text_block,
            args=(client, chunk, model, "nova", i, results, progress_bar, lock),
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    progress_bar.close()

    combined_audio = combine_audio_segments(results)
    mp3_output_file = Path("mp3") / f"{Path(text_file_path).stem}.mp3"
    combined_audio.export(mp3_output_file)
    print(
        f"Combined speech saved as {Path('mp3') / f'{Path(text_file_path).stem}.mp3'}"
    )

    # メタデータの追加
    add_metadata_to_audio(text_file_path, text)

    # AACに変換が必要な場合
    if audio_format == "aac":
        convert_mp3_to_aac(mp3_output_file)

    # sync_s3()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Text-to-Speech script using OpenAI's API.",
        epilog="Usage example: python tts-openai.py example.txt --model tts-1-hd --format mp3",
    )
    parser.add_argument("text_file_path", help="Path to the text file.")
    parser.add_argument(
        "--model",
        default="tts-1",
        choices=["tts-1", "tts-1-hd"],
        help="Model to use for text-to-speech. Choices are tts-1 or tts-1-hd. Default is tts-1.",
    )
    parser.add_argument(
        "--format",
        default="mp3",
        choices=["mp3", "aac"],
        help="Audio format for the output file. Choices are mp3 or aac. Default is mp3.",
    )
    args = parser.parse_args()

    main(args.text_file_path, args.model, args.format)
