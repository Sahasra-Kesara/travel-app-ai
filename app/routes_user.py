from flask import Blueprint, render_template, request
from models.rag_model import get_recommendations, destinations_with_embeddings

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    # Just show search page
    return render_template('home.html')

@user_bp.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return render_template('destination.html', results=[])

    # ✅ Use RAG knowledge base with embeddings
    results = get_recommendations(
        query,
        destinations=destinations_with_embeddings
    )

    return render_template('destination.html', results=results)