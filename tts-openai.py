import os
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


def load_text(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def split_text(text, max_length):
    words = text.split()
    split_texts = []
    current_text = ""
    for word in words:
        if len(current_text) + len(word) + 1 > max_length:
            split_texts.append(current_text)
            current_text = word
        else:
            current_text += " " + word
    split_texts.append(current_text)

    for i, part_text in enumerate(split_texts):
        temp_file_path = Path(text_file_path).with_name(
            Path(text_file_path).stem + f"_temp_{i}.mp3"
        )
        print(f"Processing: {temp_file_path}")

    return split_texts

def generate_speech(client, text, model_name="tts-1", voice="nova"):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = client.audio.speech.create(
                model=model_name, voice=voice, input=text.strip()
            )
            return response
        except Exception as e:
            print(f"Error in API call: {e}")
            print(f"Retrying ({retry_count+1}/{MAX_RETRIES})...")
            retry_count += 1
    return None


def process_text_block(
    client, text, model_name, voice, temp_file_path, block_number, progress_bar, lock
):
    try:
        response = generate_speech(client, text, model_name, voice)
        if response:
            with open(temp_file_path, "wb") as file:
                file.write(response.content)
    except Exception as e:
        print(f"Error processing block {block_number}: {e}")
    finally:
        with lock:
            progress_bar.update(1)


def main(text_file_path):
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key)

    text = load_text(text_file_path)
    split_texts = split_text(text, MAX_LENGTH)

    progress_bar = tqdm(total=len(split_texts), desc="Processing")
    lock = threading.Lock()

    threads = []

    for i, part_text in enumerate(split_texts, start=1):
        temp_file_path = Path(text_file_path).with_name(
            f"{Path(text_file_path).stem}_temp_{i}.mp3"
        )
        thread = threading.Thread(
            target=process_text_block,
            args=(
                client,
                part_text,
                "tts-1",
                "nova",
                temp_file_path,
                i,
                progress_bar,
                lock,
            ),
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    progress_bar.close()

    combined = AudioSegment.empty()
    for i, _ in enumerate(split_texts, start=1):
        temp_file_path = Path(text_file_path).with_name(
            f"{Path(text_file_path).stem}_temp_{i}.mp3"
        )
        combined += AudioSegment.from_mp3(temp_file_path)
        os.remove(temp_file_path)

    combined.export(Path("mp3") / f"{Path(text_file_path).stem}.mp3", format="mp3")
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
