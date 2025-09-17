# Pythonの公式イメージをベースにする
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# Streamlitが使用するポートを公開
EXPOSE 8501

# アプリケーションを起動するコマンド
CMD ["streamlit", "run", "app.py"]