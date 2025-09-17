import streamlit as st
import os
from pathlib import Path
import tempfile

# coreモジュールをインポートするために、
# このファイルの親ディレクトリ（app）をPythonのパスに追加
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from core.inference import VoiceConverter

# --- 定数定義 ---
MODEL_DIR = "./models/female_voice_1"

def save_uploaded_file(uploaded_file) -> str:
    """
    アップロードされたファイルを一時ディレクトリに保存し、そのパスを返します。

    Args:
        uploaded_file: st.file_uploaderから得られるUploadedFileオブジェクト。

    Returns:
        str: 保存された一時ファイルのパス。
    """
    try:
        # 一時ファイルを作成して内容を書き込む
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            fp.write(uploaded_file.getvalue())
            return fp.name
    except Exception as e:
        st.error(f"ファイルの保存中にエラーが発生しました: {e}")
        return ""

def main():
    """
    Streamlitアプリケーションのメイン関数。
    """
    st.set_page_config(
        page_title="AI Voice Labo",
        page_icon="🎙️",
        layout="centered"
    )

    st.title("AI Voice Labo 🗣️ -> 👩")
    st.markdown("---_男性の声を特定の女性の声に変換するデモアプリケーションです。_---")

    # --- 1. UIコンポーネントの配置 ---
    st.header("1. 音声ファイルをアップロード")
    uploaded_file = st.file_uploader(
        "変換したいWAVファイルを選択してください", type=["wav"]
    )

    st.header("2. パラメータを設定")
    pitch_change = st.slider(
        "ピッチ（音の高さ）調整",
        min_value=-24, 
        max_value=24, 
        value=12, 
        step=1,
        help="数値を上げると声が高く、下げると低くなります。男性から女性への変換では+12が一般的です。"
    )

    st.header("3. 変換を実行")
    convert_button = st.button("変換実行", type="primary")

    st.markdown("---")

    # --- 2. 実行フローの実装 ---
    if convert_button and uploaded_file is not None:
        # アップロードされたファイルを一時保存
        input_wav_path = save_uploaded_file(uploaded_file)
        if not input_wav_path:
            return

        # VoiceConverterのインスタンスを作成
        try:
            converter = VoiceConverter(model_dir=MODEL_DIR)
        except FileNotFoundError as e:
            st.error(f"モデルファイルの読み込みに失敗しました: {e}")
            st.error("管理者にお問い合わせください。")
            return

        # スピナーを表示して変換処理を実行
        with st.spinner("AIによる音声変換を実行中... 少々お待ちください。"):
            try:
                output_wav_path = converter.convert_voice(input_wav_path, pitch_change)
            except Exception as e:
                st.error(f"音声変換中に予期せぬエラーが発生しました: {e}")
                return
        
        st.success("音声変換が完了しました！")

        # --- 3. 結果の表示とダウンロード ---
        st.header("変換結果")
        st.audio(output_wav_path, format="audio/wav")

        with open(output_wav_path, "rb") as f:
            st.download_button(
                label="変換後の音声をダウンロード",
                data=f,
                file_name=f"converted_voice_{Path(output_wav_path).name}",
                mime="audio/wav"
            )
        
        # 一時ファイルをクリーンアップ
        os.remove(input_wav_path)
        # os.remove(output_wav_path) # ダウンロードのために残す

    elif convert_button and uploaded_file is None:
        st.warning("変換するWAVファイルをアップロードしてください。")

if __name__ == "__main__":
    main()