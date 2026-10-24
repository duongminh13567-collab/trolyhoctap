from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import re
from collections import Counter
from functools import wraps

app = Flask(__name__)
app.secret_key = 'studymate-ai-secret-key-2024'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studymate.db')

# ==================== DATABASE SETUP ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, title TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, title TEXT, done INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, question TEXT, answer TEXT
            );
        ''')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def summarize_text(text, num_sentences=3):
    # Tách câu đơn giản
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= num_sentences:
        return text
    
    # Đếm tần suất từ (loại bỏ từ dừng cơ bản)
    words = re.findall(r'\w+', text.lower())
    stop_words = {'và', 'là', 'của', 'có', 'trong', 'được', 'cho', 'những', 'các', 'một', 'để', 'với', 'ra', 'về'}
    words = [w for w in words if w not in stop_words]
    word_freq = Counter(words)
    
    # Chấm điểm câu dựa trên tần suất từ
    sentence_scores = {}
    for sent in sentences:
        for word in re.findall(r'\w+', sent.lower()):
            if word in word_freq:
                sentence_scores[sent] = sentence_scores.get(sent, 0) + word_freq[word]
                
    # Lấy top câu có điểm cao nhất
    sorted_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
    summary = " ".join([s[0] for s in sorted_sentences[:num_sentences]])
    return summary

def get_ai_response(message):
    msg = message.lower().strip()
    
    # Từ điển kiến thức cơ bản về AI
    knowledge_base = {
        "trí tuệ nhân tạo": "Trí tuệ nhân tạo (AI) là lĩnh vực khoa học máy tính tập trung vào việc tạo ra các hệ thống có thể thực hiện các nhiệm vụ đòi hỏi trí thông minh của con người như học tập, suy luận, và tự sửa lỗi.",
        "ai là gì": "Trí tuệ nhân tạo (AI) là lĩnh vực khoa học máy tính tập trung vào việc tạo ra các hệ thống có thể thực hiện các nhiệm vụ đòi hỏi trí thông minh của con người như học tập, suy luận, và tự sửa lỗi.",
        "machine learning": "Học máy (Machine Learning) là một nhánh của AI, cho phép máy tính học từ dữ liệu mà không cần lập trình cụ thể. Ví dụ: hệ thống gợi ý phim, lọc spam email.",
        "học máy": "Học máy (Machine Learning) là một nhánh của AI, cho phép máy tính học từ dữ liệu mà không cần lập trình cụ thể. Ví dụ: hệ thống gợi ý phim, lọc spam email.",
        "deep learning": "Học sâu (Deep Learning) là một kỹ thuật của Học máy sử dụng các mạng nơ-ron nhân tạo (Neural Networks) nhiều lớp để xử lý dữ liệu phức tạp như hình ảnh, âm thanh và văn bản.",
        "học sâu": "Học sâu (Deep Learning) là một kỹ thuật của Học máy sử dụng các mạng nơ-ron nhân tạo (Neural Networks) nhiều lớp để xử lý dữ liệu phức tạp như hình ảnh, âm thanh và văn bản.",
        "neural network": "Mạng nơ-ron nhân tạo (Neural Network) là mô hình tính toán lấy cảm hứng từ cấu trúc của não bộ con người, gồm nhiều nút (neuron) liên kết với nhau để truyền và xử lý thông tin.",
        "mạng nơ-ron": "Mạng nơ-ron nhân tạo (Neural Network) là mô hình tính toán lấy cảm hứng từ cấu trúc của não bộ con người, gồm nhiều nút (neuron) liên kết với nhau để truyền và xử lý thông tin.",
        "nlp": "Xử lý ngôn ngữ tự nhiên (NLP) giúp máy tính hiểu, phân tích và tạo ra ngôn ngữ của con người. Ví dụ: Google Dịch, ChatGPT.",
        "xử lý ngôn ngữ tự nhiên": "Xử lý ngôn ngữ tự nhiên (NLP) giúp máy tính hiểu, phân tích và tạo ra ngôn ngữ của con người. Ví dụ: Google Dịch, ChatGPT.",
        "computer vision": "Thị giác máy tính (Computer Vision) giúp máy tính 'nhìn' và hiểu hình ảnh/video. Ví dụ: Nhận diện khuôn mặt, xe tự lái.",
        "thị giác máy tính": "Thị giác máy tính (Computer Vision) giúp máy tính 'nhìn' và hiểu hình ảnh/video. Ví dụ: Nhận diện khuôn mặt, xe tự lái.",
        "python": "Python là ngôn ngữ lập trình phổ biến nhất để học AI nhờ cú pháp đơn giản và hệ sinh thái thư viện mạnh mẽ như TensorFlow, PyTorch, Scikit-learn."
    }

    # Xử lý từ khóa chào hỏi
    if any(word in msg for word in ["chào", "hello", "hi", "xin chào"]):
        return "Xin chào! Mình là Trợ lý AI. Bạn muốn tìm hiểu khái niệm nào về Trí tuệ nhân tạo hôm nay? (Ví dụ: Học máy, Deep Learning, NLP...)"
    
    if "cảm ơn" in msg or "thank" in msg:
        return "Không có gì! Chúc bạn học tập môn Trí tuệ nhân tạo thật tốt. 😊"
    
    # Tìm kiếm trong từ điển kiến thức
    for key, answer in knowledge_base.items():
        if key in msg:
            return answer
            
    # Câu trả lời mặc định nếu không tìm thấy
    return "Xin lỗi, câu hỏi này nằm ngoài cơ sở dữ liệu của mình. Bạn hãy thử hỏi về: 'AI là gì', 'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision' hoặc 'Python' nhé."


init_db()

# ==================== ROUTES ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            flash('Đăng ký thành công, hãy đăng nhập!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Tên đăng nhập đã tồn tại!', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Sai tài khoản hoặc mật khẩu!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== DASHBOARD & FEATURES ====================
@app.route('/dashboard')
@login_required
def dashboard():
    with get_db() as conn:
        notes_count = conn.execute('SELECT COUNT(*) FROM notes WHERE user_id=?', (session['user_id'],)).fetchone()[0]
        tasks_count = conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=0', (session['user_id'],)).fetchone()[0]
        cards_count = conn.execute('SELECT COUNT(*) FROM flashcards WHERE user_id=?', (session['user_id'],)).fetchone()[0]
    return render_template('dashboard.html', stats={'notes': notes_count, 'tasks': tasks_count, 'cards': cards_count})

@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        with get_db() as conn:
            conn.execute('INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)', (session['user_id'], title, content))
        return redirect(url_for('notes'))
    with get_db() as conn:
        all_notes = conn.execute('SELECT * FROM notes WHERE user_id=? ORDER BY id DESC', (session['user_id'],)).fetchall()
    return render_template('notes.html', notes=all_notes)

@app.route('/delete_note/<int:id>')
@login_required
def delete_note(id):
    with get_db() as conn:
        conn.execute('DELETE FROM notes WHERE id=? AND user_id=?', (id, session['user_id']))
    return redirect(url_for('notes'))

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        title = request.form['title']
        with get_db() as conn:
            conn.execute('INSERT INTO tasks (user_id, title) VALUES (?, ?)', (session['user_id'], title))
        return redirect(url_for('tasks'))
    with get_db() as conn:
        all_tasks = conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY done, id DESC', (session['user_id'],)).fetchall()
    return render_template('tasks.html', tasks=all_tasks)

@app.route('/toggle_task/<int:id>')
@login_required
def toggle_task(id):
    with get_db() as conn:
        conn.execute('UPDATE tasks SET done = 1 - done WHERE id=? AND user_id=?', (id, session['user_id']))
    return redirect(url_for('tasks'))

@app.route('/flashcards', methods=['GET', 'POST'])
@login_required
def flashcards():
    if request.method == 'POST':
        q = request.form['question']
        a = request.form['answer']
        with get_db() as conn:
            conn.execute('INSERT INTO flashcards (user_id, question, answer) VALUES (?, ?, ?)', (session['user_id'], q, a))
        return redirect(url_for('flashcards'))
    with get_db() as conn:
        cards = conn.execute('SELECT * FROM flashcards WHERE user_id=?', (session['user_id'],)).fetchall()
    return render_template('flashcards.html', cards=cards)

@app.route('/summarizer', methods=['GET', 'POST'])
@login_required
def summarizer():
    summary = None
    original_text = ""
    if request.method == 'POST':
        original_text = request.form['text']
        if len(original_text) > 50:
            summary = summarize_text(original_text, num_sentences=3)
        else:
            summary = "Văn bản quá ngắn để tóm tắt (cần > 50 ký tự)."
    return render_template('summarizer.html', summary=summary, original=original_text)

# ==================== CHAT API ====================

@app.route('/chat')
@login_required
def chat(): 
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    return jsonify({'reply': get_bot_response(request.get_json().get('message', ''))})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(host='0.0.0.0', port=port, debug=False)

