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
            print(f"Raw input - image_path: {repr(image_path)}, threshold: {repr(threshold)}, kwargs: {kwargs}", file=sys.stderr)
            
            # Handle input as JSON if provided
            if isinstance(image_path, dict):
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
                return [types.TextContent(type="text", text="Error: No image path provided")]
            
            if not os.path.exists(image_path):
                return [types.TextContent(type="text", text=f"Error: Image file not found at {image_path}")]
            
            # Ensure threshold is within valid range
            threshold_float = float(threshold)
            if threshold_float < 0.0 or threshold_float > 1.0:
                threshold_float = 0.5
                print(f"Threshold value out of range, using default: {threshold_float}", file=sys.stderr)
            
            # Create output filename
            file_name, file_ext = os.path.splitext(os.path.basename(image_path))
            output_path = os.path.join(tempfile.gettempdir(), f"{file_name}_binarized{file_ext}")
            
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
            
            return [
                types.TextContent(type="text", text=f"Image binarized successfully. Output saved to: {output_path}"),
                types.ImageContent(
                    type="image",
                    format=mime_type,
                    data=img_data
                )
            ]
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"Error in binarize_image: {traceback_str}", file=sys.stderr)
            
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
