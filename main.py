from app import app, init_app

init_app()

if __name__ == '__main__':
    # Only used for running locally. When running on production, it will
    # look for a variable named "app" in main.py and run that directly.
    app.run(host='127.0.0.1', port=8080, debug=True)
