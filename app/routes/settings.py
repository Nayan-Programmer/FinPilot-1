from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Expense, Invoice, Budget
from sqlalchemy import func

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def index():
    return render_template('settings/index.html')

@settings_bp.route('/api/settings/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    current_user.name = name
    db.session.commit()
    return jsonify({'success': True, 'name': current_user.name})

@settings_bp.route('/api/settings/password', methods=['PUT'])
@login_required
def change_password():
    data = request.json
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    if not current_user.check_password(current_pw):
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
    if len(new_pw) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    current_user.set_password(new_pw)
    db.session.commit()
    return jsonify({'success': True})

@settings_bp.route('/api/settings/stats')
@login_required
def account_stats():
    from app.models import ChatSession, UploadedFile, Report
    return jsonify({
        'expenses': Expense.query.filter_by(user_id=current_user.id).count(),
        'invoices': Invoice.query.filter_by(user_id=current_user.id).count(),
        'budgets': Budget.query.filter_by(user_id=current_user.id).count(),
        'chat_sessions': ChatSession.query.filter_by(user_id=current_user.id).count(),
        'files': UploadedFile.query.filter_by(user_id=current_user.id).count(),
        'reports': Report.query.filter_by(user_id=current_user.id).count(),
        'member_since': current_user.created_at.strftime('%B %Y'),
        'role': current_user.role.replace('_', ' ').title()
    })
