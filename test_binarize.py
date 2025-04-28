import sys
import os
from wand.image import Image
import tempfile

def binarize_image(image_path, threshold=0.5):
    """
    画像を二値化する関数
    
    Args:
        image_path: 二値化する画像のパス
        threshold: 二値化の閾値（0.0〜1.0）
    
    Returns:
        出力画像のパス
    """
    try:
        # 入力の検証
        if not os.path.exists(image_path):
            print(f"エラー: 画像ファイルが見つかりません: {image_path}")
            return None
        
        # 閾値の範囲チェック
        threshold_float = float(threshold)
        if threshold_float < 0.0 or threshold_float > 1.0:
            threshold_float = 0.5
            print(f"閾値が範囲外です。デフォルト値を使用します: {threshold_float}")
        
        # 出力ファイル名の作成
        file_name, file_ext = os.path.splitext(os.path.basename(image_path))
        output_path = os.path.join(tempfile.gettempdir(), f"{file_name}_binarized{file_ext}")
        
        # ImageMagickを使用して画像を処理
        with Image(filename=image_path) as img:
            # グレースケールに変換
            img.type = 'grayscale'
            # 閾値処理で二値化
            img.threshold(threshold_float)
            # 処理した画像を保存
            img.save(filename=output_path)
        
        print(f"画像の二値化が成功しました。出力: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"二値化処理中にエラーが発生しました: {str(e)}")
        return None

if __name__ == "__main__":
    # コマンドライン引数をチェック
    if len(sys.argv) < 2:
        print("使用方法: python test_binarize.py <画像パス> [閾値]")
        sys.exit(1)
    
    # 引数の取得
    image_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    
    # 二値化処理の実行
    output_path = binarize_image(image_path, threshold)
    
    if output_path:
        print(f"テスト成功: 二値化された画像が {output_path} に保存されました")
    else:
        print("テスト失敗: 画像の二値化処理に失敗しました")
        sys.exit(1)
