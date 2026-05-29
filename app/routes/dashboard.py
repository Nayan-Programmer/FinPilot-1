from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models import Expense, Invoice, Budget
from app import db
from datetime import date, timedelta
from sqlalchemy import func
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/api/dashboard/stats')
@login_required
def stats():
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    month_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id, Expense.date >= month_start).scalar() or 0
    last_month_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= last_month_start, Expense.date < month_start).scalar() or 0

    total_invoiced = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id).scalar() or 0
    paid_invoices = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='paid').scalar() or 0
    outstanding = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='unpaid').scalar() or 0
    overdue = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='overdue').scalar() or 0

    budget_count = Budget.query.filter_by(user_id=current_user.id).count()
    over_budget = Budget.query.filter(Budget.user_id == current_user.id, Budget.spent > Budget.allocated).count()

    exp_change = 0
    if last_month_expenses > 0:
        exp_change = round(((month_expenses - last_month_expenses) / last_month_expenses) * 100, 1)

    return jsonify({
        'total_expenses': round(total_expenses, 2),
        'month_expenses': round(month_expenses, 2),
        'expense_change': exp_change,
        'total_invoiced': round(total_invoiced, 2),
        'paid_invoices': round(paid_invoices, 2),
        'outstanding': round(outstanding, 2),
        'overdue': round(overdue, 2),
        'budget_count': budget_count,
        'over_budget': over_budget,
        'invoice_count': Invoice.query.filter_by(user_id=current_user.id).count(),
        'expense_count': Expense.query.filter_by(user_id=current_user.id).count()
    })

@dashboard_bp.route('/api/dashboard/expense-chart')
@login_required
def expense_chart():
    today = date.today()
    months = []
    for i in range(5, -1, -1):
        first = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        last = (first.replace(month=first.month % 12 + 1, day=1) - timedelta(days=1)) if first.month < 12 else first.replace(month=12, day=31)
        amount = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= first, Expense.date <= last).scalar() or 0
        months.append({'month': first.strftime('%b %Y'), 'amount': round(amount, 2)})
    return jsonify(months)

@dashboard_bp.route('/api/dashboard/category-chart')
@login_required
def category_chart():
    results = db.session.query(Expense.category, func.sum(Expense.amount)).filter_by(
        user_id=current_user.id).group_by(Expense.category).all()
    return jsonify([{'category': r[0], 'amount': round(r[1], 2)} for r in results])

@dashboard_bp.route('/api/dashboard/recent-activity')
@login_required
def recent_activity():
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.created_at.desc()).limit(5).all()
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).limit(5).all()
    activity = []
    for e in expenses:
        activity.append({'type': 'expense', 'title': e.title, 'amount': e.amount,
                         'category': e.category, 'date': e.date.strftime('%b %d')})
    for i in invoices:
        activity.append({'type': 'invoice', 'title': f'Invoice #{i.invoice_number}',
                         'client': i.client_name, 'amount': i.total, 'status': i.status,
                         'date': i.issue_date.strftime('%b %d')})
    return jsonify(activity[:8])

@dashboard_bp.route('/api/dashboard/budget-overview')
@login_required
def budget_overview():
    budgets = Budget.query.filter_by(user_id=current_user.id).limit(6).all()
    return jsonify([b.to_dict() for b in budgets])
