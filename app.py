from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib, os, sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pyttsx3
import speech_recognition as sr
import os

if not os.path.exists("model.pkl"):
    train_model()

from openai import OpenAI
client = OpenAI(api_key="YOUR_API_KEY")

app = Flask(__name__)
app.secret_key = 'secret123'

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
def train_model():
    if not os.path.exists('model.pkl'):
        data = pd.read_csv('calories.csv')
        X = data[['Age','Height','Weight','Heart_Rate','Body_Temp','Duration']]
        y = data['Calories']

        model = RandomForestRegressor()
        model.fit(X, y)
        joblib.dump(model, 'model.pkl')

train_model()
model = joblib.load('model.pkl')

# ---------- TTS ----------
def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# ---------- VOICE INPUT ----------
def get_voice():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except:
        return "Error"

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

        return render_template('login.html', error="Invalid")

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

        # BMI
        bmi = inputs[2]/((inputs[1]/100)**2)
        if bmi<18.5: fitness="Underweight"
        elif bmi<25: fitness="Normal"
        elif bmi<30: fitness="Overweight"
        else: fitness="Obese"

        # Suggestion
        suggestion = "Great job!" if result>300 else "Increase activity"

        # Save history
        conn = sqlite3.connect('users.db', timeout=10)
        cur=conn.cursor()
        cur.execute("""INSERT INTO history (username,age,height,weight,heart_rate,body_temp,duration,calories)
        VALUES (?,?,?,?,?,?,?,?)""",(session['user'],*inputs,result))
        conn.commit()
        conn.close()

        speak(f"You burned {result} calories")

    conn = sqlite3.connect('users.db', timeout=10)
    cur=conn.cursor()
    cur.execute("SELECT * FROM history WHERE username=?", (session['user'],))
    history=cur.fetchall()
    conn.close()

    return render_template('dashboard.html', result=result, inputs=inputs,
                           suggestion=suggestion, bmi=bmi, fitness=fitness, history=history)


@app.route('/chat', methods=['POST'])
def chat():
    msg = request.form['msg']

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"You are a fitness trainer and diet expert."},
            {"role":"user","content":msg}
        ]
    )

    return response.choices[0].message.content

@app.route('/voice')
def voice():
    return get_voice()

@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/login')

if __name__ == "__main__":
    app.run()
