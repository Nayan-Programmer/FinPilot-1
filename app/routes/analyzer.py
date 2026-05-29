from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import UploadedFile
from app.services.ai_service import analyze_financial_data
import os, json
from werkzeug.utils import secure_filename
from flask import current_app

analyzer_bp = Blueprint('analyzer', __name__)
ALLOWED = {'xlsx', 'xls', 'csv', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

@analyzer_bp.route('/analyzer')
@login_required
def index():
    files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.created_at.desc()).all()
    return render_template('analyzer/index.html', files=files)

@analyzer_bp.route('/api/analyzer/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type. Allowed: xlsx, xls, csv, pdf'}), 400

    filename = secure_filename(f.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_name = f'user{current_user.id}_{int(__import__("time").time())}_{filename}'
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    f.save(filepath)

    analysis = {}
    file_type = 'pdf' if ext == 'pdf' else 'excel'

    try:
        if ext in ['xlsx', 'xls', 'csv']:
            analysis = analyze_excel(filepath, ext)
        elif ext == 'pdf':
            analysis = analyze_pdf(filepath)
    except Exception as e:
        analysis = {'error': str(e), 'summary': 'Could not analyze file automatically.'}

    analysis_json = json.dumps(analysis)
    record = UploadedFile(
        user_id=current_user.id, filename=unique_name,
        original_name=f.filename, file_type=file_type, analysis=analysis_json
    )
    db.session.add(record)
    db.session.commit()

    ai_insights = analyze_financial_data(json.dumps(analysis, indent=2)[:2000])
    analysis['ai_insights'] = ai_insights

    return jsonify({'success': True, 'file_id': record.id, 'analysis': analysis})

def analyze_excel(filepath, ext):
    import pandas as pd
    if ext == 'csv':
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    result = {
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist()[:20],
        'numeric_columns': numeric_cols[:10],
        'missing_values': int(df.isnull().sum().sum()),
        'summary': {}
    }
    for col in numeric_cols[:5]:
        result['summary'][col] = {
            'min': round(float(df[col].min()), 2),
            'max': round(float(df[col].max()), 2),
            'mean': round(float(df[col].mean()), 2),
            'sum': round(float(df[col].sum()), 2),
            'std': round(float(df[col].std()), 2)
        }

    anomalies = []
    for col in numeric_cols[:3]:
        mean, std = df[col].mean(), df[col].std()
        outliers = df[df[col] > mean + 3*std]
        if len(outliers) > 0:
            anomalies.append(f'{len(outliers)} outliers in "{col}" (>{mean+3*std:.2f})')
    result['anomalies'] = anomalies[:5]

    top_expenses = []
    for col in numeric_cols[:2]:
        top = df.nlargest(5, col)[col].tolist()
        top_expenses.extend([round(float(v), 2) for v in top])
    result['top_values'] = top_expenses[:10]

    return result

def analyze_pdf(filepath):
    try:
        import PyPDF2
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ''
            for i, page in enumerate(reader.pages[:10]):
                text += page.extract_text() or ''
        words = len(text.split())
        lines = text.split('\n')
        numbers = []
        import re
        for line in lines:
            nums = re.findall(r'\$?[\d,]+\.?\d*', line)
            numbers.extend(nums[:3])
        return {
            'pages': len(reader.pages),
            'word_count': words,
            'extracted_numbers': numbers[:20],
            'preview': text[:500],
            'summary': f'PDF with {len(reader.pages)} pages and {words} words extracted.'
        }
    except Exception as e:
        return {'error': str(e), 'summary': 'PDF extraction failed.'}

@analyzer_bp.route('/api/analyzer/files')
@login_required
def list_files():
    files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.created_at.desc()).all()
    return jsonify([{
        'id': f.id, 'original_name': f.original_name, 'file_type': f.file_type,
        'created_at': f.created_at.strftime('%b %d, %Y')
    } for f in files])

@analyzer_bp.route('/api/analyzer/files/<int:file_id>')
@login_required
def get_analysis(file_id):
    f = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    analysis = json.loads(f.analysis or '{}')
    return jsonify({'original_name': f.original_name, 'file_type': f.file_type,
                    'created_at': f.created_at.strftime('%b %d, %Y'), 'analysis': analysis})
