from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from alesp import get_project_content, construct_search_url, extract_search_results, fetch_and_clean_deputados_data, get_deputado_by_name
import json
import os

app = Flask(__name__)
CORS(app)
static_dir = 'static'

#Set ups cache
cache_dir = 'cache'
os.makedirs(cache_dir, exist_ok=True)
deputados_filepath = os.path.join(cache_dir, "deputados.json")
if os.path.exists(deputados_filepath):
    with open(deputados_filepath, "r") as deputados_file:
        deputados = json.load(deputados_file)
else:
    deputados = fetch_and_clean_deputados_data()
    with open(deputados_filepath, "w") as deputados_file:
        json.dump(deputados, deputados_file)

#Serves static
@app.route('/logo.png')
def serve_logo():
    return send_from_directory(static_dir, 'logo.png')

@app.route('/openapi.yaml')
def serve_yaml():
    return send_from_directory(static_dir, 'openapi.yaml')

@app.route('/.well-known/ai-plugin.json')
def serve_json():
    return send_from_directory(static_dir, '.well-known/ai-plugin.json')

#API Endpoints
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
        with open(cache_filepath, 'w') as cache_file:
            json.dump(response, cache_file)

    return jsonify(response)

@app.route('/search')
def search():
    # Extract query parameters from the request
    author = request.args.get('author')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tipo = request.args.get('type')
    
    if author:
        deputado = get_deputado_by_name(deputados, author)
        author_id = deputado.get('IdSPL',None)
    else:
        author_id = None
        
    # Construct the search URL based on the query parameters
    search_url = construct_search_url(tipo=tipo,author_id=author_id, start_date=start_date, end_date=end_date)
    print(search_url)
    # Extract the search results from the URL
    search_results = extract_search_results(search_url)

    # Return the search results as JSON
    return jsonify(search_results)


@app.route('/get_deputado')
def get_deputado():
    # Extract the deputado name from the request
    deputado_name = request.args.get('name')

    # Validate the query parameter
    if not deputado_name:
        return jsonify({'error': 'Missing required parameter: name'}), 400

    # Get the deputado ID based on the name
    deputado = get_deputado_by_name(deputados, deputado_name)
    # Check if the deputado was found
    if deputado == {}:
        return jsonify({'error': 'Deputado not found'}), 404

    # Construct the search URL to get the projects (PLs) of the deputado
    search_url = construct_search_url(author_id=deputado.get('IdSPL',None), tipo='PL')
    print(search_url)

    # Extract the search results (projects) from the URL
    search_results = extract_search_results(search_url)

    # Combine the metadata and projects into a single JSON object
    response = {
        "metadata": deputado,
        "projects": search_results
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)
