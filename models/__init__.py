from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

# Asia/Kolkata timezone
ASIA_KOLKATA = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current time in Asia/Kolkata timezone"""
    return datetime.now(Asia_Kolkata)

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))
    department = db.relationship('Department', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        for role in self.roles:
            if permission in [p.name for p in role.permissions]:
                return True
        return False
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Role(db.Model):
    """Role model"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    permissions = db.relationship('Permission', secondary='role_permissions', backref=db.backref('roles', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Role {self.name}>'

class Permission(db.Model):
    """Permission model"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Permission {self.name}>'

# Association tables
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'))
)

class Vendor(db.Model):
    """Vendor Master"""
    __tablename__ = 'vendors'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    country = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    work_orders = db.relationship('WorkOrder', backref='vendor', lazy=True)
    
    def __repr__(self):
        return f'<Vendor {self.name}>'

class Customer(db.Model):
    """Customer Master"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    country = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Party(db.Model):
    """Party Master"""
    __tablename__ = 'parties'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    country = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Party {self.name}>'

class WorkflowConfig(db.Model):
    """Workflow configuration for modules"""
    __tablename__ = 'workflow_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(120), nullable=False)  # NFA, Work Order, etc.
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    steps = db.relationship('WorkflowStep', backref='config', lazy=True, cascade='all, delete-orphan')

class WorkflowStep(db.Model):
    """Workflow step within a workflow"""
    __tablename__ = 'workflow_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    workflow_config_id = db.Column(db.Integer, db.ForeignKey('workflow_configs.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(120), nullable=False)  # Submit, Approve, Reject
    approver_type = db.Column(db.String(120))  # Role-based or User-based
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    approver = db.relationship('User', backref='approver_workflows')
    assigned_role = db.relationship('Role', backref='approver_workflows')

# Individual document models
class NFA(db.Model):
    """Note for Approval"""
    __tablename__ = 'nfa'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')  # Draft, Submitted, Approved, Rejected
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    amount = db.Column(db.Float)
    approval_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    
    created_by = db.relationship('User', backref=db.backref('nfa_created', lazy='dynamic'))
    department = db.relationship('Department', backref='nfa_documents')
    vendor = db.relationship('Vendor', backref='nfa_documents')
    customer = db.relationship('Customer', backref='nfa_documents')
    attachments = db.relationship('Attachment', backref='nfa', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='nfa', lazy=True, cascade='all, delete-orphan')

class WorkOrder(db.Model):
    """Work Order"""
    __tablename__ = 'work_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    wo_po_number = db.Column(db.String(120))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))
    amount = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    created_by = db.relationship('User', backref=db.backref('work_order_created', lazy='dynamic'))
    department = db.relationship('Department', backref='work_order_documents')
    attachments = db.relationship('Attachment', backref='work_order', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='work_order', lazy=True, cascade='all, delete-orphan')

class CostContract(db.Model):
    """Cost Contract"""
    __tablename__ = 'cost_contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    contract_type = db.Column(db.String(120))
    vendor_name = db.Column(db.String(255))
    contract_value = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    created_by = db.relationship('User', backref=db.backref('cost_contract_created', lazy='dynamic'))
    department = db.relationship('Department', backref='cost_contract_documents')
    vendor = db.relationship('Vendor', backref='cost_contracts')
    customer = db.relationship('Customer', backref='cost_contracts')
    attachments = db.relationship('Attachment', backref='cost_contract', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='cost_contract', lazy=True, cascade='all, delete-orphan')

class RevenueContract(db.Model):
    """Revenue Contract"""
    __tablename__ = 'revenue_contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    customer_name = db.Column(db.String(255))
    contract_value = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    terms = db.Column(db.Text)
    
    created_by = db.relationship('User', backref=db.backref('revenue_contract_created', lazy='dynamic'))
    department = db.relationship('Department', backref='revenue_contract_documents')
    customer = db.relationship('Customer', backref='revenue_contracts')
    attachments = db.relationship('Attachment', backref='revenue_contract', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='revenue_contract', lazy=True, cascade='all, delete-orphan')

class Agreement(db.Model):
    """Agreement"""
    __tablename__ = 'agreements'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    effective_date = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    
    created_by = db.relationship('User', backref=db.backref('agreement_created', lazy='dynamic'))
    department = db.relationship('Department', backref='agreement_documents')
    customer = db.relationship('Customer', backref='agreements')
    party = db.relationship('Party', backref='agreements')
    attachments = db.relationship('Attachment', backref='agreement', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='agreement', lazy=True, cascade='all, delete-orphan')

class StatutoryDocument(db.Model):
    """Statutory Document"""
    __tablename__ = 'statutory_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(120), default='Draft')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejected_remarks = db.Column(db.Text)
    
    document_type = db.Column(db.String(120))
    regulatory_body = db.Column(db.String(255))
    due_date = db.Column(db.DateTime)
    
    created_by = db.relationship('User', backref=db.backref('statutory_document_created', lazy='dynamic'))
    department = db.relationship('Department', backref='statutory_document_documents')
    party = db.relationship('Party', backref='statutory_documents')
    attachments = db.relationship('Attachment', backref='statutory_document', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalHistory', backref='statutory_document', lazy=True, cascade='all, delete-orphan')

class Department(db.Model):
    """Department model for organization structure"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Attachment(db.Model):
    """File attachment for documents"""
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_readonly = db.Column(db.Boolean, default=False)
    
    # Document associations
    nfa_id = db.Column(db.Integer, db.ForeignKey('nfa.id'))
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'))
    cost_contract_id = db.Column(db.Integer, db.ForeignKey('cost_contracts.id'))
    revenue_contract_id = db.Column(db.Integer, db.ForeignKey('revenue_contracts.id'))
    agreement_id = db.Column(db.Integer, db.ForeignKey('agreements.id'))
    statutory_document_id = db.Column(db.Integer, db.ForeignKey('statutory_documents.id'))
    
    uploaded_by = db.relationship('User', backref='attachments')

class ApprovalHistory(db.Model):
    """Approval history for documents"""
    __tablename__ = 'approval_history'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(120), nullable=False)  # Submitted, Approved, Rejected
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.Column(db.Text)
    workflow_step_id = db.Column(db.Integer, db.ForeignKey('workflow_steps.id'))
    
    # Document associations
    nfa_id = db.Column(db.Integer, db.ForeignKey('nfa.id'))
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'))
    cost_contract_id = db.Column(db.Integer, db.ForeignKey('cost_contracts.id'))
    revenue_contract_id = db.Column(db.Integer, db.ForeignKey('revenue_contracts.id'))
    agreement_id = db.Column(db.Integer, db.ForeignKey('agreements.id'))
    statutory_document_id = db.Column(db.Integer, db.ForeignKey('statutory_documents.id'))
    
    approved_by = db.relationship('User', backref='approvals')

