# TextToSpeach:TTS

## 参考文献

OpenAI: speach
- https://platform.openai.com/docs/guides/speech-to-text

AWS: AWS Polly
- https://aws.amazon.com/jp/polly/

Google: gTTS (Google Text-to-Speech)
- https://cloud.google.com/text-to-speech?hl=ja

SpeechT5
- https://huggingface.co/microsoft/speecht5_tts

LISTEN
- https://listen.style/p/listennews/dkcjirkq

## 環境構築手順

### 1. リポジトリのクローン

```bash
git clone xxx
```

### 2. asdfでpythonのバージョン管理

```bash
asdf install
```

### 3. pythonの仮想環境

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### 4. スクリプトの実行

```bash
python tts-openai.py text/sample-text-jp.txt
```

```bash
$ python tts-openai.py -h                                                                                                    254 ↵
usage: tts-openai.py [-h] [--model {tts-1,tts-1-hd}] text_file_path

Text-to-Speech script using OpenAI's API.

positional arguments:
  text_file_path        Path to the text file.

options:
  -h, --help            show this help message and exit
  --model {tts-1,tts-1-hd}
                        Model to use for text-to-speech. Choices are tts-1 or tts-1-hd. Default is tts-1.

Usage example: python tts-openai.py example.txt --model tts-1-hd
```


```bash
ffprobe mp3 mp3/sample-text-jp.mp3
```
