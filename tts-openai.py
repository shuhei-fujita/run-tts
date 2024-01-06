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

MAX_LENGTH = 2048  # テキストの最大長
MAX_RETRIES = 3  # 最大再試行回数


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


def main(text_file_path):
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
            args=(client, chunk, "tts-1", "nova", i, results, progress_bar, lock),
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    progress_bar.close()

    combined_audio = combine_audio_segments(results)
    combined_audio.export(
        Path("mp3") / f"{Path(text_file_path).stem}.mp3", format="mp3"
    )
    print(
        f"Combined speech saved as {Path('mp3') / f'{Path(text_file_path).stem}.mp3'}"
    )

    sync_s3()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tts-openai.py <text_file_path>")
        sys.exit(1)

    text_file_path = sys.argv[1]
    main(sys.argv[1])
