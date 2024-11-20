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
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50MB max download size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition, Content-Length')
    return response

# Request logging middleware
@app.before_request
def log_request_info():
    logger.info('Request Headers: %s', dict(request.headers))
    logger.info('Request URL: %s %s', request.method, request.url)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    logger.info('Serving index page')
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.info(f"Attempting to download file: {filename}")
        
        # Validate file existence
        if not os.path.exists(file_path):
            logger.error(f"File not found: {filename}")
            return jsonify({'error': 'File not found or expired'}), 404
        
        # Validate file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_DOWNLOAD_SIZE:
            logger.error(f"File size exceeds limit: {filename} ({file_size} bytes)")
            return jsonify({'error': 'File size exceeds maximum limit'}), 413
            
        # Validate filename format (UUID prefix)
        if not filename.startswith(tuple(str(uuid.UUID(x)) for x in [filename.split('_')[0]])):
            logger.error(f"Invalid filename format: {filename}")
            return jsonify({'error': 'Invalid file request'}), 400
            
        logger.info(f"Sending file: {filename} (size: {file_size} bytes)")
        
        response = send_file(
            file_path,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename.split('_', 1)[1]  # Remove UUID prefix
        )
        
        # Add required headers
        response.headers.update({
            'Content-Type': 'audio/mpeg',
            'Content-Length': str(file_size),
            'Content-Disposition': f'attachment; filename="{filename.split("_", 1)[1]}"',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        return jsonify({'error': 'Error processing download request'}), 500

@app.route('/convert', methods=['POST'])
def convert():
    if request.method == 'OPTIONS':
        return '', 204
        
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

        # Return download URL with HTTPS scheme
        download_url = url_for('download_file', filename=output_filename, _external=True, _scheme='https')
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

# Log startup information
logger.info("Application startup configuration:")
logger.info(f"Upload folder: {UPLOAD_FOLDER}")
logger.info(f"Max content length: {MAX_CONTENT_LENGTH} bytes")
logger.info(f"Max download size: {MAX_DOWNLOAD_SIZE} bytes")
logger.info(f"Cleanup delay: {CLEANUP_DELAY} seconds")
logger.info("CORS headers enabled")
