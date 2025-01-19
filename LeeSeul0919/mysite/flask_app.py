import random
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file
import mysql.connector
from gtts import gTTS
import os

app = Flask(__name__)
app.secret_key = '0000'

def get_db_connection():
    conn = mysql.connector.connect(
        host='LeeSeul0919.mysql.pythonanywhere-services.com',
        user='LeeSeul0919',
        password='Dltmf1356@',  # 실제 비밀번호로 변경
        database='LeeSeul0919$default'
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_id = request.form['id']
        password = request.form['pw']
        nickname = request.form['nickname']

        conn = get_db_connection()
        cursor = conn.cursor()

        # 이미 존재하는 아이디인지 확인
        cursor.execute("SELECT * FROM users WHERE ID = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            return "이미 존재하는 아이디입니다. 다른 아이디를 선택하세요."

        # users 테이블에 새 사용자 추가
        cursor.execute("INSERT INTO users (ID, PW, Nickname) VALUES (%s, %s, %s)",
                       (user_id, password, nickname))
        conn.commit()
        cursor.close()
        conn.close()

        return render_template('index.html')  # 회원가입 후 로그인 페이지로 이동

    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['id']
    password = request.form['password']

    # MySQL 연결 및 로그인 처리
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ID, PW FROM users WHERE ID = %s", (user_id,))
    user = cursor.fetchone()

    if user and user[1] == password:
        session['user_id'] = user_id  # 로그인한 유저의 ID를 세션에 저장
        return redirect(url_for('login_index'))  # 로그인 성공 시 login_index.html로 리디렉션
    else:
        flash('Invalid ID or password')  # 로그인 실패 시 에러 메시지 표시
        return redirect(url_for('index'))

@app.route('/login_index')
def login_index():
    if 'user_id' in session:
        return render_template('login_index.html', user_id=session['user_id'])  # 세션에서 user_id 전달
    else:
        return redirect(url_for('index'))  # 로그인하지 않았으면 메인 페이지로 리디렉션

@app.route('/logout')
def logout():
    session.clear()  # 로그아웃 시 세션 비우기
    return redirect(url_for('index'))

@app.route('/scriptlist')
def select_script_list():
    user_id = session.get('user_id')  # 로그인한 사용자의 ID 가져오기
    if not user_id:
        return redirect(url_for('login'))  # 로그인 페이지로 리다이렉트

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. 스크립트 데이터 가져오기
    cursor.execute('SELECT CG_id, QST_id, ANS_script, ANS_memo FROM script WHERE ID = %s', (user_id,))
    scripts = cursor.fetchall()

    script_details = []

    for script in scripts:
        cg_id = script['CG_id']
        qst_id = script['QST_id']
        ans_script = script['ANS_script']
        ans_memo = script['ANS_memo']

        # 2. 카테고리 데이터 가져오기
        cursor.execute('SELECT CG_name FROM category WHERE CG_id = %s', (cg_id,))
        category = cursor.fetchone()
        cg_name = category['CG_name']

        # 3. 질문 데이터 가져오기
        cursor.execute('SELECT QST_tag, QST_type, QST_content FROM question WHERE CG_id = %s AND QST_id = %s', (cg_id, qst_id))
        questions = cursor.fetchall()

        # 결과를 리스트에 추가
        script_details.append({
            'CG_id': cg_id,
            'CG_name': cg_name,
            'QST_id': qst_id,
            'ANS_script': ans_script,
            'ANS_memo': ans_memo,
            'questions': questions
        })

    cursor.close()
    conn.close()

    cg_list = []
    grouped_data = []

    for script in script_details:
        if script['CG_id'] not in cg_list:
            cg_list.append(script['CG_id'])
            grouped_data.append({'CG_name': script['CG_name'], 'questions': [script]})
        else:
            idx = cg_list.index(script['CG_id'])
            grouped_data[idx]['questions'].append(script)

    return render_template('script_list.html', cg_list=cg_list, grouped_data=grouped_data, enumerate=enumerate)

@app.route('/register')
def script_registration():
    return render_template('register.html')

@app.route('/memorization')
def memorization_page():
    user_id = session.get('user_id')  # 세션에서 사용자 ID 가져오기
    if not user_id:
        return redirect(url_for('index'))
    return render_template('memorization.html', user_id=user_id)

@app.route('/categories')
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM category')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(categories)

@app.route('/questions')
def get_questions():
    CG_id = request.args.get('CG_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT DISTINCT QST_id, QST_tag FROM question WHERE CG_id = %s', (CG_id,))
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(questions)

@app.route('/register', methods=['POST'])
def register_script():
    CG_id = request.form['CG_id']
    QST_id = request.form['QST_id']
    ANS_script = request.form['ANS_script']
    ANS_memo = request.form['ANS_memo']

    # 유효한 사용자 ID로 설정 (테스트용)
    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM script WHERE ID = %s and CG_id = %s and QST_id = %s', (user_id, CG_id, QST_id,))
        res = cursor.fetchall()
        if res:
            cursor.execute(
                'UPDATE script SET ANS_script = %s, ANS_memo = %s WHERE ID = %s AND CG_id = %s AND QST_id = %s',
                (ANS_script, ANS_memo, user_id, CG_id, QST_id)
            )
        else:
            cursor.execute(
                'INSERT INTO script (ID, CG_id, QST_id, ANS_script, ANS_memo) VALUES (%s, %s, %s, %s, %s)',
                (user_id, CG_id, QST_id, ANS_script, ANS_memo)  # 유효한 사용자 ID 사용
            )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('script_registration'))  # 등록 화면으로 리다이렉트
    except Exception as e:
        return f'Error occurred: {e}', 500

@app.route('/question-content', methods=['GET'])
def get_question_content():
    qst_id = request.args.get('QST_id')
    cg_id = request.args.get('CG_id')

    if qst_id and cg_id:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT QST_type, QST_content FROM question WHERE QST_id = %s AND CG_id = %s', (qst_id, cg_id))
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(results)
    return jsonify([]), 404

@app.route('/get-script-data', methods=['GET'])
def get_script_data():
    CG_id = request.args.get('CG_id')
    QST_id = request.args.get('QST_id')
    session_id = session.get('user_id')  # 세션에서 사용자 ID 가져오기

    if session_id and CG_id and QST_id:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = '''
        SELECT ANS_script, ANS_memo
        FROM script
        WHERE ID = %s AND CG_id = %s AND QST_id = %s
        '''
        cursor.execute(query, (session_id, CG_id, QST_id))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return jsonify(result)
        else:
            return jsonify({'ANS_script': '', 'ANS_memo': ''})
    else:
        return jsonify({'error': 'Invalid parameters'})

@app.route('/get_scripts', methods=['GET'])
def get_scripts():
    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # script 테이블에서 현재 사용자의 데이터를 가져옴
        cursor.execute('SELECT CG_id, QST_id, ANS_script, ANS_memo FROM script WHERE ID = %s', (user_id,))
        scripts = cursor.fetchall()  # 모든 스크립트를 가져옴

        results = []
        for script in scripts:
            cur_CG_id = script['CG_id']
            cur_QST_id = script['QST_id']

            # 여러 결과를 가져오기 위해 fetchall 사용
            cursor.execute('SELECT QST_content, QST_tag, QST_type FROM question WHERE CG_id = %s and QST_id = %s', (cur_CG_id, cur_QST_id,))
            cur_questions = cursor.fetchall()

            if cur_questions:  # 결과가 존재하는 경우
                if len(cur_questions) == 1:  # 결과가 하나일 때
                    results.append({
                        'QST_tag': cur_questions[0]['QST_tag'],
                        'QST_content': cur_questions[0]['QST_content'],
                        'ANS_script': script['ANS_script'],
                        'ANS_memo': script['ANS_memo'],
                    })
                else:  # 여러 결과 중 랜덤 선택
                    random_question = random.choice(cur_questions)
                    #question_lst.append(random_question)
                    results.append({
                        'QST_tag': random_question['QST_tag'],
                        'QST_content': random_question['QST_content'],
                        'ANS_script': script['ANS_script'],
                        'ANS_memo': script['ANS_memo'],
                    })

        cursor.close()
        conn.close()

        # 데이터를 클라이언트로 JSON 형태로 반환
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def text_to_speech(text, filename):
    tts = gTTS(text=text, lang='en')
    tts.save(filename)

@app.route('/speak', methods=['POST'])
def speak_text():
    data = request.json
    text = data.get('text')
    if text:
        # Flask 애플리케이션 실행 디렉토리에서 파일 저장
        filename = os.path.join(os.getcwd(), 'voice.mp3')  # 현재 작업 디렉토리로 설정
        text_to_speech(text, filename)

        if os.path.exists(filename):
            return send_file(filename, mimetype='audio/mp3', as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 500
    return jsonify({'error': 'No text provided'}), 400

if __name__ == '__main__':
    app.run(debug=True)
