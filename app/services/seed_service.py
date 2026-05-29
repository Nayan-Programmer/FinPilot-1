from datetime import date, timedelta
import random

def seed_demo_data():
    from app import db
    from app.models import User, Expense, Invoice, Budget, ChatSession, ChatMessage
    import json

    if User.query.count() > 0:
        return

    admin = User(name='Alex Morgan', email='admin@finpilot.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()

    categories = ['Salaries', 'Marketing', 'Operations', 'Technology', 'Travel', 'Office', 'Utilities', 'Legal']
    today = date.today()

    for i in range(40):
        exp_date = today - timedelta(days=random.randint(0, 180))
        expense = Expense(
            user_id=admin.id,
            title=random.choice(['Team Lunch', 'Software License', 'Cloud Hosting', 'Ad Campaign', 'Office Supplies',
                                  'Business Travel', 'Legal Consultation', 'Electricity Bill', 'Internet Service',
                                  'Equipment Purchase', 'Training Course', 'Conference Fee']),
            amount=round(random.uniform(50, 8000), 2),
            category=random.choice(categories),
            description='Demo expense entry',
            date=exp_date
        )
        db.session.add(expense)

    statuses = ['paid', 'unpaid', 'overdue', 'paid', 'paid']
    clients = ['Acme Corp', 'TechVentures Ltd', 'Global Finance Inc', 'StartupXYZ', 'Premier Solutions',
               'DataDrive Co', 'NextGen Systems', 'Alpha Capital']
    for i in range(12):
        items = json.dumps([{'desc': 'Consulting Services', 'qty': random.randint(1, 10),
                              'rate': random.uniform(100, 500),
                              'amount': round(random.uniform(500, 5000), 2)}])
        subtotal = round(random.uniform(1000, 15000), 2)
        tax = round(subtotal * 0.1, 2)
        inv = Invoice(
            user_id=admin.id,
            invoice_number=f'INV-2024-{str(i+1).zfill(3)}',
            client_name=random.choice(clients),
            client_email='client@example.com',
            items=items,
            subtotal=subtotal, tax_rate=10, tax_amount=tax,
            total=round(subtotal + tax, 2),
            status=random.choice(statuses),
            issue_date=today - timedelta(days=random.randint(0, 90)),
            due_date=today + timedelta(days=random.randint(-10, 30))
        )
        db.session.add(inv)

    for cat in categories:
        budget = Budget(
            user_id=admin.id,
            name=f'{cat} Budget',
            category=cat,
            allocated=round(random.uniform(5000, 30000), 2),
            spent=round(random.uniform(1000, 25000), 2),
            period='monthly'
        )
        db.session.add(budget)

    session = ChatSession(user_id=admin.id, title='Welcome to FinPilot AI')
    db.session.add(session)
    db.session.flush()

    db.session.add(ChatMessage(session_id=session.id, role='assistant',
                               content='Hello! I\'m your AI Finance Assistant. I can help you analyze your financial data, answer finance questions, generate insights, and much more. What would you like to explore today?'))

    db.session.commit()
