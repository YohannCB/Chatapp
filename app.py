from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)
users = {}

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    content = db.Column(db.String(500))

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('set_username')
def set_username(username):
    global users
    username = username.strip()
    if username:
        users[request.sid] = username
        # Message système de bienvenue
        socketio.emit('message_system', f"👋 {username} a rejoint le chat")
        print(f"✅ {username} connecté.")

        # Envoie l’historique des messages
        messages = Message.query.order_by(Message.id.asc()).limit(50).all()
        for msg in messages:
            emit('message_object', {
                'id': msg.id,
                'username': msg.username,
                'content': msg.content
            })

        # Met à jour la liste des utilisateurs
        update_user_list()
    else:
        print("⚠️ Pseudo vide reçu.")

@socketio.on('message')
def handle_message(msg):
    username = users.get(request.sid, 'Anonyme')
    new_message = Message(username=username, content=msg)
    db.session.add(new_message)
    db.session.commit()

    socketio.emit('message_object', {
        'id': new_message.id,
        'username': username,
        'content': msg
    })

@socketio.on('delete_message')
def delete_message(message_id):
    message = Message.query.get(message_id)
    if message and users.get(request.sid) == message.username:
        db.session.delete(message)
        db.session.commit()
        socketio.emit('message_deleted', message_id)

@socketio.on('disconnect')
def handle_disconnect():
    global users
    username = users.pop(request.sid, 'Anonyme')
    print(f"❌ {username} s’est déconnecté.")
    socketio.emit('message_system', f"❌ {username} s’est déconnecté")
    update_user_list()

def update_user_list():
    user_list = list(users.values())
    socketio.emit('user_list', user_list)

if __name__ == '__main__':
    socketio.run(app, debug=True)
