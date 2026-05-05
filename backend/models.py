from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20), nullable=False, default='student')
    organization = db.Column(db.String(100))
    student_or_staff_id = db.Column(db.String(50))
    avatar_url = db.Column(db.Text)
    account_status = db.Column(db.String(20), nullable=False, default='active')
    register_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    last_login_time = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    extra_fields = db.Column(db.JSON)

class Event(db.Model):
    __tablename__ = 'events'
    
    event_id = db.Column(db.BigInteger, primary_key=True)
    event_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='ongoing')
    event_start_time = db.Column(db.DateTime(timezone=True))
    event_end_time = db.Column(db.DateTime(timezone=True))
    upload_start_time = db.Column(db.DateTime(timezone=True))
    upload_end_time = db.Column(db.DateTime(timezone=True))
    creator_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    leader_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'))
    total_budget = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    reimbursed_amount = db.Column(db.Numeric(12, 2), default=0.00)
    remaining_budget = db.Column(db.Numeric(12, 2), default=0.00)
    invoice_count = db.Column(db.Integer, default=0)
    invoice_total_amount = db.Column(db.Numeric(12, 2), default=0.00)
    voucher_count = db.Column(db.Integer, default=0)
    voucher_total_amount = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    extra_fields = db.Column(db.JSON)
    need_invoice_review = db.Column(db.Boolean, default=True)
    
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_events')
    leader = db.relationship('User', foreign_keys=[leader_id], backref='led_events')

class EventMember(db.Model):
    __tablename__ = 'event_members'
    
    id = db.Column(db.BigInteger, primary_key=True)
    event_id = db.Column(db.BigInteger, db.ForeignKey('events.event_id'), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    role_in_event = db.Column(db.String(20), nullable=False)
    join_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    
    event = db.relationship('Event', backref='members')
    user = db.relationship('User', backref='event_memberships')
    
    __table_args__ = (db.UniqueConstraint('event_id', 'user_id'),)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    invoice_id = db.Column(db.BigInteger, primary_key=True)
    event_id = db.Column(db.BigInteger, db.ForeignKey('events.event_id'), nullable=False)
    uploader_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_md5 = db.Column(db.String(64))
    image_url = db.Column(db.Text, nullable=False)
    preview_image_url = db.Column(db.Text)
    invoice_type = db.Column(db.String(50))
    invoice_number = db.Column(db.String(50))
    project_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='approved')
    is_reimbursed = db.Column(db.Boolean, default=False)
    reimbursed_at = db.Column(db.DateTime(timezone=True))
    reviewer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'))
    review_time = db.Column(db.DateTime(timezone=True))
    rejection_reason = db.Column(db.Text)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    extra_fields = db.Column(db.JSON)
    
    event = db.relationship('Event', backref='invoices')
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_invoices')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_invoices')

class Voucher(db.Model):
    __tablename__ = 'vouchers'
    
    voucher_id = db.Column(db.BigInteger, primary_key=True)
    event_id = db.Column(db.BigInteger, db.ForeignKey('events.event_id'), nullable=False)
    uploader_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_md5 = db.Column(db.String(64))
    file_url = db.Column(db.Text, nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    voucher_type = db.Column(db.String(50))
    purchase_channel = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    is_reimbursed = db.Column(db.Boolean, default=False)
    reimbursed_at = db.Column(db.DateTime(timezone=True))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    
    event = db.relationship('Event', backref='vouchers')
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_vouchers')

class InvitationCode(db.Model):
    __tablename__ = 'invitation_codes'
    
    id = db.Column(db.BigInteger, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    target_user_type = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    max_uses = db.Column(db.Integer, default=-1)
    used_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_invitation_codes')

class PurchaseRecord(db.Model):
    __tablename__ = 'purchase_records'
    
    record_id = db.Column(db.BigInteger, primary_key=True)
    event_id = db.Column(db.BigInteger, db.ForeignKey('events.event_id'), nullable=False)
    uploader_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    
    item_name = db.Column(db.String(200), nullable=False)
    purchase_platform = db.Column(db.String(100), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    
    receipt_image_url = db.Column(db.Text, nullable=False)
    receipt_image_name = db.Column(db.String(255))
    receipt_file_md5 = db.Column(db.String(64))
    
    has_invoice = db.Column(db.Boolean, default=False)
    invoice_file_key = db.Column(db.Text)
    invoice_preview_key = db.Column(db.Text)
    invoice_original_filename = db.Column(db.String(255))
    invoice_md5 = db.Column(db.String(64))
    invoice_type = db.Column(db.String(50))
    invoice_number = db.Column(db.String(50))
    total_amount = db.Column(db.Numeric(12, 2), default=0.00)
    invoice_date = db.Column(db.Date)
    
    status = db.Column(db.String(20), nullable=False, default='pending')
    is_reimbursed = db.Column(db.Boolean, default=False)
    reimbursed_at = db.Column(db.DateTime(timezone=True))
    reviewer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'))
    review_time = db.Column(db.DateTime(timezone=True))
    rejection_reason = db.Column(db.Text)
    
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    extra_fields = db.Column(db.JSON)
    
    event = db.relationship('Event', backref='purchase_records')
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_purchase_records')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_purchase_records')
