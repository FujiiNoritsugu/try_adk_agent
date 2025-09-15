import requests
import subprocess
import tempfile
import os

# 音声合成クエリの作成
response = requests.post(
    "http://localhost:50021/audio_query", params={"text": "こんにちは", "speaker": 1}
)
query = response.json()

# 音声合成
response = requests.post(
    "http://localhost:50021/synthesis", params={"speaker": 1}, json=query
)

# 一時ファイルに保存して再生
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
    tmp_file.write(response.content)
    tmp_file_path = tmp_file.name

# paplayで再生
subprocess.run(["paplay", tmp_file_path])

# 一時ファイルを削除
os.remove(tmp_file_path)
