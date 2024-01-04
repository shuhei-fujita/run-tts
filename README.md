# TextToSpeach:TTS

- OpenAI: speach
- AWS: AWS Polly
- Google: gTTS (Google Text-to-Speech):

## Tutorial

https://huggingface.co/microsoft/speecht5_tts


## 先行事例

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
