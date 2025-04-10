from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from api.models import db, Room, Reservation
from datetime import datetime
from functools import wraps

rooms_bp = Blueprint('rooms', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acesso negado. Você precisa ser um administrador.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@rooms_bp.route('/')
@login_required
def list():
    """List all available rooms"""
    rooms = Room.query.filter_by(status='available').all()
    return render_template('rooms/list.html', rooms=rooms)

@rooms_bp.route('/<int:room_id>')
@login_required
def details(room_id):
    """Show room details and availability"""
    room = Room.query.get_or_404(room_id)
    
    # Get room's reservations for the next 7 days
    upcoming_reservations = Reservation.query.filter_by(
        room_id=room_id,
        status='confirmed'
    ).filter(
        Reservation.start_time >= datetime.now()
    ).order_by(Reservation.start_time).all()
    
    return render_template('rooms/details.html', room=room, reservations=upcoming_reservations)

@rooms_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Create a new room (admin only)"""
    if request.method == 'POST':
        name = request.form['name']
        capacity = request.form['capacity']
        description = request.form['description']
        image_url = request.form['image_url']
        
        new_room = Room(
            name=name,
            capacity=capacity,
            description=description,
            image_url=image_url,
            status='available'
        )
        
        try:
            db.session.add(new_room)
            db.session.commit()
            flash('Sala criada com sucesso!', 'success')
            return redirect(url_for('rooms.list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar sala. Por favor, tente novamente.', 'error')
            return redirect(url_for('rooms.create'))
    
    return render_template('rooms/create.html')

@rooms_bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(room_id):
    """Edit an existing room (admin only)"""
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        room.name = request.form['name']
        room.capacity = request.form['capacity']
        room.description = request.form['description']
        room.image_url = request.form['image_url']
        room.status = request.form['status']
        
        try:
            db.session.commit()
            flash('Sala atualizada com sucesso!', 'success')
            return redirect(url_for('rooms.details', room_id=room.id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar sala. Por favor, tente novamente.', 'error')
    
    return render_template('rooms/edit.html', room=room)

@rooms_bp.route('/<int:room_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(room_id):
    """Delete a room (admin only)"""
    room = Room.query.get_or_404(room_id)
    
    try:
        db.session.delete(room)
        db.session.commit()
        flash('Sala removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover sala. Por favor, tente novamente.', 'error')
    
    return redirect(url_for('rooms.list'))

@rooms_bp.route('/check-availability', methods=['POST'])
@login_required
def check_availability():
    """Check room availability for a specific time slot"""
    room_id = request.form.get('room_id')
    start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
    
    # Check if there are any conflicting reservations
    conflicting_reservations = Reservation.query.filter_by(
        room_id=room_id,
        status='confirmed'
    ).filter(
        (Reservation.start_time <= end_time) & (Reservation.end_time >= start_time)
    ).first()
    
    return jsonify({
        'available': not conflicting_reservations,
        'message': 'Sala disponível' if not conflicting_reservations else 'Sala já reservada para este horário'
    })
