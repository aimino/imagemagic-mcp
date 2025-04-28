import json
import sys
import os
import click
import platform
import mcp.types as types
from mcp.server.lowlevel import Server
import anyio
import traceback
from wand.image import Image
import tempfile
import base64
import datetime

# ログファイルの設定
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagemagick_server_log.txt")

def log_to_file(message):
    """ログをファイルに出力する"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

@click.command()
@click.option("--transport", default="stdio", type=click.Choice(["stdio"]), help="Transport type (only stdio supported)")
def main(transport: str) -> int:
    """Run the ImageMagick MCP server."""
    app = Server("ImageMagick MCP Server")

    @app.call_tool()
    async def binarize_image(
        image_path: str = None,
        threshold: float = 0.5,
        **kwargs
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Binarize an image using ImageMagick.
        
        Args:
            image_path: Path to the image file to binarize
            threshold: Threshold value for binarization (0.0 to 1.0)
        """
        try:
            log_to_file(f"Raw input - image_path: {repr(image_path)}, threshold: {repr(threshold)}, kwargs: {kwargs}")
            log_to_file(f"DEBUG: Received arguments: {locals()}")
            
            # 特殊なケース：image_pathが'binarize_image'で、thresholdが辞書の場合
            if image_path == 'binarize_image' and isinstance(threshold, dict):
                log_to_file(f"DEBUG: Detected special case - image_path is 'binarize_image' and threshold is a dictionary")
                if "image_path" in threshold:
                    image_path = threshold.get("image_path")
                    log_to_file(f"DEBUG: Using image_path from threshold dictionary: {image_path}")
                if "threshold" in threshold:
                    threshold = threshold.get("threshold")
                    log_to_file(f"DEBUG: Using threshold from threshold dictionary: {threshold}")
            
            # デバッグ出力をさらに詳細に
            log_to_file(f"DEBUG: kwargs type: {type(kwargs)}")
            log_to_file(f"DEBUG: kwargs keys: {kwargs.keys() if kwargs else 'None'}")
            if "arguments" in kwargs:
                log_to_file(f"DEBUG: arguments type: {type(kwargs['arguments'])}")
                log_to_file(f"DEBUG: arguments content: {kwargs['arguments']}")
            
            # 引数の処理をさらに改善
            if kwargs:
                if "arguments" in kwargs:
                    args = kwargs["arguments"]
                    log_to_file(f"DEBUG: Found arguments in kwargs: {args}")
                    if isinstance(args, dict):
                        if "image_path" in args:
                            image_path = args["image_path"]
                            log_to_file(f"DEBUG: Using image_path from arguments: {image_path}")
                        if "threshold" in args:
                            threshold = args["threshold"]
                            log_to_file(f"DEBUG: Using threshold from arguments: {threshold}")
            elif isinstance(image_path, dict):
                print(f"Image path is a dictionary: {image_path}", file=sys.stderr)
                if "image_path" in image_path:
                    image_path = image_path.get("image_path")
                if "threshold" in image_path:
                    threshold = image_path.get("threshold")
            elif image_path and isinstance(image_path, str) and image_path.strip().startswith("{"):
                try:
                    json_data = json.loads(image_path)
                    print(f"Parsed JSON from image_path: {json_data}", file=sys.stderr)
                    if "image_path" in json_data:
                        image_path = json_data.get("image_path")
                    if "threshold" in json_data:
                        threshold = json_data.get("threshold")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON from image_path", file=sys.stderr)
            
            # Validate inputs
            if not image_path:
                log_to_file("Error: No image path provided")
                return [types.TextContent(type="text", text="Error: No image path provided")]
            
            log_to_file(f"Checking if file exists: {image_path}")
            if not os.path.exists(image_path):
                log_to_file(f"Error: Image file not found at {image_path}")
                return [types.TextContent(type="text", text=f"Error: Image file not found at {image_path}")]
            
            # Ensure threshold is within valid range
            threshold_float = float(threshold)
            if threshold_float < 0.0 or threshold_float > 1.0:
                threshold_float = 0.5
                print(f"Threshold value out of range, using default: {threshold_float}", file=sys.stderr)
            
            # Create output filename
            file_name, file_ext = os.path.splitext(os.path.basename(image_path))
            output_dir = os.path.dirname(image_path)
            output_path = os.path.join(output_dir, f"{file_name}_binarized{file_ext}")
            
            # Process the image with ImageMagick using Wand
            with Image(filename=image_path) as img:
                # Convert to grayscale first
                img.type = 'grayscale'
                # Apply threshold to binarize
                img.threshold(threshold_float)
                # Save the processed image
                img.save(filename=output_path)
            
            print(f"Image binarized successfully. Output saved to: {output_path}", file=sys.stderr)
            
            # Read the processed image as base64 for embedding
            with open(output_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Determine MIME type based on file extension
            mime_type = "image/jpeg"  # Default
            if file_ext.lower() in ['.png']:
                mime_type = "image/png"
            elif file_ext.lower() in ['.gif']:
                mime_type = "image/gif"
            elif file_ext.lower() in ['.bmp']:
                mime_type = "image/bmp"
            elif file_ext.lower() in ['.tiff', '.tif']:
                mime_type = "image/tiff"
            
            # 画像データのサイズを小さくするために、画像をリサイズするオプションを追加
            # 元の画像データを返す代わりに、処理済み画像へのパスを返す
            return [
                types.TextContent(type="text", text=f"Image binarized successfully. Output saved to: {output_path}"),
                types.TextContent(type="text", text=f"画像の二値化が完了しました。出力ファイル: {output_path}")
            ]
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"Error in binarize_image: {traceback_str}", file=sys.stderr)
            
            return [
                types.TextContent(type="text", text=f"Error: {str(e)}")
            ]

    @app.call_tool()
    async def modify_colors(
        image_path: str = None,
        hue_shift: float = 0.0,
        brightness: float = 100.0,
        saturation: float = 100.0,
        **kwargs
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Modify the colors of an image using ImageMagick.
        
        Args:
            image_path: Path to the image file to modify
            hue_shift: Hue shift value in degrees (-360.0 to 360.0)
            brightness: Brightness adjustment (0.0 to 200.0, 100.0 is original)
            saturation: Saturation adjustment (0.0 to 200.0, 100.0 is original)
        """
        try:
            log_to_file(f"Raw input - image_path: {repr(image_path)}, hue_shift: {repr(hue_shift)}, brightness: {repr(brightness)}, saturation: {repr(saturation)}, kwargs: {kwargs}")
            log_to_file(f"DEBUG: Received arguments: {locals()}")
            
            # 特殊なケース：image_pathが'modify_colors'で、hue_shiftが辞書の場合
            if image_path == 'modify_colors' and isinstance(hue_shift, dict):
                log_to_file(f"DEBUG: Detected special case - image_path is 'modify_colors' and hue_shift is a dictionary")
                if "image_path" in hue_shift:
                    image_path = hue_shift.get("image_path")
                    log_to_file(f"DEBUG: Using image_path from hue_shift dictionary: {image_path}")
                if "hue_shift" in hue_shift:
                    hue_shift = hue_shift.get("hue_shift")
                    log_to_file(f"DEBUG: Using hue_shift from hue_shift dictionary: {hue_shift}")
                if "brightness" in hue_shift:
                    brightness = hue_shift.get("brightness")
                    log_to_file(f"DEBUG: Using brightness from hue_shift dictionary: {brightness}")
                if "saturation" in hue_shift:
                    saturation = hue_shift.get("saturation")
                    log_to_file(f"DEBUG: Using saturation from hue_shift dictionary: {saturation}")
            
            # デバッグ出力をさらに詳細に
            log_to_file(f"DEBUG: kwargs type: {type(kwargs)}")
            log_to_file(f"DEBUG: kwargs keys: {kwargs.keys() if kwargs else 'None'}")
            if "arguments" in kwargs:
                log_to_file(f"DEBUG: arguments type: {type(kwargs['arguments'])}")
                log_to_file(f"DEBUG: arguments content: {kwargs['arguments']}")
            
            # 引数の処理をさらに改善
            if kwargs:
                if "arguments" in kwargs:
                    args = kwargs["arguments"]
                    log_to_file(f"DEBUG: Found arguments in kwargs: {args}")
                    if isinstance(args, dict):
                        if "image_path" in args:
                            image_path = args["image_path"]
                            log_to_file(f"DEBUG: Using image_path from arguments: {image_path}")
                        if "hue_shift" in args:
                            hue_shift = args["hue_shift"]
                            log_to_file(f"DEBUG: Using hue_shift from arguments: {hue_shift}")
                        if "brightness" in args:
                            brightness = args["brightness"]
                            log_to_file(f"DEBUG: Using brightness from arguments: {brightness}")
                        if "saturation" in args:
                            saturation = args["saturation"]
                            log_to_file(f"DEBUG: Using saturation from arguments: {saturation}")
            elif isinstance(image_path, dict):
                log_to_file(f"Image path is a dictionary: {image_path}")
                if "image_path" in image_path:
                    image_path = image_path.get("image_path")
                if "hue_shift" in image_path:
                    hue_shift = image_path.get("hue_shift")
                if "brightness" in image_path:
                    brightness = image_path.get("brightness")
                if "saturation" in image_path:
                    saturation = image_path.get("saturation")
            elif image_path and isinstance(image_path, str) and image_path.strip().startswith("{"):
                try:
                    json_data = json.loads(image_path)
                    log_to_file(f"Parsed JSON from image_path: {json_data}")
                    if "image_path" in json_data:
                        image_path = json_data.get("image_path")
                    if "hue_shift" in json_data:
                        hue_shift = json_data.get("hue_shift")
                    if "brightness" in json_data:
                        brightness = json_data.get("brightness")
                    if "saturation" in json_data:
                        saturation = json_data.get("saturation")
                except json.JSONDecodeError:
                    log_to_file(f"Failed to parse JSON from image_path")
            
            # Validate inputs
            if not image_path:
                log_to_file("Error: No image path provided")
                return [types.TextContent(type="text", text="Error: No image path provided")]
            
            log_to_file(f"Checking if file exists: {image_path}")
            if not os.path.exists(image_path):
                log_to_file(f"Error: Image file not found at {image_path}")
                return [types.TextContent(type="text", text=f"Error: Image file not found at {image_path}")]
            
            # パラメータの範囲チェックと正規化
            # 色相変更量の範囲チェック
            hue_shift_float = float(hue_shift)
            # 値を-360〜360の範囲に正規化
            while hue_shift_float < -360.0:
                hue_shift_float += 360.0
            while hue_shift_float > 360.0:
                hue_shift_float -= 360.0
            
            # 輝度の範囲チェック
            brightness_float = float(brightness)
            if brightness_float < 0.0:
                brightness_float = 0.0
                log_to_file(f"Brightness value out of range, using minimum: {brightness_float}")
            elif brightness_float > 200.0:
                brightness_float = 200.0
                log_to_file(f"Brightness value out of range, using maximum: {brightness_float}")
            
            # 彩度の範囲チェック
            saturation_float = float(saturation)
            if saturation_float < 0.0:
                saturation_float = 0.0
                log_to_file(f"Saturation value out of range, using minimum: {saturation_float}")
            elif saturation_float > 200.0:
                saturation_float = 200.0
                log_to_file(f"Saturation value out of range, using maximum: {saturation_float}")
            
            log_to_file(f"Using normalized values - hue_shift: {hue_shift_float}, brightness: {brightness_float}, saturation: {saturation_float}")
            
            # Create output filename
            file_name, file_ext = os.path.splitext(os.path.basename(image_path))
            output_dir = os.path.dirname(image_path)
            output_path = os.path.join(output_dir, f"{file_name}_color_modified{file_ext}")
            
            # Process the image with ImageMagick using Wand
            with Image(filename=image_path) as img:
                # 色相、輝度、彩度を変更
                # modulate関数のパラメータ:
                # - brightness: 輝度（0〜200、100が元の輝度）
                # - saturation: 彩度（0〜200、100が元の彩度）
                # - hue: 色相（0〜200、100が元の色相）
                # 色相の変更は100 + hue_shift * 100 / 360 で変換
                img.modulate(
                    brightness=brightness_float,
                    saturation=saturation_float,
                    hue=100.0 + hue_shift_float * 100.0 / 360.0
                )
                # Save the processed image
                img.save(filename=output_path)
            
            log_to_file(f"Image colors modified successfully. Output saved to: {output_path}")
            
            # Read the processed image as base64 for embedding
            with open(output_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Determine MIME type based on file extension
            mime_type = "image/jpeg"  # Default
            if file_ext.lower() in ['.png']:
                mime_type = "image/png"
            elif file_ext.lower() in ['.gif']:
                mime_type = "image/gif"
            elif file_ext.lower() in ['.bmp']:
                mime_type = "image/bmp"
            elif file_ext.lower() in ['.tiff', '.tif']:
                mime_type = "image/tiff"
            
            # 元の画像データを返す代わりに、処理済み画像へのパスを返す
            return [
                types.TextContent(type="text", text=f"Image colors modified successfully. Output saved to: {output_path}"),
                types.TextContent(type="text", text=f"画像の色調が変更されました。出力ファイル: {output_path}")
            ]
        except Exception as e:
            traceback_str = traceback.format_exc()
            log_to_file(f"Error in modify_colors: {traceback_str}")
            
            return [
                types.TextContent(type="text", text=f"Error: {str(e)}")
            ]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List the available tools for this MCP server."""
        return [
            types.Tool(
                name="binarize_image",
                description="Binarize an image using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to binarize"
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Threshold value for binarization (0.0 to 1.0)",
                            "default": 0.5
                        }
                    }
                }
            ),
            types.Tool(
                name="modify_colors",
                description="Modify the colors (hue, brightness, saturation) of an image using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to modify"
                        },
                        "hue_shift": {
                            "type": "number",
                            "description": "Hue shift value in degrees (-360.0 to 360.0)",
                            "default": 0.0
                        },
                        "brightness": {
                            "type": "number",
                            "description": "Brightness adjustment (0.0 to 200.0, 100.0 is original)",
                            "default": 100.0
                        },
                        "saturation": {
                            "type": "number",
                            "description": "Saturation adjustment (0.0 to 200.0, 100.0 is original)",
                            "default": 100.0
                        }
                    }
                }
            )
        ]

    from mcp.server.stdio import stdio_server

    async def arun():
        async with stdio_server() as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    anyio.run(arun)
    return 0

if __name__ == "__main__":
    main()
