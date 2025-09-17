import time
import shutil
from pathlib import Path
from typing import Optional

class VoiceConverter:
    """
    RVCモデルを使用して声質変換を行うクラス。
    UIから独立したバックエンド処理をカプセル化します。
    """

    def __init__(self, model_dir: str):
        """
        VoiceConverterのコンストラクタ。

        Args:
            model_dir (str): .pthモデルファイルと.indexファイルが格納されている
                             ディレクトリのパス。
        """
        self.model_dir = Path(model_dir)
        self.model_path: Optional[Path] = self._find_file("*.pth")
        self.index_path: Optional[Path] = self._find_file("*.index")
        
        # このファイルの場所を基準にappディレクトリのルートパスを取得
        self.app_root: Path = Path(__file__).resolve().parent.parent

        if not self.model_path:
            raise FileNotFoundError(f".pthファイルがディレクトリ内に見つかりません: {model_dir}")
        if not self.index_path:
            raise FileNotFoundError(f".indexファイルがディレクトリ内に見つかりません: {model_dir}")

        # ここで実際のモデルロード処理を行う (今回はダミーとしてログ出力)
        # from rvc import load_model
        # self.model = load_model(self.model_path)
        print(f"モデルをロードしました: {self.model_path}")
        print(f"インデックスをロードしました: {self.index_path}")

    def _find_file(self, pattern: str) -> Optional[Path]:
        """
        指定されたパターンのファイルをディレクトリ内で検索します。

        Args:
            pattern (str): 検索するファイルのglobパターン。

        Returns:
            Optional[Path]: 見つかったファイルのPathオブジェクト。見つからない場合はNone。
        """
        try:
            return next(self.model_dir.glob(pattern))
        except StopIteration:
            return None

    def convert_voice(self, input_wav_path: str, pitch_change: int) -> str:
        """
        声質変換を実行します。
        実際のRVC推論の代わりに、入力ファイルをコピーするダミー処理を行います。

        Args:
            input_wav_path (str): 変換元のWAVファイルのパス。
            pitch_change (int): ピッチの変更量（半音単位）。

        Returns:
            str: 保存した変換後WAVファイルのパス。
        """
        print(f"音声変換を開始します: {input_wav_path}")
        print(f"ピッチ変更量: {pitch_change}")

        # --- ここからRVCの推論処理（ダミー） ---
        # 処理時間をシミュレート
        time.sleep(3) 
        
        # 出力先ディレクトリを作成
        output_dir: Path = self.app_root / "temp"
        output_dir.mkdir(exist_ok=True)
        
        # 出力ファイル名を一意にする
        timestamp = int(time.time())
        output_wav_path: Path = output_dir / f"output_{timestamp}.wav"
        
        # ダミー処理として入力ファイルをコピー
        shutil.copy(input_wav_path, output_wav_path)
        # --- ここまでRVCの推論処理（ダミー） ---

        print(f"音声変換が完了しました: {output_wav_path}")
        return str(output_wav_path)