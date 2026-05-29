from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Expense, Invoice, Budget
from app.services.ai_service import get_ai_response
from datetime import date, timedelta
from sqlalchemy import func

insights_bp = Blueprint('insights', __name__)

@insights_bp.route('/insights')
@login_required
def index():
    return render_template('insights/index.html')

@insights_bp.route('/api/insights/cfo-brief')
@login_required
def cfo_brief():
    snapshot = _build_snapshot()
    prompt = f"""You are a CFO advisor. Based on this financial snapshot, provide a structured executive brief:

{snapshot}

Provide:
1. **Executive Summary** (2-3 sentences)
2. **Key Strengths** (bullet points)
3. **Risk Factors** (bullet points)
4. **Top 3 Recommendations** (numbered, actionable)
5. **30-Day Priority Actions**

Be specific, data-driven, and professional. Use markdown."""
    response = get_ai_response([{"role": "user", "content": prompt}])
    return jsonify({'brief': response, 'snapshot': snapshot})

@insights_bp.route('/api/insights/risk-analysis')
@login_required
def risk_analysis():
    snapshot = _build_snapshot()
    prompt = f"""Perform a financial risk assessment based on:

{snapshot}

Provide a structured risk analysis covering:
1. **Liquidity Risk** — cash flow concerns
2. **Concentration Risk** — revenue/expense dependencies
3. **Budget Risk** — over-budget categories
4. **Operational Risk** — spending patterns
5. **Overall Risk Score** (Low/Medium/High) with justification

Use markdown formatting."""
    response = get_ai_response([{"role": "user", "content": prompt}])
    return jsonify({'analysis': response})

@insights_bp.route('/api/insights/cost-savings')
@login_required
def cost_savings():
    snapshot = _build_snapshot()
    prompt = f"""Analyze this financial data and identify cost-saving opportunities:

{snapshot}

Provide:
1. **Quick Wins** (0-30 days, low effort)
2. **Medium-Term Savings** (1-3 months)
3. **Strategic Cost Reduction** (3-12 months)
4. **Estimated Savings Potential** per category
5. **Prioritized Action Plan**

Be specific and quantify where possible. Use markdown."""
    response = get_ai_response([{"role": "user", "content": prompt}])
    return jsonify({'recommendations': response})

@insights_bp.route('/api/insights/performance')
@login_required
def performance():
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(days=1)

    def month_data(start, end):
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= start, Expense.date <= end).scalar() or 0
        rev = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id,
            Invoice.issue_date >= start, Invoice.issue_date <= end).scalar() or 0
        return float(exp), float(rev)

    cur_exp, cur_rev = month_data(month_start, today)
    prev_exp, prev_rev = month_data(last_month_start, last_month_end)

    def pct_change(cur, prev):
        if prev == 0:
            return 0
        return round((cur - prev) / prev * 100, 1)

    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    over_budget = [b for b in budgets if b.utilization >= 100]
    near_budget = [b for b in budgets if 80 <= b.utilization < 100]

    # Category breakdown this month
    cats = db.session.query(Expense.category, func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id, Expense.date >= month_start
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    return jsonify({
        'current': {'expenses': round(cur_exp, 2), 'revenue': round(cur_rev, 2), 'net': round(cur_rev - cur_exp, 2)},
        'previous': {'expenses': round(prev_exp, 2), 'revenue': round(prev_rev, 2), 'net': round(prev_rev - prev_exp, 2)},
        'changes': {
            'expenses': pct_change(cur_exp, prev_exp),
            'revenue': pct_change(cur_rev, prev_rev),
            'net': pct_change(cur_rev - cur_exp, prev_rev - prev_exp)
        },
        'budget_alerts': {
            'over': [{'name': b.name, 'utilization': b.utilization} for b in over_budget],
            'near': [{'name': b.name, 'utilization': b.utilization} for b in near_budget]
        },
        'top_categories': [{'category': r[0], 'amount': round(r[1], 2)} for r in cats[:6]],
        'margin': round((cur_rev - cur_exp) / cur_rev * 100, 1) if cur_rev > 0 else 0
    })

@insights_bp.route('/api/insights/notifications')
@login_required
def notifications():
    today = date.today()
    notes = []

    overdue = Invoice.query.filter_by(user_id=current_user.id, status='unpaid').filter(
        Invoice.due_date < today).all()
    for inv in overdue:
        days = (today - inv.due_date).days
        notes.append({'type': 'danger', 'icon': '⚠️',
                       'title': f'Overdue Invoice: {inv.invoice_number}',
                       'message': f'{inv.client_name} — ${inv.total:,.2f} ({days} days overdue)',
                       'link': '/invoices'})

    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    for b in budgets:
        if b.utilization >= 100:
            notes.append({'type': 'danger', 'icon': '🚨',
                           'title': f'Budget Exceeded: {b.category}',
                           'message': f'Spent ${b.spent:,.2f} of ${b.allocated:,.2f} allocated ({b.utilization}%)',
                           'link': '/budgets'})
        elif b.utilization >= b.alert_threshold:
            notes.append({'type': 'warning', 'icon': '⚡',
                           'title': f'Budget Alert: {b.category}',
                           'message': f'{b.utilization}% utilized — ${b.allocated - b.spent:,.2f} remaining',
                           'link': '/budgets'})

    unpaid_count = Invoice.query.filter_by(user_id=current_user.id, status='unpaid').count()
    if unpaid_count > 0:
        unpaid_total = db.session.query(func.sum(Invoice.total)).filter_by(
            user_id=current_user.id, status='unpaid').scalar() or 0
        notes.append({'type': 'info', 'icon': '📋',
                       'title': f'{unpaid_count} Pending Invoice{"s" if unpaid_count > 1 else ""}',
                       'message': f'${unpaid_total:,.2f} awaiting payment',
                       'link': '/invoices'})

    return jsonify({'notifications': notes, 'count': len(notes)})

def _build_snapshot():
    today = date.today()
    month_start = today.replace(day=1)
    total_exp = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    month_exp = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id, Expense.date >= month_start).scalar() or 0
    total_rev = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id).scalar() or 0
    paid_rev = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='paid').scalar() or 0
    outstanding = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='unpaid').scalar() or 0
    overdue = db.session.query(func.sum(Invoice.total)).filter_by(user_id=current_user.id, status='overdue').scalar() or 0
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    cats = db.session.query(Expense.category, func.sum(Expense.amount)).filter_by(
        user_id=current_user.id).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(5).all()
    return f"""
Total Expenses (All Time): ${total_exp:,.2f}
Current Month Expenses: ${month_exp:,.2f}
Total Revenue Invoiced: ${total_rev:,.2f}
Collected Revenue: ${paid_rev:,.2f}
Outstanding Receivables: ${outstanding:,.2f}
Overdue Amounts: ${overdue:,.2f}
Net Position: ${(paid_rev - total_exp):,.2f}
Active Budgets: {len(budgets)}
Over-Budget Categories: {sum(1 for b in budgets if b.utilization >= 100)}
Top Expense Categories: {', '.join(f"{r[0]}: ${r[1]:,.0f}" for r in cats[:5])}
Average Budget Utilization: {round(sum(b.utilization for b in budgets) / len(budgets), 1) if budgets else 0}%
"""
