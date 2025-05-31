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
            is_resize = False
            is_convert_format = False
            is_blur = False
            is_grayscale = False
            is_get_info = False
            if name == 'binarize_image':
                log_to_file(f"Detected binarize_image call, will perform binarization")
                is_binarize = True
            elif name == 'resize_image':
                log_to_file(f"Detected resize_image call, will perform resizing")
                is_resize = True
            elif name == 'convert_image_format':
                log_to_file(f"Detected convert_image_format call, will perform format conversion")
                is_convert_format = True
            elif name == 'blur_image':
                log_to_file(f"Detected blur_image call, will perform blurring")
                is_blur = True
            elif name == 'grayscale_image':
                log_to_file(f"Detected grayscale_image call, will perform grayscale conversion")
                is_grayscale = True
            elif name == 'get_image_info':
                log_to_file(f"Detected get_image_info call, will get image information")
                is_get_info = True
            
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
            
            # フォーマット変換処理
            elif is_convert_format:
                # フォーマット変換用パラメータの取得
                output_format = None
                quality = None
                
                if arguments and isinstance(arguments, dict):
                    if "output_format" in arguments:
                        output_format = arguments.get("output_format")
                        log_to_file(f"DEBUG: Using output_format from arguments: {output_format}")
                    if "quality" in arguments:
                        quality = arguments.get("quality")
                        log_to_file(f"DEBUG: Using quality from arguments: {quality}")
                
                log_to_file(f"After argument processing - image_path: {image_path}, output_format: {output_format}, quality: {quality}")
                
                # パラメータの検証
                if not output_format:
                    log_to_file(f"Error: No output format specified")
                    return [types.TextContent(type="text", text=f"Error: No output format specified")]
                
                # 出力フォーマットの正規化（小文字に変換し、ドットを削除）
                output_format = output_format.lower().strip('.')
                
                # 品質パラメータの処理（JPEGなどの圧縮フォーマット用）
                try:
                    quality_int = int(quality) if quality is not None else 85
                    if quality_int < 1:
                        quality_int = 1
                        log_to_file(f"Quality value out of range, using minimum: {quality_int}")
                    elif quality_int > 100:
                        quality_int = 100
                        log_to_file(f"Quality value out of range, using maximum: {quality_int}")
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting quality to integer: {e}")
                    quality_int = 85
                
                # 出力ファイル名の作成
                output_path = os.path.join(output_dir, f"{file_name}.{output_format}")
                
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    # 品質設定（JPEGなどの圧縮フォーマット用）
                    img.compression_quality = quality_int
                    
                    # 画像を保存（フォーマットは拡張子から自動的に判断される）
                    img.save(filename=output_path)
                
                log_to_file(f"Image format converted successfully. Output saved to: {output_path}")
                return [types.TextContent(type="text", text=f"Image format converted successfully. Output saved to: {output_path}")]
            
            # リサイズ処理
            elif is_resize:
                # リサイズ用パラメータの取得
                width = None
                height = None
                scale = None
                
                if arguments and isinstance(arguments, dict):
                    if "width" in arguments:
                        width = arguments.get("width")
                        log_to_file(f"DEBUG: Using width from arguments: {width}")
                    if "height" in arguments:
                        height = arguments.get("height")
                        log_to_file(f"DEBUG: Using height from arguments: {height}")
                    if "scale" in arguments:
                        scale = arguments.get("scale")
                        log_to_file(f"DEBUG: Using scale from arguments: {scale}")
                
                log_to_file(f"After argument processing - image_path: {image_path}, width: {width}, height: {height}, scale: {scale}")
                
                # パラメータの型変換と検証
                try:
                    # scaleが指定されている場合は、widthとheightは無視する
                    if scale is not None:
                        scale_float = float(scale)
                        if scale_float <= 0:
                            log_to_file(f"Scale value must be positive, using default: 1.0")
                            scale_float = 1.0
                        width_float = None
                        height_float = None
                    else:
                        scale_float = None
                        # widthとheightの処理
                        if width is not None:
                            width_float = float(width)
                            if width_float <= 0:
                                log_to_file(f"Width value must be positive, using original width")
                                width_float = None
                        else:
                            width_float = None
                        
                        if height is not None:
                            height_float = float(height)
                            if height_float <= 0:
                                log_to_file(f"Height value must be positive, using original height")
                                height_float = None
                        else:
                            height_float = None
                        
                        # widthもheightも指定されていない場合は、元のサイズを使用
                        if width_float is None and height_float is None and scale_float is None:
                            log_to_file(f"No resize parameters specified, using original size")
                            return [types.TextContent(type="text", text=f"Error: No resize parameters specified")]
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting resize parameters to float: {e}")
                    return [types.TextContent(type="text", text=f"Error: Invalid resize parameters - {str(e)}")]
                
                output_path = os.path.join(output_dir, f"{file_name}_resized{file_ext}")
                
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    original_width = img.width
                    original_height = img.height
                    
                    # リサイズ処理
                    if scale_float is not None:
                        # スケールに基づいてリサイズ
                        new_width = int(original_width * scale_float)
                        new_height = int(original_height * scale_float)
                        log_to_file(f"Resizing image using scale factor {scale_float} to {new_width}x{new_height}")
                        img.resize(new_width, new_height)
                    else:
                        # widthとheightに基づいてリサイズ
                        if width_float is not None and height_float is not None:
                            # 両方指定されている場合
                            log_to_file(f"Resizing image to {width_float}x{height_float}")
                            img.resize(int(width_float), int(height_float))
                        elif width_float is not None:
                            # widthのみ指定されている場合、アスペクト比を維持
                            aspect_ratio = original_height / original_width
                            new_height = int(width_float * aspect_ratio)
                            log_to_file(f"Resizing image to width {width_float} (height {new_height} calculated to maintain aspect ratio)")
                            img.resize(int(width_float), new_height)
                        elif height_float is not None:
                            # heightのみ指定されている場合、アスペクト比を維持
                            aspect_ratio = original_width / original_height
                            new_width = int(height_float * aspect_ratio)
                            log_to_file(f"Resizing image to height {height_float} (width {new_width} calculated to maintain aspect ratio)")
                            img.resize(new_width, int(height_float))
                    
                    # Save the processed image
                    img.save(filename=output_path)
                
                log_to_file(f"Image resized successfully. Output saved to: {output_path}")
                return [types.TextContent(type="text", text=f"Image resized successfully. Output saved to: {output_path}")]
            
            # ぼかし処理
            elif is_blur:
                # ぼかし用パラメータの取得
                radius = None
                sigma = None
                
                if arguments and isinstance(arguments, dict):
                    if "radius" in arguments:
                        radius = arguments.get("radius")
                        log_to_file(f"DEBUG: Using radius from arguments: {radius}")
                    if "sigma" in arguments:
                        sigma = arguments.get("sigma")
                        log_to_file(f"DEBUG: Using sigma from arguments: {sigma}")
                
                log_to_file(f"After argument processing - image_path: {image_path}, radius: {radius}, sigma: {sigma}")
                
                # パラメータの型変換と検証
                try:
                    radius_float = float(radius) if radius is not None else 0.0
                    if radius_float < 0.0:
                        log_to_file(f"Radius value must be non-negative, using default: 0.0")
                        radius_float = 0.0
                    
                    sigma_float = float(sigma) if sigma is not None else 3.0
                    if sigma_float < 0.0:
                        log_to_file(f"Sigma value must be non-negative, using default: 3.0")
                        sigma_float = 3.0
                except (TypeError, ValueError) as e:
                    log_to_file(f"Error converting blur parameters to float: {e}")
                    radius_float = 0.0
                    sigma_float = 3.0
                    log_to_file(f"Using default blur parameters due to conversion error: radius={radius_float}, sigma={sigma_float}")
                
                output_path = os.path.join(output_dir, f"{file_name}_blurred{file_ext}")
                
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    # ぼかし処理を適用
                    img.blur(radius=radius_float, sigma=sigma_float)
                    # 処理した画像を保存
                    img.save(filename=output_path)
                
                log_to_file(f"Image blurred successfully. Output saved to: {output_path}")
                return [types.TextContent(type="text", text=f"Image blurred successfully. Output saved to: {output_path}")]
            
            # グレースケール変換処理
            elif is_grayscale:
                output_path = os.path.join(output_dir, f"{file_name}_grayscale{file_ext}")
                
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    # グレースケールに変換
                    img.type = 'grayscale'
                    # 処理した画像を保存
                    img.save(filename=output_path)
                
                log_to_file(f"Image converted to grayscale successfully. Output saved to: {output_path}")
                return [types.TextContent(type="text", text=f"Image converted to grayscale successfully. Output saved to: {output_path}")]
            
            # 画像情報取得処理
            elif is_get_info:
                # Process the image with ImageMagick using Wand
                with Image(filename=image_path) as img:
                    # 基本情報を取得
                    image_info = {
                        "filename": os.path.basename(image_path),
                        "full_path": image_path,
                        "format": img.format,
                        "width": img.width,
                        "height": img.height,
                        "depth": img.depth,
                        "colorspace": img.colorspace,
                        "compression": img.compression,
                        "resolution": {
                            "x": getattr(img.resolution, 'x', None) if hasattr(img, 'resolution') else None,
                            "y": getattr(img.resolution, 'y', None) if hasattr(img, 'resolution') else None
                        },
                        "file_size_bytes": os.path.getsize(image_path),
                        "has_alpha": img.alpha_channel,
                        "type": img.type
                    }
                    
                    # ファイルサイズを人間が読める形式に変換
                    file_size = image_info["file_size_bytes"]
                    if file_size < 1024:
                        size_str = f"{file_size} bytes"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    # 結果を整理して表示
                    result_text = f"""Image Information:
Filename: {image_info['filename']}
Path: {image_info['full_path']}
Format: {image_info['format']}
Dimensions: {image_info['width']} x {image_info['height']} pixels
Color Depth: {image_info['depth']} bits
Colorspace: {image_info['colorspace']}
Compression: {image_info['compression']}
File Size: {size_str}
Has Alpha Channel: {image_info['has_alpha']}
Image Type: {image_info['type']}"""
                    
                    if image_info['resolution']['x'] and image_info['resolution']['y']:
                        result_text += f"\nResolution: {image_info['resolution']['x']:.1f} x {image_info['resolution']['y']:.1f} DPI"
                
                log_to_file(f"Image information retrieved successfully for: {image_path}")
                return [types.TextContent(type="text", text=result_text)]
            
            # 色調変更処理
            elif name == 'modify_colors':
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
            
            # 当てはまる機能がない場合はエラーを返す
            else:
                error_message = f"Error: Unknown tool name '{name}'. Available tools are: binarize_image, blur_image, convert_image_format, get_image_info, grayscale_image, modify_colors, resize_image"
                log_to_file(error_message)
                return [types.TextContent(type="text", text=error_message)]
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
                name="blur_image",
                description="Blur an image using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to blur"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Blur radius (0.0 or higher, 0.0 means auto-select)",
                            "default": 0.0
                        },
                        "sigma": {
                            "type": "number",
                            "description": "Blur sigma - controls the blur strength (higher values create stronger blur)",
                            "default": 3.0
                        }
                    }
                }
            ),
            types.Tool(
                name="convert_image_format",
                description="Convert an image from one format to another (e.g., PNG to JPG, BMP to TGA)",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "output_format"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to convert"
                        },
                        "output_format": {
                            "type": "string",
                            "description": "Output format (e.g., jpg, png, tiff, bmp, tga, webp, etc.)"
                        },
                        "quality": {
                            "type": "number",
                            "description": "Quality for lossy formats like JPG (1-100, higher is better quality)",
                            "default": 85
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
            ),
            types.Tool(
                name="resize_image",
                description="Resize an image using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to resize"
                        },
                        "width": {
                            "type": "number",
                            "description": "New width in pixels. If only width is specified, height will be calculated to maintain aspect ratio.",
                            "default": None
                        },
                        "height": {
                            "type": "number",
                            "description": "New height in pixels. If only height is specified, width will be calculated to maintain aspect ratio.",
                            "default": None
                        },
                        "scale": {
                            "type": "number",
                            "description": "Scale factor (e.g., 0.5 for half size, 2.0 for double size). If specified, width and height are ignored.",
                            "default": None
                        }
                    }
                }
            ),
            types.Tool(
                name="grayscale_image",
                description="Convert an image to grayscale using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to convert to grayscale"
                        }
                    }
                }
            ),
            types.Tool(
                name="get_image_info",
                description="Get detailed information about an image using ImageMagick",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to analyze"
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
