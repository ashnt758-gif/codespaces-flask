from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, NFA, WorkOrder, CostContract, RevenueContract, Agreement, StatutoryDocument, Attachment, ApprovalHistory
from forms import NFAForm, WorkOrderForm, CostContractForm, RevenueContractForm, AgreementForm, StatutoryDocumentForm, ApprovalForm
from utils import save_uploaded_file, get_next_reference_number, WorkflowEngine
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

# Dashboard
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get statistics
    nfa_count = NFA.query.count()
    work_order_count = WorkOrder.query.count()
    cost_contract_count = CostContract.query.count()
    revenue_contract_count = RevenueContract.query.count()
    agreement_count = Agreement.query.count()
    statutory_doc_count = StatutoryDocument.query.count()
    
    pending_approvals = ApprovalHistory.query.filter(
        ApprovalHistory.action == 'Submitted'
    ).count()
    
    stats = {
        'nfa': nfa_count,
        'work_orders': work_order_count,
        'cost_contracts': cost_contract_count,
        'revenue_contracts': revenue_contract_count,
        'agreements': agreement_count,
        'statutory_docs': statutory_doc_count,
        'pending_approvals': pending_approvals
    }
    
    return render_template('dashboard.html', stats=stats)

# ============ NFA Routes ============
@main_bp.route('/nfa', methods=['GET'])
@login_required
def nfa_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = NFA.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(NFA.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    
    return render_template('pages/nfa_list.html', items=items)

@main_bp.route('/nfa/create', methods=['GET', 'POST'])
@login_required
def nfa_create():
    form = NFAForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('NFA')
        nfa = NFA(
            reference_number=reference_number,
            title=form.title.data,
            amount=form.amount.data,
            description=form.description.data,
            approval_date=form.approval_date.data,
            notes=form.notes.data,
            created_by_id=current_user.id
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
    can_edit = nfa.status == 'Draft' and (nfa.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    
    return render_template('pages/nfa_view.html', nfa=nfa, approvals=approvals, can_edit=can_edit)

@main_bp.route('/nfa/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def nfa_edit(id):
    nfa = NFA.query.get_or_404(id)
    
    if nfa.status != 'Draft':
        flash('Cannot edit a document that is not in Draft status', 'warning')
        return redirect(url_for('main.nfa_view', id=id))
    
    form = NFAForm()
    if form.validate_on_submit():
        nfa.title = form.title.data
        nfa.amount = form.amount.data
        nfa.description = form.description.data
        nfa.approval_date = form.approval_date.data
        nfa.notes = form.notes.data
        
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
        flash('NFA updated successfully!', 'success')
        return redirect(url_for('main.nfa_view', id=nfa.id))
    
    elif request.method == 'GET':
        form.title.data = nfa.title
        form.amount.data = nfa.amount
        form.description.data = nfa.description
        form.approval_date.data = nfa.approval_date
        form.notes.data = nfa.notes
    
    return render_template('pages/nfa_form.html', form=form, nfa=nfa, title='Edit NFA')

@main_bp.route('/nfa/<int:id>/submit', methods=['POST'])
@login_required
def nfa_submit(id):
    nfa = NFA.query.get_or_404(id)
    
    if nfa.status != 'Draft':
        flash('Document is not in Draft status', 'warning')
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
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(WorkOrder.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    
    return render_template('pages/work_order_list.html', items=items)

@main_bp.route('/work-orders/create', methods=['GET', 'POST'])
@login_required
def work_order_create():
    form = WorkOrderForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('WorkOrder')
        work_order = WorkOrder(
            reference_number=reference_number,
            title=form.title.data,
            po_number=form.po_number.data,
            vendor_name=form.vendor_name.data,
            amount=form.amount.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            created_by_id=current_user.id
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
    can_edit = work_order.status == 'Draft' and (work_order.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    
    return render_template('pages/work_order_view.html', work_order=work_order, approvals=approvals, can_edit=can_edit)

@main_bp.route('/work-orders/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def work_order_edit(id):
    work_order = WorkOrder.query.get_or_404(id)
    
    if work_order.status != 'Draft':
        flash('Cannot edit a document that is not in Draft status', 'warning')
        return redirect(url_for('main.work_order_view', id=id))
    
    form = WorkOrderForm()
    if form.validate_on_submit():
        work_order.title = form.title.data
        work_order.po_number = form.po_number.data
        work_order.vendor_name = form.vendor_name.data
        work_order.amount = form.amount.data
        work_order.start_date = form.start_date.data
        work_order.end_date = form.end_date.data
        work_order.description = form.description.data
        
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
        flash('Work Order updated successfully!', 'success')
        return redirect(url_for('main.work_order_view', id=work_order.id))
    
    elif request.method == 'GET':
        form.title.data = work_order.title
        form.po_number.data = work_order.po_number
        form.vendor_name.data = work_order.vendor_name
        form.amount.data = work_order.amount
        form.start_date.data = work_order.start_date
        form.end_date.data = work_order.end_date
        form.description.data = work_order.description
    
    return render_template('pages/work_order_form.html', form=form, work_order=work_order, title='Edit Work Order')

@main_bp.route('/work-orders/<int:id>/submit', methods=['POST'])
@login_required
def work_order_submit(id):
    work_order = WorkOrder.query.get_or_404(id)
    
    if work_order.status != 'Draft':
        flash('Document is not in Draft status', 'warning')
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
@main_bp.route('/cost-contracts', methods=['GET'])
@login_required
def cost_contract_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = CostContract.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(CostContract.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/cost_contract_list.html', items=items)

@main_bp.route('/cost-contracts/create', methods=['GET', 'POST'])
@login_required
def cost_contract_create():
    form = CostContractForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('CostContract')
        contract = CostContract(
            reference_number=reference_number,
            title=form.title.data,
            contract_type=form.contract_type.data,
            vendor_name=form.vendor_name.data,
            contract_value=form.contract_value.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            created_by_id=current_user.id
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
    can_edit = contract.status == 'Draft' and (contract.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    return render_template('pages/cost_contract_view.html', contract=contract, approvals=approvals, can_edit=can_edit)

# ============ Revenue Contract Routes ============
@main_bp.route('/revenue-contracts', methods=['GET'])
@login_required
def revenue_contract_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = RevenueContract.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(RevenueContract.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/revenue_contract_list.html', items=items)

@main_bp.route('/revenue-contracts/create', methods=['GET', 'POST'])
@login_required
def revenue_contract_create():
    form = RevenueContractForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('RevenueContract')
        contract = RevenueContract(
            reference_number=reference_number,
            title=form.title.data,
            customer_name=form.customer_name.data,
            contract_value=form.contract_value.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            terms=form.terms.data,
            description=form.description.data,
            created_by_id=current_user.id
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
    can_edit = contract.status == 'Draft' and (contract.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    return render_template('pages/revenue_contract_view.html', contract=contract, approvals=approvals, can_edit=can_edit)

# ============ Agreement Routes ============
@main_bp.route('/agreements', methods=['GET'])
@login_required
def agreement_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = Agreement.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Agreement.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/agreement_list.html', items=items)

@main_bp.route('/agreements/create', methods=['GET', 'POST'])
@login_required
def agreement_create():
    form = AgreementForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('Agreement')
        agreement = Agreement(
            reference_number=reference_number,
            title=form.title.data,
            agreement_type=form.agreement_type.data,
            party_name=form.party_name.data,
            effective_date=form.effective_date.data,
            expiry_date=form.expiry_date.data,
            description=form.description.data,
            created_by_id=current_user.id
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
    can_edit = agreement.status == 'Draft' and (agreement.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    return render_template('pages/agreement_view.html', agreement=agreement, approvals=approvals, can_edit=can_edit)

# ============ Statutory Document Routes ============
@main_bp.route('/statutory-documents', methods=['GET'])
@login_required
def statutory_document_list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = StatutoryDocument.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(StatutoryDocument.title.ilike(f'%{search}%'))
    
    items = query.paginate(page=page, per_page=20)
    return render_template('pages/statutory_document_list.html', items=items)

@main_bp.route('/statutory-documents/create', methods=['GET', 'POST'])
@login_required
def statutory_document_create():
    form = StatutoryDocumentForm()
    if form.validate_on_submit():
        reference_number = get_next_reference_number('StatutoryDocument')
        document = StatutoryDocument(
            reference_number=reference_number,
            title=form.title.data,
            document_type=form.document_type.data,
            regulatory_body=form.regulatory_body.data,
            due_date=form.due_date.data,
            description=form.description.data,
            created_by_id=current_user.id
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
    can_edit = document.status == 'Draft' and (document.created_by_id == current_user.id or current_user.has_permission('edit_all'))
    return render_template('pages/statutory_document_view.html', document=document, approvals=approvals, can_edit=can_edit)
