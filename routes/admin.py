from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Role, Permission
from utils import require_role
from sqlalchemy import func
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin dashboard
@admin_bp.route('/dashboard')
@login_required
@require_role('admin')
def admin_dashboard():
    """Admin dashboard with statistics"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_roles = Role.query.count()
    total_permissions = Permission.query.count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'total_roles': total_roles,
        'total_permissions': total_permissions
    }
    
    return render_template('admin/dashboard.html', stats=stats)

# ============ User Management Routes ============

@admin_bp.route('/users', methods=['GET'])
@login_required
@require_role('admin')
def user_list():
    """List all users with pagination and search"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%'))
        )
    
    users = query.paginate(page=page, per_page=20)
    
    return render_template('admin/user_list.html', users=users, search=search)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def user_create():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '').strip()
        role_ids = request.form.getlist('roles')
        
        # Validation
        if not username or not email or not password:
            flash('Username, email, and password are required', 'danger')
            return redirect(url_for('admin.user_create'))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.user_create'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.user_create'))
        
        # Create user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        user.set_password(password)
        
        # Assign roles
        for role_id in role_ids:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {username} created successfully', 'success')
        return redirect(url_for('admin.user_list'))
    
    roles = Role.query.all()
    return render_template('admin/user_form.html', roles=roles, action='Create')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def user_edit(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.email = request.form.get('email', '').strip()
        user.is_active = request.form.get('is_active') == 'on'
        
        # Check email uniqueness
        existing_email = User.query.filter_by(email=user.email).filter(User.id != user_id).first()
        if existing_email:
            flash('Email already in use by another user', 'danger')
            return redirect(url_for('admin.user_edit', user_id=user_id))
        
        # Update roles
        role_ids = request.form.getlist('roles')
        user.roles.clear()
        for role_id in role_ids:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
        
        # Update password if provided
        password = request.form.get('password', '').strip()
        if password:
            user.set_password(password)
        
        db.session.commit()
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('admin.user_list'))
    
    roles = Role.query.all()
    user_role_ids = [role.id for role in user.roles]
    
    return render_template('admin/user_form.html', 
                         user=user, 
                         roles=roles, 
                         user_role_ids=user_role_ids,
                         action='Edit')

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@require_role('admin')
def user_toggle_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating the only admin
    if user.is_active:
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role and admin_role in user.roles:
            active_admins = User.query.filter_by(is_active=True).join(User.roles).filter(Role.name == 'admin').count()
            if active_admins <= 1:
                flash('Cannot deactivate the only active admin user', 'warning')
                return redirect(url_for('admin.user_list'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} {status}', 'success')
    return redirect(url_for('admin.user_list'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@require_role('admin')
def user_delete(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    username = user.username
    
    # Prevent deleting the only admin
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role and admin_role in user.roles:
        active_admins = User.query.filter_by(is_active=True).join(User.roles).filter(Role.name == 'admin').count()
        if active_admins <= 1:
            flash('Cannot delete the only active admin user', 'warning')
            return redirect(url_for('admin.user_list'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully', 'success')
    return redirect(url_for('admin.user_list'))

# ============ Role Management Routes ============

@admin_bp.route('/roles', methods=['GET'])
@login_required
@require_role('admin')
def role_list():
    """List all roles"""
    roles = Role.query.all()
    return render_template('admin/role_list.html', roles=roles)

@admin_bp.route('/roles/<int:role_id>', methods=['GET'])
@login_required
@require_role('admin')
def role_view(role_id):
    """View role details"""
    role = Role.query.get_or_404(role_id)
    all_permissions = Permission.query.all()
    role_permission_ids = [perm.id for perm in role.permissions]
    
    return render_template('admin/role_view.html', 
                         role=role, 
                         all_permissions=all_permissions,
                         role_permission_ids=role_permission_ids)

@admin_bp.route('/roles/<int:role_id>/edit', methods=['POST'])
@login_required
@require_role('admin')
def role_edit(role_id):
    """Edit role permissions"""
    role = Role.query.get_or_404(role_id)
    
    # Update description
    role.description = request.form.get('description', '').strip()
    
    # Update permissions
    permission_ids = request.form.getlist('permissions')
    role.permissions.clear()
    for perm_id in permission_ids:
        perm = Permission.query.get(perm_id)
        if perm:
            role.permissions.append(perm)
    
    db.session.commit()
    flash(f'Role {role.name} updated successfully', 'success')
    return redirect(url_for('admin.role_list'))

# ============ Settings Routes ============

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def settings():
    """Admin settings page"""
    if request.method == 'POST':
        # Add any global settings here
        flash('Settings updated successfully', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html')
