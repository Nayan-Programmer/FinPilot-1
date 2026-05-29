from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import ChatSession, ChatMessage
from app.services.ai_service import get_ai_response
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def index():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).all()
    return render_template('chat/index.html', sessions=sessions)

@chat_bp.route('/api/chat/sessions', methods=['GET'])
@login_required
def list_sessions():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).all()
    return jsonify([{'id': s.id, 'title': s.title, 'updated_at': s.updated_at.strftime('%b %d, %Y')} for s in sessions])

@chat_bp.route('/api/chat/sessions', methods=['POST'])
@login_required
def create_session():
    session = ChatSession(user_id=current_user.id, title='New Chat')
    db.session.add(session)
    db.session.flush()
    welcome = ChatMessage(session_id=session.id, role='assistant',
                          content="Hello! I'm your AI Finance Copilot. How can I help you today?")
    db.session.add(welcome)
    db.session.commit()
    return jsonify({'id': session.id, 'title': session.title})

@chat_bp.route('/api/chat/sessions/<int:session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    sess = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    messages = ChatMessage.query.filter_by(session_id=sess.id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([m.to_dict() for m in messages])

@chat_bp.route('/api/chat/sessions/<int:session_id>/messages', methods=['POST'])
@login_required
def send_message(session_id):
    sess = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    data = request.json
    user_content = data.get('message', '').strip()
    if not user_content:
        return jsonify({'error': 'Empty message'}), 400

    user_msg = ChatMessage(session_id=sess.id, role='user', content=user_content)
    db.session.add(user_msg)

    if sess.title == 'New Chat' and len(user_content) > 5:
        sess.title = user_content[:50] + ('...' if len(user_content) > 50 else '')

    history = ChatMessage.query.filter_by(session_id=sess.id).order_by(ChatMessage.created_at.asc()).all()
    messages = [{'role': m.role, 'content': m.content} for m in history[-10:]]
    messages.append({'role': 'user', 'content': user_content})

    ai_response = get_ai_response(messages)

    ai_msg = ChatMessage(session_id=sess.id, role='assistant', content=ai_response)
    db.session.add(ai_msg)
    sess.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'response': ai_response, 'session_title': sess.title})

@chat_bp.route('/api/chat/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    sess = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    db.session.delete(sess)
    db.session.commit()
    return jsonify({'success': True})
