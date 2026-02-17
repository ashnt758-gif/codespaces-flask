"""
Initialize roles and permissions in the database.
Run this after first setup: python init_roles.py
"""
from app import create_app
from models import db, Role, Permission, User

def init_roles_and_permissions():
    """Initialize default roles and permissions"""
    app = create_app()
    
    with app.app_context():
        # Clear existing roles and permissions (optional - comment out if you want to preserve)
        # db.session.query(Role).delete()
        # db.session.query(Permission).delete()
        # db.session.commit()
        
        # Define permissions
        permissions_data = [
            ('user_view', 'View users'),
            ('user_create', 'Create users'),
            ('user_edit', 'Edit users'),
            ('user_delete', 'Delete users'),
            ('document_view', 'View documents'),
            ('document_create', 'Create documents'),
            ('document_edit', 'Edit own documents'),
            ('document_edit_all', 'Edit all documents'),
            ('document_approve', 'Approve documents'),
            ('document_reject', 'Reject documents'),
            ('document_submit', 'Submit documents for approval'),
            ('admin_access', 'Admin panel access'),
            ('role_manage', 'Manage roles'),
            ('reports_view', 'View reports'),
            ('audit_view', 'View audit logs'),
            ('workflow_manage', 'Manage workflows'),
        ]
        
        # Create permissions
        permissions = {}
        for perm_name, perm_desc in permissions_data:
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name, description=perm_desc)
                db.session.add(perm)
            permissions[perm_name] = perm
        
        db.session.commit()
        
        # Define roles - ONLY 3 ROLES: admin, hod, emp
        roles_data = {
            'admin': {
                'description': 'Administrator with full system access',
                'permissions': [
                    'user_view', 'user_create', 'user_edit', 'user_delete',
                    'document_view', 'document_create', 'document_edit_all', 'document_approve', 'document_reject',
                    'document_submit', 'admin_access', 'role_manage', 'reports_view', 'audit_view', 'workflow_manage'
                ]
            },
            'hod': {
                'description': 'Head of Department - Can approve documents and manage team',
                'permissions': [
                    'document_view', 'document_create', 'document_edit', 'document_approve',
                    'document_reject', 'document_submit', 'reports_view', 'audit_view'
                ]
            },
            'emp': {
                'description': 'Regular employee - Can create and view own documents',
                'permissions': [
                    'document_view', 'document_create', 'document_edit', 'document_submit', 'reports_view'
                ]
            }
        }
        
        # Create roles
        for role_name, role_data in roles_data.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(
                    name=role_name,
                    description=role_data['description']
                )
                # Add permissions to role
                for perm_name in role_data['permissions']:
                    if perm_name in permissions:
                        role.permissions.append(permissions[perm_name])
                db.session.add(role)
            
        db.session.commit()
        
        # Create default admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@kspl.com',
                first_name='System',
                last_name='Administrator',
                is_active=True
            )
            admin.set_password('admin123')  # Change this password!
            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role:
                admin.roles.append(admin_role)
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created: admin / admin123")
        else:
            print("✓ Admin user already exists")
        
        print("✓ Roles and permissions initialized successfully!")
        print("\nRoles created (3 roles only):")
        print("  - Admin (Full control)")
        print("  - HOD (Head of Department - Can approve documents)")
        print("  - Emp (Employee - Can create and manage own documents)")

if __name__ == '__main__':
    init_roles_and_permissions()
