from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, DateTimeField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from models import User

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
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[Optional()])
    description = TextAreaField('Description')
    approval_date = DateTimeField('Approval Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    notes = TextAreaField('Notes')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save NFA')

class WorkOrderForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    po_number = StringField('PO Number')
    vendor_name = StringField('Vendor Name')
    amount = FloatField('Amount', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    description = TextAreaField('Description')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save Work Order')

class CostContractForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    contract_type = StringField('Contract Type')
    vendor_name = StringField('Vendor Name')
    contract_value = FloatField('Contract Value', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    description = TextAreaField('Description')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save Cost Contract')

class RevenueContractForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    customer_name = StringField('Customer Name')
    contract_value = FloatField('Contract Value', validators=[Optional()])
    start_date = DateTimeField('Start Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    terms = TextAreaField('Terms')
    description = TextAreaField('Description')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save Revenue Contract')

class AgreementForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    agreement_type = StringField('Agreement Type')
    party_name = StringField('Party Name')
    effective_date = DateTimeField('Effective Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    expiry_date = DateTimeField('Expiry Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    description = TextAreaField('Description')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save Agreement')

class StatutoryDocumentForm(FlaskForm):
    reference_number = StringField('Reference Number', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    document_type = StringField('Document Type')
    regulatory_body = StringField('Regulatory Body')
    due_date = DateTimeField('Due Date', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    description = TextAreaField('Description')
    attachments = FileField('Attachments', render_kw={'multiple': True})
    submit = SubmitField('Save Statutory Document')

class ApprovalForm(FlaskForm):
    action = SelectField('Action', choices=[('approve', 'Approve'), ('reject', 'Reject')], validators=[DataRequired()])
    comments = TextAreaField('Comments')
    submit = SubmitField('Submit Approval')
