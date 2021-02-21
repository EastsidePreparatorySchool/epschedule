from app import app, init_app
from flask import abort, request, redirect, session

init_app()

# Only used for running locally. When running on production, it will
# look for a variable named "app" in main.py and run that directly.
if __name__ == '__main__':
    # Allows impersonation of other users, for debugging purposes.
    # We specifically only enable this when running locally, since we only
    # want developers to have this sort of access. Even so, respect the
    # privacy of others when using this mechanism.
    @app.route('/login')
    def handle_login():
        if 'u' not in request.args:
            return abort(400)

        session['username'] = request.args['u']
        return redirect('/')

    app.run(host='127.0.0.1', port=8080, debug=True)
