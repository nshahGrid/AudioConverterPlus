import os
from flask import Flask, render_template, request, send_file, jsonify
import subprocess
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'m4a'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format. Only M4A files are allowed'}), 400

    try:
        # Generate unique filename
        input_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{input_filename}")
        output_filename = f"{os.path.splitext(input_filename)[0]}.mp3"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{output_filename}")

        # Save uploaded file
        file.save(input_path)

        # Convert using ffmpeg
        try:
            subprocess.run(['ffmpeg', '-i', input_path, output_path], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return jsonify({'error': 'Conversion failed'}), 500
        except FileNotFoundError:
            return jsonify({'error': 'FFMPEG not installed'}), 500

        # Send converted file
        try:
            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename
            )
        finally:
            # Cleanup temporary files
            try:
                os.remove(input_path)
                os.remove(output_path)
            except:
                pass

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html'), 500
