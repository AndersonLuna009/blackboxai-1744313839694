from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from api.models import db, Reservation, Room, Notification
from datetime import datetime
from functools import wraps

reservations_bp = Blueprint('reservations', __name__)

@reservations_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create a new reservation"""
    room_id = request.form.get('room_id')
    start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
    description = request.form.get('description')
    
    # Validate input
    if not all([room_id, start_time, end_time]):
        flash('Todos os campos são obrigatórios.', 'error')
        return redirect(url_for('rooms.details', room_id=room_id))
    
    # Check if room exists and is available
    room = Room.query.get_or_404(room_id)
    if room.status != 'available':
        flash('Esta sala não está disponível para reservas.', 'error')
        return redirect(url_for('rooms.details', room_id=room_id))
    
    # Check for conflicting reservations
    conflicting_reservation = Reservation.query.filter_by(
        room_id=room_id,
        status='confirmed'
    ).filter(
        (Reservation.start_time <= end_time) & (Reservation.end_time >= start_time)
    ).first()
    
    if conflicting_reservation:
        flash('Esta sala já está reservada para o horário selecionado.', 'error')
        return redirect(url_for('rooms.details', room_id=room_id))
    
    # Create reservation
    new_reservation = Reservation(
        user_id=current_user.id,
        room_id=room_id,
        start_time=start_time,
        end_time=end_time,
        status='confirmed'
    )
    
    try:
        db.session.add(new_reservation)
        
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            message=f'Sua reserva para a sala {room.name} foi confirmada para {start_time.strftime("%d/%m/%Y %H:%M")}.'
        )
        db.session.add(notification)
        
        db.session.commit()
        flash('Reserva criada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao criar reserva. Por favor, tente novamente.', 'error')
    
    return redirect(url_for('rooms.details', room_id=room_id))

@reservations_bp.route('/my-reservations')
@login_required
def my_reservations():
    """List user's reservations"""
    active_reservations = Reservation.query.filter_by(
        user_id=current_user.id,
        status='confirmed'
    ).filter(
        Reservation.end_time >= datetime.now()
    ).order_by(Reservation.start_time).all()
    
    past_reservations = Reservation.query.filter_by(
        user_id=current_user.id
    ).filter(
        Reservation.end_time < datetime.now()
    ).order_by(Reservation.start_time.desc()).limit(5).all()
    
    return render_template('reservations/my_reservations.html',
                         active_reservations=active_reservations,
                         past_reservations=past_reservations)

@reservations_bp.route('/<int:reservation_id>/cancel', methods=['POST'])
@login_required
def cancel(reservation_id):
    """Cancel a reservation"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check if user is authorized to cancel
    if reservation.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Não autorizado'}), 403
    
    # Check if reservation can be cancelled (not in the past)
    if reservation.start_time < datetime.now():
        return jsonify({'error': 'Não é possível cancelar reservas passadas'}), 400
    
    try:
        reservation.status = 'cancelled'
        
        # Create notification
        notification = Notification(
            user_id=reservation.user_id,
            message=f'Sua reserva para a sala {reservation.room.name} em {reservation.start_time.strftime("%d/%m/%Y %H:%M")} foi cancelada.'
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({'message': 'Reserva cancelada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao cancelar reserva'}), 500

@reservations_bp.route('/admin')
@login_required
def admin_view():
    """Admin view of all reservations"""
    if not current_user.is_admin:
        flash('Acesso negado. Você precisa ser um administrador.', 'error')
        return redirect(url_for('index'))
    
    reservations = Reservation.query.order_by(Reservation.start_time.desc()).all()
    return render_template('reservations/admin.html', reservations=reservations)
