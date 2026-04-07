from flask import Flask, render_template, request, redirect, session, jsonify
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib, os, sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
<<<<<<< HEAD
import os

=======
from flask_cors import CORS
>>>>>>> 11811b6 (fixed render deployment issues)
from openai import OpenAI

# ---------- APP INIT ----------
app = Flask(__name__)
app.secret_key = 'secret123'
CORS(app)

# ---------- OPENAI ----------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY,
        username TEXT,
        age REAL,
        height REAL,
        weight REAL,
        heart_rate REAL,
        body_temp REAL,
        duration REAL,
        calories REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()

init_db()

# ---------- ML MODEL ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, 'model.pkl')

def train_model():
    if not os.path.exists(model_path):
        data = pd.read_csv(os.path.join(BASE_DIR, 'calories.csv'))
        X = data[['Age','Height','Weight','Heart_Rate','Body_Temp','Duration']]
        y = data['Calories']

        model = RandomForestRegressor()
        model.fit(X, y)
        joblib.dump(model, model_path)

train_model()
model = joblib.load(model_path)

# ---------- ROUTES ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/diet')
def diet():
    return render_template('diet.html')

@app.route('/trainer')
def trainer():
    return render_template('trainer.html')

@app.route('/assistant')
def assistant():
    return render_template('assistant.html')

@app.route('/history')
def history_page():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM history WHERE username=?", (session['user'],))
    data = cur.fetchall()
    conn.close()

    return render_template('history.html', history=data)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (u,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[2], p):
            session['user'] = u
            return redirect('/dashboard')

        return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        u = request.form['username']
        p = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users VALUES (NULL,?,?)",(u,p))
            conn.commit()
        except:
            return render_template('signup.html', error="User exists")
        conn.close()

        return redirect('/login')

    return render_template('signup.html')

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    result=None
    suggestion=""
    bmi=None
    fitness=""
    inputs=[0,0,0,0,0,0]

    if request.method == 'POST':
        inputs = [float(request.form[x]) for x in ['age','height','weight','heart_rate','body_temp','duration']]
        result = round(model.predict([inputs])[0],2)

        bmi = inputs[2]/((inputs[1]/100)**2)
        if bmi<18.5: fitness="Underweight"
        elif bmi<25: fitness="Normal"
        elif bmi<30: fitness="Overweight"
        else: fitness="Obese"

        suggestion = "Great job!" if result>300 else "Increase activity"

        conn = sqlite3.connect('users.db', timeout=10)
        cur=conn.cursor()
        cur.execute("""INSERT INTO history 
        (username,age,height,weight,heart_rate,body_temp,duration,calories)
        VALUES (?,?,?,?,?,?,?,?)""",(session['user'],*inputs,result))
        conn.commit()
        conn.close()

    conn = sqlite3.connect('users.db', timeout=10)
    cur=conn.cursor()
    cur.execute("SELECT * FROM history WHERE username=?", (session['user'],))
    history=cur.fetchall()
    conn.close()

    return render_template('dashboard.html', result=result, inputs=inputs,
                           suggestion=suggestion, bmi=bmi, fitness=fitness, history=history)

# ---------- API (IMPORTANT FOR MOBILE) ----------
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    inputs = [
        data['age'],
        data['height'],
        data['weight'],
        data['heart_rate'],
        data['body_temp'],
        data['duration']
    ]

    result = round(model.predict([inputs])[0],2)

    return jsonify({"calories": result})

# ---------- CHAT ----------
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg = data.get('msg')

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"You are a fitness trainer and diet expert."},
            {"role":"user","content":msg}
        ]
    )

    return jsonify({"reply": response.choices[0].message.content})

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/login')

<<<<<<< HEAD
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
=======
# ❌ REMOVE app.run()
>>>>>>> 11811b6 (fixed render deployment issues)
