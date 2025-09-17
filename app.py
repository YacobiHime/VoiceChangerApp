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
st.title("🎙️ ボイスチェンジャーアプリ")

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

@st.cache_resource
def get_rvc_inference_model(pth_path: Path, index_path: Optional[Path]) -> RVCInference:
    """
    RVCモデルを読み込み、キャッシュします。
    """
    st.info(f"モデルを読み込んでいます: {pth_path.name}")
    return RVCInference(model_path=pth_path, index_path=index_path)

# --- 3. UIコンポーネントの配置 ---

st.sidebar.header("推論パラメータ")

if not models:
    st.error("'models' ディレクトリにモデルが見つかりません。RVCモデルを追加してください。")
    st.stop()

model_name: str = st.sidebar.selectbox("RVCモデルを選択", options=list(models.keys()))

transpose: int = st.sidebar.slider(
    "トランスポーズ（ピッチ）", min_value=-24, max_value=24, value=0, step=1,
    help="ピッチを調整します。+12で1オクターブ上、-12で1オクターブ下です。"
)

f0_method: str = st.sidebar.selectbox(
    "ピッチ抽出アルゴリズム", options=["rmvpe", "pm", "harvest", "crepe"], index=0,
    help="ほとんどの場合でRMVPEを推奨します。"
)

index_rate: float = st.sidebar.slider(
    "インデックスレート", min_value=0.0, max_value=1.0, value=0.75, step=0.01,
    help="インデックスファイルが結果に与える影響を制御します。値が高いほど、元のアクセントがより保持されます。"
)

filter_radius: int = st.sidebar.slider(
    "フィルター半径", min_value=0, max_value=10, value=3, step=1,
    help=">=3の場合、ピッチの結果にメディアンフィルタを適用して、息っぽさを軽減します。"
)

resample_sr: int = st.sidebar.select_slider(
    "出力のリサンプリング", options=[0, 16000, 22050, 24000, 44100, 48000], value=0,
    help="出力音声をリサンプリングします。0はリサンプリングなしです。"
)

rms_mix_rate: float = st.sidebar.slider(
    "音量エンベロープのミックスレート", min_value=0.0, max_value=1.0, value=0.25, step=0.01,
    help="ソースと出力の音量エンベロープのバランスを取ります。0に近いほど、元の音量を模倣します。"
)

protect: float = st.sidebar.slider(
    "無声子音を保護", min_value=0.0, max_value=0.5, value=0.33, step=0.01,
    help="'s', 't', 'k'のような無声子音を保護します。0.5で無効になります。"
)

# --- 4. 音声変換処理のコアロジック ---

def run_conversion(input_path: Path, output_filename_prefix: str) -> None:
    """
    指定された音声ファイルをRVCモデルで変換し、結果をUIに表示します。

    Args:
        input_path (Path): 変換する入力音声ファイルのパス。
        output_filename_prefix (str): 出力ファイル名のプレフィックス。
    """
    with st.spinner("変換中... しばらくお待ちください。"):
        try:
            output_filename = f"{output_filename_prefix}_converted.wav"
            output_path = OUTPUT_DIR / output_filename

            model_paths = models[model_name]
            
            # 最初の.pthファイルを選択
            pth_path: Path = model_paths["pth"][0]
            
            #.indexファイルが存在すれば最初のものを選択
            index_path: Optional[Path] = model_paths["index"][0] if model_paths["index"] else None

            # キャッシュされたRVCモデルを取得
            rvc = get_rvc_inference_model(pth_path, index_path)

            # 推論を実行
            rvc.infer_file(
                input_path=input_path,
                output_path=output_path,
                f0_up_key=transpose,
                f0_method=f0_method,
                index_rate=index_rate,
                filter_radius=filter_radius,
                resample_sr=resample_sr,
                rms_mix_rate=rms_mix_rate,
                protect=protect
            )

            st.success("変換に成功しました！")
            st.audio(str(output_path), format="audio/wav")

            with open(output_path, "rb") as f:
                st.download_button(
                    label="変換後のファイルをダウンロード",
                    data=f,
                    file_name=output_filename,
                    mime="audio/wav"
                )
        except Exception as e:
            st.error(f"変換中にエラーが発生しました: {e}")

# --- 5. タブUIによる入力方法の選択 ---

tab_upload, tab_record = st.tabs(["⬆️ ファイルをアップロード", "🎙️ マイクで録音"])

with tab_upload:
    st.header("音声ファイルをアップロード")
    uploaded_file = st.file_uploader(
        "音声ファイル (WAV, MP3) をアップロード", type=["wav", "mp3"], label_visibility="collapsed"
    )

    if uploaded_file:
        st.audio(uploaded_file, format=uploaded_file.type)
        if st.button("アップロードしたファイルを変換"):
            input_path = INPUT_DIR / uploaded_file.name
            with open(input_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            run_conversion(input_path, Path(uploaded_file.name).stem)

with tab_record:
    st.header("マイクから音声を録音")
    audio: AudioSegment = audiorecorder("クリックして録音", "クリックして停止")

    if len(audio) > 0:
        st.audio(audio.export().read())
        
        if st.button("録音した音声を変換"):
            # ユニークなファイル名を生成して録音データを一時保存
            input_filename = f"recorded_{uuid.uuid4()}.wav"
            input_path = INPUT_DIR / input_filename
            audio.export(input_path, format="wav")
            
            run_conversion(input_path, Path(input_filename).stem)