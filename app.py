import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import certifi

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- UPLOAD FOLDER ---------------- #

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- MONGODB CONNECTION ---------------- #

MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["lost_found"]

users = db["users"]
items = db["items"]
messages = db["messages"]

# ---------------- HOME ---------------- #

@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return redirect('/login')

# ---------------- REGISTER ---------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        username = request.form['username']
        password = request.form['password']

        file = request.files.get('profile_pic')
        filename = ""

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        users.insert_one({
            "name": name,
            "username": username,
            "password": password,
            "profile_pic": filename
        })

        return redirect('/login')

    return render_template('register.html')

# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        user = users.find_one({
            "username": request.form['username'],
            "password": request.form['password']
        })

        if user:
            session['user'] = user['username']
            return redirect('/dashboard')

    return render_template('login.html')

# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')

# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    user_items = list(
        items.find(
            {"user": session['user']}
        ).sort("_id", -1)
    )

    return render_template(
        'dashboard.html',
        items=user_items,
        user=session['user']
    )

# ---------------- POST PAGE ---------------- #

@app.route('/post')
def post_page():

    if 'user' not in session:
        return redirect('/login')

    return render_template('post.html')

# ---------------- ADD ITEM ---------------- #

@app.route('/add', methods=['POST'])
def add():

    if 'user' not in session:
        return redirect('/login')

    file = request.files['image']
    filename = ""

    if file and file.filename != "":

        filename = secure_filename(file.filename)

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

    items.insert_one({
        "title": request.form['title'],
        "description": request.form['description'],
        "status": request.form['status'],
        "image": filename,
        "user": session['user'],
        "created_at": datetime.now()
    })

    return redirect('/dashboard')

# ---------------- SEARCH ---------------- #

@app.route('/search')
def search():

    if 'user' not in session:
        return redirect('/login')

    query = {}

    keyword = request.args.get('keyword')
    status = request.args.get('status')

    if keyword:
        query["title"] = {
            "$regex": keyword,
            "$options": "i"
        }

    if status:
        query["status"] = status

    results = list(
        items.find(query).sort("_id", -1)
    )

    return render_template(
        'search.html',
        items=results,
        user=session['user']
    )

# ---------------- DELETE ---------------- #

@app.route('/delete/<id>')
def delete(id):

    if 'user' not in session:
        return redirect('/login')

    items.delete_one({
        "_id": ObjectId(id)
    })

    return redirect('/dashboard')

# ---------------- CHAT ---------------- #

@app.route('/chat/<id>')
def chat(id):

    if 'user' not in session:
        return redirect('/login')

    item = items.find_one({
        "_id": ObjectId(id)
    })

    chat_msgs = list(
        messages.find({
            "item_id": id
        }).sort("_id", 1)
    )

    return render_template(
        'chat.html',
        item=item,
        messages=chat_msgs,
        user=session['user']
    )

# ---------------- SEND MESSAGE ---------------- #

@app.route('/send_message/<id>', methods=['POST'])
def send_message(id):

    if 'user' not in session:
        return redirect('/login')

    item = items.find_one({
        "_id": ObjectId(id)
    })

    messages.insert_one({
        "item_id": id,
        "sender": session['user'],
        "receiver": item['user'],
        "message": request.form['message'],
        "time": datetime.now()
    })

    return redirect('/chat/' + id)

# ---------------- RUN ---------------- #

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host='0.0.0.0',
        port=port
    )