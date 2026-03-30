from werkzeug.security import generate_password_hash

password = 'admin'
password_hash = generate_password_hash(password)
print(f"Password hash: {password_hash}")
print(f"\nSQL to update database:")
print(f"UPDATE users SET password_hash = '{password_hash}' WHERE username = 'admin';")
