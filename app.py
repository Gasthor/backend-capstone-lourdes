from flask import Flask, request, jsonify
from routes.files import files_bp

app = Flask(__name__)
app.register_blueprint(files_bp, url_prefix='/api/files')

@app.route('/', methods=['GET'])
def health():
    return "Server is Up and Running"

if __name__ == '__main__':
    app.run(debug=True, port=8000)
