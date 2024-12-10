from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
from colorthief import ColorThief
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['THUMBNAIL_FOLDER'] = 'static/thumbnails'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_thumbnail(image_path, thumbnail_path):
    with Image.open(image_path) as img:
        img.thumbnail((100, 100))
        img.save(thumbnail_path)


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def get_top_colors(image_path, num_colors=10, tolerance=10):
    color_thief = ColorThief(image_path)
    palette = color_thief.get_palette(color_count=num_colors)

    # Tolerance for grouping similar colors
    def color_within_tolerance(c1, c2):
        if not isinstance(c1, tuple) or not isinstance(c2, tuple):
            return False
        return all(abs(c1[i] - c2[i]) <= tolerance for i in range(3))

    with Image.open(image_path) as img:
        pixels = list(img.getdata())
        total_pixels = len(pixels)
        color_counts = {color: 0 for color in palette}
        unique_colors = set()

        # Group colors within tolerance
        for pixel in pixels:
            added = False
            for color in list(color_counts.keys()):
                if color_within_tolerance(pixel, color):
                    color_counts[color] += 1
                    unique_colors.add(color)
                    added = True
                    break
            if not added:
                unique_colors.add(pixel)

        # Calculate color percentages based on the total number of pixels
        color_percentage = [(color, count / total_pixels) for color, count in color_counts.items()]

        # Sort by percentage
        sorted_colors = sorted(color_percentage, key=lambda x: x[1], reverse=True)[:num_colors]

        # Convert RGB to HEX for displaying
        sorted_colors_hex = [{'hex': rgb_to_hex(color), 'rgb': color, 'percentage': percentage} for color, percentage in
                             sorted_colors]

        # Ensure exactly num_colors in the list
        while len(sorted_colors_hex) < num_colors:
            sorted_colors_hex.append({'hex': '#ffffff', 'rgb': (255, 255, 255), 'percentage': 0})

        for color_data in sorted_colors_hex:
            print(
                f"Color: {color_data['rgb']}, Hex: {color_data['hex']}, Percentage: {color_data['percentage'] * 100:.2f}%")

    return sorted_colors_hex, len(unique_colors)


@app.route('/', methods=['GET', 'POST'])
def index():
    tolerance = 10  # Define your tolerance value here
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(file_path)

            thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
            if not os.path.exists(app.config['THUMBNAIL_FOLDER']):
                os.makedirs(app.config['THUMBNAIL_FOLDER'])
            create_thumbnail(file_path, thumbnail_path)

            top_colors, total_colors = get_top_colors(file_path, num_colors=10, tolerance=tolerance)

            return render_template('index.html', filename=filename, colors=top_colors)

    return render_template('index.html', tolerance=tolerance)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/thumbnails/<filename>')
def thumbnail_file(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)
