from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, NFA, WorkOrder, CostContract, RevenueContract, Agreement, StatutoryDocument, Attachment, ApprovalHistory, Department, Vendor, Customer, Party
from forms import NFAForm, WorkOrderForm, CostContractForm, RevenueContractForm, AgreementForm, StatutoryDocumentForm, ApprovalForm
from utils import save_uploaded_file, get_next_reference_number, WorkflowEngine, require_permission, require_role
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

# Helper function to populate department choices based on role
def get_department_choices():
    """Get department choices based on user role"""
    user_roles = [role.name for role in current_user.roles]
    if 'admin' in user_roles:
        # Admin can see all departments
        return [(0, '-- Select Department --')] + [(d.id, f"{d.name} ({d.code})") for d in Department.query.filter_by(status='Active').all()]
    else:
        # Non-admin employees only see their current department
        if current_user.department:
            return [(current_user.department_id, f"{current_user.department.name} ({current_user.department.code})")]
        else:
            return [(0, 'No Department Assigned')]

def get_vendor_choices():
    """Get vendor choices"""
    return [(0, '-- Select Vendor --')] + [(v.id, f"{v.name} ({v.code})") for v in Vendor.query.filter_by(is_active=True).all()]

def get_customer_choices():
    """Get customer choices"""
    return [(0, '-- Select Customer --')] + [(c.id, f"{c.name} ({c.code})") for c in Customer.query.filter_by(is_active=True).all()]

def get_party_choices():
    """Get party choices"""
    return [(0, '-- Select Party --')] + [(p.id, f"{p.name} ({p.code})") for p in Party.query.filter_by(is_active=True).all()]

# Dashboard
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get statistics based on user role
    user_roles = [role.name for role in current_user.roles]
    
    # Initialize pending notifications for HOD
    pending_notifications = []
    
    # Filter based on role - viewers can only see their own created documents
    # HOD can see submitted documents pending approval
    if 'hod' in user_roles:
        # HOD sees submitted documents pending their approval
        pending_approvals = db.session.query(NFA, WorkOrder, CostContract, RevenueContract, Agreement, StatutoryDocument).filter(
            NFA.status == 'Submitted'
        ).count()
        # Count pending for all document types
        pending_nfa = NFA.query.filter_by(status='Submitted').count()
        pending_wo = WorkOrder.query.filter_by(status='Submitted').count()
        pending_cc = CostContract.query.filter_by(status='Submitted').count()
        pending_rc = RevenueContract.query.filter_by(status='Submitted').count()
        pending_ag = Agreement.query.filter_by(status='Submitted').count()
        pending_sd = StatutoryDocument.query.filter_by(status='Submitted').count()
        pending_approvals = pending_nfa + pending_wo + pending_cc + pending_rc + pending_ag + pending_sd
        
        # Get top 2 pending requests for notifications
        nfa_docs = NFA.query.filter_by(status='Submitted').order_by(NFA.created_at.desc()).limit(2).all()
        for doc in nfa_docs:
            pending_notifications.append({
                'type': 'NFA',
                'id': doc.id,
                'title': doc.title,
                'reference': doc.reference_number,
                'created_by': doc.created_by.username,
                'created_at': doc.created_at,
                'route': 'main.nfa_approval_detail'
            })
        
        if len(pending_notifications) < 2:
            wo_docs = WorkOrder.query.filter_by(status='Submitted').order_by(WorkOrder.created_at.desc()).limit(2 - len(pending_notifications)).all()
            for doc in wo_docs:
                pending_notifications.append({
                    'type': 'Work Order',
                    'id': doc.id,
                    'title': doc.title,
                    'reference': doc.reference_number,
                    'created_by': doc.created_by.username,
                    'created_at': doc.created_at,
                    'route': 'main.work_order_approval_detail'
                })
        
        if len(pending_notifications) < 2:
            cc_docs = CostContract.query.filter_by(status='Submitted').order_by(CostContract.created_at.desc()).limit(2 - len(pending_notifications)).all()
            for doc in cc_docs:
                pending_notifications.append({
                    'type': 'Cost Contract',
                    'id': doc.id,
                    'title': doc.title,
                    'reference': doc.reference_number,
                    'created_by': doc.created_by.username,
                    'created_at': doc.created_at,
                    'route': 'main.cost_contract_approval_detail'
                })
        
        if len(pending_notifications) < 2:
            rc_docs = RevenueContract.query.filter_by(status='Submitted').order_by(RevenueContract.created_at.desc()).limit(2 - len(pending_notifications)).all()
            for doc in rc_docs:
                pending_notifications.append({
                    'type': 'Revenue Contract',
                    'id': doc.id,
                    'title': doc.title,
                    'reference': doc.reference_number,
                    'created_by': doc.created_by.username,
                    'created_at': doc.created_at,
                    'route': 'main.revenue_contract_approval_detail'
                })
        
        if len(pending_notifications) < 2:
            ag_docs = Agreement.query.filter_by(status='Submitted').order_by(Agreement.created_at.desc()).limit(2 - len(pending_notifications)).all()
            for doc in ag_docs:
                pending_notifications.append({
                    'type': 'Agreement',
                    'id': doc.id,
                    'title': doc.title,
                    'reference': doc.reference_number,
                    'created_by': doc.created_by.username,
                    'created_at': doc.created_at,
                    'route': 'main.agreement_approval_detail'
                })
        
        if len(pending_notifications) < 2:
            sd_docs = StatutoryDocument.query.filter_by(status='Submitted').order_by(StatutoryDocument.created_at.desc()).limit(2 - len(pending_notifications)).all()
            for doc in sd_docs:
                pending_notifications.append({
                    'type': 'Statutory Document',
                    'id': doc.id,
                    'title': doc.title,
                    'reference': doc.reference_number,
                    'created_by': doc.created_by.username,
                    'created_at': doc.created_at,
                    'route': 'main.statutory_document_approval_detail'
                })
    elif 'reviewer' in user_roles:
        pending_approvals = 0
    else:
        pending_approvals = 0
    
    # Get counts - restrict for non-admin users
    if 'admin' not in user_roles and 'hod' not in user_roles:
        # Regular users - count by status
        # Draft documents
        draft_nfa = NFA.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_wo = WorkOrder.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_cc = CostContract.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_rc = RevenueContract.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_ag = Agreement.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_sd = StatutoryDocument.query.filter_by(created_by_id=current_user.id, status='Draft').count()
        draft_count = draft_nfa + draft_wo + draft_cc + draft_rc + draft_ag + draft_sd
        
        # Pending Review (Submitted) documents
        pending_nfa = NFA.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_wo = WorkOrder.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_cc = CostContract.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_rc = RevenueContract.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_ag = Agreement.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_sd = StatutoryDocument.query.filter_by(created_by_id=current_user.id, status='Submitted').count()
        pending_review_count = pending_nfa + pending_wo + pending_cc + pending_rc + pending_ag + pending_sd
        
        # Approved documents
        approved_nfa = NFA.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_wo = WorkOrder.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_cc = CostContract.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_rc = RevenueContract.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_ag = Agreement.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_sd = StatutoryDocument.query.filter_by(created_by_id=current_user.id, status='Approved').count()
        approved_count = approved_nfa + approved_wo + approved_cc + approved_rc + approved_ag + approved_sd
        
        # Total documents
        total_nfa = NFA.query.filter_by(created_by_id=current_user.id).count()
        total_wo = WorkOrder.query.filter_by(created_by_id=current_user.id).count()
        total_cc = CostContract.query.filter_by(created_by_id=current_user.id).count()
        total_rc = RevenueContract.query.filter_by(created_by_id=current_user.id).count()
        total_ag = Agreement.query.filter_by(created_by_id=current_user.id).count()
        total_sd = StatutoryDocument.query.filter_by(created_by_id=current_user.id).count()
        total_docs = total_nfa + total_wo + total_cc + total_rc + total_ag + total_sd
        
        nfa_count = total_docs
        work_order_count = draft_count
        cost_contract_count = approved_count
        revenue_contract_count = 0
        agreement_count = 0
        statutory_doc_count = 0
        pending_approvals = pending_review_count
    elif 'hod' in user_roles:
        # HOD sees submitted documents (pending approval) and approved documents
        nfa_count = NFA.query.filter(NFA.status.in_(['Submitted', 'Approved'])).count()
        work_order_count = WorkOrder.query.filter(WorkOrder.status.in_(['Submitted', 'Approved'])).count()
        cost_contract_count = CostContract.query.filter(CostContract.status.in_(['Submitted', 'Approved'])).count()
        revenue_contract_count = RevenueContract.query.filter(RevenueContract.status.in_(['Submitted', 'Approved'])).count()
        agreement_count = Agreement.query.filter(Agreement.status.in_(['Submitted', 'Approved'])).count()
        statutory_doc_count = StatutoryDocument.query.filter(StatutoryDocument.status.in_(['Submitted', 'Approved'])).count()
    else:
        # Admins see all documents
        nfa_count = NFA.query.count()
        work_order_count = WorkOrder.query.count()
        cost_contract_count = CostContract.query.count()
        revenue_contract_count = RevenueContract.query.count()
        agreement_count = Agreement.query.count()
        statutory_doc_count = StatutoryDocument.query.count()
    
    stats = {
        'nfa': nfa_count,
        'work_orders': work_order_count,
        'cost_contracts': cost_contract_count,
        'revenue_contracts': revenue_contract_count,
        'agreements': agreement_count,
        'statutory_docs': statutory_doc_count,
        'pending_approvals': pending_approvals,
        'user_roles': user_roles
    }
    
    return render_template('dashboard.html', stats=stats, pending_notifications=pending_notifications)

