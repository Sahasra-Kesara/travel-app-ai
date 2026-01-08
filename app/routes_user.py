from flask import Blueprint, render_template, request, jsonify
import json
from models.rag_model import get_recommendations

user_bp = Blueprint('user', __name__)

# Load knowledge base
with open('knowledge_base/destinations.json') as f:
    destinations = json.load(f)['destinations']

@user_bp.route('/')
def home():
    return render_template('home.html', categories=destinations)

@user_bp.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    
    # Get recommendations using RAG model
    results = get_recommendations(query, destinations)
    
    return render_template('destination.html', results=results)