# ImageMagick MCP Server

The ImageMagick MCP Server is a server that provides ImageMagick image processing capabilities using the MCP protocol (Model Context Protocol). It implements image binarization and color adjustment functions.

## Features

- Image binarization processing (threshold can be specified)
- Image color adjustment (hue, brightness, saturation can be adjusted)
- Image resizing (width, height, or scale factor can be specified)
- Image format conversion (convert between various formats like PNG, JPG, BMP, TGA, etc.)
- Image blurring (radius and sigma can be specified)
- Integration with AI assistants via MCP protocol

## Requirements

- Python 3.8 or higher
- ImageMagick
- MCP library
- Wand library (Python bindings for ImageMagick)
- Click library

## Installation

1. Clone the repository:
```bash
git clone https://github.com/aimino/imagemagic-mcp.git
cd imagemagic-mcp
```

2. Install dependencies:

### For Windows:
```bash
# Install ImageMagick
# Download and install the installer from the official site
# https://imagemagick.org/script/download.php#windows
# Select "Install development headers and libraries for C and C++" option during installation

# Install Python packages
pip install wand mcp click
```

### For Linux:
```bash
# Install ImageMagick
sudo apt-get update
sudo apt-get install -y imagemagick libmagickwand-dev

# Install Python packages
pip install wand mcp click
```

## Usage

### Running the Server

You can run the server using the following methods:

1. Directly with Python:
```bash
python imagemagick_server.py
```

2. Using the MCP CLI tool:
```bash
mcp run imagemagick_server.py
```

This server provides the following tools:
- `binarize_image`: Binarize an image using ImageMagick
- `modify_colors`: Adjust the hue, brightness, and saturation of an image using ImageMagick
- `resize_image`: Resize an image using ImageMagick
- `convert_image_format`: Convert an image from one format to another (e.g., PNG to JPG, BMP to TGA)
- `blur_image`: Blur an image using ImageMagick

### MCP Server Configuration

To use the MCP server, you need to create a `cline_mcp_settings.json` file in the appropriate location:

#### Windows
```
%APPDATA%\cline\cline_mcp_settings.json
```

#### macOS/Linux
```
~/.config/cline/cline_mcp_settings.json
```

The contents of the `cline_mcp_settings.json` file should be as follows:

```json
{
  "mcpServers": {
    "imagemagick-mcp": {
      "command": "python",
      "args": ["C:/path/to/imagemagic-mcp/imagemagick_server.py"],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

Replace `C:/path/to/imagemagic-mcp` with the actual path to the repository.

### Testing with Claude or Other MCP Clients

Once the server is running and configured, Claude or other MCP clients can use it for image processing.

#### Example of Using the Binarization Feature

In Claude, you can use it as follows:

```
I want to binarize an image using the imagemagick-mcp tool.
```

Claude can binarize an image using the MCP server with a command like this:

```json
{
  "image_path": "/path/to/image.jpg",
  "threshold": 0.5
}
```

#### Example of Using the Color Adjustment Feature

In Claude, you can use it as follows:

```
I want to adjust the colors of an image using the imagemagick-mcp tool.
```

Claude can adjust the colors of an image using the MCP server with a command like this:

```json
{
  "image_path": "/path/to/image.jpg",
  "hue_shift": 180.0,
  "brightness": 110.0,
  "saturation": 120.0
}
```

Parameter descriptions:
- `hue_shift`: Amount of hue change (-360.0 to 360.0 degrees, 0.0 is the original hue)
- `brightness`: Brightness adjustment (0.0 to 200.0, 100.0 is the original brightness)
- `saturation`: Saturation adjustment (0.0 to 200.0, 100.0 is the original saturation)

#### Example of Using the Resizing Feature

In Claude, you can use it as follows:

```
I want to resize an image using the imagemagick-mcp tool.
```

Claude can resize an image using the MCP server with a command like this:

```json
{
  "image_path": "/path/to/image.jpg",
  "width": 800,
  "height": 600
}
```

Or resize by specifying only one dimension to maintain aspect ratio:

```json
{
  "image_path": "/path/to/image.jpg",
  "width": 800
}
```

Or resize using a scale factor:

```json
{
  "image_path": "/path/to/image.jpg",
  "scale": 0.5
}
```

Parameter descriptions:
- `width`: New width in pixels. If only width is specified, height will be calculated to maintain aspect ratio.
- `height`: New height in pixels. If only height is specified, width will be calculated to maintain aspect ratio.
- `scale`: Scale factor (e.g., 0.5 for half size, 2.0 for double size). If specified, width and height are ignored.

#### Example of Using the Format Conversion Feature

In Claude, you can use it as follows:

```
I want to convert an image format using the imagemagick-mcp tool.
```

Claude can convert an image format using the MCP server with a command like this:

```json
{
  "image_path": "/path/to/image.png",
  "output_format": "jpg",
  "quality": 90
}
```

Or convert to other formats:

```json
{
  "image_path": "/path/to/image.bmp",
  "output_format": "tga"
}
```

Parameter descriptions:
- `output_format`: The target format to convert to (e.g., jpg, png, tiff, bmp, tga, webp, etc.)
- `quality`: Quality for lossy formats like JPG (1-100, higher is better quality). Default is 85.

#### Example of Using the Blur Feature

In Claude, you can use it as follows:

```
I want to blur an image using the imagemagick-mcp tool.
```

Claude can blur an image using the MCP server with a command like this:

```json
{
  "image_path": "/path/to/image.jpg",
  "sigma": 5.0
}
```

Or with more control over the blur parameters:

```json
{
  "image_path": "/path/to/image.jpg",
  "radius": 0.0,
  "sigma": 3.0
}
```

Parameter descriptions:
- `radius`: Blur radius (0.0 or higher, 0.0 means auto-select). Default is 0.0.
- `sigma`: Blur sigma - controls the blur strength (higher values create stronger blur). Default is 3.0.

### How It Works

The server uses the MCP protocol to receive requests from AI assistants and uses ImageMagick (via the Wand library) to process images. Communication is done through stdio (standard input/output) and is compatible with Claude and other MCP-compatible assistants.

When Claude receives a request to binarize an image:
1. It connects to the MCP server using the settings in `cline_mcp_settings.json`
2. It calls the `binarize_image` tool with the image path and threshold parameters
3. The server binarizes the image using ImageMagick and returns the result

## License

MIT
