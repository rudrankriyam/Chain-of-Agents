from flask import Flask, request, jsonify, Response, stream_with_context
from chain_of_agents import ChainOfAgents
from chain_of_agents.utils import read_pdf, get_pdf_page_count
from dotenv import load_dotenv
import json
import os
import tempfile
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)
coa = ChainOfAgents(
    worker_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    manager_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    chunk_size=2000
)

logger = logging.getLogger(__name__)

@app.route('/process', methods=['POST'])
def process_text():
    data = request.get_json(silent=True) or {}
    input_text = data.get('text')
    query = data.get('query')

    if not input_text:
        return jsonify({'error': "Missing required field 'text' in JSON body"}), 400

    if not query:
        return jsonify({'error': "Missing required field 'query' in JSON body"}), 400

    try:
        result = coa.process(input_text, query)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process-stream', methods=['POST'])
def process_stream():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400

    pdf_file = request.files['pdf']
    query = request.form.get('query')

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Save the upload to a unique temporary file per request so concurrent
    # requests cannot clobber each other's files.
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(temp_fd)

    try:
        pdf_file.save(temp_path)

        # Extract text and page count from PDF
        input_text = read_pdf(temp_path)
        total_pages = get_pdf_page_count(temp_path)

        def generate():
            try:
                for message in coa.process_stream(input_text, query, total_pages=total_pages):
                    formatted_message = f"data: {json.dumps(message)}\n\n"
                    logger.info(f"Sending SSE message: {formatted_message}")  # Debug log
                    yield formatted_message
            except Exception as e:
                error_message = f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                logger.error(f"Error message: {error_message}")  # Debug log
                yield error_message

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Bind to localhost by default; set HOST to override (e.g. HOST=0.0.0.0).
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(host=host, port=8000)
