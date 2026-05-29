from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Expense, Invoice
from datetime import date, timedelta
from sqlalchemy import func
import json

forecasting_bp = Blueprint('forecasting', __name__)

@forecasting_bp.route('/forecasting')
@login_required
def index():
    return render_template('forecasting/index.html')

@forecasting_bp.route('/api/forecasting/data')
@login_required
def forecast_data():
    today = date.today()
    months = []
    actuals_exp = []
    actuals_rev = []

    for i in range(11, -1, -1):
        first = _month_start(today, -i)
        last = _month_end(first)
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= first, Expense.date <= last).scalar() or 0
        rev = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id,
            Invoice.issue_date >= first, Invoice.issue_date <= last).scalar() or 0
        months.append(first.strftime('%b %Y'))
        actuals_exp.append(round(float(exp), 2))
        actuals_rev.append(round(float(rev), 2))

    exp_forecast = _linear_forecast(actuals_exp, 6)
    rev_forecast = _linear_forecast(actuals_rev, 6)

    future_months = []
    for i in range(1, 7):
        future_months.append(_month_start(today, i).strftime('%b %Y'))

    return jsonify({
        'historical_months': months,
        'future_months': future_months,
        'actuals_expense': actuals_exp,
        'actuals_revenue': actuals_rev,
        'forecast_expense': exp_forecast,
        'forecast_revenue': rev_forecast,
        'net_income': [round(r - e, 2) for r, e in zip(actuals_rev, actuals_exp)],
        'projected_net': [round(r - e, 2) for r, e in zip(rev_forecast, exp_forecast)]
    })

@forecasting_bp.route('/api/forecasting/summary')
@login_required
def forecast_summary():
    today = date.today()
    actuals_exp, actuals_rev = [], []
    for i in range(5, -1, -1):
        first = _month_start(today, -i)
        last = _month_end(first)
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= first, Expense.date <= last).scalar() or 0
        rev = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id,
            Invoice.issue_date >= first, Invoice.issue_date <= last).scalar() or 0
        actuals_exp.append(float(exp))
        actuals_rev.append(float(rev))

    next_exp = _linear_forecast(actuals_exp, 1)[0]
    next_rev = _linear_forecast(actuals_rev, 1)[0]
    avg_exp = sum(actuals_exp) / len(actuals_exp) if actuals_exp else 0
    avg_rev = sum(actuals_rev) / len(actuals_rev) if actuals_rev else 0
    growth_exp = ((actuals_exp[-1] - actuals_exp[0]) / actuals_exp[0] * 100) if actuals_exp[0] else 0
    growth_rev = ((actuals_rev[-1] - actuals_rev[0]) / actuals_rev[0] * 100) if actuals_rev[0] else 0

    return jsonify({
        'next_month_expense': round(next_exp, 2),
        'next_month_revenue': round(next_rev, 2),
        'next_month_net': round(next_rev - next_exp, 2),
        'avg_monthly_expense': round(avg_exp, 2),
        'avg_monthly_revenue': round(avg_rev, 2),
        'expense_growth_6m': round(growth_exp, 1),
        'revenue_growth_6m': round(growth_rev, 1),
        'burn_rate': round(avg_exp, 2),
        'runway_months': round(avg_rev / avg_exp, 1) if avg_exp > 0 else 99
    })

@forecasting_bp.route('/api/forecasting/category')
@forecasting_bp.route('/api/forecasting/cashflow')
@login_required
def cashflow():
    today = date.today()
    result = []
    running = 0
    for i in range(11, -1, -1):
        first = _month_start(today, -i)
        last = _month_end(first)
        rev = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id, Invoice.status == 'paid',
            Invoice.issue_date >= first, Invoice.issue_date <= last).scalar() or 0
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.date >= first, Expense.date <= last).scalar() or 0
        net = float(rev) - float(exp)
        running += net
        result.append({
            'month': first.strftime('%b %Y'),
            'inflow': round(float(rev), 2),
            'outflow': round(float(exp), 2),
            'net': round(net, 2),
            'cumulative': round(running, 2)
        })
    return jsonify(result)


def _month_start(ref, offset):
    m = ref.month - 1 + offset
    y = ref.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)

def _month_end(first):
    m2 = first.month % 12 + 1
    y2 = first.year + (1 if first.month == 12 else 0)
    return date(y2, m2, 1) - timedelta(days=1)

def _linear_forecast(data, steps):
    n = len(data)
    if n < 2:
        return [data[-1] if data else 0] * steps
    try:
        import numpy as np
        x = np.arange(n, dtype=float)
        y = np.array(data, dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        return [max(0, round(slope * (n + i) + intercept, 2)) for i in range(steps)]
    except Exception:
        avg = sum(data[-3:]) / min(3, len(data))
        return [round(avg, 2)] * steps
