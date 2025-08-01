from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
from flask_cors import  CORS
import datetime
from datetime import datetime , timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
import threading

from backend import ExpertTechnicalInterviewer
from shared_state import interview_state, save_to_conversation_history



  # when user sends a message

app = Flask(__name__)
CORS(app)



def initialize_interviewer():
    global interviewer
    try:
        interviewer = ExpertTechnicalInterviewer(accent="indian")
        return True
    except Exception as e:
        print(f"Failed to initialize interviewer: {e}")
        return False

@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    global interviewer, interview_state

    if not initialize_interviewer():
        return jsonify({'error': 'Failed to initialize interviewer'}), 500

    # Reset interview state
    interview_state.update({
        'active': True,
        'stage': 'greeting',
        'conversation_history': [],
        'skill_questions_asked': 0,
        'coding_questions_asked': 0,
        'personal_info_collected': False,
        'tech_background_collected': False,
        'skills_collected': '',
        'current_domain': None,
        'current_question': None,
        'interview_links': {}
    })

   
    try:
        import threading
        threading.Thread(target=interviewer.start_interview, daemon=True).start()
    except Exception as e:
        print(f"🔥 Interview launch error: {e}")
        return jsonify({'error': 'Failed to launch interview thread'}), 500

    return jsonify({
        'status': 'started',
        'interview_active': True,
        'stage': 'greeting'
    })



# Replace your transcript endpoint in flask_server.py with this:


# Also, make sure your conversation history is being saved properly.
# Update your process_speech endpoint to ensure timestamps are saved:

