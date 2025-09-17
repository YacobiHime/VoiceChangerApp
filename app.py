import streamlit as st
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from audiorecorder import audiorecorder
from pydub import AudioSegment
from rvc_python.infer import RVCInference

# --- 1. 初期設定と定数定義 ---

st.set_page_config(layout="wide")
st.title("🎙️ VoiceChangerApp")

# ディレクトリパスの定義
MODELS_DIR = Path("models")
INPUT_DIR = Path("input_audio")
OUTPUT_DIR = Path("output_audio")

# 必要なディレクトリが存在しない場合は作成
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --- 2. モデル読み込みとキャッシュ ---

@st.cache_resource
def get_rvc_models() -> Dict[str, Dict[str, List[Path]]]:
    """
    `models`ディレクトリから利用可能なRVCモデルを読み込みます。
    各モデルはサブディレクトリに格納されていることを前提とします。

    Returns:
        Dict[str, Dict[str, List[Path]]]: モデル名と、その.pthおよび.indexファイルのパスリストを格納した辞書。
    """
    models: Dict[str, Dict[str, List[Path]]] = {}
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                pth_files = sorted(list(model_dir.glob("*.pth")))
                index_files = sorted(list(model_dir.glob("*.index")))
                if pth_files:
                    models[model_dir.name] = {
                        "pth": pth_files,
                        "index": index_files
                    }
    return models

models = get_rvc_models()

# --- 3. UIコンポーネントの配置 ---

st.sidebar.header("Inference Parameters")

if not models:
    st.error("No models found in the 'models' directory. Please add RVC models.")
    st.stop()

model_name: str = st.sidebar.selectbox("Select RVC Model", options=list(models.keys()))

transpose: int = st.sidebar.slider(
    "Transpose (Pitch Shift)", min_value=-24, max_value=24, value=0, step=1,
    help="Adjust the pitch. +12 for one octave up, -12 for one octave down."
)

f0_method: str = st.sidebar.selectbox(
    "Pitch Extraction Algorithm", options=["rmvpe", "pm", "harvest", "crepe"], index=0,
    help="RMVPE is recommended for most cases."
)

index_rate: float = st.sidebar.slider(
    "Index Rate", min_value=0.0, max_value=1.0, value=0.75, step=0.01,
    help="Controls how much the index file affects the result. Higher values preserve more of the original accent."
)

filter_radius: int = st.sidebar.slider(
    "Filter Radius", min_value=0, max_value=10, value=3, step=1,
    help="If >=3, applies median filtering to the pitch results to reduce breathiness."
)

resample_sr: int = st.sidebar.select_slider(
    "Resample Output", options=[0, 16000, 22050, 24000, 44100, 48000], value=0,
    help="Resamples the output audio. 0 for no resampling."
)

rms_mix_rate: float = st.sidebar.slider(
    "Volume Envelope Mix Rate", min_value=0.0, max_value=1.0, value=0.25, step=0.01,
    help="Balances the volume envelope between the source and the output. Closer to 0 mimics the original volume."
)

protect: float = st.sidebar.slider(
    "Protect Voiceless Consonants", min_value=0.0, max_value=0.5, value=0.33, step=0.01,
    help="Protects voiceless sounds like 's', 't', 'k'. 0.5 to disable."
)

# --- 4. 音声変換処理のコアロジック ---

def run_conversion(input_path: Path, output_filename_prefix: str) -> None:
    """
    指定された音声ファイルをRVCモデルで変換し、結果をUIに表示します。

    Args:
        input_path (Path): 変換する入力音声ファイルのパス。
        output_filename_prefix (str): 出力ファイル名のプレフィックス。
    """
    with st.spinner("Converting... This may take a moment."):
        try:
            output_filename = f"{output_filename_prefix}_converted.wav"
            output_path = OUTPUT_DIR / output_filename

            model_paths = models[model_name]
            
            # 最初の.pthファイルを選択
            pth_path: Path = model_paths["pth"][0]
            
            #.indexファイルが存在すれば最初のものを選択
            index_path: Optional[Path] = model_paths["index"][0] if model_paths["index"] else None

            # RVCInferenceのインスタンス化時にモデルパスを渡す
            rvc = RVCInference(model_path=pth_path)

            rvc.infer_file(
                input_path=input_path,
                output_path=output_path,
                f0_up_key=transpose,
                f0_method=f0_method,
                index_path=model_paths["index"][0] if model_paths["index"] else None,
                index_rate=index_rate,
                filter_radius=filter_radius,
                resample_sr=resample_sr,
                rms_mix_rate=rms_mix_rate,
                protect=protect
            )

            st.success("Conversion successful!")
            st.audio(str(output_path), format="audio/wav")

            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Converted File",
                    data=f,
                    file_name=output_filename,
                    mime="audio/wav"
                )
        except Exception as e:
            st.error(f"An error occurred during conversion: {e}")

# --- 5. タブUIによる入力方法の選択 ---

tab_upload, tab_record = st.tabs(["⬆️ Upload File", "🎙️ Record Audio"])

with tab_upload:
    st.header("Upload an audio file")
    uploaded_file = st.file_uploader(
        "Upload an audio file (WAV, MP3)", type=["wav", "mp3"], label_visibility="collapsed"
    )

    if uploaded_file:
        st.audio(uploaded_file, format=uploaded_file.type)
        if st.button("Convert Uploaded File"):
            input_path = INPUT_DIR / uploaded_file.name
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            run_conversion(input_path, Path(uploaded_file.name).stem)

with tab_record:
    st.header("Record audio from your microphone")
    audio: AudioSegment = audiorecorder("Click to record", "Click to stop recording")

    if len(audio) > 0:
        st.audio(audio.export().read())
        
        if st.button("Convert Recorded Audio"):
            # ユニークなファイル名を生成して録音データを一時保存
            input_filename = f"recorded_{uuid.uuid4()}.wav"
            input_path = INPUT_DIR / input_filename
            audio.export(input_path, format="wav")
            
            run_conversion(input_path, Path(input_filename).stem)