from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, DateTimeField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, ValidationError as WTFValidationError
from models import User, Department, NFA, WorkOrder, CostContract, RevenueContract, Agreement, StatutoryDocument

class AttachmentRequired:
    """Validator to ensure at least one attachment is uploaded"""
    def __init__(self, message='At least one attachment is required.'):
        self.message = message
    
    def __call__(self, form, field):
        if not field.data:
            raise WTFValidationError(self.message)

class UniqueReferenceNumber:
    """Validator to check if reference number is unique across the model"""
    def __init__(self, model_class, message='Reference number already exists. Please use a different one.'):
        self.model_class = model_class
        self.message = message

    def __call__(self, form, field):
        if field.data:
            existing = self.model_class.query.filter_by(reference_number=field.data).first()
            if existing:
                raise ValidationError(self.message)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    password = PasswordField('Password', validators=[DataRequired()])
    password_confirm = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class NFAForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(NFA)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[Optional()])
    description = TextAreaField('Description')
    approval_date = DateTimeField('Approval Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    vendor_id = SelectField('Vendor', coerce=int, validators=[Optional()])
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save NFA')

class WorkOrderForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(WorkOrder)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    wo_po_number = StringField('WO/PO Number')
    vendor_id = SelectField('Vendor', coerce=int, validators=[Optional()])
    amount = FloatField('Amount', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d', validators=[Optional()])
    description = TextAreaField('Description')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save Work Order')

class CostContractForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(CostContract)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    vendor_id = SelectField('Vendor', coerce=int, validators=[Optional()])
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    contract_value = FloatField('Contract Value', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d', validators=[Optional()])
    description = TextAreaField('Description')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save Cost Contract')

class RevenueContractForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(RevenueContract)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    customer_name = StringField('Customer Name')
    contract_value = FloatField('Contract Value', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d', validators=[Optional()])
    terms = TextAreaField('Terms')
    description = TextAreaField('Description')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save Revenue Contract')

class AgreementForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(Agreement)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    party_id = SelectField('Party', coerce=int, validators=[Optional()])
    effective_date = DateTimeField('Effective Date', format='%Y-%m-%d', validators=[Optional()])
    expiry_date = DateTimeField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    description = TextAreaField('Description')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save Agreement')

class StatutoryDocumentForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[Optional(), UniqueReferenceNumber(StatutoryDocument)], render_kw={'placeholder': 'Leave blank to auto-generate'})
    title = StringField('Title', validators=[DataRequired()])
    document_type = StringField('Document Type')
    regulatory_body = StringField('Regulatory Body')
    party_id = SelectField('Party', coerce=int, validators=[Optional()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    description = TextAreaField('Description')
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    attachments = FileField('Attachments', validators=[Optional()], render_kw={'multiple': True})
    submit = SubmitField('Save Statutory Document')

class ApprovalForm(FlaskForm):
    action = SelectField('Action', choices=[('approve', 'Approve'), ('reject', 'Reject')], validators=[DataRequired()])
    comments = TextAreaField('Comments')
    submit = SubmitField('Submit Approval')
class DepartmentForm(FlaskForm):
    """Form for creating and editing departments"""
    name = StringField('Department Name', validators=[DataRequired()])
    code = StringField('Department Code', validators=[DataRequired()])
    description = TextAreaField('Description')
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], validators=[DataRequired()])
    submit = SubmitField('Save Department')