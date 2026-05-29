from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Budget, Expense
from datetime import date, datetime
from sqlalchemy import func

budgets_bp = Blueprint('budgets', __name__)

CATEGORIES = ['Salaries', 'Marketing', 'Operations', 'Technology', 'Travel',
              'Office', 'Utilities', 'Legal', 'R&D', 'Training', 'Other']

@budgets_bp.route('/budgets')
@login_required
def index():
    return render_template('budgets/index.html', categories=CATEGORIES)

@budgets_bp.route('/api/budgets', methods=['GET'])
@login_required
def list_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).order_by(Budget.created_at.desc()).all()
    return jsonify([b.to_dict() for b in budgets])

@budgets_bp.route('/api/budgets', methods=['POST'])
@login_required
def create_budget():
    data = request.json
    try:
        budget = Budget(
            user_id=current_user.id,
            name=data['name'],
            category=data['category'],
            allocated=float(data['allocated']),
            spent=float(data.get('spent', 0)),
            period=data.get('period', 'monthly'),
            alert_threshold=float(data.get('alert_threshold', 80))
        )
        if data.get('start_date'):
            budget.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if data.get('end_date'):
            budget.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        db.session.add(budget)
        db.session.commit()
        return jsonify({'success': True, 'budget': budget.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@budgets_bp.route('/api/budgets/<int:budget_id>', methods=['PUT'])
@login_required
def update_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    data = request.json
    budget.name = data.get('name', budget.name)
    budget.category = data.get('category', budget.category)
    budget.allocated = float(data.get('allocated', budget.allocated))
    budget.spent = float(data.get('spent', budget.spent))
    budget.period = data.get('period', budget.period)
    budget.alert_threshold = float(data.get('alert_threshold', budget.alert_threshold))
    db.session.commit()
    return jsonify({'success': True, 'budget': budget.to_dict()})

@budgets_bp.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    db.session.delete(budget)
    db.session.commit()
    return jsonify({'success': True})

@budgets_bp.route('/api/budgets/sync')
@login_required
def sync_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    today = date.today()
    month_start = today.replace(day=1)
    for b in budgets:
        actual = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.category == b.category,
            Expense.date >= month_start
        ).scalar() or 0
        b.spent = round(actual, 2)
    db.session.commit()
    return jsonify({'success': True, 'synced': len(budgets)})

@budgets_bp.route('/api/budgets/alerts')
@login_required
def alerts():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    alerts = []
    for b in budgets:
        if b.utilization >= b.alert_threshold:
            status = 'exceeded' if b.utilization >= 100 else 'warning'
            alerts.append({
                'id': b.id, 'name': b.name, 'category': b.category,
                'utilization': b.utilization, 'status': status,
                'allocated': b.allocated, 'spent': b.spent
            })
    return jsonify(alerts)
