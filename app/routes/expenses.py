from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Expense
from datetime import date, datetime

expenses_bp = Blueprint('expenses', __name__)

CATEGORIES = ['Salaries', 'Marketing', 'Operations', 'Technology', 'Travel',
              'Office', 'Utilities', 'Legal', 'R&D', 'Training', 'Other']

@expenses_bp.route('/expenses')
@login_required
def index():
    return render_template('expenses/index.html', categories=CATEGORIES)

@expenses_bp.route('/api/expenses', methods=['GET'])
@login_required
def list_expenses():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    query = Expense.query.filter_by(user_id=current_user.id)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Expense.title.ilike(f'%{search}%'))

    pagination = query.order_by(Expense.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'expenses': [e.to_dict() for e in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@expenses_bp.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    data = request.json
    try:
        expense = Expense(
            user_id=current_user.id,
            title=data['title'],
            amount=float(data['amount']),
            category=data['category'],
            description=data.get('description', ''),
            date=datetime.strptime(data.get('date', str(date.today())), '%Y-%m-%d').date(),
            is_recurring=data.get('is_recurring', False)
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify({'success': True, 'expense': expense.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@expenses_bp.route('/api/expenses/<int:exp_id>', methods=['PUT'])
@login_required
def update_expense(exp_id):
    expense = Expense.query.filter_by(id=exp_id, user_id=current_user.id).first_or_404()
    data = request.json
    try:
        expense.title = data.get('title', expense.title)
        expense.amount = float(data.get('amount', expense.amount))
        expense.category = data.get('category', expense.category)
        expense.description = data.get('description', expense.description)
        if 'date' in data:
            expense.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        expense.is_recurring = data.get('is_recurring', expense.is_recurring)
        db.session.commit()
        return jsonify({'success': True, 'expense': expense.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@expenses_bp.route('/api/expenses/<int:exp_id>', methods=['DELETE'])
@login_required
def delete_expense(exp_id):
    expense = Expense.query.filter_by(id=exp_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'success': True})

@expenses_bp.route('/api/expenses/export')
@login_required
def export_csv():
    import csv
    import io
    from flask import Response
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Title', 'Category', 'Amount', 'Description', 'Recurring'])
    for e in expenses:
        writer.writerow([e.date, e.title, e.category, e.amount, e.description, 'Yes' if e.is_recurring else 'No'])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=expenses.csv'}
    )

@expenses_bp.route('/api/expenses/summary')
@login_required
def summary():
    from sqlalchemy import func
    results = db.session.query(Expense.category, func.sum(Expense.amount), func.count(Expense.id)).filter_by(
        user_id=current_user.id).group_by(Expense.category).all()
    return jsonify([{'category': r[0], 'total': round(r[1], 2), 'count': r[2]} for r in results])
