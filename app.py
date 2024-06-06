import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from routes.files import files_bp
from routes.vendimia import vendimia_bp

load_dotenv()

origins = os.environ.get("ACCESS_CONTROL_ALLOW_ORIGIN", "").split(",")
print("CORS origins:", origins)

app = Flask(__name__)

# Configurar CORS para manejar orígenes explícitamente
CORS(app, origins=origins)
app.register_blueprint(files_bp, url_prefix='/api/files')
app.register_blueprint(vendimia_bp, url_prefix='/api/vendimia')


@app.route('/', methods=['GET'])
def health():
    return "Server is Up and Running"


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)