import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, abort
from flask_login import current_user
from functools import wraps

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file):
    """Save uploaded file and return file path"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    return file_path

def get_next_reference_number(module):
    """Generate next reference number for a module"""
    from models import NFA, WorkOrder, CostContract, RevenueContract, Agreement, StatutoryDocument
    
    module_map = {
        'NFA': NFA,
        'WorkOrder': WorkOrder,
        'CostContract': CostContract,
        'RevenueContract': RevenueContract,
        'Agreement': Agreement,
        'StatutoryDocument': StatutoryDocument
    }
    
    model = module_map.get(module)
    if not model:
        return None
    
    count = model.query.count() + 1
    date_str = datetime.utcnow().strftime('%Y%m')
    
    return f'{module}-{date_str}-{count:05d}'

def send_approval_notification(document, action, user):
    """Send approval notification (placeholder for email sending)"""
    # This can be extended to send actual emails
    print(f'Notification: {document.reference_number} has been {action} by {user.username}')

def require_permission(permission_name):
    """Decorator to check if user has required permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(role_name):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            user_role_names = [role.name for role in current_user.roles]
            if role_name not in user_role_names:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class WorkflowEngine:
    """Workflow approval engine"""
    
    @staticmethod
    def get_next_approvers(document_model, module_name):
        """Get next approvers for a document"""
        from models import WorkflowConfig, ApprovalHistory, db
        
        workflow = WorkflowConfig.query.filter_by(module=module_name, is_active=True).first()
        if not workflow:
            return []
        
        # Get approval history count to determine next step
        approval_count = ApprovalHistory.query.filter_by(**{f'{module_name.lower()}_id': document_model.id}).count()
        
        # Get next workflow step
        next_step = workflow.steps[approval_count] if approval_count < len(workflow.steps) else None
        
        if not next_step:
            return []
        
        approvers = []
        if next_step.approver_type == 'user' and next_step.approver_id:
            approvers.append(next_step.approver)
        elif next_step.approver_type == 'role' and next_step.role_id:
            approvers = list(next_step.assigned_role.users)
        
        return approvers
    
    @staticmethod
    def approve_document(document_model, approved_by_user, module_name, comments=''):
        """Approve a document"""
        from models import ApprovalHistory, db
        
        history = ApprovalHistory(
            action='Approved',
            approved_by_id=approved_by_user.id,
            comments=comments,
            **{f'{module_name.lower()}_id': document_model.id}
        )
        
        db.session.add(history)
        document_model.status = 'Approved'
        db.session.commit()
        
        return history
    
    @staticmethod
    def reject_document(document_model, rejected_by_user, module_name, remarks=''):
        """Reject a document"""
        from models import ApprovalHistory, db
        
        history = ApprovalHistory(
            action='Rejected',
            approved_by_id=rejected_by_user.id,
            comments=remarks,
            **{f'{module_name.lower()}_id': document_model.id}
        )
        
        db.session.add(history)
        document_model.status = 'Rejected'
        document_model.rejected_remarks = remarks
        db.session.commit()
        
        return history
