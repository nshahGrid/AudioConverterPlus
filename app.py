import os
import logging
from flask import Flask, render_template, request, send_file, jsonify, url_for
import subprocess
import uuid
from werkzeug.utils import secure_filename
import time
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'m4a'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
CLEANUP_DELAY = 600  # 10 minutes

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
        logger.info(f"Attempting to download file: {filename}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {filename}")
            return jsonify({'error': 'File not found or expired'}), 404
            
        if not filename.startswith(tuple(str(uuid.UUID(x)) for x in [filename.split('_')[0]])):
            logger.error(f"Invalid filename format: {filename}")
            return jsonify({'error': 'Invalid file request'}), 400
            
        logger.info(f"Sending file: {filename}")
        
        response = send_file(
            file_path,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename.split('_', 1)[1]  # Remove UUID prefix
        )
        
        # Add Cache-Control and Content-Disposition headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename.split("_", 1)[1]}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        return jsonify({'error': 'Error processing download request'}), 500

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        logger.error("No file uploaded in request")
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    bitrate = request.form.get('bitrate', '192k')  # Default to 192k if not specified
    
    if file.filename == '':
        logger.error("Empty filename submitted")
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        logger.error(f"Invalid file format: {file.filename}")
        return jsonify({'error': 'Invalid file format. Only M4A files are allowed'}), 400

    try:
        # Generate unique filename
        input_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{input_filename}")
        output_filename = f"{unique_id}_{os.path.splitext(input_filename)[0]}.mp3"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        logger.info(f"Saving uploaded file: {input_filename}")
        file.save(input_path)

        # Convert using ffmpeg with specified bitrate
        try:
            logger.info(f"Starting conversion: {input_filename} to MP3 at {bitrate}")
            subprocess.run([
                'ffmpeg', '-i', input_path,
                '-b:a', bitrate,
                output_path
            ], check=True, capture_output=True)
            logger.info("Conversion completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion failed: {str(e)}")
            return jsonify({'error': 'Conversion failed'}), 500
        except FileNotFoundError:
            logger.error("FFMPEG not installed")
            return jsonify({'error': 'FFMPEG not installed'}), 500

        # Clean up input file
        try:
            os.remove(input_path)
            logger.info(f"Cleaned up input file: {input_filename}")
        except Exception as e:
            logger.warning(f"Failed to clean up input file: {str(e)}")

        # Schedule cleanup of output file
        def cleanup_file():
            time.sleep(CLEANUP_DELAY)
            try:
                os.remove(output_path)
                logger.info(f"Cleaned up output file: {output_filename}")
            except Exception as e:
                logger.warning(f"Failed to clean up output file: {str(e)}")

        # Start cleanup thread
        Thread(target=cleanup_file, daemon=True).start()
        logger.info(f"Scheduled cleanup for: {output_filename} in {CLEANUP_DELAY} seconds")

        # Return download URL with absolute path
        download_url = url_for('download_file', filename=output_filename, _external=True)
        logger.info(f"Generated download URL: {download_url}")
        
        return jsonify({
            'success': True,
            'download_url': download_url,
            'filename': os.path.splitext(input_filename)[0] + '.mp3'
        })

    except Exception as e:
        logger.error(f"Error processing conversion: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    logger.error(f"File too large error: {str(e)}")
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html'), 500
