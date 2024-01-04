from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
from pydub import AudioSegment
import subprocess

"""
OpenAIのAPIではMAX_LENGTHが4096が上限なのですが、テキストの処理に限界でネットワークが途切れる恐れがある。
なので、実験的にMAX_LENGTHを下げて、1つあたりのTTS処理をさらに細かく処理するアプローチをとる。

メリット：
- より堅牢なエラーハンドリング: 小さなテキストブロックでエラーが発生した場合、再処理が必要なデータ量が少なくなります。これにより、APIコールの効率が向上します。
- API制限への対応: OpenAIのAPIには特定の制限があります（例えば、テキストの最大長）。より小さいテキストブロックを使用することで、これらの制限をより簡単に遵守することができます。
- メモリ使用量の削減: 同時に処理されるデータ量が少なくなるため、スクリプトのメモリ使用量が削減される可能性があります。

デメリット：
- 処理時間の増加: より多くの小さいテキストブロックを処理するため、全体の処理時間が増加する可能性があります。
- 音声の自然さへの影響: テキストを細かく分割すると、音声が不自然に聞こえる場合があります。特に、文や段落の途中で分割されると、音声の流れが断ち切られる可能性があります。
"""

MAX_LENGTH = 2048  # テキストの最大長
MAX_RETRIES = 3  # 最大再試行回数

def sync_s3():
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
        print("Sync completed successfully.")
    else:
        print(f"Sync failed with error: {result.stderr}")


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
    return split_texts


def generate_speech(client, text, model_name="tts-1", voice="nova"):
    retry_count = 0  # 再試行回数を初期化
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
    print("Max retries reached. Unable to generate speech.")
    return None  # エラー時はNoneを返す


def main(text_file_path):
    # 環境変数のロード
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key)

    print("loaded environment variables")

    # テキストファイルの読み込み
    text = load_text(text_file_path)
    print("loaded text file")

    # テキストを分割
    split_texts = split_text(text, MAX_LENGTH)
    print("split text")

    # 音声の生成と一時保存
    combined = AudioSegment.empty()
    temp_files = []
    for i, part_text in enumerate(split_texts, start=1):
        speech = generate_speech(client, part_text)
        temp_file_path = Path(text_file_path).with_name(
            Path("mp3") / Path(text_file_path).stem + f"_temp_{i}.mp3"
        )
        with open(temp_file_path, "wb") as file:
            file.write(speech.content)
        print(f"generated speech part: {temp_file_path}")

        # 部分音声を読み込み、結合
        part = AudioSegment.from_mp3(temp_file_path)
        combined += part

        # 一時ファイルのパスを保存
        temp_files.append(temp_file_path)

    # 結合された音声ファイルを保存
    # combined_file_path = Path(text_file_path).with_name(
    #     Path(text_file_path).stem + ".mp3"
    # )
    combined_file_path = Path("mp3") / (Path(text_file_path).stem + ".mp3")

    combined.export(combined_file_path, format="mp3")
    print(f"Combined speech saved as {combined_file_path}")

    # 一時ファイルの削除
    for temp_file in temp_files:
        os.remove(temp_file)
        print(f"Removed temporary file: {temp_file}")

    # S3にアップロード
    print("Uploading to S3...")
    sync_s3()
    print("Upload S3 completed")


# スクリプトの実行
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tts-openai.py <text_file_path>")
        sys.exit(1)

    text_file_path = sys.argv[1]
    main(text_file_path)
