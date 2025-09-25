# --- 1. ビルダーステージ ---
# CUDA対応のPythonイメージをビルダーステージのベースとして使用
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 as builder

# ビルドとuvのインストールに必要なシステムパッケージを一度にインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# uvをインストールし、同じRUN命令内で仮想環境を作成
# インストーラーがuvを/root/.local/binに配置するため、そのパスをエクスポートする
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.local/bin:$PATH" && \
    uv venv /opt/venv
    
# uvのパスと仮想環境のパスを両方とも環境変数に設定
ENV PATH="/root/.local/bin:/opt/venv/bin:$PATH"

# uvを使ってrequirements.txtをインストール
COPY requirements.txt .
RUN uv pip install --no-cache --index-strategy unsafe-best-match -r requirements.txt


# --- 2. 最終ステージ ---
# CUDA対応のPythonイメージを最終ステージのベースとして使用
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# 実行時に必要なシステムライブラリのみをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# ビルダーステージから仮想環境（インストール済みライブラリ）をコピー
COPY --from=builder /opt/venv /opt/venv

# プロジェクトの全ファイルをコンテナの作業ディレクトリにコピー
COPY . .

# 仮想環境のPythonを使うようにPATHを設定
ENV PATH="/opt/venv/bin:$PATH"

# Streamlitがデフォルトで使用するポート8501を外部に公開
EXPOSE 8501

# コンテナ起動時に実行するコマンドを設定
# 0.0.0.0を指定することで、コンテナ外部からのアクセスを許可
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]