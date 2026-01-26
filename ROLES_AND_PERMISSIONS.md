# Role-Based Access Control System

## Overview
A comprehensive role-based user management system with three default roles: **Admin**, **HOD**, and **Employee**.

## Roles & Permissions

### 1. **Admin** (Full Control)
- ✅ User management (create, edit, delete, deactivate users)
- ✅ Role and permission management
- ✅ Access to admin dashboard
- ✅ Full document access (create, edit, approve, reject)
- ✅ View reports
- ✅ System configuration

**Permissions**: `user_view`, `user_create`, `user_edit`, `user_delete`, `document_view`, `document_create`, `document_edit`, `document_approve`, `document_reject`, `admin_access`, `role_manage`, `reports_view`

### 2. **HOD** (Head of Department)
- ✅ Create and edit documents
- ✅ Approve/reject documents
- ✅ View reports
- ❌ Cannot manage users or roles
- ❌ Cannot access admin panel

**Permissions**: `document_view`, `document_create`, `document_edit`, `document_approve`, `document_reject`, `reports_view`

### 3. **Employee** (Basic User)
- ✅ Create and edit own documents
- ✅ View documents
- ✅ View reports
- ❌ Cannot approve documents
- ❌ Cannot manage users

**Permissions**: `document_view`, `document_create`, `document_edit`, `reports_view`

## Default Credentials

```
Username: admin
Password: admin123
Role: Admin
```

⚠️ **Change this password immediately after first login!**

## Files Created/Modified

### New Files
- `routes/admin.py` - Admin panel routes (user, role management)
- `templates/admin/dashboard.html` - Admin dashboard
- `templates/admin/user_list.html` - User list and search
- `templates/admin/user_form.html` - User create/edit form
- `templates/admin/role_list.html` - Role list view
- `templates/admin/role_view.html` - Role permission editor
- `templates/admin/settings.html` - Settings page
- `init_roles.py` - Script to initialize roles and permissions

### Modified Files
- `app.py` - Added admin blueprint registration
- `utils/__init__.py` - Added `require_permission()` and `require_role()` decorators
- `templates/index.html` - Added admin link in navbar (visible only to admins)

## Admin Features

### User Management
1. **List Users** - `/admin/users`
   - Search and filter users
   - View user details and assigned roles
   - Pagination support (20 users per page)

2. **Create User** - `/admin/users/create`
   - Create new user with username, email, name
   - Assign roles at creation time
   - Automatic password hashing

3. **Edit User** - `/admin/users/<user_id>/edit`
   - Modify user information
   - Change assigned roles
   - Reset password
   - Activate/deactivate account

4. **Toggle Active Status** - `/admin/users/<user_id>/toggle`
   - Deactivate users (prevent login without deletion)
   - Reactivate deactivated users

5. **Delete User** - `/admin/users/<user_id>/delete`
   - Permanently remove user from system
   - Confirmation required

### Role Management
1. **View Roles** - `/admin/roles`
   - See all available roles
   - View permissions per role
   - See number of users per role

2. **Edit Role Permissions** - `/admin/roles/<role_id>/edit`
   - Add/remove permissions from a role
   - Modify role description
   - Automatically updates for all users with that role

## Usage Guide

### For Admin Users
1. Login with admin account
2. Click "⚙️ Admin" link in navbar
3. Navigate to:
   - **User Management** - Create/edit/delete users
   - **Role Management** - Configure roles and permissions
   - **Settings** - System configuration

### For HOD Users
1. Login with HOD account
2. Access to document management (all modules)
3. Can approve/reject documents
4. No access to admin panel

### For Employee Users
1. Login with employee account
2. Can create and manage own documents
3. Cannot approve documents
4. Cannot access admin panel

## API Endpoints

### Admin Routes
| Method | Endpoint | Permission | Description |
|--------|----------|-----------|-------------|
| GET | `/admin/dashboard` | admin | Admin dashboard |
| GET | `/admin/users` | admin | List users |
| GET | `/admin/users/create` | admin | User create form |
| POST | `/admin/users/create` | admin | Create user |
| GET | `/admin/users/<id>/edit` | admin | User edit form |
| POST | `/admin/users/<id>/edit` | admin | Update user |
| POST | `/admin/users/<id>/toggle` | admin | Toggle active status |
| POST | `/admin/users/<id>/delete` | admin | Delete user |
| GET | `/admin/roles` | admin | List roles |
| GET | `/admin/roles/<id>` | admin | View role |
| POST | `/admin/roles/<id>/edit` | admin | Update role |
| GET | `/admin/settings` | admin | Settings page |

## Access Control Implementation

### Decorators
The system uses two decorators for access control:

```python
from utils import require_permission, require_role

# Check for specific permission
@require_permission('admin_access')
def admin_only():
    pass

# Check for specific role
@require_role('admin')
def admins_only():
    pass
```

### User Methods
```python
# Check if user has permission
user.has_permission('admin_access')  # Returns True/False

# Get user roles
user.roles  # Returns list of Role objects

# Get role permissions
role.permissions  # Returns list of Permission objects
```

## Security Features

1. **Password Hashing** - All passwords are hashed using Werkzeug
2. **Admin Protection** - Cannot delete or deactivate the only active admin
3. **Unique Constraints** - Username and email are unique
4. **Session Management** - Flask-Login handles user sessions
5. **CSRF Protection** - Built-in with Flask-WTF

## Testing the System

### Test Scenario 1: Admin User
```
1. Login as admin / admin123
2. Click ⚙️ Admin in navbar
3. Navigate User Management
4. Create new user with HOD or Employee role
5. Edit user roles
```

### Test Scenario 2: HOD User
```
1. Create HOD user via admin panel
2. Login as HOD user
3. No ⚙️ Admin link visible
4. Can create/approve documents
```

### Test Scenario 3: Employee User
```
1. Create Employee user via admin panel
2. Login as Employee
3. Can create documents
4. Cannot approve documents
```

## Permission System

Permissions are stored in the database and can be extended:

```python
Permission(
    name='custom_permission',
    description='Custom permission description'
)
```

Then assign to roles:
```python
role.permissions.append(permission)
db.session.commit()
```

## Future Enhancements

- [ ] Email notifications on user/role changes
- [ ] Audit logs for admin actions
- [ ] Two-factor authentication
- [ ] IP-based access control
- [ ] Permission hierarchy/inheritance
- [ ] Role templates for quick setup
- [ ] Bulk user import (CSV)
- [ ] User activity tracking

## Troubleshooting

### 403 Forbidden Error
- User doesn't have required permission/role
- Check user roles in User Management
- Verify permission is assigned to role

### Admin Link Not Showing
- User doesn't have `admin_access` permission
- Assign user to Admin role

### Cannot Deactivate Admin
- System prevents deactivating only active admin
- Create another admin user first, then deactivate

## Files Reference

- `models/__init__.py` - User, Role, Permission models
- `routes/admin.py` - All admin routes
- `templates/admin/` - Admin interface templates
- `init_roles.py` - Initialize default roles/permissions
- `utils/__init__.py` - Access control decorators

---

**Last Updated:** January 25, 2026
**Version:** 1.0.0
