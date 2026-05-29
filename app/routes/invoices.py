from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Invoice
from datetime import date, datetime
import json

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/invoices')
@login_required
def index():
    return render_template('invoices/index.html')

@invoices_bp.route('/api/invoices', methods=['GET'])
@login_required
def list_invoices():
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    query = Invoice.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Invoice.client_name.ilike(f'%{search}%') | Invoice.invoice_number.ilike(f'%{search}%'))
    invoices = query.order_by(Invoice.created_at.desc()).all()
    return jsonify([i.to_dict() for i in invoices])

@invoices_bp.route('/api/invoices', methods=['POST'])
@login_required
def create_invoice():
    data = request.json
    try:
        last = Invoice.query.filter_by(user_id=current_user.id).count() + 1
        inv_num = data.get('invoice_number') or f'INV-{datetime.now().year}-{str(last).zfill(4)}'
        items = data.get('items', [])
        subtotal = sum(float(i.get('amount', 0)) for i in items)
        tax_rate = float(data.get('tax_rate', 0))
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal + tax_amount, 2)
        invoice = Invoice(
            user_id=current_user.id,
            invoice_number=inv_num,
            client_name=data['client_name'],
            client_email=data.get('client_email', ''),
            client_address=data.get('client_address', ''),
            items=json.dumps(items),
            subtotal=subtotal, tax_rate=tax_rate, tax_amount=tax_amount, total=total,
            status=data.get('status', 'unpaid'),
            issue_date=datetime.strptime(data.get('issue_date', str(date.today())), '%Y-%m-%d').date(),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
            notes=data.get('notes', '')
        )
        db.session.add(invoice)
        db.session.commit()
        return jsonify({'success': True, 'invoice': invoice.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@invoices_bp.route('/api/invoices/<int:inv_id>', methods=['GET'])
@login_required
def get_invoice(inv_id):
    inv = Invoice.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    data = inv.to_dict()
    data['items'] = json.loads(inv.items or '[]')
    data['client_address'] = inv.client_address
    data['client_email'] = inv.client_email
    data['notes'] = inv.notes
    data['tax_rate'] = inv.tax_rate
    data['subtotal'] = inv.subtotal
    return jsonify(data)

@invoices_bp.route('/api/invoices/<int:inv_id>/status', methods=['PATCH'])
@login_required
def update_status(inv_id):
    inv = Invoice.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    data = request.json
    inv.status = data.get('status', inv.status)
    db.session.commit()
    return jsonify({'success': True, 'status': inv.status})

@invoices_bp.route('/api/invoices/<int:inv_id>', methods=['DELETE'])
@login_required
def delete_invoice(inv_id):
    inv = Invoice.query.filter_by(id=inv_id, user_id=current_user.id).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    return jsonify({'success': True})

@invoices_bp.route('/api/invoices/stats')
@login_required
def stats():
    from sqlalchemy import func
    results = db.session.query(Invoice.status, func.count(Invoice.id), func.sum(Invoice.total)).filter_by(
        user_id=current_user.id).group_by(Invoice.status).all()
    return jsonify([{'status': r[0], 'count': r[1], 'total': round(r[2] or 0, 2)} for r in results])