# ============ HOD Approval Requests ============
@main_bp.route('/approval-requests', methods=['GET'])
@login_required
def approval_requests():
    """View all pending approval requests for HOD"""
    user_roles = [role.name for role in current_user.roles]
    if 'hod' not in user_roles and 'admin' not in user_roles:
        flash('You do not have permission to access approval requests', 'danger')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    doc_type = request.args.get('type', '', type=str)
    
    # Collect all pending documents from all types
    pending_docs = []
    
    # For HOD: only get documents from their department
    # For Admin: get all documents
    if 'hod' in user_roles and 'admin' not in user_roles:
        # HOD - filter by department
        nfa_docs = NFA.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in nfa_docs:
            pending_docs.append({'type': 'NFA', 'doc': doc, 'id': doc.id})
        
        wo_docs = WorkOrder.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in wo_docs:
            pending_docs.append({'type': 'Work Order', 'doc': doc, 'id': doc.id})
        
        cc_docs = CostContract.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in cc_docs:
            pending_docs.append({'type': 'Cost Contract', 'doc': doc, 'id': doc.id})
        
        rc_docs = RevenueContract.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in rc_docs:
            pending_docs.append({'type': 'Revenue Contract', 'doc': doc, 'id': doc.id})
        
        ag_docs = Agreement.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in ag_docs:
            pending_docs.append({'type': 'Agreement', 'doc': doc, 'id': doc.id})
        
        sd_docs = StatutoryDocument.query.filter_by(status='Submitted', department_id=current_user.department_id).all()
        for doc in sd_docs:
            pending_docs.append({'type': 'Statutory Document', 'doc': doc, 'id': doc.id})
    else:
        # Admin - get all submitted documents
        nfa_docs = NFA.query.filter_by(status='Submitted').all()
        for doc in nfa_docs:
            pending_docs.append({'type': 'NFA', 'doc': doc, 'id': doc.id})
        
        wo_docs = WorkOrder.query.filter_by(status='Submitted').all()
        for doc in wo_docs:
            pending_docs.append({'type': 'Work Order', 'doc': doc, 'id': doc.id})
        
        cc_docs = CostContract.query.filter_by(status='Submitted').all()
        for doc in cc_docs:
            pending_docs.append({'type': 'Cost Contract', 'doc': doc, 'id': doc.id})
        
        rc_docs = RevenueContract.query.filter_by(status='Submitted').all()
        for doc in rc_docs:
            pending_docs.append({'type': 'Revenue Contract', 'doc': doc, 'id': doc.id})
        
        ag_docs = Agreement.query.filter_by(status='Submitted').all()
        for doc in ag_docs:
            pending_docs.append({'type': 'Agreement', 'doc': doc, 'id': doc.id})
        
        sd_docs = StatutoryDocument.query.filter_by(status='Submitted').all()
        for doc in sd_docs:
            pending_docs.append({'type': 'Statutory Document', 'doc': doc, 'id': doc.id})
    
    # Filter by document type if specified
    if doc_type:
        pending_docs = [d for d in pending_docs if d['type'].lower().replace(' ', '-') == doc_type.lower().replace(' ', '-')]
    
    # Sort by created date (newest first)
    pending_docs.sort(key=lambda x: x['doc'].created_at, reverse=True)
    
    return render_template('pages/approval_requests.html', pending_docs=pending_docs)

