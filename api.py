from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from alesp import get_project_content
import json
import os

app = Flask(__name__)
CORS(app)
static_dir = 'static'
cache_dir = 'cache'

@app.route('/logo.png')
def serve_logo():
    return send_from_directory(static_dir, 'logo.png')

@app.route('/openapi.yaml')
def serve_yaml():
    return send_from_directory(static_dir, 'openapi.yaml')

@app.route('/.well-known/ai-plugin.json')
def serve_json():
    return send_from_directory(static_dir, '.well-known/ai-plugin.json')

@app.route('/get_project', methods=['GET'])
def get_project():
    # Retrieve query parameters
    project_type = request.args.get('type')
    project_number = request.args.get('number')
    project_year = request.args.get('year')

    # Validate query parameters
    if not project_type or not project_number or not project_year:
        return jsonify({'error': 'Missing required parameters: type, number, year'}), 400

    # Generate a unique cache filename based on the project type, number, and year
    cache_filename = f"{project_type}_{project_number}_{project_year}.json"
    cache_filepath = os.path.join(cache_dir, cache_filename)

    # Check if the cache file exists
    if os.path.exists(cache_filepath):
        # Read the content from the cache file
        with open(cache_filepath, 'r') as cache_file:
            response = json.load(cache_file)
    else:
        # Retrieve project content
        response = get_project_content(project_type, project_number, project_year)

        # Check if the project was found
        if response is None:
            return jsonify({'error': 'Project not found'}), 404

        # Save the content to the cache file
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_filepath, 'w') as cache_file:
            json.dump(response, cache_file)

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
