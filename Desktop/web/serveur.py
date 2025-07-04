from flask import Flask, request, send_from_directory, jsonify, redirect
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os, requests

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'

# Variables d'environnement pour OneDrive
CLIENT_ID = os.environ.get("ONEDRIVE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ONEDRIVE_CLIENT_SECRET")
TENANT_ID = os.environ.get("ONEDRIVE_TENANT_ID")
REDIRECT_URI = os.environ.get("ONEDRIVE_REDIRECT_URI")
SECRET_KEY = os.environ.get("SECRET_KEY")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

app = Flask(__name__, static_folder=STATIC_FOLDER)
app.secret_key = SECRET_KEY
CORS(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

access_token = None

def get_token(code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    r = requests.post(TOKEN_URL, data=data)
    return r.json()

def upload_to_onedrive(token, file_path, filename):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/octet-stream'
    }
    with open(file_path, 'rb') as f:
        url = f"{GRAPH_URL}/me/drive/special/approot:/MonUpload/{filename}:/content"
        r = requests.put(url, headers=headers, data=f)
        return r.status_code in (200, 201)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/callback')
def callback():
    global access_token
    code = request.args.get('code')
    token_data = get_token(code)
    access_token = token_data.get('access_token')
    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload():
    global access_token
    files = request.files.getlist('files')
    if not files:
        return 'Aucun fichier reçu', 400
    if not access_token:
        auth_url = (
            f"{AUTHORITY}/oauth2/v2.0/authorize?"
            f"client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
            f"&response_mode=query&scope=offline_access Files.ReadWrite.All"
        )
        return redirect(auth_url)

    saved = []
    for f in files:
        filename = secure_filename(f.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(path)
        if upload_to_onedrive(access_token, path, filename):
            saved.append(filename)
    return jsonify({'uploaded': saved}), 200

if __name__ == '__main__':
    print("Démarrage du serveur Flask sur http://localhost:5001")
    app.run(host='0.0.0.0', port=5001)
