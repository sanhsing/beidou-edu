from . import auth, api, pages

def register_blueprints(app):
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(pages.bp)
