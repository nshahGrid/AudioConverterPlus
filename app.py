import os
from flask import Flask, render_template, request, send_file, jsonify, url_for
import subprocess
import uuid
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'m4a'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
CLEANUP_DELAY = 300  # 5 minutes

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename.split('_', 1)[1]  # Remove UUID prefix
            )
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    bitrate = request.form.get('bitrate', '192k')  # Default to 192k if not specified
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format. Only M4A files are allowed'}), 400

    try:
        # Generate unique filename
        input_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{input_filename}")
        output_filename = f"{unique_id}_{os.path.splitext(input_filename)[0]}.mp3"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        # Save uploaded file
        file.save(input_path)

        # Convert using ffmpeg with specified bitrate
        try:
            subprocess.run([
                'ffmpeg', '-i', input_path,
                '-b:a', bitrate,
                output_path
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return jsonify({'error': 'Conversion failed'}), 500
        except FileNotFoundError:
            return jsonify({'error': 'FFMPEG not installed'}), 500

        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass

        # Schedule cleanup of output file
        def cleanup_file():
            time.sleep(CLEANUP_DELAY)
            try:
                os.remove(output_path)
            except:
                pass

        # Start cleanup thread
        from threading import Thread
        Thread(target=cleanup_file, daemon=True).start()

        # Return download URL
        download_url = url_for('download_file', filename=output_filename, _external=True)
        return jsonify({
            'success': True,
            'download_url': download_url,
            'filename': os.path.splitext(input_filename)[0] + '.mp3'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html'), 500
