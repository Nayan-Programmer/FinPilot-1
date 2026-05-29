from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='employee')  # admin, finance_manager, employee
    avatar = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    expenses = db.relationship('Expense', backref='user', lazy=True)
    invoices = db.relationship('Invoice', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'amount': self.amount,
            'category': self.category, 'description': self.description,
            'date': self.date.strftime('%Y-%m-%d'), 'is_recurring': self.is_recurring
        }


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(120), default='')
    client_address = db.Column(db.Text, default='')
    items = db.Column(db.Text, default='[]')  # JSON string
    subtotal = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='unpaid')  # paid, unpaid, overdue, draft
    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'invoice_number': self.invoice_number,
            'client_name': self.client_name, 'client_email': self.client_email,
            'total': self.total, 'status': self.status,
            'issue_date': self.issue_date.strftime('%Y-%m-%d'),
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None
        }


class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    allocated = db.Column(db.Float, nullable=False)
    spent = db.Column(db.Float, default=0)
    period = db.Column(db.String(20), default='monthly')  # monthly, quarterly, annual
    start_date = db.Column(db.Date, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=True)
    alert_threshold = db.Column(db.Float, default=80)  # percent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def utilization(self):
        if self.allocated == 0:
            return 0
        return round((self.spent / self.allocated) * 100, 1)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'category': self.category,
            'allocated': self.allocated, 'spent': self.spent,
            'period': self.period, 'utilization': self.utilization,
            'alert_threshold': self.alert_threshold
        }


class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='New Chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'role': self.role, 'content': self.content,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')}


class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    original_name = db.Column(db.String(300), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # excel, pdf
    analysis = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # monthly, quarterly, annual
    period = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, default='')
    ai_summary = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
