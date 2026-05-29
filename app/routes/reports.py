from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Expense, Invoice, Budget, Report
from app.services.ai_service import generate_report_summary
from datetime import date, datetime, timedelta
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/api/reports/generate', methods=['POST'])
@login_required
def generate():
    data = request.json
    report_type = data.get('type', 'monthly')
    period = data.get('period', '')
    today = date.today()

    if report_type == 'monthly':
        try:
            year, month = map(int, period.split('-'))
            start = date(year, month, 1)
            end = (date(year, month % 12 + 1, 1) - timedelta(days=1)) if month < 12 else date(year, 12, 31)
        except Exception:
            start = today.replace(day=1)
            end = today
    elif report_type == 'quarterly':
        q = int(period[-1]) if period else ((today.month - 1) // 3 + 1)
        year = int(period[:4]) if period else today.year
        start = date(year, (q - 1) * 3 + 1, 1)
        end = date(year, q * 3, 30) if q < 4 else date(year, 12, 31)
    else:
        year = int(period) if period else today.year
        start = date(year, 1, 1)
        end = date(year, 12, 31)

    total_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start, Expense.date <= end).scalar() or 0

    cat_breakdown = db.session.query(Expense.category, func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start, Expense.date <= end
    ).group_by(Expense.category).all()

    total_invoiced = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.user_id == current_user.id,
        Invoice.issue_date >= start, Invoice.issue_date <= end).scalar() or 0

    paid_amount = db.session.query(func.sum(Invoice.total)).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'paid',
        Invoice.issue_date >= start, Invoice.issue_date <= end).scalar() or 0

    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    total_allocated = sum(b.allocated for b in budgets)
    total_spent = sum(b.spent for b in budgets)

    report_data = {
        'period': f'{start.strftime("%b %d, %Y")} — {end.strftime("%b %d, %Y")}',
        'type': report_type,
        'total_expenses': round(total_expenses, 2),
        'total_invoiced': round(total_invoiced, 2),
        'paid_amount': round(paid_amount, 2),
        'outstanding': round(total_invoiced - paid_amount, 2),
        'net_income': round(total_invoiced - total_expenses, 2),
        'budget_allocated': round(total_allocated, 2),
        'budget_spent': round(total_spent, 2),
        'budget_utilization': round((total_spent / total_allocated * 100) if total_allocated else 0, 1),
        'category_breakdown': [{'category': r[0], 'amount': round(r[1], 2)} for r in cat_breakdown]
    }

    summary_text = f"""
Financial Report: {report_data['period']}
Total Revenue: ${report_data['total_invoiced']:,.2f}
Total Expenses: ${report_data['total_expenses']:,.2f}
Net Income: ${report_data['net_income']:,.2f}
Paid Invoices: ${report_data['paid_amount']:,.2f}
Outstanding: ${report_data['outstanding']:,.2f}
Budget Utilization: {report_data['budget_utilization']}%
Top Categories: {', '.join([f"{c['category']}: ${c['amount']:,.2f}" for c in report_data['category_breakdown'][:5]])}
"""
    report_data['ai_summary'] = generate_report_summary(summary_text)

    report = Report(
        user_id=current_user.id,
        title=f'{report_type.capitalize()} Report — {period}',
        report_type=report_type,
        period=period or str(today),
        content=str(report_data),
        ai_summary=report_data['ai_summary']
    )
    db.session.add(report)
    db.session.commit()

    return jsonify(report_data)

@reports_bp.route('/api/reports/history')
@login_required
def history():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': r.id, 'title': r.title, 'type': r.report_type,
        'period': r.period, 'created_at': r.created_at.strftime('%b %d, %Y')
    } for r in reports])