# ============ NFA Routes ============
@main_bp.route('/nfa', methods=['GET'])
@login_required
def nfa_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = NFA.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(NFA.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(NFA.status.in_(['Submitted', 'Approved']), NFA.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(NFA.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    
    return render_template('pages/nfa_list.html', items=items)

@main_bp.route('/nfa/create', methods=['GET', 'POST'])
@login_required
def nfa_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    form = NFAForm()
    form.department_id.choices = get_department_choices()
    
    # Populate vendor and customer choices
    form.vendor_id.choices = get_vendor_choices()
    form.customer_id.choices = get_customer_choices()
    
    if form.validate_on_submit():
        # Check if at least one attachment is provided for new documents
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            from wtforms.validators import ValidationError
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/nfa_form.html', form=form, title='Create NFA')
        
        # Use provided reference_number or auto-generate one
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('NFA')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        nfa = NFA(
            reference_number=reference_number,
            title=form.title.data,
            amount=form.amount.data,
            description=form.description.data,
            approval_date=form.approval_date.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
            department_id=department_id,
            vendor_id=form.vendor_id.data if form.vendor_id.data else None,
            customer_id=form.customer_id.data if form.customer_id.data else None
        )
        
        db.session.add(nfa)
        db.session.flush()
        
        # Handle file uploads
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            nfa_id=nfa.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('NFA created successfully!', 'success')
        return redirect(url_for('main.nfa_view', id=nfa.id))
    
    return render_template('pages/nfa_form.html', form=form, title='Create NFA')

@main_bp.route('/nfa/<int:id>/view', methods=['GET'])
@login_required
def nfa_view(id):
    nfa = NFA.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(nfa_id=id).all()
    can_edit = (nfa.status != 'Approved' and (nfa.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (nfa.status == 'Approved' and current_user.has_role('admin'))
    
    return render_template('pages/nfa_view.html', nfa=nfa, approvals=approvals, can_edit=can_edit)

@main_bp.route('/nfa/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def nfa_edit(id):
    print(f"\n{'='*60}")
    print(f"DEBUG: nfa_edit called with id={id}, method={request.method}")
    print(f"DEBUG: All form data keys: {list(request.form.keys())}")
    print(f"DEBUG: All request files: {list(request.files.keys())}")
    print(f"{'='*60}")
    
    nfa = NFA.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if nfa.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.nfa_view', id=id))
    
    form = NFAForm()
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating) 
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # IMPORTANT: Set choices BEFORE validation
    form.department_id.choices = get_department_choices()
    
    # Populate vendor and customer choices
    form.vendor_id.choices = get_vendor_choices()
    form.customer_id.choices = get_customer_choices()
    
    print(f"DEBUG: Form choices set. department_id={len(form.department_id.choices)}, vendor_id={len(form.vendor_id.choices)}, customer_id={len(form.customer_id.choices)}")
    print(f"DEBUG: form.validate_on_submit() = {form.validate_on_submit()}")
    if request.method == 'POST':
        print(f"DEBUG: POST request form validation errors: {form.errors}")
    
    if form.validate_on_submit():
        print(f"DEBUG: Form validated successfully")
        print(f"DEBUG: Request form keys: {list(request.form.keys())}")
        
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(nfa.attachments)
        
        print(f"DEBUG: has_files={has_files}, has_existing={has_existing}, existing attachments count={len(nfa.attachments)}")
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            print(f"DEBUG: No files and no existing attachments - returning form")
            return render_template('pages/nfa_form.html', form=form, nfa=nfa, title='Edit NFA')
        
        nfa.title = form.title.data
        nfa.amount = form.amount.data
        nfa.description = form.description.data
        nfa.approval_date = form.approval_date.data
        nfa.notes = form.notes.data
        nfa.vendor_id = form.vendor_id.data if form.vendor_id.data else None
        nfa.customer_id = form.customer_id.data if form.customer_id.data else None
        
        print(f"DEBUG: NFA fields updated - title={nfa.title}")
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        print(f"DEBUG: Found attachment replacement keys: {attachment_keys}")
        
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            print(f"DEBUG: Processing key {key} with old_attachment_id: {old_attachment_id}")
            
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                print(f"DEBUG: new_file_path for {old_attachment_id}: {new_file_path}")
                
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        print(f"DEBUG: Found old attachment: {old_attachment}")
                        
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                                print(f"DEBUG: Deleted file: {old_attachment.file_path}")
                            db.session.delete(old_attachment)
                            print(f"DEBUG: Deleted attachment from DB")
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            nfa_id=nfa.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                        print(f"DEBUG: Created new attachment: {new_file_path}")
                    except Exception as e:
                        print(f"DEBUG: Error replacing attachment: {str(e)}")
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            print(f"DEBUG: Processing new file uploads")
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            nfa_id=nfa.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
                        print(f"DEBUG: Added new attachment from file upload: {file_path}")
        
        try:
            db.session.commit()
            print(f"DEBUG: NFA edit committed successfully for ID: {id}")
            flash('NFA updated successfully!', 'success')
            return redirect(url_for('main.nfa_view', id=nfa.id))
        except Exception as e:
            print(f"DEBUG: Error during commit: {str(e)}")
            db.session.rollback()
            flash(f'Error saving NFA: {str(e)}', 'danger')
            return render_template('pages/nfa_form.html', form=form, nfa=nfa, title='Edit NFA')
    else:
        # POST validation failed - populate form with existing data for re-display
        print(f"DEBUG: Form validation failed on POST")
        form.title.data = nfa.title
        form.amount.data = nfa.amount
        form.description.data = nfa.description
        form.approval_date.data = nfa.approval_date
        form.notes.data = nfa.notes
        form.vendor_id.data = nfa.vendor_id if nfa.vendor_id else 0
        form.customer_id.data = nfa.customer_id if nfa.customer_id else 0
        form.department_id.data = nfa.department_id if nfa.department_id else 0
    
    if request.method == 'GET':
        print(f"DEBUG: GET request - populating form with existing data")
        form.title.data = nfa.title
        form.amount.data = nfa.amount
        form.description.data = nfa.description
        form.approval_date.data = nfa.approval_date
        form.notes.data = nfa.notes
        form.vendor_id.data = nfa.vendor_id if nfa.vendor_id else 0
        form.customer_id.data = nfa.customer_id if nfa.customer_id else 0
        form.department_id.data = nfa.department_id if nfa.department_id else 0
    
    print(f"DEBUG: Rendering nfa_form.html")
    return render_template('pages/nfa_form.html', form=form, nfa=nfa, title='Edit NFA')

@main_bp.route('/nfa/<int:id>/submit', methods=['POST'])
@login_required
def nfa_submit(id):
    nfa = NFA.query.get_or_404(id)
    
    if nfa.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.nfa_view', id=id))
    
    nfa.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        nfa_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('NFA submitted for approval!', 'success')
    return redirect(url_for('main.nfa_view', id=id))

@main_bp.route('/nfa/<int:id>/approval-detail', methods=['GET'])
@login_required
def nfa_approval_detail(id):
    """Show NFA approval detail page for HOD"""
    nfa = NFA.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    # Check if user has permission to approve (only HOD)
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.nfa_view', id=id))
    
    # Check if document is in Submitted status
    if nfa.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.nfa_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/nfa_approval_detail.html', nfa=nfa, form=form)

@main_bp.route('/nfa/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def nfa_approve(id):
    nfa = NFA.query.get_or_404(id)
    form = ApprovalForm()
    
    if nfa.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.nfa_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(nfa, current_user, 'NFA', form.comments.data)
            flash('NFA approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(nfa, current_user, 'NFA', form.comments.data)
            flash('NFA rejected!', 'warning')
        
        return redirect(url_for('main.nfa_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=nfa, module='NFA')

# ============ Work Order Routes ============
@main_bp.route('/work-orders', methods=['GET'])
@login_required
def work_order_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = WorkOrder.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(WorkOrder.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(WorkOrder.status.in_(['Submitted', 'Approved']), WorkOrder.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(WorkOrder.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    
    return render_template('pages/work_order_list.html', items=items)

@main_bp.route('/work-orders/create', methods=['GET', 'POST'])
@login_required
def work_order_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    from models import Vendor
    form = WorkOrderForm()
    # Populate vendor and department choices
    form.vendor_id.choices = [(0, '-- Select Vendor --')] + [(v.id, f"{v.code} - {v.name}") for v in Vendor.query.filter_by(is_active=True).all()]
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if files are being uploaded
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/work_order_form.html', form=form, title='Create Work Order')
        
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('WorkOrder')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        work_order = WorkOrder(
            reference_number=reference_number,
            title=form.title.data,
            wo_po_number=form.wo_po_number.data,
            vendor_id=form.vendor_id.data if form.vendor_id.data else None,
            amount=form.amount.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            created_by_id=current_user.id,
            department_id=department_id
        )
        
        db.session.add(work_order)
        db.session.flush()
        
        # Handle file uploads
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            work_order_id=work_order.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Work Order created successfully!', 'success')
        return redirect(url_for('main.work_order_view', id=work_order.id))
    
    return render_template('pages/work_order_form.html', form=form, title='Create Work Order')

@main_bp.route('/work-orders/<int:id>/view', methods=['GET'])
@login_required
def work_order_view(id):
    work_order = WorkOrder.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(work_order_id=id).all()
    can_edit = (work_order.status != 'Approved' and (work_order.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (work_order.status == 'Approved' and current_user.has_role('admin'))
    
    return render_template('pages/work_order_view.html', work_order=work_order, approvals=approvals, can_edit=can_edit)

@main_bp.route('/work-orders/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def work_order_edit(id):
    from models import Vendor
    work_order = WorkOrder.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if work_order.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.work_order_view', id=id))
    
    form = WorkOrderForm(obj=work_order)
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating)
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # Populate vendor and department choices
    form.vendor_id.choices = [(0, '-- Select Vendor --')] + [(v.id, f"{v.code} - {v.name}") for v in Vendor.query.filter_by(is_active=True).all()]
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(work_order.attachments)
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/work_order_form.html', form=form, work_order=work_order, title='Edit Work Order')
        
        work_order.title = form.title.data
        work_order.wo_po_number = form.wo_po_number.data
        work_order.vendor_id = form.vendor_id.data if form.vendor_id.data else None
        work_order.amount = form.amount.data
        work_order.start_date = form.start_date.data
        work_order.end_date = form.end_date.data
        work_order.description = form.description.data
        work_order.department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                            db.session.delete(old_attachment)
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            work_order_id=work_order.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                    except Exception as e:
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            work_order_id=work_order.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Work Order updated successfully!', 'success')
        return redirect(url_for('main.work_order_view', id=work_order.id))
    
    return render_template('pages/work_order_form.html', form=form, work_order=work_order, title='Edit Work Order')

@main_bp.route('/work-orders/<int:id>/submit', methods=['POST'])
@login_required
def work_order_submit(id):
    work_order = WorkOrder.query.get_or_404(id)
    
    if work_order.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.work_order_view', id=id))
    
    work_order.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        work_order_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('Work Order submitted for approval!', 'success')
    return redirect(url_for('main.work_order_view', id=id))

@main_bp.route('/cost-contracts/<int:id>/submit', methods=['POST'])
@login_required
def cost_contract_submit(id):
    cost_contract = CostContract.query.get_or_404(id)
    
    if cost_contract.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    cost_contract.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        cost_contract_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('Cost Contract submitted for approval!', 'success')
    return redirect(url_for('main.cost_contract_view', id=id))

@main_bp.route('/revenue-contracts/<int:id>/submit', methods=['POST'])
@login_required
def revenue_contract_submit(id):
    revenue_contract = RevenueContract.query.get_or_404(id)
    
    if revenue_contract.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    revenue_contract.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        revenue_contract_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('Revenue Contract submitted for approval!', 'success')
    return redirect(url_for('main.revenue_contract_view', id=id))

@main_bp.route('/agreements/<int:id>/submit', methods=['POST'])
@login_required
def agreement_submit(id):
    agreement = Agreement.query.get_or_404(id)
    
    if agreement.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.agreement_view', id=id))
    
    agreement.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        agreement_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('Agreement submitted for approval!', 'success')
    return redirect(url_for('main.agreement_view', id=id))

@main_bp.route('/statutory-documents/<int:id>/submit', methods=['POST'])
@login_required
def statutory_document_submit(id):
    statutory_document = StatutoryDocument.query.get_or_404(id)
    
    if statutory_document.status not in ['Draft', 'Rejected']:
        flash('Document is not in Draft or Rejected status', 'warning')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    statutory_document.status = 'Submitted'
    history = ApprovalHistory(
        action='Submitted',
        approved_by_id=current_user.id,
        statutory_document_id=id
    )
    
    db.session.add(history)
    db.session.commit()
    
    flash('Statutory Document submitted for approval!', 'success')
    return redirect(url_for('main.statutory_document_view', id=id))

@main_bp.route('/work-orders/<int:id>/approval-detail', methods=['GET'])
@login_required
def work_order_approval_detail(id):
    """Show Work Order approval detail page for HOD"""
    work_order = WorkOrder.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.work_order_view', id=id))
    
    if work_order.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.work_order_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/work_order_approval_detail.html', work_order=work_order, form=form)

@main_bp.route('/work-orders/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def work_order_approve(id):
    work_order = WorkOrder.query.get_or_404(id)
    form = ApprovalForm()
    
    if work_order.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.work_order_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(work_order, current_user, 'WorkOrder', form.comments.data)
            flash('Work Order approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(work_order, current_user, 'WorkOrder', form.comments.data)
            flash('Work Order rejected!', 'warning')
        
        return redirect(url_for('main.work_order_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=work_order, module='Work Order')

# ============ Cost Contract Routes ============
@main_bp.route('/cost-contracts/<int:id>/approval-detail', methods=['GET'])
@login_required
def cost_contract_approval_detail(id):
    """Show Cost Contract approval detail page for HOD"""
    cost_contract = CostContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    if cost_contract.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/cost_contract_approval_detail.html', cost_contract=cost_contract, form=form)

@main_bp.route('/cost-contracts/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def cost_contract_approve(id):
    cost_contract = CostContract.query.get_or_404(id)
    form = ApprovalForm()
    
    if cost_contract.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(cost_contract, current_user, 'CostContract', form.comments.data)
            flash('Cost Contract approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(cost_contract, current_user, 'CostContract', form.comments.data)
            flash('Cost Contract rejected!', 'warning')
        
        return redirect(url_for('main.cost_contract_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=cost_contract, module='Cost Contract')

# ============ Revenue Contract Routes ============
@main_bp.route('/revenue-contracts/<int:id>/approval-detail', methods=['GET'])
@login_required
def revenue_contract_approval_detail(id):
    """Show Revenue Contract approval detail page for HOD"""
    revenue_contract = RevenueContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    if revenue_contract.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/revenue_contract_approval_detail.html', revenue_contract=revenue_contract, form=form)

@main_bp.route('/revenue-contracts/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def revenue_contract_approve(id):
    revenue_contract = RevenueContract.query.get_or_404(id)
    form = ApprovalForm()
    
    if revenue_contract.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(revenue_contract, current_user, 'RevenueContract', form.comments.data)
            flash('Revenue Contract approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(revenue_contract, current_user, 'RevenueContract', form.comments.data)
            flash('Revenue Contract rejected!', 'warning')
        
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=revenue_contract, module='Revenue Contract')

# ============ Agreement Routes ============
@main_bp.route('/agreements/<int:id>/approval-detail', methods=['GET'])
@login_required
def agreement_approval_detail(id):
    """Show Agreement approval detail page for HOD"""
    agreement = Agreement.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.agreement_view', id=id))
    
    if agreement.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.agreement_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/agreement_approval_detail.html', agreement=agreement, form=form)

@main_bp.route('/agreements/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def agreement_approve(id):
    agreement = Agreement.query.get_or_404(id)
    form = ApprovalForm()
    
    if agreement.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.agreement_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(agreement, current_user, 'Agreement', form.comments.data)
            flash('Agreement approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(agreement, current_user, 'Agreement', form.comments.data)
            flash('Agreement rejected!', 'warning')
        
        return redirect(url_for('main.agreement_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=agreement, module='Agreement')

# ============ Statutory Document Routes ============
@main_bp.route('/statutory-documents/<int:id>/approval-detail', methods=['GET'])
@login_required
def statutory_document_approval_detail(id):
    """Show Statutory Document approval detail page for HOD"""
    statutory_document = StatutoryDocument.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if 'hod' not in user_roles:
        flash('You do not have permission to approve documents', 'danger')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    if statutory_document.status != 'Submitted':
        flash('This document is not pending approval', 'warning')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    form = ApprovalForm()
    return render_template('pages/statutory_document_approval_detail.html', statutory_document=statutory_document, form=form)

@main_bp.route('/statutory-documents/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def statutory_document_approve(id):
    statutory_document = StatutoryDocument.query.get_or_404(id)
    form = ApprovalForm()
    
    if statutory_document.status == 'Draft':
        flash('Cannot approve a document in Draft status', 'warning')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            WorkflowEngine.approve_document(statutory_document, current_user, 'StatutoryDocument', form.comments.data)
            flash('Statutory Document approved successfully!', 'success')
        else:
            WorkflowEngine.reject_document(statutory_document, current_user, 'StatutoryDocument', form.comments.data)
            flash('Statutory Document rejected!', 'warning')
        
        return redirect(url_for('main.statutory_document_view', id=id))
    
    return render_template('pages/approve_form.html', form=form, document=statutory_document, module='Statutory Document')

# ============ Cost Contract Routes ============
@main_bp.route('/cost-contracts', methods=['GET'])
@login_required
def cost_contract_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = CostContract.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(CostContract.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(CostContract.status.in_(['Submitted', 'Approved']), CostContract.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(CostContract.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/cost_contract_list.html', items=items)

@main_bp.route('/cost-contracts/create', methods=['GET', 'POST'])
@login_required
def cost_contract_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    form = CostContractForm()
    # Populate vendor, customer and department dropdown
    form.vendor_id.choices = get_vendor_choices()
    form.customer_id.choices = get_customer_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if files are being uploaded
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/cost_contract_form.html', form=form, title='Create Cost Contract')
        
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('CostContract')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        contract = CostContract(
            reference_number=reference_number,
            title=form.title.data,
            vendor_id=form.vendor_id.data if form.vendor_id.data else None,
            customer_id=form.customer_id.data if form.customer_id.data else None,
            contract_value=form.contract_value.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            created_by_id=current_user.id,
            department_id=department_id
        )
        
        db.session.add(contract)
        db.session.flush()
        
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            cost_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Cost Contract created successfully!', 'success')
        return redirect(url_for('main.cost_contract_view', id=contract.id))
    
    return render_template('pages/cost_contract_form.html', form=form, title='Create Cost Contract')

@main_bp.route('/cost-contracts/<int:id>/view', methods=['GET'])
@login_required
def cost_contract_view(id):
    contract = CostContract.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(cost_contract_id=id).all()
    can_edit = (contract.status != 'Approved' and (contract.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (contract.status == 'Approved' and current_user.has_role('admin'))
    return render_template('pages/cost_contract_view.html', contract=contract, approvals=approvals, can_edit=can_edit)

@main_bp.route('/cost-contracts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def cost_contract_edit(id):
    contract = CostContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if contract.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    form = CostContractForm(obj=contract)
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating)
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # Populate vendor, customer and department choices
    form.vendor_id.choices = get_vendor_choices()
    form.customer_id.choices = get_customer_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(contract.attachments)
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/cost_contract_form.html', form=form, contract=contract, title='Edit Cost Contract')
        
        contract.title = form.title.data
        contract.vendor_id = form.vendor_id.data if form.vendor_id.data else None
        contract.customer_id = form.customer_id.data if form.customer_id.data else None
        contract.contract_value = form.contract_value.data
        contract.start_date = form.start_date.data
        contract.end_date = form.end_date.data
        contract.description = form.description.data
        contract.department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                            db.session.delete(old_attachment)
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            cost_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                    except Exception as e:
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            cost_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Cost Contract updated successfully!', 'success')
        return redirect(url_for('main.cost_contract_view', id=contract.id))
    
    return render_template('pages/cost_contract_form.html', form=form, contract=contract, title='Edit Cost Contract')

@main_bp.route('/revenue-contracts', methods=['GET'])
@login_required
def revenue_contract_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = RevenueContract.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(RevenueContract.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(RevenueContract.status.in_(['Submitted', 'Approved']), RevenueContract.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(RevenueContract.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/revenue_contract_list.html', items=items)

@main_bp.route('/revenue-contracts/create', methods=['GET', 'POST'])
@login_required
def revenue_contract_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    form = RevenueContractForm()
    # Populate customer and department dropdown
    form.customer_id.choices = get_customer_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if files are being uploaded
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/revenue_contract_form.html', form=form, title='Create Revenue Contract')
        
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('RevenueContract')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        contract = RevenueContract(
            reference_number=reference_number,
            title=form.title.data,
            customer_id=form.customer_id.data if form.customer_id.data else None,
            customer_name=form.customer_name.data,
            contract_value=form.contract_value.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            terms=form.terms.data,
            description=form.description.data,
            created_by_id=current_user.id,
            department_id=department_id
        )
        
        db.session.add(contract)
        db.session.flush()
        
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            revenue_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Revenue Contract created successfully!', 'success')
        return redirect(url_for('main.revenue_contract_view', id=contract.id))
    
    return render_template('pages/revenue_contract_form.html', form=form, title='Create Revenue Contract')

@main_bp.route('/revenue-contracts/<int:id>/view', methods=['GET'])
@login_required
def revenue_contract_view(id):
    contract = RevenueContract.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(revenue_contract_id=id).all()
    can_edit = (contract.status != 'Approved' and (contract.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (contract.status == 'Approved' and current_user.has_role('admin'))
    return render_template('pages/revenue_contract_view.html', contract=contract, approvals=approvals, can_edit=can_edit)

@main_bp.route('/revenue-contracts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def revenue_contract_edit(id):
    contract = RevenueContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if contract.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    form = RevenueContractForm(obj=contract)
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating)
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # Populate customer and department choices
    form.customer_id.choices = get_customer_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(contract.attachments)
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/revenue_contract_form.html', form=form, contract=contract, title='Edit Revenue Contract')
        
        contract.title = form.title.data
        contract.customer_id = form.customer_id.data if form.customer_id.data else None
        contract.customer_name = form.customer_name.data
        contract.contract_value = form.contract_value.data
        contract.start_date = form.start_date.data
        contract.end_date = form.end_date.data
        contract.terms = form.terms.data
        contract.description = form.description.data
        contract.department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                            db.session.delete(old_attachment)
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            revenue_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                    except Exception as e:
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            revenue_contract_id=contract.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Revenue Contract updated successfully!', 'success')
        return redirect(url_for('main.revenue_contract_view', id=contract.id))
    
    return render_template('pages/revenue_contract_form.html', form=form, contract=contract, title='Edit Revenue Contract')

# ============ Agreement Routes ============
@main_bp.route('/agreements', methods=['GET'])
@login_required
def agreement_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = Agreement.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(Agreement.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(Agreement.status.in_(['Submitted', 'Approved']), Agreement.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Agreement.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/agreement_list.html', items=items)

@main_bp.route('/agreements/create', methods=['GET', 'POST'])
@login_required
def agreement_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    form = AgreementForm()
    # Populate customer, party and department dropdown
    form.customer_id.choices = get_customer_choices()
    form.party_id.choices = get_party_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if files are being uploaded
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/agreement_form.html', form=form, title='Create Agreement')
        
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('Agreement')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        agreement = Agreement(
            reference_number=reference_number,
            title=form.title.data,
            customer_id=form.customer_id.data if form.customer_id.data else None,
            party_id=form.party_id.data if form.party_id.data else None,
            effective_date=form.effective_date.data,
            expiry_date=form.expiry_date.data,
            description=form.description.data,
            created_by_id=current_user.id,
            department_id=department_id
        )
        
        db.session.add(agreement)
        db.session.flush()
        
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            agreement_id=agreement.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Agreement created successfully!', 'success')
        return redirect(url_for('main.agreement_view', id=agreement.id))
    
    return render_template('pages/agreement_form.html', form=form, title='Create Agreement')

@main_bp.route('/agreements/<int:id>/view', methods=['GET'])
@login_required
def agreement_view(id):
    agreement = Agreement.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(agreement_id=id).all()
    can_edit = (agreement.status != 'Approved' and (agreement.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (agreement.status == 'Approved' and current_user.has_role('admin'))
    return render_template('pages/agreement_view.html', agreement=agreement, approvals=approvals, can_edit=can_edit)

@main_bp.route('/agreements/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def agreement_edit(id):
    agreement = Agreement.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if agreement.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.agreement_view', id=id))
    
    form = AgreementForm(obj=agreement)
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating)
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # Populate customer, party and department choices
    form.customer_id.choices = get_customer_choices()
    form.party_id.choices = get_party_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(agreement.attachments)
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/agreement_form.html', form=form, agreement=agreement, title='Edit Agreement')
        
        agreement.title = form.title.data
        agreement.customer_id = form.customer_id.data if form.customer_id.data else None
        agreement.party_id = form.party_id.data if form.party_id.data else None
        agreement.effective_date = form.effective_date.data
        agreement.expiry_date = form.expiry_date.data
        agreement.description = form.description.data
        agreement.department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                            db.session.delete(old_attachment)
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            agreement_id=agreement.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                    except Exception as e:
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            agreement_id=agreement.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Agreement updated successfully!', 'success')
        return redirect(url_for('main.agreement_view', id=agreement.id))
    
    return render_template('pages/agreement_form.html', form=form, agreement=agreement, title='Edit Agreement')

@main_bp.route('/statutory-documents', methods=['GET'])
@login_required
def statutory_document_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = StatutoryDocument.query
    user_roles = [role.name for role in current_user.roles]
    
    # Role-based filtering
    if 'admin' in user_roles:
        # Admin sees only approved documents
        query = query.filter(StatutoryDocument.status == 'Approved')
    elif 'hod' in user_roles:
        # HOD sees submitted and approved documents from their department
        query = query.filter(StatutoryDocument.status.in_(['Submitted', 'Approved']), StatutoryDocument.department_id == current_user.department_id)
    else:
        # Regular users only see their own documents from their department
        query = query.filter_by(created_by_id=current_user.id, department_id=current_user.department_id)
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(StatutoryDocument.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/statutory_document_list.html', items=items)

@main_bp.route('/statutory-documents/create', methods=['GET', 'POST'])
@login_required
def statutory_document_create():
    # HOD cannot create documents
    if current_user.has_role('hod'):
        flash('Head of Departments can only review and approve documents, not create them.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    form = StatutoryDocumentForm()
    # Populate party and department dropdown
    form.party_id.choices = get_party_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if files are being uploaded
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        if not has_files:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/statutory_document_form.html', form=form, title='Create Statutory Document')
        
        reference_number = form.reference_number.data if form.reference_number.data else get_next_reference_number('StatutoryDocument')
        # Use selected department or current user's department
        department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        document = StatutoryDocument(
            reference_number=reference_number,
            title=form.title.data,
            document_type=form.document_type.data,
            regulatory_body=form.regulatory_body.data,
            party_id=form.party_id.data if form.party_id.data else None,
            due_date=form.due_date.data,
            description=form.description.data,
            created_by_id=current_user.id,
            department_id=department_id
        )
        
        db.session.add(document)
        db.session.flush()
        
        if request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            statutory_document_id=document.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Statutory Document created successfully!', 'success')
        return redirect(url_for('main.statutory_document_view', id=document.id))
    
    return render_template('pages/statutory_document_form.html', form=form, title='Create Statutory Document')

@main_bp.route('/statutory-documents/<int:id>/view', methods=['GET'])
@login_required
def statutory_document_view(id):
    document = StatutoryDocument.query.get_or_404(id)
    approvals = ApprovalHistory.query.filter_by(statutory_document_id=id).all()
    can_edit = (document.status != 'Approved' and (document.created_by_id == current_user.id or current_user.has_permission('edit_all'))) or (document.status == 'Approved' and current_user.has_role('admin'))
    return render_template('pages/statutory_document_view.html', document=document, approvals=approvals, can_edit=can_edit)

@main_bp.route('/statutory-documents/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def statutory_document_edit(id):
    document = StatutoryDocument.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if document.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot edit an approved document', 'warning')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    form = StatutoryDocumentForm(obj=document)
    
    # Remove UniqueReferenceNumber validator on POST (for edit, not creating)
    if request.method == 'POST':
        from forms import UniqueReferenceNumber
        form.reference_number.validators = [v for v in form.reference_number.validators if not isinstance(v, UniqueReferenceNumber)]
    
    # Populate party and department choices
    form.party_id.choices = get_party_choices()
    form.department_id.choices = get_department_choices()
    
    if form.validate_on_submit():
        # Check if new files are being uploaded or if existing attachments exist
        files_list = request.files.getlist('attachments') if request.files else []
        has_files = bool(files_list and files_list[0])
        has_existing = bool(document.attachments)
        
        if not has_files and not has_existing:
            form.attachments.errors = ['At least one attachment is required.']
            return render_template('pages/statutory_document_form.html', form=form, document=document, title='Edit Statutory Document')
        
        document.title = form.title.data
        document.document_type = form.document_type.data
        document.regulatory_body = form.regulatory_body.data
        document.party_id = form.party_id.data if form.party_id.data else None
        document.due_date = form.due_date.data
        document.description = form.description.data
        document.department_id = form.department_id.data if form.department_id.data else current_user.department_id
        
        # Handle attachment replacements from hidden fields
        attachment_keys = [key for key in request.form.keys() if key.startswith('old_attachment_id_')]
        for key in attachment_keys:
            old_attachment_id = request.form.get(key)
            if old_attachment_id:
                new_file_path = request.form.get(f"new_attachment_filename_{old_attachment_id}")
                if new_file_path:
                    try:
                        # Delete old attachment
                        old_attachment = Attachment.query.get(int(old_attachment_id))
                        if old_attachment:
                            if os.path.exists(old_attachment.file_path):
                                os.remove(old_attachment.file_path)
                            db.session.delete(old_attachment)
                        
                        # Create new attachment with the uploaded file
                        new_attachment = Attachment(
                            filename=os.path.basename(new_file_path),
                            file_path=new_file_path,
                            statutory_document_id=document.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(new_attachment)
                    except Exception as e:
                        flash(f'Error replacing attachment: {str(e)}', 'warning')
        
        # Handle file uploads
        if has_files and request.files:
            for file in request.files.getlist('attachments'):
                if file and file.filename:
                    file_path = save_uploaded_file(file)
                    if file_path:
                        attachment = Attachment(
                            filename=file.filename,
                            file_path=file_path,
                            statutory_document_id=document.id,
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
        
        db.session.commit()
        flash('Statutory Document updated successfully!', 'success')
        return redirect(url_for('main.statutory_document_view', id=document.id))
    
    return render_template('pages/statutory_document_form.html', form=form, document=document, title='Edit Statutory Document')

# ============ Delete Routes ============
@main_bp.route('/nfa/<int:id>/delete', methods=['POST'])
@login_required
def nfa_delete(id):
    """Delete an NFA document"""
    nfa = NFA.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if nfa.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.nfa_view', id=id))
    
    db.session.delete(nfa)
    db.session.commit()
    flash('NFA deleted successfully!', 'success')
    return redirect(url_for('main.nfa_list'))

@main_bp.route('/work-orders/<int:id>/delete', methods=['POST'])
@login_required
def work_order_delete(id):
    """Delete a Work Order document"""
    work_order = WorkOrder.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if work_order.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.work_order_view', id=id))
    
    db.session.delete(work_order)
    db.session.commit()
    flash('Work Order deleted successfully!', 'success')
    return redirect(url_for('main.work_order_list'))

@main_bp.route('/cost-contracts/<int:id>/delete', methods=['POST'])
@login_required
def cost_contract_delete(id):
    """Delete a Cost Contract document"""
    contract = CostContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if contract.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.cost_contract_view', id=id))
    
    db.session.delete(contract)
    db.session.commit()
    flash('Cost Contract deleted successfully!', 'success')
    return redirect(url_for('main.cost_contract_list'))

@main_bp.route('/revenue-contracts/<int:id>/delete', methods=['POST'])
@login_required
def revenue_contract_delete(id):
    """Delete a Revenue Contract document"""
    contract = RevenueContract.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if contract.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.revenue_contract_view', id=id))
    
    db.session.delete(contract)
    db.session.commit()
    flash('Revenue Contract deleted successfully!', 'success')
    return redirect(url_for('main.revenue_contract_list'))

@main_bp.route('/agreements/<int:id>/delete', methods=['POST'])
@login_required
def agreement_delete(id):
    """Delete an Agreement document"""
    agreement = Agreement.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if agreement.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.agreement_view', id=id))
    
    db.session.delete(agreement)
    db.session.commit()
    flash('Agreement deleted successfully!', 'success')
    return redirect(url_for('main.agreement_list'))

@main_bp.route('/statutory-documents/<int:id>/delete', methods=['POST'])
@login_required
def statutory_document_delete(id):
    """Delete a Statutory Document"""
    document = StatutoryDocument.query.get_or_404(id)
    user_roles = [role.name for role in current_user.roles]
    
    if document.status == 'Approved' and 'admin' not in user_roles:
        flash('Cannot delete an approved document', 'danger')
        return redirect(url_for('main.statutory_document_view', id=id))
    
    db.session.delete(document)
    db.session.commit()
    flash('Statutory Document deleted successfully!', 'success')
    return redirect(url_for('main.statutory_document_list'))

# Download attachment
from flask import send_file
import os

@main_bp.route('/attachment/<int:attachment_id>/download', methods=['GET'])
@login_required
def download_attachment(attachment_id):
    """Download an attachment file"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Check if file exists
    if not os.path.exists(attachment.file_path):
        flash('File not found', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    try:
        return send_file(
            attachment.file_path,
            as_attachment=True,
            download_name=attachment.filename
        )
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))

@main_bp.route('/attachment/upload', methods=['POST'])
@login_required
def upload_attachment():
    """Handle AJAX file uploads for edit forms - file only saved temporarily"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part'}), 400
        
        file = request.files['file']
        document_id = request.form.get('document_id')
        document_type = request.form.get('document_type')
        old_attachment_id = request.form.get('old_attachment_id')
        
        if not file or not document_id or not document_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Save file temporarily
        file_path = save_uploaded_file(file)
        if not file_path:
            return jsonify({'success': False, 'message': 'Failed to save file'}), 500
        
        return jsonify({
            'success': True, 
            'filename': file.filename,
            'file_path': file_path,
            'old_attachment_id': old_attachment_id
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500




@main_bp.route('/attachment/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    """Delete an attachment and return to the referrer"""
    attachment = Attachment.query.get_or_404(attachment_id)
    
    # Delete physical file if it exists
    if os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except Exception as e:
            flash(f'Error deleting file: {str(e)}', 'warning')
    
    # Delete from database
    db.session.delete(attachment)
    db.session.commit()
    
    flash('Attachment deleted successfully!', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))
