from flask import Flask, redirect

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'

    # Register Blueprints
    from .routes_user import user_bp
    from .routes_admin import admin_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Redirect root URL to user portal
    @app.route('/')
    def index():
        return redirect('/user/')

    return app
