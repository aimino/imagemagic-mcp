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
    async def process_image(
        name: str = None,
        arguments: dict = None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Process an image using ImageMagick.
        
        Args:
            name: Tool name (should be 'modify_colors' or 'binarize_image')
            arguments: Dictionary containing the actual arguments
        """
        try:
            log_to_file(f"FUNCTION CALLED: process_image")
            log_to_file(f"Raw input - name: {repr(name)}, arguments: {repr(arguments)}")
            log_to_file(f"DEBUG: Received arguments: {locals()}")
            
            # nameパラメータに基づいて処理を分岐
            is_binarize = False
            if name == 'binarize_image':
                log_to_file(f"Detected binarize_image call, will perform binarization")
                is_binarize = True
            
            # 共通の引数処理
            image_path = None
            if arguments and isinstance(arguments, dict):
                log_to_file(f"DEBUG: Processing arguments dictionary: {arguments}")
                if "image_path" in arguments:
                    image_path = arguments.get("image_path")
                    log_to_file(f"DEBUG: Using image_path from arguments: {image_path}")
            
            # Validate inputs
            if not image_path:
                log_to_file("Error: No image path provided")
                return [types.TextContent(type="text", text="Error: No image path provided")]
            
            log_to_file(f"Checking if file exists: {image_path}")
            if not os.path.exists(image_path):
                log_to_file(f"Error: Image file not found at {image_path}")
                return [types.TextContent(type="text", text=f"Error: Image file not found at {image_path}")]
            
            # Create output filename
            file_name, file_ext = os.path.splitext(os.path.basename(image_path))
            output_dir = os.path.dirname(image_path)
            
            # 二値化処理
            if is_binarize:
                # 二値化用パラメータの取得
                threshold = 0.5  # デフォルト値
                if arguments and isinstance(arguments, dict) and "threshold" in arguments:
                    threshold = arguments.get("threshold")
                    log_to_file(f"DEBUG: Using threshold from arguments: {threshold}")
                
                log_to_file(f"After argument processing - image_path: {image_path}, threshold: {threshold}")
                
                # しきい値の型変換と範囲チェック
                try:
                    threshold_float = float(threshold) if threshold is not None else 0.5
                    if threshold_float < 0.0 or threshold_float > 1.0:
                        threshold_float = 0.5
                        log_to_file(f"Threshold value out of range, using default: {threshold_float}")
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting threshold to float: {e}")
                    threshold_float = 0.5
                    log_to_file(f"Using default threshold due to conversion error: {threshold_float}")
                
                output_path = os.path.join(output_dir, f"{file_name}_binarized{file_ext}")
                
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    # Convert to grayscale first
                    img.type = 'grayscale'
                    # Apply threshold to binarize
                    img.threshold(threshold_float)
                    # Save the processed image
                    img.save(filename=output_path)
                
                log_to_file(f"Image binarized successfully. Output saved to: {output_path}")
                return [types.TextContent(type="text", text=f"Image binarized successfully. Output saved to: {output_path}")]
            
            # 色調変更処理
            else:
                # 色調変更用パラメータの取得
                hue_shift = 0.0  # デフォルト値
                brightness = 100.0  # デフォルト値
                saturation = 100.0  # デフォルト値
                
                if arguments and isinstance(arguments, dict):
                    if "hue_shift" in arguments:
                        hue_shift = arguments.get("hue_shift")
                        log_to_file(f"DEBUG: Using hue_shift from arguments: {hue_shift}")
                    if "brightness" in arguments:
                        brightness = arguments.get("brightness")
                        log_to_file(f"DEBUG: Using brightness from arguments: {brightness}")
                    if "saturation" in arguments:
                        saturation = arguments.get("saturation")
                        log_to_file(f"DEBUG: Using saturation from arguments: {saturation}")
                
                log_to_file(f"After argument processing - image_path: {image_path}, hue_shift: {hue_shift}, brightness: {brightness}, saturation: {saturation}")
                
                # パラメータの型変換と範囲チェック
                # 色相変更量の処理
                try:
                    hue_shift_float = float(hue_shift) if hue_shift is not None else 0.0
                    # 値を-360〜360の範囲に正規化
                    while hue_shift_float < -360.0:
                        hue_shift_float += 360.0
                    while hue_shift_float > 360.0:
                        hue_shift_float -= 360.0
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting hue_shift to float: {e}")
                    hue_shift_float = 0.0
                
                # 輝度の処理
                try:
                    brightness_float = float(brightness) if brightness is not None else 100.0
                    if brightness_float < 0.0:
                        brightness_float = 0.0
                        log_to_file(f"Brightness value out of range, using minimum: {brightness_float}")
                    elif brightness_float > 200.0:
                        brightness_float = 200.0
                        log_to_file(f"Brightness value out of range, using maximum: {brightness_float}")
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting brightness to float: {e}")
                    brightness_float = 100.0
                
                # 彩度の処理
                try:
                    saturation_float = float(saturation) if saturation is not None else 100.0
                    if saturation_float < 0.0:
                        saturation_float = 0.0
                        log_to_file(f"Saturation value out of range, using minimum: {saturation_float}")
                    elif saturation_float > 200.0:
                        saturation_float = 200.0
                        log_to_file(f"Saturation value out of range, using maximum: {saturation_float}")
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting saturation to float: {e}")
                    saturation_float = 100.0
                
                log_to_file(f"Using normalized values - hue_shift: {hue_shift_float}, brightness: {brightness_float}, saturation: {saturation_float}")
                
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
                return [types.TextContent(type="text", text=f"Image colors modified successfully. Output saved to: {output_path}")]
        except Exception as e:
            traceback_str = traceback.format_exc()
            log_to_file(f"Error in process_image: {traceback_str}")
            
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