# In your process_speech function, replace the conversation history saving with:
def save_to_conversation_history(role, content):
    """Helper function to save messages with proper timestamps"""
    interview_state["conversation_history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })
from datetime import datetime

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    history = interview_state.get("conversation_history", [])

    transcript = []
    for entry in history:
        if entry.get("role") in ["user", "assistant"]:
            transcript.append({
                "speaker": "User" if entry["role"] == "user" else "AI",
                "message": entry["content"],
                "timestamp": int(datetime.fromisoformat(entry["timestamp"]).timestamp() * 1000)
            })

    return jsonify({ "transcript": transcript })


@app.route('/api/problems/random', methods=['GET'])
def get_random_problem():
    problems = [
        "Write a function to reverse a string.",
        "Find the factorial of a number using recursion.",
        "Implement binary search on a sorted list."
    ]
    return jsonify({
        "question": random.choice(problems)
    })

@app.route('/api/process-speech', methods=['POST'])
def process_speech():
    global interviewer, interview_state

    data = request.json
    user_input = data.get('text', '').strip()

    if not user_input:
        return jsonify({'error': 'No input'}), 400

    # ✅ Save user message ONCE, only if not a command


    print("📥 process_speech called with:", user_input)

    response = ""

    # ✅ Handle coding start
    if user_input.lower() == "ready_for_coding":
        interview_state['stage'] = 'coding_challenges'
        interview_state['coding_questions_asked'] = 1
        coding_question = interviewer._generate_coding_question(
            interview_state.get("current_domain", "python")
        )
        interview_state['current_question'] = coding_question
        response = "✅ Great! Now let's move to the coding challenge."

        print("🤖 AI (coding intro):", response)
        try:
            interviewer.speak(response)
        except Exception as e:
            print("TTS error:", e)

        save_to_conversation_history("assistant", response)

        return jsonify({
            "response": response,
            "question": coding_question,
            "stage": "coding_challenges"
        })

    # ✅ Handle coding done
    if user_input.lower() == "done_coding":
        response = "Thanks for your submission. Let's move on to any questions you might have."
        interview_state['stage'] = 'doubt_clearing'

        print("🤖 AI (done coding):", response)
        try:
            interviewer.speak(response)
        except Exception as e:
            print("TTS error:", e)

        save_to_conversation_history("assistant", response)

        return jsonify({
            "response": response,
            "stage": "doubt_clearing"
        })

    # ✅ Main Interview Logic
    try:
        if interview_state['stage'] == 'greeting':
            response = "Thanks for the intro! Tell me more about your technical background."
            interview_state['stage'] = 'tech_background'

        elif interview_state['stage'] == 'tech_background':
            interview_state['stage'] = 'skill_questions'
            followup = interviewer._add_domain_specific_followup(
                interview_state.get("current_domain", "general")
            )
            response = f"Awesome! Let's begin your technical round.\n\n{followup}"

        elif interview_state['stage'] == 'skill_questions':
            followup = interviewer._add_domain_specific_followup(
                interview_state.get("current_domain", "general")
            )
            response = f"Great. Here's your next question:\n\n{followup}"

        else:
            response = "Let's continue."

        print("🤖 AI says:", response)
        try:
            interviewer.speak(response)
        except Exception as e:
            print("TTS error:", e)

        save_to_conversation_history("assistant", response)

        return jsonify({
            "response": response,
            "stage": interview_state['stage']
        })

    except Exception as e:
        print("❌ Error during process_speech:", e)
        return jsonify({"error": str(e)}), 500


def save_to_conversation_history(role, content):
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    interview_state["conversation_history"].append(entry)
    print(f"💾 SAVED TO HISTORY: [{role.upper()}] {content}")
    print(f"🧠 Last 2 messages:")
    for msg in interview_state["conversation_history"][-2:]:
        print(f"  - {msg['role']}: {msg['content']}")


@app.route('/api/log-warning', methods=['POST'])
def log_warning():
    data = request.json
    warning_type = data.get('type')
    timestamp = data.get('timestamp')
    message = data.get('message')
    
    # Add to interview state
    if 'warnings' not in interview_state:
        interview_state['warnings'] = []
    
    # Add the warning
    interview_state['warnings'].append({
        'type': warning_type,
        'timestamp': timestamp,
        'message': message,
        'stage': interview_state.get('stage', 'unknown')
    })
    
    violation_count = len(interview_state['warnings'])
    print(f"🚨 WARNING LOGGED: {warning_type} - {message} (Violation #{violation_count})")
    
    # Optional: Add escalating responses
    if violation_count >= 3:
        print("🔴 CRITICAL: Multiple violations detected!")
        # You could end the interview here or send additional warnings
    
    return jsonify({
        'status': 'logged',
        'violation_count': violation_count,
        'total_violations': violation_count
    })

@app.route('/api/get-warnings', methods=['GET'])
def get_warnings():
    warnings = interview_state.get('warnings', [])
    return jsonify({'warnings': warnings, 'count': len(warnings)})

# Fix 3: Add debug endpoint to check conversation history
@app.route('/api/debug-transcript', methods=['GET'])
def debug_transcript():
    """Debug endpoint to check raw conversation history"""
    return jsonify({
        "raw_history": interview_state.get("conversation_history", []),
        "history_length": len(interview_state.get("conversation_history", [])),
        "last_entry": interview_state.get("conversation_history", [])[-1] if interview_state.get("conversation_history") else None
    })

@app.route('/api/generate-interview-link', methods=['POST'])
def generate_interview_link():
    data = request.json
    recipient_email = data.get('email')
    
    if not recipient_email:
        return jsonify({'error': 'Recipient email is required'}), 400
    
    token = secrets.token_urlsafe(32)
    
    expiration_date = datetime.datetime.now() + timedelta(days=7)
    
    interview_state['interview_links'][token] = {
        'email': recipient_email,
        'expires_at': expiration_date.isoformat(),
        'used': False,
        'created_at': datetime.datetime.now().isoformat()
    }
    
    interview_link = f"https://yourdomain.com/interview/{token}"
    
    try:
        send_interview_link_email(recipient_email, interview_link, expiration_date)
        return jsonify({
            'status': 'success',
            'message': 'Interview link sent successfully',
            'expires_at': expiration_date.isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': f'Failed to send email: {str(e)}',
            'interview_link': interview_link 
        }), 500

def send_interview_link_email(recipient, link, expires_at):
    """Helper function to send interview link email"""
    SMTP_SERVER = "your_smtp_server.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "your_email@example.com"
    SMTP_PASSWORD = "your_email_password"
    SENDER_EMAIL = "no-reply@yourdomain.com"
    
    subject = "Your Technical Interview Link"
    body = f"""
    <p>Hello,</p>
    <p>Here is your interview link: <a href="{link}">{link}</a></p>
    <p>This link will expire on {expires_at.strftime('%Y-%m-%d %H:%M:%S')}.</p>
    <p>Please complete your interview before this date.</p>
    <p>Best regards,<br>Interview Team</p>
    """
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

@app.route('/api/validate-interview-link/<token>', methods=['GET'])
def validate_interview_link(token):
    """Endpoint to validate an interview link"""
    if token not in interview_state['interview_links']:
        return jsonify({'valid': False, 'reason': 'Invalid token'}), 404
    
    link_data = interview_state['interview_links'][token]
    expiration_date = datetime.datetime.fromisoformat(link_data['expires_at'])
    
    if datetime.datetime.now() > expiration_date:
        return jsonify({'valid': False, 'reason': 'Link expired'}), 410
    
    if link_data['used']:
        return jsonify({'valid': False, 'reason': 'Link already used'}), 403
    
    return jsonify({
        'valid': True,
        'expires_at': link_data['expires_at'],
        'email': link_data['email']
    })

@app.route('/api/mark-link-used/<token>', methods=['POST'])
def mark_link_used(token):
    """Mark an interview link as used"""
    if token not in interview_state['interview_links']:
        return jsonify({'error': 'Invalid token'}), 404
    
    interview_state['interview_links'][token]['used'] = True
    return jsonify({'status': 'success'})
@app.route('/api/interview-status', methods=['GET'])
def get_interview_status():
    """Get current interview status and progress"""
    return jsonify({
        'active': interview_state['active'],
        'stage': interview_state['stage'],
        'skill_questions_asked': interview_state['skill_questions_asked'],
        'coding_questions_asked': interview_state['coding_questions_asked'],
        'total_skill_questions': 3,
        'total_coding_questions': 2,
        'current_domain': interview_state.get('current_domain', 'unknown'),
        'current_question': interview_state.get('current_question')
    })

@app.route('/api/end-interview', methods=['POST'])
def end_interview():
    """Manually end the interview"""
    global interview_state
    
    interview_state['active'] = False
    interview_state['stage'] = 'concluded'
    
    return jsonify({
        'status': 'ended',
        'message': 'Interview has been ended manually.'
    })

@app.route('/api/current-coding-question', methods=['GET'])
def get_current_coding_question():
    if interview_state['stage'] != 'coding_challenges':
        return jsonify({
            'question': None, 
            'error': f'Not in coding stage. Current stage: {interview_state["stage"]}'
        }), 400
    
    current_question = interview_state.get('current_question')
    if not current_question:
        # Generate a fallback question if none exists
        try:
            current_question = interviewer._generate_coding_question(
                interview_state.get("current_domain", "python")
            )
            interview_state['current_question'] = current_question
        except:
            current_question = "Write a function that takes a string and returns it reversed. For example, 'hello' should return 'olleh'."
            interview_state['current_question'] = current_question
    
    return jsonify({
        'question': current_question,
        'stage': interview_state['stage'],
        'coding_questions_asked': interview_state['coding_questions_asked']
    })

@app.route('/api/submit-code', methods=['POST'])
def submit_code():
    data = request.get_json()
    user_code = data.get("code", "")
    language = data.get("language", "python")

    # Save code and language in global state
    interview_state['latest_code'] = user_code
    interview_state['language'] = language

    try:
        # 🔧 Run code using backend method (safe execution)
        output = interviewer._execute_code(language, user_code)

        # 🤖 Generate follow-up question using Gemini
        followup = interviewer._coding_followup(user_code, language)

        success = True
    except Exception as e:
        output = ""
        followup = f"❌ Error while running code: {str(e)}"
        success = False

    return jsonify({
        "success": success,
        "output": output,
        "followup_question": followup
    })


@app.route("/api/generate-coding-question", methods=["POST"])
def api_generate_coding_question():
    data = request.get_json()
    domain = data.get("domain", "python")
    session_id = data.get("session_id", "default")

    try:
        question = interviewer._generate_coding_question(domain)
        return jsonify({"question": question})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Debug endpoint to check interview state
@app.route('/api/debug-state', methods=['GET'])
def debug_state():
    """Debug endpoint to inspect current interview state"""
    return jsonify(interview_state)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)